# Phase 1 Implementation Report

Date: 2026-09-25  
Status: Complete for the defined Phase 1 baseline; Phase 2 has not started.

## Delivered

- Complete repository skeleton with Python/TypeScript boundary, project-local dependencies, CLI entry point, schemas, themes, prompts, examples, tests, docs, and project-local Codex skill.
- Typed Pydantic models and checked-in JSON Schemas for:
  - `paper_structure.json`
  - `visual_manifest.json`
  - `source_manifest.json`
  - `evidence_graph.json`
  - `presentation_plan.json`
  - `slide_spec.json`
- PDF parsing through a portable `pypdf` baseline: metadata, page count, page-grounded text, simple heading detection, and embedded-image extraction.
- LaTeX directory/ZIP ingestion with traversal and symlink protection, local `input/include` expansion, section hierarchy, paragraphs, figures, captions, tables, equations, labels, and graphic paths.
- Source-grounded asset extraction with deterministic priority:
  1. LaTeX vector
  2. LaTeX raster
  3. PDF embedded image
  4. PDF crop (schema reserved; automatic crop generation is not yet available)
- Resumable Phase 1 pipeline keyed by source SHA-256, plus explicit `--force` regeneration.
- Offline fixtures modeled on two public AI papers, with deterministic fixture regeneration and no copied paper figures/full text.
- A validated `research-presentation` Codex skill with mode-specific and QA references.

## Acceptance evidence

| Criterion | Evidence | Result |
|---|---|---|
| fixture | `tests/fixtures/attention_is_all_you_need`, `tests/fixtures/vision_transformer` | Pass |
| tests | unit, security, schema-sync, CLI, two end-to-end integrations | Pass |
| example output | `examples/phase1/attention` | Pass |
| schema validation | project skill validator against Draft 2020-12 schemas | Pass |
| resumability | second parse reuses artifacts; `--force` regenerates | Pass |
| README | install, CLI, outputs, phase status, validation commands | Pass |

Most recent local verification:

```text
python -m pytest -q
7 passed

python scripts/export_schemas.py --check
exit 0

python .agents/skills/research-presentation/scripts/validate_artifacts.py examples/phase1/attention/data
OK paper_structure.json
OK visual_manifest.json
OK source_manifest.json

quick_validate.py .agents/skills/research-presentation
Skill is valid!
```

## Known limitations and Phase 2 handoff

- `pypdf` is the reproducible baseline and does not provide robust reading order or paragraph bounding boxes for complex papers. The parser boundary is ready for a high-fidelity backend, but MinerU/Docling integration should be implemented and fixture-tested before production claims are made.
- LaTeX parsing intentionally does not execute TeX or arbitrary macros. Complex macro-generated captions/paths may require a syntax-tree backend later.
- LaTeX source assets do not yet have a PDF page number unless that mapping can be recovered; the manifest records `page: null` explicitly rather than inventing one.
- Automatic high-resolution PDF crop creation is not implemented; the schema and priority policy reserve it as the final fallback.
- Table content is preserved as LaTeX, but editable-table normalization belongs to a later rendering contract.
- The future schemas freeze the initial interface shape, but their behavioral generation begins only in their assigned phases.

Phase 2 should consume the validated Phase 1 artifacts and implement Scientific Understanding + Evidence Graph without changing the Renderer or generating slides.

