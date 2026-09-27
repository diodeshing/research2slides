# Phase 3 Implementation Report

Date: 2026-09-25  
Status: Complete for the evidence-grounded storyline baseline; Phase 4 has not started.

## Delivered

- Distinct `paper-reading` and `own-research` prompts with different voice, background depth, critical-analysis, and contribution rules.
- Provider-neutral `StorylineDraft` contract with offline JSON and Responses API adapters.
- `PresentationPlan` v1.1 containing ordered presentation units, role, question, main claim, evidence IDs, importance, estimated time, rationale, and transition intent.
- Local planning gates for unknown evidence, unsupported numbers, paper-reading/own-research voice leakage, invalid ending placement, and key Problem -> Insight -> Method -> Evidence order constraints.
- Mode-specific coverage reporting that exposes unsupported narrative sections instead of generating them from outside knowledge.
- Clarity First full plan plus deterministic time-budget compression that retains the original full plan.
- Stable unit IDs and resumable planning fingerprints.
- `plan` CLI command and two mode-specific example workspaces.
- Shared Responses Structured Outputs client extracted from Phase 2 so understanding and planning use one tested adapter boundary.

## Acceptance evidence

| Criterion | Evidence | Result |
|---|---|---|
| fixtures | paper-reading fixtures for two papers; own-research fixture | Pass |
| mode separation | distinct prompts, mode validation, voice gate | Pass |
| tests | Phase 1–2 regression + planning/compression/CLI tests | Pass |
| full example | `examples/phase3/paper-reading/data/presentation_plan.full.json` | Pass |
| compressed example | 390s full plan -> 345s selected plan | Pass |
| own-research example | `examples/phase3/own-research/data/presentation_plan.json` | Pass |
| artifact validation | both examples validate against checked-in schemas | Pass |

Most recent local verification:

```text
python -m pytest -q
22 passed

python scripts/export_schemas.py --check
exit 0

validate_artifacts.py examples/phase3/paper-reading/data
OK paper_structure.json
OK visual_manifest.json
OK source_manifest.json
OK evidence_graph.json
OK scientific_understanding.json
OK presentation_plan.json
OK presentation_plan.full.json
```

## Known limitations and Phase 4 handoff

- A live model call was not made because no API credential was supplied; strict request construction remains covered by the shared injected-transport test.
- Coverage gaps are reported, not repaired. For the compact fixtures, research-gap evidence is intentionally absent.
- Compression drops whole units and does not yet merge two units into one slide; safe merging requires Phase 4 content/layout judgment.
- Transition intent is preserved after compression and may need rewriting when an adjacent optional unit is removed. Phase 4 should generate final transitions from the selected plan.
- Semantic entailment remains bounded by Phase 2 evidence quality; the planner validates IDs and numbers but cannot independently prove every paraphrase.
- Phase 4 must convert each selected unit into a complete Slide Spec with claim-based title, visual selection, takeaway, annotations, and speaker notes. It must not read the raw paper to bypass the plan.

