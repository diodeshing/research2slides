from __future__ import annotations

import hashlib
import json

from research2slides.exceptions import QualityAssuranceError
from research2slides.models import QAIssue, QARepairAction, Repairability, SlideSpec


TITLE_PUNCTUATION = "。！？!?；;：:"


def _evidence_signature(spec: SlideSpec) -> str:
    payload = [
        {
            "slide_id": slide.slide_id,
            "evidence_ids": slide.evidence_ids,
            "citations": [citation.model_dump(mode="json") for citation in slide.citations],
            "visuals": [
                {
                    "kind": visual.kind,
                    "source_ref": visual.source_ref,
                    "treatment": visual.treatment,
                }
                for visual in slide.visuals
            ],
        }
        for slide in spec.slides
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def apply_safe_repairs(spec: SlideSpec, issues: list[QAIssue]) -> tuple[SlideSpec, list[QARepairAction]]:
    repaired = spec.model_copy(deep=True)
    before_signature = _evidence_signature(repaired)
    actions: list[QARepairAction] = []
    slide_by_id = {slide.slide_id: slide for slide in repaired.slides}
    for finding in issues:
        if finding.repairability != Repairability.AUTOMATIC:
            continue
        if finding.code == "TITLE_TRAILING_PUNCTUATION" and len(finding.slide_ids) == 1:
            slide = slide_by_id.get(finding.slide_ids[0])
            if slide is None:
                continue
            before = slide.title
            after = before.rstrip().rstrip(TITLE_PUNCTUATION).rstrip()
            if after and after != before:
                slide.title = after
                action_seed = f"{finding.issue_id}\x1f{slide.slide_id}\x1f{after}"
                actions.append(
                    QARepairAction(
                        action_id=f"repair_{hashlib.sha256(action_seed.encode('utf-8')).hexdigest()[:12]}",
                        issue_id=finding.issue_id,
                        slide_id=slide.slide_id,
                        field_path=finding.field_path or "title",
                        before=before,
                        after=after,
                        evidence_preserved=True,
                    )
                )
    if _evidence_signature(repaired) != before_signature:
        raise QualityAssuranceError("Automatic QA repair attempted to change evidence-bearing fields")
    return repaired, actions
