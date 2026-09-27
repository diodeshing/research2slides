from __future__ import annotations

import json

from research2slides.models import EvidenceGraph, PaperStructure, PresentationPlan, VisualManifest


def build_slide_context(
    plan: PresentationPlan,
    graph: EvidenceGraph,
    paper: PaperStructure,
    visuals: VisualManifest,
    theme: str,
) -> str:
    payload = {
        "paper_id": plan.paper_id,
        "mode": plan.mode.value,
        "theme": theme,
        "language_profile": plan.language_profile.value,
        "presentation": plan.presentation.model_dump(mode="json"),
        "presentation_plan": plan.model_dump(mode="json"),
        "evidence_graph": graph.model_dump(mode="json"),
        "available_visual_assets": [asset.model_dump(mode="json") for asset in visuals.assets],
        "available_tables": [table.model_dump(mode="json") for table in paper.tables],
        "available_equations": [equation.model_dump(mode="json") for equation in paper.equations],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
