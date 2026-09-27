# Phase 5.1 Implementation Report

Date: 2026-09-26  
Status: Complete for Chinese-first bilingual terminology; Phase 6 has not started.

## Outcome

The default presentation language profile is now `zh_cn_bilingual_terms`. Presentation Plan and Slide Spec directly contain natural Chinese research-presentation wording, while established English technical terms, equations, model names, dataset names, metrics, and source-figure labels remain unchanged where precision requires them.

The implementation does not use an `English slide -> machine translation -> Chinese slide` pipeline. Scientific Understanding remains source-grounded and language-independent; presentation wording begins in Planning and becomes render-ready in Slide Spec.

## Changed files and rationale

- `research2slides/models.py`: added typed language profile/config fields and editable-table column labels.
- `research2slides/language_policy.py`: added local CJK gates for Plan and Slide Spec text.
- `research2slides/planning/*`: carried the selected language profile into context, fingerprints, validation, and artifacts.
- `research2slides/slide_authoring/*`: required Plan/Spec policy consistency and rejected English-first slide content.
- `prompts/*storyline.md` and `prompts/*slides.md`: changed authoring instructions from vague bilingual guidance to direct Chinese-first scientific writing rules.
- `research2slides/narration/speaker_notes.py`: generated a Chinese-first outline while retaining stable schema field names.
- `renderer/src/*`: added language metadata, font-candidate resolution, typed table-header overrides, and stable fixed-size takeaway rendering. No translation logic was added.
- `themes/*/theme.json`: added the same CJK font fallback order to both themes.
- `tests/fixtures/*`: rewrote storylines, slide specs, notes, takeaways, and annotations as Chinese-first bilingual content.
- `tests/test_planning.py`, `tests/test_slide_authoring.py`, `renderer/tests/renderer.test.ts`: added policy rejection and ten bilingual/CJK acceptance scenarios.
- `schemas/*`, examples, README, architecture, and project skill: synchronized contracts and usage documentation.

## Language architecture

```text
Scientific meaning
  -> Chinese presentation planning
  -> Chinese-first Slide Spec with bilingual terminology
  -> layout-only Renderer
```

`presentation_plan.json` and `slide_spec.json` now declare:

```json
{
  "language": "zh-CN",
  "language_profile": "zh_cn_bilingual_terms",
  "presentation": {
    "language": "zh-CN",
    "terminology_mode": "bilingual",
    "preserve_source_visual_language": true,
    "translate_generic_labels": true,
    "translate_speaker_notes": true
  }
}
```

The schema changed by adding typed language-policy fields and `table_column_labels`. Prompt versions changed to the Phase 5.1 bilingual variants. Renderer architecture remains unchanged apart from CJK typography and applying content decisions already present in Slide Spec.

## Tests added

The Renderer suite now explicitly covers:

1. Chinese title rendering.
2. Chinese text with English terminology.
3. CJK run preservation and line-wrapping metadata.
4. Bilingual annotations.
5. Chinese takeaway text.
6. Chinese speaker notes.
7. Original English Figure preservation.
8. English model names with localized generic table headers.
9. `conference-minimal` theme compatibility.
10. `group-meeting` theme compatibility.

Python tests also verify language-profile propagation, CJK Plan/Spec content, outline generation, table-header configuration, and rejection of English-first slide copy.

## Acceptance result

- Python: 28 tests passed.
- TypeScript Renderer: 14 tests passed.
- Both six-slide PPTX files opened and exported through the local presentation application.
- All 12 pages were inspected at full size. Long takeaway compatibility clipping and a crowded closing title were repaired and rechecked.
- Original Figure labels remain English; Equation notation remains unchanged; editable table headers are Chinese while model names and values remain original.
- Both themes use Microsoft YaHei in the current Windows environment and declare CJK fallback candidates.

## Outputs

- `examples/phase5/paper-reading/output/presentation.pptx`
- `examples/phase5/paper-reading/output/phase5.1-preview/`
- `examples/phase5/own-research/output/presentation.pptx`
- `examples/phase5/own-research/output/phase5.1-preview/`

## Known limitations

- Font availability still depends on the target machine. The renderer selects known installed Windows candidates and supports `RESEARCH2SLIDES_FONT_FAMILY`, but PowerPoint may substitute fonts on another system.
- The terminology policy is prompt- and artifact-validated, not a global linguistic translation engine. A future terminology registry may improve consistency across very long decks.
- The editable LaTeX-table parser still targets straightforward `tabular` input.
- Equations remain editable text rather than native Office Math.
- PDF/PNG production is acceptance tooling rather than a product CLI guarantee.
- Automatic visual/factual/storyline QA and repair remain Phase 6 work and were not started.
