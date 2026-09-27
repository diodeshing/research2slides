from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from research2slides.artifacts import read_model
from research2slides.exceptions import QualityAssuranceError
from research2slides.models import (
    EvidenceGraph,
    PresentationPlan,
    QASeverity,
    SemanticQADraft,
    SlideSpec,
)
from research2slides.qa.pipeline import run_quality_assurance
from research2slides.qa.semantic import (
    JsonSemanticQAProvider,
    OpenAISemanticQAProvider,
    run_semantic_qa,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT_ROOT / "examples" / "phase5" / "paper-reading"
DRAFT_PATH = PROJECT_ROOT / "tests" / "fixtures" / "phase9" / "semantic_qa_valid.json"
PROMPT = PROJECT_ROOT / "prompts" / "semantic-qa.md"


class StaticProvider:
    provider_name = "static-test"
    model_name = "offline"

    def __init__(self, draft: SemanticQADraft, key: str = "static") -> None:
        self.draft = draft
        self.key = key

    def cache_key(self) -> str:
        return self.key.ljust(64, "0")[:64]

    def evaluate(self, context: str) -> SemanticQADraft:
        assert "main_claim" in context
        return self.draft


def load_inputs(workspace: Path) -> tuple[SlideSpec, PresentationPlan, EvidenceGraph]:
    data = workspace / "data"
    return (
        read_model(data / "slide_spec.json", SlideSpec),
        read_model(data / "presentation_plan.json", PresentationPlan),
        read_model(data / "evidence_graph.json", EvidenceGraph),
    )


def copied_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "paper-reading"
    shutil.copytree(WORKSPACE, workspace)
    return workspace


def test_semantic_qa_writes_and_reuses_grounded_result(tmp_path: Path) -> None:
    workspace = copied_workspace(tmp_path)
    spec, plan, graph = load_inputs(workspace)
    provider = JsonSemanticQAProvider(DRAFT_PATH)
    result, issues, counts, resumed = run_semantic_qa(workspace, spec, plan, graph, provider)
    assert resumed is False
    assert not issues
    assert counts
    assert result.paper_id == spec.paper_id
    assert (workspace / "data" / "semantic_qa.json").is_file()
    _, _, _, resumed = run_semantic_qa(workspace, spec, plan, graph, provider)
    assert resumed is True


@pytest.mark.parametrize(
    ("field", "value", "expected_code", "expected_severity"),
    [
        ("claim_evidence", "unsupported", "CLAIM_EVIDENCE_UNSUPPORTED", QASeverity.ERROR),
        ("claim_evidence", "partially_supported", "CLAIM_EVIDENCE_PARTIAL", QASeverity.WARNING),
        ("claim_strength", "overstated", "CLAIM_STRENGTH_OVERSTATED", QASeverity.ERROR),
    ],
)
def test_semantic_qa_surfaces_entailment_and_strength_failures(
    tmp_path: Path,
    field: str,
    value: str,
    expected_code: str,
    expected_severity: QASeverity,
) -> None:
    workspace = copied_workspace(tmp_path)
    spec, plan, graph = load_inputs(workspace)
    draft = SemanticQADraft.model_validate_json(DRAFT_PATH.read_text(encoding="utf-8"))
    setattr(draft.evaluations[3], field, value)
    _, issues, _, _ = run_semantic_qa(
        workspace,
        spec,
        plan,
        graph,
        StaticProvider(draft, key=f"{field}-{value}"),
    )
    finding = next(item for item in issues if item.code == expected_code)
    assert finding.severity == expected_severity
    assert finding.repairability.value == "none"


def test_semantic_qa_detects_storyline_dependency_order(tmp_path: Path) -> None:
    workspace = copied_workspace(tmp_path)
    spec, plan, graph = load_inputs(workspace)
    draft = SemanticQADraft.model_validate_json(DRAFT_PATH.read_text(encoding="utf-8"))
    draft.evaluations[2].dependencies[0].prerequisite_slide_ids = ["S04"]
    _, issues, _, _ = run_semantic_qa(
        workspace,
        spec,
        plan,
        graph,
        StaticProvider(draft, key="late-dependency"),
    )
    assert "STORYLINE_DEPENDENCY_ORDER" in {item.code for item in issues}


def test_semantic_qa_rejects_evidence_outside_slide(tmp_path: Path) -> None:
    workspace = copied_workspace(tmp_path)
    spec, plan, graph = load_inputs(workspace)
    draft = SemanticQADraft.model_validate_json(DRAFT_PATH.read_text(encoding="utf-8"))
    draft.evaluations[0].evidence_ids = ["evidence_38e5dbdebe5f"]
    with pytest.raises(QualityAssuranceError, match="outside the slide"):
        run_semantic_qa(
            workspace,
            spec,
            plan,
            graph,
            StaticProvider(draft, key="outside-evidence"),
        )


def test_pipeline_records_semantic_checks(tmp_path: Path) -> None:
    workspace = copied_workspace(tmp_path)
    report = run_quality_assurance(
        workspace,
        render_artifacts=False,
        repair=False,
        semantic_provider=JsonSemanticQAProvider(DRAFT_PATH),
    )
    assert report.provenance.qa_version == "phase9-v1"
    assert "semantic-claim-evidence-v1" in report.provenance.checks
    assert (workspace / "data" / "semantic_qa.json").is_file()


def test_openai_semantic_provider_uses_strict_structured_output() -> None:
    captured: dict = {}
    draft = SemanticQADraft.model_validate_json(DRAFT_PATH.read_text(encoding="utf-8"))

    def transport(payload: dict) -> dict:
        captured.update(payload)
        return {"status": "completed", "output_text": draft.model_dump_json()}

    provider = OpenAISemanticQAProvider(
        prompt=PROMPT.read_text(encoding="utf-8"),
        transport=transport,
    )
    assert provider.evaluate("context") == draft
    assert captured["model"] == "gpt-5.6-sol"
    assert captured["reasoning"]["effort"] == "high"
    assert captured["text"]["format"]["strict"] is True
    assert captured["store"] is False
