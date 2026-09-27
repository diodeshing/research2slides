import type { Box } from "../layouts/index.js";
import type { SlideLike } from "../pptx.js";
import type { SlideSpecSlide, ThemeTokens } from "../types.js";

const LINE = "line";

export function addBodyText(
  slide: SlideLike,
  specSlide: SlideSpecSlide,
  theme: ThemeTokens,
  box: Box,
  emphasizeClaim = false,
): void {
  if (emphasizeClaim) {
    slide.addText(specSlide.main_claim, {
      x: box.x,
      y: box.y,
      w: box.w,
      h: Math.min(1.5, box.h * 0.38),
      fontFace: theme.fontFamily,
      fontSize: theme.bodySize + 6,
      bold: true,
      color: theme.text,
      margin: 0,
      fit: "shrink",
      valign: "mid",
      lang: "zh-CN",
    });
  }
  const startY = emphasizeClaim ? box.y + Math.min(1.7, box.h * 0.42) : box.y;
  const available = box.h - (startY - box.y);
  const gap = Math.min(0.2, available * 0.06);
  const lineHeight = Math.min(0.82, (available - gap * Math.max(0, specSlide.body.length - 1)) / specSlide.body.length);
  specSlide.body.forEach((line, index) => {
    const y = startY + index * (lineHeight + gap);
    slide.addShape(LINE, {
      x: box.x,
      y: y + 0.12,
      w: 0.18,
      h: 0,
      line: { color: index === 0 ? theme.accent : theme.secondary, width: 2.5 },
    });
    slide.addText(line, {
      x: box.x + 0.32,
      y,
      w: box.w - 0.32,
      h: lineHeight,
      fontFace: theme.fontFamily,
      fontSize: theme.bodySize,
      color: theme.text,
      margin: 0,
      fit: "shrink",
      valign: "mid",
      lang: "zh-CN",
    });
  });
}
