import { RendererError } from "./errors.js";
import type { SlideLayout, SlideSpec, ThemeName, VisualKind } from "./types.js";

const THEMES = new Set<ThemeName>(["conference-minimal", "group-meeting"]);
const LAYOUTS = new Set<SlideLayout>([
  "minimal_text",
  "visual_left_text_right",
  "text_left_visual_right",
  "full_visual",
  "comparison",
  "equation_focus",
  "table_focus",
  "process",
]);
const VISUAL_KINDS = new Set<VisualKind>([
  "source_asset",
  "source_table",
  "source_equation",
  "conceptual_diagram",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(record: Record<string, unknown>, key: string, context: string): string {
  const value = record[key];
  if (typeof value !== "string" || value.trim() === "") {
    throw new RendererError(`${context}.${key} must be a non-empty string`);
  }
  return value;
}

function requiredArray(record: Record<string, unknown>, key: string, context: string): unknown[] {
  const value = record[key];
  if (!Array.isArray(value)) {
    throw new RendererError(`${context}.${key} must be an array`);
  }
  return value;
}

export function validateSlideSpec(value: unknown): asserts value is SlideSpec {
  if (!isRecord(value)) {
    throw new RendererError("slide_spec.json must contain an object");
  }
  if (value.schema_version !== "1.1") {
    throw new RendererError("Renderer supports slide_spec schema_version 1.1 only");
  }
  const paperId = requiredString(value, "paper_id", "slide_spec");
  const theme = requiredString(value, "theme", "slide_spec") as ThemeName;
  if (!THEMES.has(theme)) {
    throw new RendererError(`Unsupported theme: ${theme}`);
  }
  requiredString(value, "title", "slide_spec");
  if (value.language !== "zh-CN" || value.language_profile !== "zh_cn_bilingual_terms") {
    throw new RendererError("Renderer requires the zh_cn_bilingual_terms language profile");
  }
  if (!isRecord(value.presentation)) {
    throw new RendererError("slide_spec.presentation must be an object");
  }
  const presentation = value.presentation;
  if (
    presentation.language !== "zh-CN"
    || presentation.terminology_mode !== "bilingual"
    || presentation.preserve_source_visual_language !== true
    || presentation.translate_generic_labels !== true
    || presentation.translate_speaker_notes !== true
  ) {
    throw new RendererError("slide_spec.presentation does not match zh_cn_bilingual_terms");
  }
  const slides = requiredArray(value, "slides", "slide_spec");
  if (slides.length === 0) {
    throw new RendererError("slide_spec.slides cannot be empty");
  }
  const ids = new Set<string>();
  const units = new Set<string>();
  let seconds = 0;
  slides.forEach((rawSlide, index) => {
    const context = `slide_spec.slides[${index}]`;
    if (!isRecord(rawSlide)) {
      throw new RendererError(`${context} must be an object`);
    }
    const slideId = requiredString(rawSlide, "slide_id", context);
    const unitId = requiredString(rawSlide, "unit_id", context);
    if (ids.has(slideId) || units.has(unitId)) {
      throw new RendererError(`${context} contains a duplicate slide_id or unit_id`);
    }
    ids.add(slideId);
    units.add(unitId);
    if (rawSlide.order !== index + 1) {
      throw new RendererError(`${context}.order must be ${index + 1}`);
    }
    for (const key of ["section", "purpose", "question", "title", "main_claim", "takeaway"]) {
      requiredString(rawSlide, key, context);
    }
    if (!LAYOUTS.has(rawSlide.layout as SlideLayout)) {
      throw new RendererError(`${context}.layout is unsupported`);
    }
    const body = requiredArray(rawSlide, "body", context);
    if (body.length === 0 || body.some((item) => typeof item !== "string" || item.trim() === "")) {
      throw new RendererError(`${context}.body must contain non-empty strings`);
    }
    const citations = requiredArray(rawSlide, "citations", context);
    if (citations.length === 0) {
      throw new RendererError(`${context}.citations cannot be empty`);
    }
    const visuals = requiredArray(rawSlide, "visuals", context);
    for (const [visualIndex, rawVisual] of visuals.entries()) {
      const visualContext = `${context}.visuals[${visualIndex}]`;
      if (!isRecord(rawVisual)) {
        throw new RendererError(`${visualContext} must be an object`);
      }
      requiredString(rawVisual, "visual_id", visualContext);
      requiredString(rawVisual, "source_ref", visualContext);
      if (!VISUAL_KINDS.has(rawVisual.kind as VisualKind)) {
        throw new RendererError(`${visualContext}.kind is unsupported`);
      }
      if (rawVisual.table_column_labels !== null && rawVisual.table_column_labels !== undefined) {
        if (
          rawVisual.kind !== "source_table"
          || !Array.isArray(rawVisual.table_column_labels)
          || rawVisual.table_column_labels.length === 0
          || rawVisual.table_column_labels.some(
            (label) => typeof label !== "string" || label.trim() === "",
          )
        ) {
          throw new RendererError(`${visualContext}.table_column_labels is invalid`);
        }
      }
    }
    if (!isRecord(rawSlide.speaker_notes)) {
      throw new RendererError(`${context}.speaker_notes must be an object`);
    }
    for (const key of ["purpose", "main_message", "script", "visual_guidance", "transition"]) {
      requiredString(rawSlide.speaker_notes, key, `${context}.speaker_notes`);
    }
    const estimated = rawSlide.speaker_notes.estimated_seconds;
    if (!Number.isInteger(estimated) || Number(estimated) <= 0) {
      throw new RendererError(`${context}.speaker_notes.estimated_seconds must be a positive integer`);
    }
    seconds += Number(estimated);
  });
  if (value.paper_id !== paperId) {
    throw new RendererError("slide_spec.paper_id is invalid");
  }
  if (value.estimated_total_seconds !== seconds) {
    throw new RendererError("slide_spec.estimated_total_seconds does not match speaker notes");
  }
}
