from __future__ import annotations

import json
from pathlib import Path

import pytest

from research2slides.exceptions import EvidenceError
from research2slides.models import AnalysisDraft, DraftClaim, DraftEvidenceRef
from research2slides.pipeline import parse_sources
from research2slides.understanding.catalog import SourceCatalog
from research2slides.understanding.evidence_graph import build_evidence_graph
from research2slides.understanding.pipeline import run_understanding
from research2slides.understanding.providers import JsonDraftProvider, OpenAIResponsesProvider


FIXTURES = Path(__file__).parent / "fixtures"
PROMPT = Path(__file__).parents[1] / "prompts" / "understand-paper.md"


def make_workspace(tmp_path: Path, fixture: str = "attention_is_all_you_need") -> tuple[Path, Path]:
    source = FIXTURES / fixture
    workspace = tmp_path / fixture
    parse_sources(source / "paper.pdf", workspace, source / "source.zip")
    return source, workspace


@pytest.mark.parametrize("fixture", ["attention_is_all_you_need", "vision_transformer"])
def test_phase2_pipeline_builds_traceable_graph_and_answers(tmp_path: Path, fixture: str) -> None:
    source, workspace = make_workspace(tmp_path, fixture)
    provider = JsonDraftProvider(source / "analysis_draft.json")
    understanding, graph, resumed = run_understanding(workspace, provider)
    assert resumed is False
    assert graph.nodes
    assert all(node.sources for node in graph.nodes)
    assert all(locator.source_id for node in graph.nodes for locator in node.sources)
    assert understanding.answers.problem.status == "supported"
    assert understanding.answers.ablation_findings.status == "insufficient_evidence"
    assert (workspace / "data" / "evidence_graph.json").is_file()
    assert (workspace / "data" / "scientific_understanding.json").is_file()

    _, _, resumed = run_understanding(workspace, provider)
    assert resumed is True


def test_unknown_source_id_is_rejected(tmp_path: Path) -> None:
    source, workspace = make_workspace(tmp_path)
    provider = JsonDraftProvider(source / "analysis_draft.json")
    draft = provider.analyze("")
    draft.claims[0].source_refs[0].source_id = "missing_source"
    paper = json.loads((workspace / "data" / "paper_structure.json").read_text(encoding="utf-8"))
    from research2slides.models import PaperStructure

    catalog = SourceCatalog.from_paper(PaperStructure.model_validate(paper))
    with pytest.raises(EvidenceError, match="Unknown evidence source ID"):
        build_evidence_graph(paper["paper_id"], draft, catalog)


def test_quantitative_claim_number_must_exist_in_cited_source(tmp_path: Path) -> None:
    source, workspace = make_workspace(tmp_path)
    provider = JsonDraftProvider(source / "analysis_draft.json")
    draft = provider.analyze("")
    result = next(claim for claim in draft.claims if claim.type == "experimental_result")
    result.claim = "The fixture model improves the score by 99.9 points."
    from research2slides.artifacts import read_model
    from research2slides.models import PaperStructure

    catalog = SourceCatalog.from_paper(read_model(workspace / "data" / "paper_structure.json", PaperStructure))
    with pytest.raises(EvidenceError, match="99.9"):
        build_evidence_graph("paper", draft, catalog)


def test_evidence_excerpt_must_be_verbatim_from_source(tmp_path: Path) -> None:
    source, workspace = make_workspace(tmp_path)
    provider = JsonDraftProvider(source / "analysis_draft.json")
    draft = provider.analyze("")
    draft.claims[0].source_refs[0].excerpt = "This sentence does not exist in the source."
    from research2slides.artifacts import read_model
    from research2slides.models import PaperStructure

    catalog = SourceCatalog.from_paper(read_model(workspace / "data" / "paper_structure.json", PaperStructure))
    with pytest.raises(EvidenceError, match="not present"):
        build_evidence_graph("paper", draft, catalog)


def test_openai_responses_provider_uses_strict_structured_output() -> None:
    captured: dict = {}
    draft = AnalysisDraft(
        claims=[
            DraftClaim(
                category="problem",
                type="problem",
                claim="A grounded claim.",
                source_refs=[DraftEvidenceRef(source_id="para_1", excerpt="source")],
                confidence="high",
            )
        ],
        relations=[],
    )

    def transport(payload: dict) -> dict:
        captured.update(payload)
        return {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": draft.model_dump_json()}],
                }
            ],
        }

    provider = OpenAIResponsesProvider(
        prompt=PROMPT.read_text(encoding="utf-8"),
        transport=transport,
    )
    assert provider.analyze("context") == draft
    assert captured["model"] == "gpt-5.6-sol"
    assert captured["reasoning"]["effort"] == "high"
    assert captured["text"]["format"]["type"] == "json_schema"
    assert captured["text"]["format"]["strict"] is True
    assert captured["store"] is False
