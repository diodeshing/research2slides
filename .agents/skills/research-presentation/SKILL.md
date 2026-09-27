---
name: research-presentation
description: Create source-grounded presentations from papers, LaTeX projects, and research documents for paper reading, group meetings, own-research talks, defenses, and conferences. Use when claims, visuals, speaker notes, and slide structure must remain traceable to scientific sources; do not use for generic business decks or arbitrary slide beautification.
---

# Research Presentation

Build the presentation through validated artifacts. Do not jump from source documents directly to slides.

## Workflow

1. Identify `paper-reading` or `own-research` mode. Read the matching mode reference below.
2. Parse PDF and available LaTeX into `paper_structure.json` and `visual_manifest.json`. Prefer original LaTeX vector/raster assets over PDF extraction; never substitute a lookalike web image for a paper figure.
3. Build evidence nodes for important claims, numbers, equations, limitations, and conclusions. A central quantitative claim without a source locator is not ready for slides.
4. Reorganize evidence into a presentation storyline. The paper's section order is evidence organization, not automatically the best speaking order.
5. Produce `presentation_plan.json`, then `slide_spec.json`. Each slide needs one main idea and should connect Question -> Claim -> Evidence/Visual -> Explanation -> Takeaway.
6. Render from the validated slide spec. Lookup artifacts may resolve already-selected visual, table, and equation references, but must not introduce new claims or reread the raw paper for content decisions.
7. Run Phase 6 QA to validate evidence, storyline, PPTX geometry, notes, fonts, PDF, and every rendered page. Allow only evidence-preserving automatic repairs; evidence, number, or source-visual changes require explicit human approval and a full recheck.

Default language profile is `zh_cn_bilingual_terms`: author natural Chinese presentation wording in the Presentation Plan and Slide Spec, introduce important technical terms with their English names, and keep original English Figure/Table/Equation labels. Do not create English slides for a translation post-process. Renderer code may apply CJK typography but must not decide or translate scientific content.

## References

- For paper reading or group meeting requests, read [references/paper-reading-mode.md](references/paper-reading-mode.md).
- For the user's own research, defense, or conference talk, read [references/own-research-mode.md](references/own-research-mode.md).
- Before planning information units, read [references/storytelling.md](references/storytelling.md).
- Before authoring or reviewing slide specs, read [references/slide-design.md](references/slide-design.md).
- Before delivery, read [references/quality-checklist.md](references/quality-checklist.md).

Use `scripts/validate_artifacts.py <data-directory>` to validate generated JSON against the project schemas. In the Research2Slides repository, run `research2slides qa <workspace>` for Phase 6 and use `scripts/validate_pptx.py <deck.pptx> --require-notes --require-native-table` for an additional package check. Theme tokens in `assets/academic-theme-tokens.json` are starting constraints, not permission to bypass an existing user template.

Do not claim a presentation is delivery-ready when render QA has not run. A `pass_with_warnings` report requires the warnings to be disclosed for human judgment.
