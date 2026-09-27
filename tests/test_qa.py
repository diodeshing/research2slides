from __future__ import annotations

import json
import shutil
from pathlib import Path

from research2slides.artifacts import read_model, write_model
from research2slides.models import (
    EvidenceGraph,
    PaperStructure,
    PresentationPlan,
    QASeverity,
    Repairability,
    SlideSpec,
    VisualManifest,
)
from research2slides.qa.factual import check_factual
from research2slides.qa.pipeline import run_quality_assurance
from research2slides.qa.presentation import check_presentation
from research2slides.qa.repair import apply_safe_repairs
from research2slides.qa.storyline import check_storyline
from research2slides.qa.visual import inspect_visuals


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT_ROOT / "examples" / "phase5" / "paper-reading"
QA_CASES = json.loads(
    (PROJECT_ROOT / "tests" / "fixtures" / "phase6" / "qa_cases.json").read_text(encoding="utf-8")
)["cases"]


def qa_case(case_id: str) -> dict[str, str]:
    return next(item for item in QA_CASES if item["case_id"] == case_id)


def load_inputs() -> tuple[SlideSpec, PresentationPlan, EvidenceGraph, PaperStructure, VisualManifest]:
    data = WORKSPACE / "data"
    return (
        read_model(data / "slide_spec.json", SlideSpec),
        read_model(data / "presentation_plan.json", PresentationPlan),
        read_model(data / "evidence_graph.json", EvidenceGraph),
        read_model(data / "paper_structure.json", PaperStructure),
        read_model(data / "visual_manifest.json", VisualManifest),
    )


def test_factual_qa_accepts_grounded_fixture() -> None:
    spec, _, graph, paper, visuals = load_inputs()
    issues, checks = check_factual(spec, graph, paper, visuals, WORKSPACE)
    assert checks >= 20
    assert not [item for item in issues if item.severity == QASeverity.ERROR]


def test_factual_qa_rejects_unsupported_number() -> None:
    spec, _, graph, paper, visuals = load_inputs()
    changed = spec.model_copy(deep=True)
    case = qa_case("unsupported-number")
    changed.slides[0].body.append(case["value"])
    issues, _ = check_factual(changed, graph, paper, visuals, WORKSPACE)
    assert case["expected_code"] in {item.code for item in issues}


def test_factual_qa_rejects_citation_source_drift() -> None:
    spec, _, graph, paper, visuals = load_inputs()
    changed = spec.model_copy(deep=True)
    case = qa_case("citation-source-drift")
    changed.slides[0].citations[0].source_ids = [case["value"]]
    issues, _ = check_factual(changed, graph, paper, visuals, WORKSPACE)
    assert case["expected_code"] in {item.code for item in issues}


def test_factual_qa_rejects_generated_experiment_visual() -> None:
    spec, _, graph, paper, visuals = load_inputs()
    changed = spec.model_copy(deep=True)
    visual = changed.slides[3].visuals[0]
    visual.kind = "conceptual_diagram"
    visual.source_ref = changed.slides[3].evidence_ids[0]
    visual.treatment = "diagram"
    issues, _ = check_factual(changed, graph, paper, visuals, WORKSPACE)
    assert "GENERATED_EXPERIMENT_VISUAL" in {item.code for item in issues}


def test_storyline_qa_reports_declared_gap_without_breaking_sequence() -> None:
    spec, plan, _, _, _ = load_inputs()
    issues, checks = check_storyline(plan, spec)
    assert checks >= len(spec.slides)
    assert "DECLARED_COVERAGE_GAP" in {item.code for item in issues}
    assert not [item for item in issues if item.severity == QASeverity.ERROR]


def test_storyline_qa_detects_plan_spec_drift() -> None:
    spec, plan, _, _, _ = load_inputs()
    changed = spec.model_copy(deep=True)
    changed.slides[1].main_claim = "被篡改的主张"
    issues, _ = check_storyline(plan, changed)
    assert "UNIT_CONTENT_DRIFT" in {item.code for item in issues}


def test_presentation_qa_accepts_notes_and_timing() -> None:
    spec, plan, _, _, _ = load_inputs()
    issues, checks = check_presentation(plan, spec)
    assert checks >= 30
    assert not [item for item in issues if item.severity == QASeverity.ERROR]


def test_presentation_qa_detects_notes_drift() -> None:
    spec, plan, _, _, _ = load_inputs()
    changed = spec.model_copy(deep=True)
    changed.slides[0].speaker_notes.main_message = "讲稿与页面不一致"
    issues, _ = check_presentation(plan, changed)
    assert "NOTES_MAIN_MESSAGE_DRIFT" in {item.code for item in issues}


def test_safe_repair_removes_title_punctuation_and_preserves_evidence() -> None:
    spec, plan, _, _, _ = load_inputs()
    changed = spec.model_copy(deep=True)
    case = qa_case("safe-title-punctuation")
    changed.slides[0].title += case["value"]
    issues, _ = check_presentation(plan, changed)
    finding = next(item for item in issues if item.code == case["expected_code"])
    assert finding.repairability == Repairability.AUTOMATIC
    before_evidence = changed.slides[0].evidence_ids.copy()
    repaired, actions = apply_safe_repairs(changed, issues)
    assert repaired.slides[0].title == spec.slides[0].title
    assert repaired.slides[0].evidence_ids == before_evidence
    assert len(actions) == 1
    assert actions[0].evidence_preserved is True


def test_visual_qa_accepts_renderer_geometry() -> None:
    spec, _, _, _, _ = load_inputs()
    issues, checks, metrics = inspect_visuals(
        WORKSPACE / "output" / "presentation.pptx",
        spec,
        preview_dir=None,
    )
    assert checks >= len(spec.slides)
    assert metrics["pptx_slide_count"] == len(spec.slides)
    error_codes = {item.code for item in issues if item.severity == QASeverity.ERROR}
    assert not error_codes
    assert "PREVIEW_NOT_RENDERED" in {item.code for item in issues}


def test_pipeline_writes_quality_report_without_render_backend(tmp_path: Path) -> None:
    workspace = tmp_path / "paper-reading"
    shutil.copytree(WORKSPACE, workspace)
    report = run_quality_assurance(
        workspace,
        render_artifacts=False,
        repair=False,
    )
    assert report.status.value == "pass_with_warnings"
    assert (workspace / "output" / "quality_report.json").is_file()
    assert (workspace / "output" / "quality_report.md").is_file()
    assert report.provenance.qa_version == "phase9-v1"


def test_pipeline_runs_targeted_safe_repair_and_reinspection(tmp_path: Path) -> None:
    workspace = tmp_path / "repair-loop"
    shutil.copytree(WORKSPACE, workspace)
    spec_path = workspace / "data" / "slide_spec.json"
    spec = read_model(spec_path, SlideSpec)
    spec.slides[0].title += "。"
    write_model(spec_path, spec)
    report = run_quality_assurance(
        workspace,
        render_artifacts=False,
        repair=True,
        max_iterations=2,
    )
    repaired = read_model(spec_path, SlideSpec)
    assert len(report.repairs) == 1
    assert report.repairs[0].repaired_slide_numbers == [1]
    assert not repaired.slides[0].title.endswith("。")
    assert (workspace / "data" / "slide_spec.pre-qa.json").is_file()
    assert repaired.slides[0].title in (workspace / "presentation_outline.md").read_text(encoding="utf-8")
    assert report.artifacts.targeted_review_pptx is not None
    assert Path(report.artifacts.targeted_review_pptx).is_file()
