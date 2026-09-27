from __future__ import annotations

import re

from research2slides.exceptions import SlideSpecError
from research2slides.language_policy import require_slide_chinese
from research2slides.models import (
    EvidenceGraph,
    PaperStructure,
    PresentationPlan,
    Slide,
    SlideCitation,
    SlideSpec,
    SlideSpecDraft,
    SlideSpecProvenance,
    VisualManifest,
)


GENERIC_TITLES = {
    "motivation",
    "method",
    "experiments",
    "results",
    "ablation study",
    "discussion",
    "conclusion",
    "动机",
    "方法",
    "实验",
    "结果",
    "消融实验",
    "结论",
}
BAD_TITLE_PUNCTUATION = ("—", ";", "|", "→")
COLUMN_SPEC_LETTERS = "lcrpmbX"


def _brace_group(text: str, start: int) -> tuple[str, int] | None:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != "{":
        return None
    depth = 0
    for cursor in range(index, len(text)):
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
            if depth == 0:
                return text[index + 1 : cursor], cursor + 1
    return None


def _tabular_column_count(latex: str | None) -> int | None:
    """Count the columns declared by a tabular environment.

    Splitting the first `&`-row undercounts tables whose header is grouped
    across several rows (a `multicol` group row has fewer cells than the table
    has columns), while the renderer compares labels against the parsed table
    width. Reading the declared column spec keeps both checks on one contract.
    """
    if not latex:
        return None
    match = re.search(r"\\begin\{(tabular\*?)\}", latex)
    if match is None:
        return None
    cursor = match.end()
    if match.group(1).endswith("*"):
        width = _brace_group(latex, cursor)
        if width is None:
            return None
        cursor = width[1]
    spec = _brace_group(latex, cursor)
    if spec is None:
        return None
    spec_text = re.sub(r"@\{(?:[^{}]|\{[^{}]*\})*\}", "", spec[0])
    count = sum(1 for character in spec_text if character in COLUMN_SPEC_LETTERS)
    return count or None


def _citation(evidence_id: str, graph_nodes: dict[str, object]) -> SlideCitation:
    node = graph_nodes[evidence_id]
    source_ids = [source.source_id for source in node.sources]
    labels: list[str] = []
    for source in node.sources:
        parts = []
        if source.section:
            parts.append(source.section)
        if source.page:
            parts.append(f"p. {source.page}")
        if source.figure:
            parts.append(f"Figure {source.figure}")
        if source.table:
            parts.append(f"Table {source.table}")
        if source.equation:
            parts.append(f"Equation {source.equation}")
        label = ", ".join(parts) or source.source_id
        if label not in labels:
            labels.append(label)
    return SlideCitation(
        evidence_id=evidence_id,
        source_ids=source_ids,
        display_text="; ".join(labels),
    )


def build_slide_spec(
    plan: PresentationPlan,
    draft: SlideSpecDraft,
    graph: EvidenceGraph,
    paper: PaperStructure,
    visuals: VisualManifest,
    theme: str,
    provenance: SlideSpecProvenance,
) -> SlideSpec:
    if draft.mode != plan.mode:
        raise SlideSpecError("slide-spec mode does not match presentation plan")
    if draft.theme != theme:
        raise SlideSpecError("slide-spec theme does not match requested theme")
    if draft.language_profile != plan.language_profile or draft.presentation != plan.presentation:
        raise SlideSpecError("slide-spec language policy does not match presentation plan")
    expected_units = [unit.unit_id for unit in plan.units]
    actual_units = [slide.unit_id for slide in draft.slides]
    if actual_units != expected_units:
        raise SlideSpecError("slide-spec slides must match presentation units in order")

    graph_nodes = {node.id: node for node in graph.nodes}
    assets = {asset.asset_id for asset in visuals.assets}
    tables = {table.table_id for table in paper.tables}
    equations = {equation.equation_id for equation in paper.equations}
    used_visual_sources: set[str] = set()
    slides: list[Slide] = []

    for order, (unit, draft_slide) in enumerate(zip(plan.units, draft.slides, strict=True), start=1):
        if draft_slide.question != unit.question:
            raise SlideSpecError(f"slide {order} question diverges from its presentation unit")
        if draft_slide.main_claim != unit.main_claim:
            raise SlideSpecError(f"slide {order} main claim diverges from its presentation unit")
        if set(draft_slide.evidence_ids) != set(unit.evidence_ids):
            raise SlideSpecError(f"slide {order} evidence IDs diverge from its presentation unit")
        if draft_slide.title.strip().casefold().rstrip(".") in GENERIC_TITLES:
            raise SlideSpecError(f"slide {order} uses a generic title: {draft_slide.title}")
        if draft_slide.title.endswith(".") and len(draft_slide.title) < 90:
            raise SlideSpecError(f"slide {order} has unnecessary terminal punctuation in its title")
        if any(mark in draft_slide.title for mark in BAD_TITLE_PUNCTUATION):
            raise SlideSpecError(f"slide {order} title uses disallowed presentation punctuation")
        if draft_slide.speaker_notes.main_message != draft_slide.main_claim:
            raise SlideSpecError(f"slide {order} speaker-note message diverges from the slide claim")
        if draft_slide.speaker_notes.estimated_seconds != unit.estimated_seconds:
            raise SlideSpecError(f"slide {order} speaker-note time diverges from the plan")
        if plan.language_profile.value == "zh_cn_bilingual_terms":
            language_fields = [
                (f"slide {order} purpose", draft_slide.purpose),
                (f"slide {order} question", draft_slide.question),
                (f"slide {order} title", draft_slide.title),
                (f"slide {order} main_claim", draft_slide.main_claim),
                (f"slide {order} takeaway", draft_slide.takeaway),
                (f"slide {order} notes.purpose", draft_slide.speaker_notes.purpose),
                (f"slide {order} notes.main_message", draft_slide.speaker_notes.main_message),
                (f"slide {order} notes.script", draft_slide.speaker_notes.script),
                (f"slide {order} notes.visual_guidance", draft_slide.speaker_notes.visual_guidance),
                (f"slide {order} notes.transition", draft_slide.speaker_notes.transition),
                *[(f"slide {order} body[{index}]", line) for index, line in enumerate(draft_slide.body)],
                *[
                    (f"slide {order} annotation[{index}]", annotation)
                    for index, annotation in enumerate(draft_slide.annotations)
                ],
            ]
            for visual_index, visual in enumerate(draft_slide.visuals):
                language_fields.extend(
                    (f"slide {order} visual[{visual_index}].annotation[{index}]", annotation)
                    for index, annotation in enumerate(visual.annotations)
                )
            require_slide_chinese(language_fields)
        for body_line in draft_slide.body:
            if len(body_line) > 240:
                raise SlideSpecError(f"slide {order} body line exceeds 240 characters")

        for visual in draft_slide.visuals:
            if visual.kind == "source_asset" and visual.source_ref not in assets:
                raise SlideSpecError(f"slide {order} references unknown visual asset {visual.source_ref}")
            if visual.kind == "source_table" and visual.source_ref not in tables:
                raise SlideSpecError(f"slide {order} references unknown table {visual.source_ref}")
            if visual.kind == "source_equation" and visual.source_ref not in equations:
                raise SlideSpecError(f"slide {order} references unknown equation {visual.source_ref}")
            if visual.kind == "conceptual_diagram" and visual.source_ref not in graph_nodes:
                raise SlideSpecError(f"slide {order} conceptual diagram lacks a valid evidence source")
            if visual.kind == "source_table" and visual.treatment not in {"native_table", "crop", "highlight"}:
                raise SlideSpecError(f"slide {order} uses an incompatible table treatment")
            if visual.table_column_labels is not None:
                source_table = next(table for table in paper.tables if table.table_id == visual.source_ref)
                if source_table.latex is None:
                    raise SlideSpecError(f"slide {order} table labels require editable LaTeX table data")
                header = source_table.latex.split(r"\\", maxsplit=1)[0]
                expected_columns = _tabular_column_count(source_table.latex) or len(header.split("&"))
                if len(visual.table_column_labels) != expected_columns:
                    raise SlideSpecError(f"slide {order} table_column_labels do not match source columns")
            if visual.kind == "source_equation" and visual.treatment not in {"equation", "highlight"}:
                raise SlideSpecError(f"slide {order} uses an incompatible equation treatment")
            if visual.kind == "conceptual_diagram" and visual.treatment != "diagram":
                raise SlideSpecError(f"slide {order} uses an incompatible diagram treatment")
            if visual.kind == "source_asset" and visual.treatment in {"native_table", "equation", "diagram"}:
                raise SlideSpecError(f"slide {order} uses an incompatible source-asset treatment")
            if visual.source_ref in used_visual_sources and visual.role != "background":
                raise SlideSpecError(f"visual source {visual.source_ref} is reused across slides")
            if visual.role != "background":
                used_visual_sources.add(visual.source_ref)

        visual_kinds = {visual.kind for visual in draft_slide.visuals}
        if "source_table" in visual_kinds and draft_slide.layout not in {"table_focus", "comparison"}:
            raise SlideSpecError(f"slide {order} table visual requires a table-focused layout")
        if "source_equation" in visual_kinds and draft_slide.layout != "equation_focus":
            raise SlideSpecError(f"slide {order} equation visual requires an equation-focused layout")
        if not draft_slide.visuals and draft_slide.layout == "full_visual":
            raise SlideSpecError(f"slide {order} requests a full visual layout without a visual")

        citations = [_citation(evidence_id, graph_nodes) for evidence_id in unit.evidence_ids]
        slides.append(
            Slide(
                slide_id=f"S{order:02d}",
                unit_id=unit.unit_id,
                order=order,
                section=unit.section,
                purpose=draft_slide.purpose,
                question=draft_slide.question,
                title=draft_slide.title,
                title_kind=draft_slide.title_kind,
                technical_title=draft_slide.technical_title,
                main_claim=draft_slide.main_claim,
                body=draft_slide.body,
                visuals=draft_slide.visuals,
                annotations=draft_slide.annotations,
                takeaway=draft_slide.takeaway,
                evidence_ids=draft_slide.evidence_ids,
                citations=citations,
                layout=draft_slide.layout,
                speaker_notes=draft_slide.speaker_notes,
            )
        )

    return SlideSpec(
        paper_id=plan.paper_id,
        mode=plan.mode,
        theme=theme,
        language=plan.language,
        language_profile=plan.language_profile,
        presentation=plan.presentation,
        title=plan.title,
        slides=slides,
        estimated_total_seconds=sum(slide.speaker_notes.estimated_seconds for slide in slides),
        provenance=provenance,
    )
