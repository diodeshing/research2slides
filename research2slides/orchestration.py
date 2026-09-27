from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping

from research2slides.artifacts import write_text
from research2slides.exceptions import ArtifactError, InputError, QualityAssuranceError
from research2slides.models import LanguageProfile, PresentationMode, QAStatus
from research2slides.pipeline import parse_sources
from research2slides.planning.pipeline import run_planning
from research2slides.planning.providers import StorylineProvider
from research2slides.qa.pipeline import run_quality_assurance
from research2slides.qa.semantic import SemanticQAProvider
from research2slides.rendering import run_renderer
from research2slides.slide_authoring.pipeline import run_slide_authoring
from research2slides.slide_authoring.providers import SlideSpecProvider
from research2slides.understanding.pipeline import run_understanding
from research2slides.understanding.providers import UnderstandingProvider


BUILD_VERSION = "phase9-v1"
BUILD_STEPS = ("parse", "understand", "plan", "spec", "render", "qa", "package")


@dataclass(frozen=True)
class BuildOptions:
    mode: PresentationMode = PresentationMode.PAPER_READING
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS
    theme: str = "group-meeting"
    time_budget_seconds: int | None = None
    render_qa: bool = True
    render_backend: str = "auto"
    repair: bool = True
    max_repair_iterations: int = 2
    semantic_qa: bool = False
    force: bool = False
    resume_from: str | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash_path(digest: "hashlib._Hash", path: Path | None) -> None:
    if path is None:
        digest.update(b"none")
        return
    resolved = path.resolve()
    digest.update(str(resolved).encode("utf-8"))
    if resolved.is_file():
        digest.update(resolved.read_bytes())
        return
    if resolved.is_dir():
        for item in sorted(candidate for candidate in resolved.rglob("*") if candidate.is_file()):
            digest.update(item.relative_to(resolved).as_posix().encode("utf-8"))
            digest.update(item.read_bytes())
        return
    raise InputError(f"Build input does not exist: {resolved}")


def _fingerprint(
    pdf: Path,
    latex: Path | None,
    understanding_provider: UnderstandingProvider,
    storyline_provider: StorylineProvider,
    slide_spec_provider: SlideSpecProvider,
    semantic_qa_provider: SemanticQAProvider | None,
    options: BuildOptions,
) -> str:
    digest = hashlib.sha256()
    digest.update(BUILD_VERSION.encode("utf-8"))
    _hash_path(digest, pdf)
    _hash_path(digest, latex)
    digest.update(understanding_provider.cache_key().encode("ascii"))
    digest.update(storyline_provider.cache_key().encode("ascii"))
    digest.update(slide_spec_provider.cache_key().encode("ascii"))
    digest.update(
        semantic_qa_provider.cache_key().encode("ascii")
        if semantic_qa_provider is not None
        else b"semantic-qa-disabled"
    )
    digest.update(options.mode.value.encode("utf-8"))
    digest.update(options.language_profile.value.encode("utf-8"))
    digest.update(options.theme.encode("utf-8"))
    digest.update(str(options.time_budget_seconds).encode("ascii"))
    digest.update(str(options.render_qa).encode("ascii"))
    digest.update(options.render_backend.encode("utf-8"))
    digest.update(str(options.repair).encode("ascii"))
    digest.update(str(options.max_repair_iterations).encode("ascii"))
    digest.update(str(options.semantic_qa).encode("ascii"))
    return digest.hexdigest()


def _new_checkpoint(
    fingerprint: str,
    pdf: Path,
    latex: Path | None,
    workspace: Path,
    options: BuildOptions,
) -> dict[str, object]:
    created = _now()
    return {
        "schema_version": "1.0",
        "build_version": BUILD_VERSION,
        "fingerprint": fingerprint,
        "status": "running",
        "created_at": created,
        "updated_at": created,
        "workspace": str(workspace),
        "inputs": {
            "pdf": str(pdf.resolve()),
            "latex": str(latex.resolve()) if latex else None,
        },
        "configuration": {
            "mode": options.mode.value,
            "language_profile": options.language_profile.value,
            "theme": options.theme,
            "time_budget_seconds": options.time_budget_seconds,
            "render_qa": options.render_qa,
            "render_backend": options.render_backend,
            "repair": options.repair,
            "max_repair_iterations": options.max_repair_iterations,
            "semantic_qa": options.semantic_qa,
        },
        "steps": {
            name: {"status": "pending", "started_at": None, "finished_at": None, "details": {}}
            for name in BUILD_STEPS
        },
    }


def _write_checkpoint(path: Path, checkpoint: dict[str, object]) -> None:
    checkpoint["updated_at"] = _now()
    write_text(path, json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n")


def _load_checkpoint(path: Path, fingerprint: str) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"Invalid build checkpoint {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise ArtifactError(f"Invalid build checkpoint {path}: unsupported schema")
    if payload.get("fingerprint") != fingerprint:
        return None
    steps = payload.get("steps")
    if not isinstance(steps, dict) or any(name not in steps for name in BUILD_STEPS):
        raise ArtifactError(f"Invalid build checkpoint {path}: missing build steps")
    return payload


def _expected_artifacts(
    workspace: Path,
    step: str,
    render_qa: bool,
    semantic_qa: bool,
) -> list[Path]:
    data = workspace / "data"
    output = workspace / "output"
    delivery = workspace / "delivery"
    artifacts = {
        "parse": [data / "paper_structure.json", data / "visual_manifest.json", data / "source_manifest.json"],
        "understand": [data / "scientific_understanding.json", data / "evidence_graph.json"],
        "plan": [data / "presentation_plan.full.json", data / "presentation_plan.json"],
        "spec": [data / "slide_spec.json", workspace / "speaker_notes.md", workspace / "presentation_outline.md"],
        "render": [output / "presentation.pptx"],
        "qa": [output / "quality_report.json", output / "quality_report.md"],
        "package": [delivery / "presentation.pptx", delivery / "speaker_notes.md", delivery / "presentation_outline.md", delivery / "quality_report.md"],
    }
    required = list(artifacts[step])
    if step in {"qa", "package"} and render_qa:
        required.append((output if step == "qa" else delivery) / "presentation.pdf")
    if step in {"qa", "package"} and semantic_qa:
        required.append((data if step == "qa" else delivery) / "semantic_qa.json")
    return required


def _artifacts_exist(workspace: Path, step: str, render_qa: bool, semantic_qa: bool) -> bool:
    return all(
        path.is_file()
        for path in _expected_artifacts(workspace, step, render_qa, semantic_qa)
    )


def _package_outputs(workspace: Path) -> dict[str, object]:
    delivery = workspace / "delivery"
    delivery.mkdir(parents=True, exist_ok=True)
    candidates = {
        "presentation.pptx": workspace / "output" / "presentation.pptx",
        "presentation.pdf": workspace / "output" / "presentation.pdf",
        "speaker_notes.md": workspace / "speaker_notes.md",
        "presentation_outline.md": workspace / "presentation_outline.md",
        "quality_report.md": workspace / "output" / "quality_report.md",
        "quality_report.json": workspace / "output" / "quality_report.json",
        "semantic_qa.json": workspace / "data" / "semantic_qa.json",
    }
    copied: list[str] = []
    for name, source in candidates.items():
        if source.is_file():
            target = delivery / name
            shutil.copy2(source, target)
            copied.append(str(target))
    if not (delivery / "presentation.pptx").is_file():
        raise ArtifactError("Build packaging did not receive presentation.pptx")
    return {"delivery_dir": str(delivery), "files": copied}


def run_build(
    pdf: Path,
    workspace: Path,
    *,
    latex: Path | None,
    understanding_provider: UnderstandingProvider,
    storyline_provider: StorylineProvider,
    slide_spec_provider: SlideSpecProvider,
    options: BuildOptions,
    semantic_qa_provider: SemanticQAProvider | None = None,
    handlers: Mapping[str, Callable[[], dict[str, object]]] | None = None,
) -> dict[str, object]:
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    if options.theme not in {"conference-minimal", "group-meeting"}:
        raise InputError("theme must be conference-minimal or group-meeting")
    if options.resume_from is not None and options.resume_from not in BUILD_STEPS:
        raise InputError(f"resume_from must be one of: {', '.join(BUILD_STEPS)}")
    if options.semantic_qa != (semantic_qa_provider is not None):
        raise InputError("semantic_qa option and semantic_qa_provider must be enabled together")
    fingerprint = _fingerprint(
        pdf,
        latex,
        understanding_provider,
        storyline_provider,
        slide_spec_provider,
        semantic_qa_provider,
        options,
    )
    checkpoint_path = workspace / "build_checkpoint.json"
    checkpoint = None if options.force else _load_checkpoint(checkpoint_path, fingerprint)
    if checkpoint is None:
        checkpoint = _new_checkpoint(fingerprint, pdf, latex, workspace, options)
    steps = checkpoint["steps"]
    assert isinstance(steps, dict)

    if options.resume_from:
        resume_index = BUILD_STEPS.index(options.resume_from)
        for name in BUILD_STEPS[:resume_index]:
            if not _artifacts_exist(workspace, name, options.render_qa, options.semantic_qa):
                raise ArtifactError(f"Cannot resume from {options.resume_from}: {name} artifacts are missing")
            steps[name]["status"] = "completed"
        for name in BUILD_STEPS[resume_index:]:
            steps[name] = {"status": "pending", "started_at": None, "finished_at": None, "details": {}}

    def parse_handler() -> dict[str, object]:
        paper, visuals, sources, resumed = parse_sources(pdf, workspace, latex, force=options.force)
        return {
            "status": "reused" if resumed else "generated",
            "paper_id": paper.paper_id,
            "pages": paper.page_count,
            "assets": len(visuals.assets),
            "source_fingerprint": sources.combined_sha256,
        }

    def understand_handler() -> dict[str, object]:
        understanding, graph, resumed = run_understanding(
            workspace, understanding_provider, force=options.force
        )
        return {
            "status": "reused" if resumed else "generated",
            "paper_id": understanding.paper_id,
            "evidence_nodes": len(graph.nodes),
        }

    def plan_handler() -> dict[str, object]:
        plan, full, resumed = run_planning(
            workspace,
            storyline_provider,
            options.mode,
            time_budget_seconds=options.time_budget_seconds,
            force=options.force,
            language_profile=options.language_profile,
        )
        return {
            "status": "reused" if resumed else "generated",
            "full_units": len(full.units),
            "selected_units": len(plan.units),
            "estimated_seconds": plan.estimated_total_seconds,
        }

    def spec_handler() -> dict[str, object]:
        spec, resumed = run_slide_authoring(
            workspace, slide_spec_provider, options.theme, force=options.force
        )
        return {"status": "reused" if resumed else "generated", "slides": len(spec.slides)}

    def render_handler() -> dict[str, object]:
        return run_renderer(workspace, force=options.force)

    def qa_handler() -> dict[str, object]:
        report = run_quality_assurance(
            workspace,
            render_artifacts=options.render_qa,
            render_backend=options.render_backend,
            repair=options.repair,
            max_iterations=options.max_repair_iterations,
            force=options.force,
            semantic_provider=semantic_qa_provider,
        )
        if report.status == QAStatus.FAIL:
            raise QualityAssuranceError("Build stopped because QA status is fail")
        return {
            "status": report.status.value,
            "issues": len(report.issues),
            "repairs": len(report.repairs),
        }

    default_handlers: dict[str, Callable[[], dict[str, object]]] = {
        "parse": parse_handler,
        "understand": understand_handler,
        "plan": plan_handler,
        "spec": spec_handler,
        "render": render_handler,
        "qa": qa_handler,
        "package": lambda: _package_outputs(workspace),
    }
    selected_handlers = dict(default_handlers)
    if handlers:
        selected_handlers.update(handlers)

    checkpoint["status"] = "running"
    _write_checkpoint(checkpoint_path, checkpoint)
    for name in BUILD_STEPS:
        step = steps[name]
        if step.get("status") == "completed" and _artifacts_exist(
            workspace, name, options.render_qa, options.semantic_qa
        ):
            continue
        step["status"] = "running"
        step["started_at"] = _now()
        step["finished_at"] = None
        step["details"] = {}
        _write_checkpoint(checkpoint_path, checkpoint)
        try:
            details = selected_handlers[name]()
            if not _artifacts_exist(workspace, name, options.render_qa, options.semantic_qa):
                missing = [
                    str(path)
                    for path in _expected_artifacts(
                        workspace, name, options.render_qa, options.semantic_qa
                    )
                    if not path.is_file()
                ]
                raise ArtifactError(f"Build step {name} did not create required artifacts: {missing}")
        except Exception as exc:
            step["status"] = "failed"
            step["finished_at"] = _now()
            step["details"] = {"error": str(exc)}
            checkpoint["status"] = "failed"
            checkpoint["failed_step"] = name
            _write_checkpoint(checkpoint_path, checkpoint)
            raise
        step["status"] = "completed"
        step["finished_at"] = _now()
        step["details"] = details
        checkpoint.pop("failed_step", None)
        _write_checkpoint(checkpoint_path, checkpoint)

    checkpoint["status"] = "completed"
    checkpoint["completed_at"] = _now()
    _write_checkpoint(checkpoint_path, checkpoint)
    shutil.copy2(checkpoint_path, workspace / "delivery" / "build_checkpoint.json")
    return {
        "status": "completed",
        "workspace": str(workspace),
        "checkpoint": str(checkpoint_path),
        "delivery_dir": str(workspace / "delivery"),
        "steps": {name: steps[name]["status"] for name in BUILD_STEPS},
    }
