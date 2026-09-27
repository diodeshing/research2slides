# Phase 6 QA and Repair Policy

Review the rendered research presentation in four independent layers: factual evidence, storyline,
visual layout, and presentation delivery. Treat the checked artifacts as authoritative inputs.

Never repair a finding by inventing evidence, changing a reported number, replacing a source visual,
or weakening a citation. Return semantic or evidence-changing findings for human approval. Automatic
repairs may only normalize low-risk presentation formatting while keeping evidence IDs, citations,
source references, and numerical tokens unchanged.

For every finding, identify the slide, severity, evidence or source IDs, and a concrete repair action.
After an approved repair, rerender the affected slide for review, rebuild the full deck, and run the
same checks again.
