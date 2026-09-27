from __future__ import annotations

import json

from research2slides.models import PaperStructure, VisualManifest
from research2slides.understanding.catalog import SourceCatalog


def build_analysis_context(
    paper: PaperStructure,
    visuals: VisualManifest,
    catalog: SourceCatalog,
) -> str:
    payload = {
        "paper_id": paper.paper_id,
        "metadata": paper.metadata.model_dump(mode="json"),
        "sections": [section.model_dump(mode="json") for section in paper.sections],
        "evidence_catalog": catalog.as_prompt_catalog(),
        "visual_assets": [asset.model_dump(mode="json") for asset in visuals.assets],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

