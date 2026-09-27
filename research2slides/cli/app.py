from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from research2slides import __version__
from research2slides.artifacts import read_model
from research2slides.doctor import doctor_report
from research2slides.exceptions import Research2SlidesError
from research2slides.pipeline import parse_sources
from research2slides.models import LanguageProfile, PresentationMode, PresentationPlan, QAStatus
from research2slides.orchestration import BuildOptions, run_build
from research2slides.planning.pipeline import run_planning
from research2slides.planning.providers import JsonStorylineProvider, OpenAIStorylineProvider
from research2slides.prompting import load_prompt
from research2slides.rendering import run_renderer
from research2slides.qa.pipeline import run_quality_assurance
from research2slides.qa.semantic import JsonSemanticQAProvider, OpenAISemanticQAProvider
from research2slides.slide_authoring.pipeline import run_slide_authoring
from research2slides.slide_authoring.providers import JsonSlideSpecProvider, OpenAISlideSpecProvider
from research2slides.understanding.pipeline import run_understanding
from research2slides.understanding.providers import JsonDraftProvider, OpenAIResponsesProvider


app = typer.Typer(
    no_args_is_help=True,
    help="Build source-grounded research presentation artifacts one validated phase at a time.",
)


@app.callback()
def main() -> None:
    """Research2Slides command group."""


@app.command("version")
def version_command() -> None:
    """Print the installed Research2Slides version."""
    typer.echo(__version__)


@app.command("doctor")
def doctor_command(
    require_renderer: Annotated[
        bool,
        typer.Option("--require-renderer", help="Fail when Node renderer assets are unavailable"),
    ] = False,
) -> None:
    """Check Python core, prompt assets, Node, npm, and renderer availability."""
    report = doctor_report()
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["core_ready"] or (require_renderer and not report["renderer_ready"]):
        raise typer.Exit(code=1)


@app.command("build")
def build_command(
    pdf: Annotated[Path, typer.Argument(help="Paper PDF")],
    latex: Annotated[
        Path | None,
        typer.Option("--latex", help="LaTeX source directory, ZIP, TAR, TAR.GZ, or TGZ"),
    ] = None,
    workspace: Annotated[Path, typer.Option("--workspace", "-w", help="Build workspace")] = Path("workspace"),
    mode: Annotated[PresentationMode, typer.Option("--mode")] = PresentationMode.PAPER_READING,
    language_profile: Annotated[
        LanguageProfile, typer.Option("--language-profile")
    ] = LanguageProfile.ZH_CN_BILINGUAL_TERMS,
    theme: Annotated[str | None, typer.Option("--theme")] = None,
    time_minutes: Annotated[
        float | None, typer.Option("--time-minutes", min=1.0)
    ] = None,
    analysis_draft: Annotated[Path | None, typer.Option("--analysis-draft")] = None,
    storyline_draft: Annotated[Path | None, typer.Option("--storyline-draft")] = None,
    slide_spec_draft: Annotated[Path | None, typer.Option("--slide-spec-draft")] = None,
    semantic_qa_draft: Annotated[Path | None, typer.Option("--semantic-qa-draft")] = None,
    semantic_qa: Annotated[bool, typer.Option("--semantic-qa/--no-semantic-qa")] = False,
    model: Annotated[str, typer.Option("--model")] = "gpt-5.6-sol",
    reasoning_effort: Annotated[str, typer.Option("--reasoning-effort")] = "high",
    base_url: Annotated[str, typer.Option("--base-url")] = "https://api.openai.com/v1",
    api_key_env: Annotated[str, typer.Option("--api-key-env")] = "OPENAI_API_KEY",
    render_qa: Annotated[bool, typer.Option("--render-qa/--no-render-qa")] = True,
    render_backend: Annotated[str, typer.Option("--render-backend")] = "auto",
    repair: Annotated[bool, typer.Option("--repair/--no-repair")] = True,
    max_iterations: Annotated[int, typer.Option("--max-iterations", min=0, max=5)] = 2,
    resume_from: Annotated[str | None, typer.Option("--resume-from")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Run parse through QA and package the final presentation in one resumable build."""
    understanding_provider = (
        JsonDraftProvider(analysis_draft)
        if analysis_draft
        else OpenAIResponsesProvider(
            prompt=load_prompt("understand-paper.md"),
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    )
    storyline_provider = (
        JsonStorylineProvider(storyline_draft)
        if storyline_draft
        else OpenAIStorylineProvider(
            prompt=load_prompt(
                    "paper-reading-storyline.md"
                    if mode == PresentationMode.PAPER_READING
                    else "own-research-storyline.md"
            ),
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    )
    slide_spec_provider = (
        JsonSlideSpecProvider(slide_spec_draft)
        if slide_spec_draft
        else OpenAISlideSpecProvider(
            prompt="\n\n".join(
                [
                    load_prompt("plan-slides.md"),
                    load_prompt(
                            "paper-reading-slides.md"
                            if mode == PresentationMode.PAPER_READING
                            else "own-research-slides.md"
                    ),
                ]
            ),
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    )
    semantic_provider = None
    if semantic_qa_draft:
        semantic_provider = JsonSemanticQAProvider(semantic_qa_draft)
    elif semantic_qa:
        semantic_provider = OpenAISemanticQAProvider(
            prompt=load_prompt("semantic-qa.md"),
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    selected_theme = theme or (
        "group-meeting" if mode == PresentationMode.PAPER_READING else "conference-minimal"
    )
    try:
        payload = run_build(
            pdf,
            workspace,
            latex=latex,
            understanding_provider=understanding_provider,
            storyline_provider=storyline_provider,
            slide_spec_provider=slide_spec_provider,
            options=BuildOptions(
                mode=mode,
                language_profile=language_profile,
                theme=selected_theme,
                time_budget_seconds=round(time_minutes * 60) if time_minutes else None,
                render_qa=render_qa,
                render_backend=render_backend,
                repair=repair,
                max_repair_iterations=max_iterations,
                semantic_qa=semantic_provider is not None,
                force=force,
                resume_from=resume_from,
            ),
            semantic_qa_provider=semantic_provider,
        )
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command("parse")
def parse_command(
    pdf: Annotated[Path, typer.Argument(help="Paper PDF")],
    latex: Annotated[
        Path | None,
        typer.Option("--latex", help="LaTeX source directory, ZIP, TAR, TAR.GZ, or TGZ"),
    ] = None,
    workspace: Annotated[Path, typer.Option("--workspace", "-w", help="Artifact workspace")] = Path("workspace"),
    force: Annotated[bool, typer.Option("--force", help="Regenerate Phase 1 artifacts")] = False,
) -> None:
    """Parse PDF/LaTeX into Phase 1 structured artifacts."""
    try:
        paper, visuals, sources, resumed = parse_sources(pdf, workspace, latex, force)
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(
        json.dumps(
            {
                "status": "reused" if resumed else "generated",
                "paper_id": paper.paper_id,
                "pages": paper.page_count,
                "sections": len(paper.sections),
                "assets": len(visuals.assets),
                "source_fingerprint": sources.combined_sha256,
                "workspace": str(workspace.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("render")
def render_command(
    workspace: Annotated[Path, typer.Argument(help="Workspace containing Phase 4 data/")],
    output: Annotated[Path | None, typer.Option("--output", help="Optional PPTX output path")] = None,
    force: Annotated[bool, typer.Option("--force", help="Ignore a matching render manifest")] = False,
) -> None:
    """Render the complete slide spec to an editable PowerPoint deck."""
    try:
        payload = run_renderer(workspace, output=output, force=force)
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command("rerender")
def rerender_command(
    workspace: Annotated[Path, typer.Argument(help="Workspace containing Phase 4 data/")],
    slides: Annotated[str, typer.Option("--slides", help="Original slide numbers, for example 2,4,5")],
    output: Annotated[Path | None, typer.Option("--output", help="Optional partial PPTX output path")] = None,
    force: Annotated[bool, typer.Option("--force", help="Ignore a matching render manifest")] = False,
) -> None:
    """Render selected original slides to a review deck."""
    try:
        payload = run_renderer(workspace, output=output, slides=slides, force=force)
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command("qa")
def qa_command(
    workspace: Annotated[Path, typer.Argument(help="Workspace containing rendered Phase 5 artifacts")],
    pptx: Annotated[Path | None, typer.Option("--pptx", help="Optional PPTX to inspect")] = None,
    render_artifacts: Annotated[
        bool,
        typer.Option("--render/--no-render", help="Export PDF and per-slide PNG previews"),
    ] = True,
    render_backend: Annotated[
        str,
        typer.Option("--render-backend", help="auto, windows-com, or soffice"),
    ] = "auto",
    repair: Annotated[
        bool,
        typer.Option("--repair/--no-repair", help="Apply evidence-preserving safe repairs"),
    ] = True,
    max_iterations: Annotated[
        int,
        typer.Option("--max-iterations", min=0, max=5, help="Maximum repair iterations"),
    ] = 2,
    force: Annotated[bool, typer.Option("--force", help="Regenerate PDF, previews, and repaired renders")] = False,
    semantic: Annotated[
        bool,
        typer.Option("--semantic/--no-semantic", help="Run Semantic QA 2.0 with a model provider"),
    ] = False,
    semantic_draft: Annotated[
        Path | None,
        typer.Option("--semantic-draft", help="Offline semantic QA draft JSON; bypasses remote providers"),
    ] = None,
    model: Annotated[str, typer.Option("--model", help="Semantic QA Responses API model ID")] = "gpt-5.6-sol",
    reasoning_effort: Annotated[
        str,
        typer.Option("--reasoning-effort", help="Reasoning effort for Semantic QA"),
    ] = "high",
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="OpenAI-compatible Responses API base URL"),
    ] = "https://api.openai.com/v1",
    api_key_env: Annotated[
        str,
        typer.Option("--api-key-env", help="Environment variable containing the API key"),
    ] = "OPENAI_API_KEY",
) -> None:
    """Run factual, storyline, visual, and presentation QA with a safe repair loop."""
    semantic_provider = None
    if semantic_draft:
        semantic_provider = JsonSemanticQAProvider(semantic_draft)
    elif semantic:
        semantic_provider = OpenAISemanticQAProvider(
            prompt=load_prompt("semantic-qa.md"),
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    try:
        report = run_quality_assurance(
            workspace,
            pptx=pptx,
            render_artifacts=render_artifacts,
            render_backend=render_backend,
            repair=repair,
            max_iterations=max_iterations,
            force=force,
            semantic_provider=semantic_provider,
        )
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(
        json.dumps(
            {
                "status": report.status.value,
                "slides": report.slide_count,
                "issues": len(report.issues),
                "errors": sum(item.severity.value == "error" for item in report.issues),
                "warnings": sum(item.severity.value == "warning" for item in report.issues),
                "repair_iterations": len(report.repairs),
                "pptx": report.artifacts.pptx,
                "pdf": report.artifacts.pdf,
                "preview_dir": report.artifacts.preview_dir,
                "quality_report": str((workspace.resolve() / "output" / "quality_report.md")),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if report.status == QAStatus.FAIL:
        raise typer.Exit(code=1)


@app.command("understand")
def understand_command(
    workspace: Annotated[Path, typer.Argument(help="Workspace containing Phase 1 data/")],
    draft: Annotated[
        Path | None,
        typer.Option("--draft", help="Offline analysis draft JSON; bypasses remote providers"),
    ] = None,
    model: Annotated[str, typer.Option("--model", help="Responses API model ID")] = "gpt-5.6-sol",
    reasoning_effort: Annotated[
        str,
        typer.Option("--reasoning-effort", help="Reasoning effort for the provider"),
    ] = "high",
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="OpenAI-compatible Responses API base URL"),
    ] = "https://api.openai.com/v1",
    api_key_env: Annotated[
        str,
        typer.Option("--api-key-env", help="Environment variable containing the API key"),
    ] = "OPENAI_API_KEY",
    force: Annotated[bool, typer.Option("--force", help="Regenerate Phase 2 artifacts")] = False,
) -> None:
    """Build source-grounded scientific understanding and an evidence graph."""
    if draft:
        provider = JsonDraftProvider(draft)
    else:
        provider = OpenAIResponsesProvider(
            prompt=load_prompt("understand-paper.md"),
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    try:
        understanding, graph, resumed = run_understanding(workspace, provider, force)
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    supported = sum(
        answer["status"] == "supported"
        for answer in understanding.answers.model_dump().values()
    )
    typer.echo(
        json.dumps(
            {
                "status": "reused" if resumed else "generated",
                "paper_id": understanding.paper_id,
                "evidence_nodes": len(graph.nodes),
                "evidence_edges": len(graph.edges),
                "supported_questions": supported,
                "provider": understanding.provenance.provider,
                "model": understanding.provenance.model,
                "workspace": str(workspace.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("plan")
def plan_command(
    workspace: Annotated[Path, typer.Argument(help="Workspace containing Phase 2 data/")],
    mode: Annotated[
        PresentationMode,
        typer.Option("--mode", help="Presentation mode"),
    ] = PresentationMode.PAPER_READING,
    language_profile: Annotated[
        LanguageProfile,
        typer.Option("--language-profile", help="Presentation language policy"),
    ] = LanguageProfile.ZH_CN_BILINGUAL_TERMS,
    draft: Annotated[
        Path | None,
        typer.Option("--draft", help="Offline storyline draft JSON; bypasses remote providers"),
    ] = None,
    time_minutes: Annotated[
        float | None,
        typer.Option("--time-minutes", min=1.0, help="Optional target duration; full plan is retained"),
    ] = None,
    model: Annotated[str, typer.Option("--model", help="Responses API model ID")] = "gpt-5.6-sol",
    reasoning_effort: Annotated[
        str,
        typer.Option("--reasoning-effort", help="Reasoning effort for the provider"),
    ] = "high",
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="OpenAI-compatible Responses API base URL"),
    ] = "https://api.openai.com/v1",
    api_key_env: Annotated[
        str,
        typer.Option("--api-key-env", help="Environment variable containing the API key"),
    ] = "OPENAI_API_KEY",
    force: Annotated[bool, typer.Option("--force", help="Regenerate Phase 3 artifacts")] = False,
) -> None:
    """Build a Clarity First presentation storyline and presentation plan."""
    if draft:
        provider = JsonStorylineProvider(draft)
    else:
        prompt_name = (
            "paper-reading-storyline.md"
            if mode == PresentationMode.PAPER_READING
            else "own-research-storyline.md"
        )
        provider = OpenAIStorylineProvider(
            prompt=load_prompt(prompt_name),
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    budget_seconds = round(time_minutes * 60) if time_minutes is not None else None
    try:
        plan, full, resumed = run_planning(
            workspace,
            provider,
            mode,
            time_budget_seconds=budget_seconds,
            force=force,
            language_profile=language_profile,
        )
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(
        json.dumps(
            {
                "status": "reused" if resumed else "generated",
                "paper_id": plan.paper_id,
                "mode": plan.mode.value,
                "language_profile": plan.language_profile.value,
                "full_units": len(full.units),
                "selected_units": len(plan.units),
                "estimated_seconds": plan.estimated_total_seconds,
                "coverage_gaps": plan.coverage_gaps,
                "compressed": plan.compression is not None and bool(plan.compression.omitted_unit_ids),
                "provider": plan.provenance.provider,
                "model": plan.provenance.model,
                "workspace": str(workspace.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command("spec")
def spec_command(
    workspace: Annotated[Path, typer.Argument(help="Workspace containing Phase 3 data/")],
    draft: Annotated[
        Path | None,
        typer.Option("--draft", help="Offline slide-spec draft JSON; bypasses remote providers"),
    ] = None,
    theme: Annotated[
        str | None,
        typer.Option("--theme", help="conference-minimal or group-meeting"),
    ] = None,
    model: Annotated[str, typer.Option("--model", help="Responses API model ID")] = "gpt-5.6-sol",
    reasoning_effort: Annotated[
        str,
        typer.Option("--reasoning-effort", help="Reasoning effort for the provider"),
    ] = "high",
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="OpenAI-compatible Responses API base URL"),
    ] = "https://api.openai.com/v1",
    api_key_env: Annotated[
        str,
        typer.Option("--api-key-env", help="Environment variable containing the API key"),
    ] = "OPENAI_API_KEY",
    force: Annotated[bool, typer.Option("--force", help="Regenerate Phase 4 artifacts")] = False,
) -> None:
    """Convert a presentation plan into slide specs and speaker notes."""
    try:
        plan = read_model(workspace.resolve() / "data" / "presentation_plan.json", PresentationPlan)
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    selected_theme = theme or (
        "group-meeting" if plan.mode == PresentationMode.PAPER_READING else "conference-minimal"
    )
    if selected_theme not in {"conference-minimal", "group-meeting"}:
        raise typer.BadParameter("theme must be conference-minimal or group-meeting", param_hint="--theme")
    if draft:
        provider = JsonSlideSpecProvider(draft)
    else:
        mode_prompt = (
            "paper-reading-slides.md"
            if plan.mode == PresentationMode.PAPER_READING
            else "own-research-slides.md"
        )
        prompt = "\n\n".join(
            [
                load_prompt("plan-slides.md"),
                load_prompt(mode_prompt),
            ]
        )
        provider = OpenAISlideSpecProvider(
            prompt=prompt,
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
        )
    try:
        spec, resumed = run_slide_authoring(
            workspace,
            provider,
            selected_theme,
            force=force,
        )
    except Research2SlidesError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(
        json.dumps(
            {
                "status": "reused" if resumed else "generated",
                "paper_id": spec.paper_id,
                "mode": spec.mode.value,
                "theme": spec.theme,
                "language_profile": spec.language_profile.value,
                "slides": len(spec.slides),
                "estimated_seconds": spec.estimated_total_seconds,
                "speaker_notes": str((workspace.resolve() / "speaker_notes.md")),
                "presentation_outline": str((workspace.resolve() / "presentation_outline.md")),
                "workspace": str(workspace.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    app()
