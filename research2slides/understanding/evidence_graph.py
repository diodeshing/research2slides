from __future__ import annotations

import hashlib
import re

from research2slides.exceptions import EvidenceError
from research2slides.models import (
    AnalysisDraft,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNode,
    GroundedAnswer,
    InsightCategory,
    ScientificUnderstanding,
    UnderstandingAnswers,
    UnderstandingProvenance,
)
from research2slides.understanding.catalog import SourceCatalog


CATEGORIES: tuple[InsightCategory, ...] = (
    "problem",
    "importance",
    "existing_approaches",
    "gap",
    "central_insight",
    "contributions",
    "method",
    "design_rationale",
    "experiment_findings",
    "ablation_findings",
    "limitations",
    "audience_takeaways",
)
NUMERIC_RESULT_TYPES = {"experimental_result", "ablation_result"}
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")


def _evidence_id(claim: str, source_ids: list[str]) -> str:
    seed = claim.strip().casefold() + "\0" + "\0".join(source_ids)
    return f"evidence_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _validate_numbers(claim_type: str, claim: str, source_texts: list[str]) -> None:
    if claim_type not in NUMERIC_RESULT_TYPES:
        return
    claimed_numbers = set(NUMBER_RE.findall(claim))
    source_numbers = set(NUMBER_RE.findall(" ".join(source_texts)))
    missing = sorted(claimed_numbers - source_numbers)
    if missing:
        raise EvidenceError(
            "Quantitative claim contains values absent from its cited evidence: " + ", ".join(missing)
        )


def build_evidence_graph(paper_id: str, draft: AnalysisDraft, catalog: SourceCatalog) -> EvidenceGraph:
    nodes: list[EvidenceNode] = []
    categories: list[InsightCategory] = []
    for draft_claim in draft.claims:
        records = [catalog.resolve(reference.source_id) for reference in draft_claim.source_refs]
        source_ids = [record.source_id for record in records]
        _validate_numbers(draft_claim.type, draft_claim.claim, [record.text for record in records])
        nodes.append(
            EvidenceNode(
                id=_evidence_id(draft_claim.claim, source_ids),
                type=draft_claim.type,
                claim=draft_claim.claim.strip(),
                sources=[
                    record.locator(reference.excerpt)
                    for record, reference in zip(records, draft_claim.source_refs, strict=True)
                ],
                confidence=draft_claim.confidence,
            )
        )
        categories.append(draft_claim.category)

    edges: list[EvidenceEdge] = []
    for relation in draft.relations:
        if relation.source_claim_index >= len(nodes) or relation.target_claim_index >= len(nodes):
            raise EvidenceError("Draft relation references a claim index that does not exist")
        edges.append(
            EvidenceEdge(
                source_id=nodes[relation.source_claim_index].id,
                target_id=nodes[relation.target_claim_index].id,
                relation=relation.relation,
            )
        )
    return EvidenceGraph(paper_id=paper_id, nodes=nodes, edges=edges)


def build_scientific_understanding(
    paper_id: str,
    draft: AnalysisDraft,
    graph: EvidenceGraph,
    provenance: UnderstandingProvenance,
) -> ScientificUnderstanding:
    by_category: dict[InsightCategory, list[str]] = {category: [] for category in CATEGORIES}
    for draft_claim, node in zip(draft.claims, graph.nodes, strict=True):
        by_category[draft_claim.category].append(node.id)

    answers: dict[str, GroundedAnswer] = {}
    for category in CATEGORIES:
        evidence_ids = by_category[category]
        if evidence_ids:
            answers[category] = GroundedAnswer(
                status="supported",
                evidence_ids=evidence_ids,
                note="Grounded in the cited evidence nodes.",
            )
        else:
            answers[category] = GroundedAnswer(
                status="insufficient_evidence",
                evidence_ids=[],
                note="The supplied artifacts do not contain enough evidence to answer this question safely.",
            )
    return ScientificUnderstanding(
        paper_id=paper_id,
        answers=UnderstandingAnswers.model_validate(answers),
        provenance=provenance,
    )

