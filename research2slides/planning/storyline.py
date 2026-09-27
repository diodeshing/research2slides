from __future__ import annotations

import hashlib

from research2slides.exceptions import PlanningError
from research2slides.language_policy import require_plan_chinese
from research2slides.models import (
    EvidenceGraph,
    LanguageProfile,
    PlanProvenance,
    PresentationMode,
    PresentationPlan,
    PresentationUnit,
    StorylineDraft,
    StorylineRole,
)
from research2slides.numbers import missing_numbers


PAPER_READING_FORBIDDEN = ("we propose", "our method", "我们提出", "我们的方法")
ENDING_ROLES = {"conclusion", "takeaway"}
METHOD_ROLES = {"method_overview", "method_component"}
EVIDENCE_ROLES = {"experiments", "ablation", "analysis"}


def _unit_id(role: str, claim: str, evidence_ids: list[str]) -> str:
    seed = role + "\0" + claim.strip().casefold() + "\0" + "\0".join(evidence_ids)
    return f"unit_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _first_index(roles: list[str], options: set[str]) -> int | None:
    return next((index for index, role in enumerate(roles) if role in options), None)


def _validate_sequence(roles: list[str]) -> None:
    if "opening" in roles and roles.index("opening") != 0:
        raise PlanningError("opening must be the first presentation unit")
    ending_started = False
    for role in roles:
        if role in ENDING_ROLES:
            ending_started = True
        elif ending_started:
            raise PlanningError("conclusion/takeaway units must form the end of the storyline")
    problem = _first_index(roles, {"problem"})
    method = _first_index(roles, METHOD_ROLES)
    insight = _first_index(roles, {"core_insight", "contributions"})
    evidence = _first_index(roles, EVIDENCE_ROLES)
    if problem is not None and method is not None and method < problem:
        raise PlanningError("method cannot precede the problem")
    if insight is not None and method is not None and method < insight:
        raise PlanningError("method cannot precede the core insight/contributions")
    if method is not None and evidence is not None and evidence < method:
        raise PlanningError("experimental evidence cannot precede the method")


def _coverage_gaps(mode: PresentationMode, roles: list[str]) -> list[str]:
    role_set = set(roles)
    shared = [
        ("problem", {"problem"}),
        ("core idea", {"core_insight", "contributions"}),
        ("method", METHOD_ROLES),
        ("evidence", EVIDENCE_ROLES),
        ("takeaway", {"conclusion", "takeaway"}),
    ]
    mode_specific = (
        [("research gap", {"existing_approaches", "gap"}), ("critical assessment", {"limitations", "analysis"})]
        if mode == PresentationMode.PAPER_READING
        else [("motivation or gap", {"background", "gap"}), ("limitations", {"limitations"})]
    )
    return [label for label, options in shared + mode_specific if role_set.isdisjoint(options)]


def build_presentation_plan(
    paper_id: str,
    draft: StorylineDraft,
    graph: EvidenceGraph,
    mode: PresentationMode,
    provenance: PlanProvenance,
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS,
) -> PresentationPlan:
    if draft.mode != mode:
        raise PlanningError(f"Storyline mode {draft.mode.value} does not match requested mode {mode.value}")
    if draft.language_profile != language_profile:
        raise PlanningError("Storyline language profile does not match requested language profile")
    if language_profile == LanguageProfile.ZH_CN_BILINGUAL_TERMS:
        require_plan_chinese(
            [
                ("storyline.title", draft.title),
                ("storyline.target_audience", draft.target_audience),
                *[
                    (f"storyline.units[{index}].{field}", value)
                    for index, unit in enumerate(draft.units)
                    for field, value in (
                        ("section", unit.section),
                        ("question", unit.question),
                        ("main_claim", unit.main_claim),
                        ("rationale", unit.rationale),
                        ("transition_intent", unit.transition_intent),
                    )
                ],
            ]
        )
    nodes = {node.id: node for node in graph.nodes}
    roles = [unit.role for unit in draft.units]
    _validate_sequence(roles)
    units: list[PresentationUnit] = []
    for order, unit in enumerate(draft.units, start=1):
        unknown = [evidence_id for evidence_id in unit.evidence_ids if evidence_id not in nodes]
        if unknown:
            raise PlanningError("Storyline references unknown evidence IDs: " + ", ".join(unknown))
        if mode == PresentationMode.PAPER_READING:
            lowered = unit.main_claim.casefold()
            if any(phrase in lowered for phrase in PAPER_READING_FORBIDDEN):
                raise PlanningError("paper-reading storyline uses own-research voice")
        missing_claim_numbers = missing_numbers(
            unit.main_claim,
            " ".join(nodes[evidence_id].claim for evidence_id in unit.evidence_ids),
        )
        if missing_claim_numbers:
            raise PlanningError(
                "Storyline claim contains values absent from its evidence nodes: "
                + ", ".join(missing_claim_numbers)
            )
        units.append(
            PresentationUnit(
                unit_id=_unit_id(unit.role, unit.main_claim, unit.evidence_ids),
                order=order,
                role=unit.role,
                section=unit.section,
                question=unit.question,
                main_claim=unit.main_claim,
                evidence_ids=unit.evidence_ids,
                importance=unit.importance,
                estimated_seconds=unit.estimated_seconds,
                rationale=unit.rationale,
                transition_intent=unit.transition_intent,
            )
        )
    return PresentationPlan(
        paper_id=paper_id,
        mode=mode,
        language=draft.presentation.language,
        language_profile=draft.language_profile,
        presentation=draft.presentation,
        title=draft.title,
        target_audience=draft.target_audience,
        units=units,
        estimated_total_seconds=sum(unit.estimated_seconds for unit in units),
        coverage_gaps=_coverage_gaps(mode, roles),
        provenance=provenance,
    )
