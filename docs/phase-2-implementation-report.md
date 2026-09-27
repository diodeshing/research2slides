# Phase 2 Implementation Report

Date: 2026-09-25  
Status: Complete for the source-grounded Phase 2 baseline; Phase 3 has not started.

## Delivered

- `SourceCatalog` covering paragraph, Figure, Table, and Equation source IDs.
- Provider-neutral `AnalysisDraft` contract plus:
  - deterministic offline JSON provider;
  - configurable OpenAI-compatible Responses API provider;
  - strict Structured Outputs payload using the schema generated from Pydantic.
- Evidence gate that rejects:
  - unknown source IDs;
  - excerpts that are not present in the cited artifact;
  - experimental/ablation numbers absent from cited evidence;
  - relations pointing outside the claim list;
  - duplicate evidence IDs or graph edges referencing missing nodes.
- Stable evidence IDs derived from normalized claims and source IDs.
- `scientific_understanding.json` answering all twelve analysis questions with evidence IDs or explicit `insufficient_evidence` status.
- Resume fingerprint covering Phase 1 inputs and provider configuration/draft.
- CLI command `research2slides understand` with offline and API-backed modes.
- Phase 1 merge repair: PDF paragraphs no longer retain dangling PDF section IDs after LaTeX hierarchy replaces the PDF hierarchy.

The Responses payload follows official OpenAI Structured Outputs guidance: `text.format.type=json_schema`, `strict=true`, and a generated schema. See https://developers.openai.com/api/docs/guides/structured-outputs.

## Acceptance evidence

| Criterion | Evidence | Result |
|---|---|---|
| fixtures | two grounded `analysis_draft.json` files | Pass |
| tests | Phase 1 regression + Phase 2 graph/provider/CLI/security tests | Pass |
| example output | `examples/phase2/attention` | Pass |
| schema validation | Phase 1 and Phase 2 artifacts validate | Pass |
| hallucination gates | unknown IDs, invented excerpts and unsupported numbers fail | Pass |
| resumability | unchanged provider/input fingerprint reuses artifacts | Pass |

Most recent local verification:

```text
python -m pytest -q
14 passed

python scripts/export_schemas.py --check
exit 0

python .agents/skills/research-presentation/scripts/validate_artifacts.py examples/phase2/attention/data
OK paper_structure.json
OK visual_manifest.json
OK source_manifest.json
OK evidence_graph.json
OK scientific_understanding.json

quick_validate.py .agents/skills/research-presentation
Skill is valid!
```

## Known limitations and Phase 3 handoff

- A live Responses API call was not executed because no API credential was supplied; the exact payload and response parsing are covered by an injected-transport test.
- Structured Outputs ensure schema adherence, not factual correctness. Local source/excerpt/number gates remain mandatory.
- The baseline sends the full structured evidence catalog in one request. Papers exceeding a provider context limit will need a measured section-map/reduce strategy rather than silent truncation.
- Semantic entailment is not yet independently scored: a verbatim excerpt can be cited for an over-broad interpretation. Confidence and later factual QA must treat this as a remaining risk.
- Phase 3 must consume only supported evidence IDs when building storyline units and must preserve `insufficient_evidence` rather than filling gaps from outside knowledge.
