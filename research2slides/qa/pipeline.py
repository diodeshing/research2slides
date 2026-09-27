from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from research2slides.artifacts import read_model, write_model, write_text
from research2slides.exceptions import QualityAssuranceError, Research2SlidesError
from research2slides.models import (
    EvidenceGraph,
    PaperStructure,
    PresentationPlan,
    QACategory,
    QAArtifactPaths,
    QAIssue,
    QAIteration,
    QAProvenance,
    QASeverity,
    QualityReport,
    Repairability,
    SlideSpec,
    VisualManifest,
)
from research2slides.narration.speaker_notes import render_presentation_outline, render_speaker_notes
from research2slides.qa.common import category_result, issue, overall_status
from research2slides.qa.factual import check_factual
from research2slides.qa.presentation import check_presentation
from research2slides.qa.rendering import export_pptx_to_pdf, render_pdf_previews
from research2slides.qa.repair import apply_safe_repairs
from research2slides.qa.report import render_quality_report
from research2slides.qa.semantic import SemanticQAProvider, run_semantic_qa
from research2slides.qa.storyline import check_storyline
from research2slides.qa.visual import inspect_visuals
from research2slides.rendering import run_renderer


QA_VERSION = "phase9-v1"
CHECK_NAMES = [
    "factual-evidence-v1",
    "storyline-sequence-v1",
    "pptx-geometry-preview-v1",
    "presentation-notes-v1",
]
SEMANTIC_CHECK_NAMES = [
    "semantic-claim-evidence-v1",
    "semantic-claim-strength-v1",
    "semantic-storyline-dependency-v1",
]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    digest.update(QA_VERSION.encode("utf-8"))
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(_hash_file(path).encode("ascii"))
    return digest.hexdigest()


def _load_inputs(workspace: Path) -> tuple[SlideSpec, PresentationPlan, EvidenceGraph, PaperStructure, VisualManifest]:
    data_dir = workspace / "data"
    return (
        read_model(data_dir / "slide_spec.json", SlideSpec),
        read_model(data_dir / "presentation_plan.json", PresentationPlan),
        read_model(data_dir / "evidence_graph.json", EvidenceGraph),
        read_model(data_dir / "paper_structure.json", PaperStructure),
        read_model(data_dir / "visual_manifest.json", VisualManifest),
    )


def _render_artifacts(
    pptx_path: Path,
    output_dir: Path,
    *,
    render_backend: str,
    force: bool,
) -> tuple[Path | None, Path | None, str, list[QAIssue]]:
    pdf_path = output_dir / "presentation.pdf"
    preview_dir = output_dir / "preview"
    try:
        backend = export_pptx_to_pdf(pptx_path, pdf_path, backend=render_backend, force=force)
        render_pdf_previews(pdf_path, preview_dir)
        return pdf_path, preview_dir, backend, []
    except QualityAssuranceError as exc:
        finding = issue(
            QACategory.VISUAL,
            "RENDER_INSPECT_UNAVAILABLE",
            QASeverity.ERROR,
            f"无法完成 PPTX → PDF → PNG：{exc}",
            repairability=Repairability.NONE,
            suggested_action="安装可用的 PowerPoint/LibreOffice 与 PyMuPDF 后重新运行 qa。",
        )
        return None, None, "unavailable", [finding]


def _collect_issues(
    workspace: Path,
    pptx_path: Path,
    preview_dir: Path | None,
    spec: SlideSpec,
    plan: PresentationPlan,
    graph: EvidenceGraph,
    paper: PaperStructure,
    visuals: VisualManifest,
    render_issues: list[QAIssue],
    semantic_issues: list[QAIssue],
    semantic_check_counts: dict[QACategory, int],
) -> tuple[list[QAIssue], dict[QACategory, int]]:
    factual, factual_checks = check_factual(spec, graph, paper, visuals, workspace)
    storyline, storyline_checks = check_storyline(plan, spec)
    visual, visual_checks, _ = inspect_visuals(pptx_path, spec, preview_dir)
    presentation, presentation_checks = check_presentation(plan, spec)
    issues = [*factual, *storyline, *semantic_issues, *visual, *render_issues, *presentation]
    unique = {item.issue_id: item for item in issues}
    return list(unique.values()), {
        QACategory.FACTUAL: factual_checks + semantic_check_counts.get(QACategory.FACTUAL, 0),
        QACategory.STORYLINE: storyline_checks + semantic_check_counts.get(QACategory.STORYLINE, 0),
        QACategory.VISUAL: visual_checks + (1 if render_issues else 0),
        QACategory.PRESENTATION: presentation_checks,
    }


def run_quality_assurance(
    workspace: Path,
    *,
    pptx: Path | None = None,
    render_artifacts: bool = True,
    render_backend: str = "auto",
    repair: bool = True,
    max_iterations: int = 2,
    force: bool = False,
    semantic_provider: SemanticQAProvider | None = None,
) -> QualityReport:
    workspace = workspace.resolve()
    if max_iterations < 0 or max_iterations > 5:
        raise QualityAssuranceError("max_iterations must be between 0 and 5")
    output_dir = workspace / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    pptx_path = (pptx or output_dir / "presentation.pptx").resolve()
    if not pptx_path.is_file():
        try:
            run_renderer(workspace, output=pptx_path, force=True)
        except Research2SlidesError as exc:
            raise QualityAssuranceError(f"Unable to create the deck required for QA: {exc}") from exc

    spec, plan, graph, paper, visuals = _load_inputs(workspace)
    semantic_issues: list[QAIssue] = []
    semantic_check_counts: dict[QACategory, int] = {}
    semantic_path: Path | None = None
    if semantic_provider is not None:
        _, semantic_issues, semantic_check_counts, _ = run_semantic_qa(
            workspace,
            spec,
            plan,
            graph,
            semantic_provider,
            force=force,
        )
        semantic_path = workspace / "data" / "semantic_qa.json"
    pdf_path: Path | None = None
    preview_dir: Path | None = None
    backend = "not-run"
    render_issues: list[QAIssue] = []
    if render_artifacts:
        pdf_path, preview_dir, backend, render_issues = _render_artifacts(
            pptx_path,
            output_dir,
            render_backend=render_backend,
            force=force,
        )

    issues, check_counts = _collect_issues(
        workspace,
        pptx_path,
        preview_dir,
        spec,
        plan,
        graph,
        paper,
        visuals,
        render_issues,
        semantic_issues,
        semantic_check_counts,
    )
    repairs: list[QAIteration] = []
    targeted_review: Path | None = None
    for iteration in range(1, max_iterations + 1):
        if not repair:
            break
        repaired_spec, actions = apply_safe_repairs(spec, issues)
        if not actions:
            break
        before_count = len(issues)
        source_spec = workspace / "data" / "slide_spec.json"
        backup_spec = workspace / "data" / "slide_spec.pre-qa.json"
        if not backup_spec.exists():
            shutil.copy2(source_spec, backup_spec)
        write_model(source_spec, repaired_spec)
        write_text(workspace / "speaker_notes.md", render_speaker_notes(repaired_spec))
        write_text(workspace / "presentation_outline.md", render_presentation_outline(repaired_spec))
        slide_numbers = sorted(
            slide.order
            for slide in repaired_spec.slides
            if slide.slide_id in {action.slide_id for action in actions}
        )
        targeted_review = output_dir / (
            "qa-review.slides-" + "-".join(str(number) for number in slide_numbers) + ".pptx"
        )
        run_renderer(
            workspace,
            output=targeted_review,
            slides=",".join(str(number) for number in slide_numbers),
            force=True,
        )
        run_renderer(workspace, output=pptx_path, force=True)
        spec = repaired_spec
        if render_artifacts:
            pdf_path, preview_dir, backend, render_issues = _render_artifacts(
                pptx_path,
                output_dir,
                render_backend=render_backend,
                force=True,
            )
        issues, check_counts = _collect_issues(
            workspace,
            pptx_path,
            preview_dir,
            spec,
            plan,
            graph,
            paper,
            visuals,
            render_issues,
            semantic_issues,
            semantic_check_counts,
        )
        repairs.append(
            QAIteration(
                iteration=iteration,
                issue_count_before=before_count,
                issue_count_after=len(issues),
                repaired_slide_numbers=slide_numbers,
                actions=actions,
            )
        )

    fingerprint_paths = [
        workspace / "data" / "slide_spec.json",
        workspace / "data" / "presentation_plan.json",
        workspace / "data" / "evidence_graph.json",
        workspace / "data" / "paper_structure.json",
        workspace / "data" / "visual_manifest.json",
        pptx_path,
    ]
    if semantic_path is not None:
        fingerprint_paths.append(semantic_path)
    status = overall_status(issues)
    report = QualityReport(
        paper_id=spec.paper_id,
        mode=spec.mode,
        theme=spec.theme,
        status=status,
        slide_count=len(spec.slides),
        categories=[category_result(category, issues, check_counts[category]) for category in QACategory],
        issues=issues,
        repairs=repairs,
        artifacts=QAArtifactPaths(
            pptx=str(pptx_path),
            pdf=str(pdf_path) if pdf_path else None,
            preview_dir=str(preview_dir) if preview_dir else None,
            targeted_review_pptx=str(targeted_review) if targeted_review else None,
        ),
        manual_review_required=True,
        limitations=[
            (
                "结构化 Semantic QA 已检查 claim-evidence 蕴含、措辞强度与叙事依赖，"
                "但模型判断仍需人工抽查原文。"
                if semantic_provider is not None
                else "本次未启用结构化 Semantic QA；自动规则不能证明复杂科研 claim 的语义蕴含。"
            ),
            "PNG 的最终审美、讲述节奏和目标机器字体替换仍需要人工逐页检查。",
            "自动 repair 只处理不改变证据的低风险格式问题；证据、数字和源视觉变化必须人工批准。",
        ],
        provenance=QAProvenance(
            qa_version=QA_VERSION,
            input_fingerprint=_fingerprint(fingerprint_paths),
            render_backend=backend,
            checks=[*CHECK_NAMES, *(SEMANTIC_CHECK_NAMES if semantic_provider is not None else [])],
        ),
    )
    write_model(output_dir / "quality_report.json", report)
    write_text(output_dir / "quality_report.md", render_quality_report(report))
    write_text(
        output_dir / "quality_report.manifest.json",
        json.dumps(
            {
                "qa_version": QA_VERSION,
                "input_fingerprint": report.provenance.input_fingerprint,
                "status": report.status.value,
                "quality_report": str(output_dir / "quality_report.json"),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )
    return report
