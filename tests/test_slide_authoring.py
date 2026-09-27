from __future__ import annotations

from pathlib import Path

import pytest

from research2slides.artifacts import read_model
from research2slides.exceptions import SlideSpecError
from research2slides.language_policy import contains_cjk
from research2slides.models import (
    EvidenceGraph,
    PaperStructure,
    PresentationMode,
    PresentationPlan,
    SlideSpecProvenance,
    VisualManifest,
)
from research2slides.pipeline import parse_sources
from research2slides.planning.pipeline import run_planning
from research2slides.planning.providers import JsonStorylineProvider
from research2slides.slide_authoring.builder import build_slide_spec
from research2slides.slide_authoring.pipeline import run_slide_authoring
from research2slides.slide_authoring.providers import JsonSlideSpecProvider
from research2slides.understanding.pipeline import run_understanding
from research2slides.understanding.providers import JsonDraftProvider


FIXTURE = Path(__file__).parent / "fixtures" / "attention_is_all_you_need"


def make_phase3_workspace(
    tmp_path: Path,
    mode: PresentationMode,
) -> tuple[Path, JsonSlideSpecProvider, str]:
    workspace = tmp_path / mode.value
    parse_sources(FIXTURE / "paper.pdf", workspace, FIXTURE / "source.zip")
    run_understanding(workspace, JsonDraftProvider(FIXTURE / "analysis_draft.json"))
    if mode == PresentationMode.PAPER_READING:
        storyline = FIXTURE / "storyline_paper_reading.json"
        slide_draft = FIXTURE / "slide_spec_paper_reading.json"
        theme = "group-meeting"
        budget = 345
    else:
        storyline = FIXTURE / "storyline_own_research.json"
        slide_draft = FIXTURE / "slide_spec_own_research.json"
        theme = "conference-minimal"
        budget = None
    run_planning(
        workspace,
        JsonStorylineProvider(storyline),
        mode,
        time_budget_seconds=budget,
    )
    return workspace, JsonSlideSpecProvider(slide_draft), theme


@pytest.mark.parametrize("mode", [PresentationMode.PAPER_READING, PresentationMode.OWN_RESEARCH])
def test_phase4_builds_slide_spec_notes_and_outline(tmp_path: Path, mode: PresentationMode) -> None:
    workspace, provider, theme = make_phase3_workspace(tmp_path, mode)
    spec, resumed = run_slide_authoring(workspace, provider, theme)
    assert resumed is False
    assert len(spec.slides) == 6
    assert spec.theme == theme
    assert spec.language == "zh-CN"
    assert spec.language_profile.value == "zh_cn_bilingual_terms"
    assert spec.presentation.preserve_source_visual_language is True
    assert spec.estimated_total_seconds == sum(
        slide.speaker_notes.estimated_seconds for slide in spec.slides
    )
    assert all(slide.citations for slide in spec.slides)
    assert all(slide.speaker_notes.main_message == slide.main_claim for slide in spec.slides)
    assert all(contains_cjk(slide.title) for slide in spec.slides)
    assert all(contains_cjk(slide.takeaway) for slide in spec.slides)
    assert all(contains_cjk(slide.speaker_notes.script) for slide in spec.slides)
    table_visual = next(
        visual for slide in spec.slides for visual in slide.visuals if visual.kind == "source_table"
    )
    assert table_visual.table_column_labels == ["方法", "得分"]
    notes = (workspace / "speaker_notes.md").read_text(encoding="utf-8")
    outline = (workspace / "presentation_outline.md").read_text(encoding="utf-8")
    assert "Estimated Total Presentation Time" in notes
    assert f"总计：{len(spec.slides)} 页" in outline

    _, resumed = run_slide_authoring(workspace, provider, theme)
    assert resumed is True


def test_slide_spec_rejects_generic_title_and_unknown_visual(tmp_path: Path) -> None:
    workspace, provider, theme = make_phase3_workspace(tmp_path, PresentationMode.PAPER_READING)
    draft = provider.author("")
    plan = read_model(workspace / "data" / "presentation_plan.json", PresentationPlan)
    graph = read_model(workspace / "data" / "evidence_graph.json", EvidenceGraph)
    paper = read_model(workspace / "data" / "paper_structure.json", PaperStructure)
    visuals = read_model(workspace / "data" / "visual_manifest.json", VisualManifest)
    provenance = SlideSpecProvenance(
        provider="test",
        model="test",
        prompt_version="test",
        input_fingerprint="0" * 64,
    )
    draft.slides[0].title = "Method"
    with pytest.raises(SlideSpecError, match="generic title"):
        build_slide_spec(plan, draft, graph, paper, visuals, theme, provenance)

    draft = provider.author("")
    draft.slides[1].visuals[0].source_ref = "asset_missing"
    with pytest.raises(SlideSpecError, match="unknown visual asset"):
        build_slide_spec(plan, draft, graph, paper, visuals, theme, provenance)


def test_slide_spec_rejects_plan_and_notes_drift(tmp_path: Path) -> None:
    workspace, provider, theme = make_phase3_workspace(tmp_path, PresentationMode.PAPER_READING)
    draft = provider.author("")
    plan = read_model(workspace / "data" / "presentation_plan.json", PresentationPlan)
    graph = read_model(workspace / "data" / "evidence_graph.json", EvidenceGraph)
    paper = read_model(workspace / "data" / "paper_structure.json", PaperStructure)
    visuals = read_model(workspace / "data" / "visual_manifest.json", VisualManifest)
    provenance = SlideSpecProvenance(
        provider="test",
        model="test",
        prompt_version="test",
        input_fingerprint="0" * 64,
    )
    draft.slides[0].evidence_ids = [plan.units[1].evidence_ids[0]]
    with pytest.raises(SlideSpecError, match="evidence IDs diverge"):
        build_slide_spec(plan, draft, graph, paper, visuals, theme, provenance)

    draft = provider.author("")
    draft.slides[0].speaker_notes.estimated_seconds += 1
    with pytest.raises(SlideSpecError, match="time diverges"):
        build_slide_spec(plan, draft, graph, paper, visuals, theme, provenance)


def test_slide_spec_rejects_visual_reuse(tmp_path: Path) -> None:
    workspace, provider, theme = make_phase3_workspace(tmp_path, PresentationMode.PAPER_READING)
    draft = provider.author("")
    draft.slides[4].visuals = [draft.slides[1].visuals[0].model_copy(deep=True)]
    plan = read_model(workspace / "data" / "presentation_plan.json", PresentationPlan)
    graph = read_model(workspace / "data" / "evidence_graph.json", EvidenceGraph)
    paper = read_model(workspace / "data" / "paper_structure.json", PaperStructure)
    visuals = read_model(workspace / "data" / "visual_manifest.json", VisualManifest)
    provenance = SlideSpecProvenance(
        provider="test",
        model="test",
        prompt_version="test",
        input_fingerprint="0" * 64,
    )
    with pytest.raises(SlideSpecError, match="reused across slides"):
        build_slide_spec(plan, draft, graph, paper, visuals, theme, provenance)


def test_slide_spec_rejects_english_first_copy(tmp_path: Path) -> None:
    workspace, provider, theme = make_phase3_workspace(tmp_path, PresentationMode.PAPER_READING)
    draft = provider.author("")
    plan = read_model(workspace / "data" / "presentation_plan.json", PresentationPlan)
    graph = read_model(workspace / "data" / "evidence_graph.json", EvidenceGraph)
    paper = read_model(workspace / "data" / "paper_structure.json", PaperStructure)
    visuals = read_model(workspace / "data" / "visual_manifest.json", VisualManifest)
    provenance = SlideSpecProvenance(
        provider="test",
        model="test",
        prompt_version="test",
        input_fingerprint="0" * 64,
    )
    draft.slides[0].title = "Attention becomes the architectural core"
    with pytest.raises(SlideSpecError, match="Chinese-first language profile"):
        build_slide_spec(plan, draft, graph, paper, visuals, theme, provenance)
