from __future__ import annotations

from pathlib import Path

import pytest

from research2slides.artifacts import read_model
from research2slides.exceptions import PlanningError
from research2slides.language_policy import contains_cjk
from research2slides.models import (
    EvidenceGraph,
    PlanProvenance,
    PresentationMode,
)
from research2slides.pipeline import parse_sources
from research2slides.planning.compression import compress_plan
from research2slides.planning.pipeline import run_planning
from research2slides.planning.providers import JsonStorylineProvider
from research2slides.planning.storyline import build_presentation_plan
from research2slides.understanding.pipeline import run_understanding
from research2slides.understanding.providers import JsonDraftProvider


FIXTURES = Path(__file__).parent / "fixtures"


def make_phase2_workspace(tmp_path: Path, fixture: str = "attention_is_all_you_need") -> tuple[Path, Path]:
    source = FIXTURES / fixture
    workspace = tmp_path / fixture
    parse_sources(source / "paper.pdf", workspace, source / "source.zip")
    run_understanding(workspace, JsonDraftProvider(source / "analysis_draft.json"))
    return source, workspace


@pytest.mark.parametrize(
    ("fixture", "mode", "draft_name"),
    [
        ("attention_is_all_you_need", PresentationMode.PAPER_READING, "storyline_paper_reading.json"),
        ("attention_is_all_you_need", PresentationMode.OWN_RESEARCH, "storyline_own_research.json"),
        ("vision_transformer", PresentationMode.PAPER_READING, "storyline_paper_reading.json"),
    ],
)
def test_phase3_builds_mode_specific_clarity_first_plan(
    tmp_path: Path,
    fixture: str,
    mode: PresentationMode,
    draft_name: str,
) -> None:
    source, workspace = make_phase2_workspace(tmp_path, fixture)
    provider = JsonStorylineProvider(source / draft_name)
    plan, full, resumed = run_planning(workspace, provider, mode)
    assert resumed is False
    assert plan == full
    assert plan.mode == mode
    assert plan.language_profile.value == "zh_cn_bilingual_terms"
    assert plan.presentation.language == "zh-CN"
    assert contains_cjk(plan.title)
    assert all(contains_cjk(unit.main_claim) for unit in plan.units)
    assert plan.estimated_total_seconds == sum(unit.estimated_seconds for unit in plan.units)
    assert [unit.order for unit in plan.units] == list(range(1, len(plan.units) + 1))
    assert all(unit.evidence_ids for unit in plan.units)
    assert "research gap" in plan.coverage_gaps or "motivation or gap" in plan.coverage_gaps

    _, _, resumed = run_planning(workspace, provider, mode)
    assert resumed is True


def test_time_budget_compresses_full_plan_without_replanning(tmp_path: Path) -> None:
    source, workspace = make_phase2_workspace(tmp_path)
    provider = JsonStorylineProvider(source / "storyline_paper_reading.json")
    plan, full, _ = run_planning(
        workspace,
        provider,
        PresentationMode.PAPER_READING,
        time_budget_seconds=345,
    )
    assert len(full.units) == 7
    assert len(plan.units) == 6
    assert plan.estimated_total_seconds <= 345
    assert plan.compression is not None
    assert len(plan.compression.omitted_unit_ids) == 1
    assert next(unit for unit in full.units if unit.role == "analysis").unit_id in plan.compression.omitted_unit_ids
    assert (workspace / "data" / "presentation_plan.full.json").is_file()
    assert (workspace / "data" / "presentation_plan.json").is_file()
    with pytest.raises(PlanningError, match="narrative minimum"):
        compress_plan(full, 344)


def test_storyline_rejects_unknown_evidence_and_wrong_voice(tmp_path: Path) -> None:
    source, workspace = make_phase2_workspace(tmp_path)
    provider = JsonStorylineProvider(source / "storyline_paper_reading.json")
    draft = provider.plan("")
    graph = read_model(workspace / "data" / "evidence_graph.json", EvidenceGraph)
    provenance = PlanProvenance(
        provider="test",
        model="test",
        prompt_version="test",
        input_fingerprint="0" * 64,
    )
    draft.units[0].evidence_ids = ["evidence_missing"]
    with pytest.raises(PlanningError, match="unknown evidence"):
        build_presentation_plan(graph.paper_id, draft, graph, PresentationMode.PAPER_READING, provenance)

    draft = provider.plan("")
    draft.units[0].main_claim = "我们提出一个没有证据支持的表述。"
    with pytest.raises(PlanningError, match="own-research voice"):
        build_presentation_plan(graph.paper_id, draft, graph, PresentationMode.PAPER_READING, provenance)


def test_storyline_rejects_takeaway_before_method(tmp_path: Path) -> None:
    source, workspace = make_phase2_workspace(tmp_path)
    provider = JsonStorylineProvider(source / "storyline_paper_reading.json")
    draft = provider.plan("")
    draft.units.insert(1, draft.units.pop())
    graph = read_model(workspace / "data" / "evidence_graph.json", EvidenceGraph)
    provenance = PlanProvenance(
        provider="test",
        model="test",
        prompt_version="test",
        input_fingerprint="0" * 64,
    )
    with pytest.raises(PlanningError, match="must form the end"):
        build_presentation_plan(graph.paper_id, draft, graph, PresentationMode.PAPER_READING, provenance)


def test_mode_prompts_are_distinct() -> None:
    project = Path(__file__).parents[1]
    paper = (project / "prompts" / "paper-reading-storyline.md").read_text(encoding="utf-8")
    own = (project / "prompts" / "own-research-storyline.md").read_text(encoding="utf-8")
    assert paper != own
    assert "third-person" in paper
    assert "their own research" in own
    assert "zh_cn_bilingual_terms" in paper
    assert "later translation" in paper
