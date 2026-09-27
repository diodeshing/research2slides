import type { Box } from "../layouts/index.js";
import type { SlideLike } from "../pptx.js";
import type { SlideSpecSlide, ThemeTokens } from "../types.js";

const LINE = "line";
const RECT = "rect";

export function addSlideChrome(
  slide: SlideLike,
  specSlide: SlideSpecSlide,
  theme: ThemeTokens,
  titleBox: Box,
  takeawayBox: Box,
  citationBox: Box,
  displayNumber: number,
): void {
  slide.background = { color: theme.background };
  slide.addText(specSlide.section.toUpperCase(), {
    x: titleBox.x,
    y: 0.2,
    w: 3.7,
    h: 0.25,
    fontFace: theme.fontFamily,
    fontSize: 10,
    bold: true,
    color: theme.accent,
    charSpacing: 1.1,
    margin: 0,
    lang: "zh-CN",
  });
  if (specSlide.technical_title) {
    slide.addText(specSlide.technical_title, {
      x: 8.6,
      y: 0.2,
      w: 3.85,
      h: 0.25,
      fontFace: theme.fontFamily,
      fontSize: theme.technicalTitleSize,
      color: theme.muted,
      align: "right",
      margin: 0,
      lang: "en-US",
    });
  }
  slide.addText(specSlide.title, {
    ...titleBox,
    fontFace: theme.fontFamily,
    fontSize: theme.titleSize,
    bold: true,
    color: theme.text,
    margin: 0,
    fit: "shrink",
    valign: "mid",
    lang: "zh-CN",
  });
  slide.addShape(LINE, {
    x: titleBox.x,
    y: 1.38,
    w: titleBox.w,
    h: 0,
    line: { color: theme.accentSoft, width: theme.lineWidth },
  });
  slide.addShape(RECT, {
    ...takeawayBox,
    fill: { color: theme.accentSoft },
    line: { color: theme.accentSoft, transparency: 100 },
  });
  slide.addShape(RECT, {
    x: takeawayBox.x,
    y: takeawayBox.y,
    w: 0.08,
    h: takeawayBox.h,
    fill: { color: theme.accent },
    line: { color: theme.accent, transparency: 100 },
  });
  slide.addText(specSlide.takeaway, {
    x: takeawayBox.x + 0.2,
    y: takeawayBox.y + 0.06,
    w: takeawayBox.w - 0.4,
    h: takeawayBox.h - 0.12,
    fontFace: theme.fontFamily,
    fontSize: theme.takeawaySize,
    bold: true,
    color: theme.text,
    margin: 0,
    valign: "mid",
    lang: "zh-CN",
  });
  const citations = specSlide.citations.map((item) => item.display_text).join(" · ");
  slide.addText(citations, {
    ...citationBox,
    fontFace: theme.fontFamily,
    fontSize: theme.citationSize,
    color: theme.muted,
    margin: 0,
    fit: "shrink",
    lang: "zh-CN",
  });
  slide.addText(String(displayNumber).padStart(2, "0"), {
    x: 12.35,
    y: 7.04,
    w: 0.28,
    h: 0.2,
    fontFace: theme.fontFamily,
    fontSize: 9,
    color: theme.muted,
    align: "right",
    margin: 0,
    lang: "en-US",
  });
}

export function addSpeakerNotes(slide: SlideLike, specSlide: SlideSpecSlide): void {
  const notes = [
    `Purpose: ${specSlide.speaker_notes.purpose}`,
    `Main Message: ${specSlide.speaker_notes.main_message}`,
    `Speaking Script: ${specSlide.speaker_notes.script}`,
    `Visual Guidance: ${specSlide.speaker_notes.visual_guidance}`,
    `Transition: ${specSlide.speaker_notes.transition}`,
    `Estimated Time: ${specSlide.speaker_notes.estimated_seconds} seconds`,
    `Sources: ${specSlide.citations.map((citation) => citation.display_text).join("; ")}`,
  ].join("\n\n");
  slide.addNotes(notes);
}
