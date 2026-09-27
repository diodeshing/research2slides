from __future__ import annotations

import json

from research2slides.models import (
    EvidenceGraph,
    LanguageProfile,
    PresentationLanguageConfig,
    PresentationMode,
    ScientificUnderstanding,
)


def build_storyline_context(
    understanding: ScientificUnderstanding,
    graph: EvidenceGraph,
    mode: PresentationMode,
    language_profile: LanguageProfile = LanguageProfile.ZH_CN_BILINGUAL_TERMS,
) -> str:
    presentation = PresentationLanguageConfig()
    payload = {
        "paper_id": graph.paper_id,
        "mode": mode.value,
        "language_profile": language_profile.value,
        "presentation": presentation.model_dump(mode="json"),
        "clarity_first": True,
        "one_unit_one_main_idea": True,
        "scientific_understanding": understanding.model_dump(mode="json"),
        "evidence_graph": graph.model_dump(mode="json"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
