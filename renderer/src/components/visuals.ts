import path from "node:path";
import { readFileSync } from "node:fs";

import { imageSize } from "image-size";

import { RendererError } from "../errors.js";
import type { Box } from "../layouts/index.js";
import type { SlideLike, TextRun } from "../pptx.js";
import type {
  PaperEquation,
  PaperTable,
  RenderInputs,
  SlideSpecSlide,
  SlideVisual,
  ThemeTokens,
} from "../types.js";

const RECT = "rect";
const LINE = "line";
const CHEVRON = "chevron";

function contain(sourceWidth: number, sourceHeight: number, box: Box): Box {
  const scale = Math.min(box.w / sourceWidth, box.h / sourceHeight);
  const w = sourceWidth * scale;
  const h = sourceHeight * scale;
  return { x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h };
}

function cleanLatex(text: string): string {
  let value = text
    .replace(/%.*$/gm, "")
    .replace(/\\(?:citep|citet|cite)\{[^{}]*\}/g, "")
    .replace(/\\(?:vspace|hspace)\*?\{[^{}]*\}/g, "")
    .replace(/\\rule\{[^{}]*\}\{[^{}]*\}/g, "")
    .replace(/\\(?:centering|boldmath|tiny|footnotesize|small|normalsize)\b/g, "")
    .replace(/\\#/g, "#")
    .replace(/\\\$/g, "$")
    .replace(/\\(?:cdot|times)/g, "×")
    .replace(/\\_/g, "_");
  for (let index = 0; index < 4; index += 1) {
    value = value
      .replace(/\\(?:textbf|emph|mathrm|mathbf|operatorname)\{([^{}]*)\}/g, "$1")
      .replace(
        /\\(?:multirow|multicolumn)\{[^{}]*\}\{[^{}]*\}\{((?:[^{}]|\{[^{}]*\})*)\}/g,
        "$1",
      );
  }
  return value
    .replace(/\^\{([^{}]*)\}/g, "^$1")
    .replace(/_\{([^{}]*)\}/g, "_$1")
    .replace(/\\[A-Za-z@]+\*?(?:\{[^{}]*\})?/g, "")
    .replace(/\\_/g, "_")
    .replace(/\$+/g, "")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function parseLatexTable(table: PaperTable): string[][] {
  const beginToken = "\\begin{tabular}";
  const beginIndex = table.latex.indexOf(beginToken);
  const endIndex = table.latex.indexOf("\\end{tabular}", beginIndex + beginToken.length);
  let bodyStart = beginIndex + beginToken.length;
  if (beginIndex < 0 || endIndex < 0 || table.latex[bodyStart] !== "{") {
    throw new RendererError(`Table ${table.table_id} cannot be converted to an editable table`);
  }
  let depth = 0;
  for (let index = bodyStart; index < endIndex; index += 1) {
    if (table.latex[index] === "{") depth += 1;
    if (table.latex[index] === "}") {
      depth -= 1;
      if (depth === 0) {
        bodyStart = index + 1;
        break;
      }
    }
  }
  if (depth !== 0 || bodyStart >= endIndex) {
    throw new RendererError(`Table ${table.table_id} has an invalid tabular column definition`);
  }
  const body = table.latex.slice(bodyStart, endIndex)
    .replace(/%.*$/gm, "")
    .replace(/\\(?:toprule|midrule|bottomrule|hline)\b/g, "\\\\")
    .replace(/\\cmidrule(?:\([^)]*\))?\{[^{}]*\}/g, "")
    .replace(/\\specialrule\{[^{}]*\}\{[^{}]*\}\{[^{}]*\}/g, "\\\\");
  const rows = body
    .split(/\\\\(?:\[[^\]]*\])?/)
    .map((row) => row.trim())
    .filter(Boolean)
    .map((row) => row.split("&").map(cleanLatex))
    .filter((row) => row.some(Boolean));
  const columnCount = Math.max(...rows.map((row) => row.length));
  return rows.map((row) => [...row, ...Array(Math.max(0, columnCount - row.length)).fill("")]);
}

function addPanel(slide: SlideLike, theme: ThemeTokens, box: Box): void {
  slide.addShape(RECT, {
    ...box,
    fill: { color: theme.surface },
    line: { color: theme.accentSoft, width: theme.lineWidth },
    shadow: { type: "outer", color: "AAB2C0", opacity: 0.12, blur: 1, angle: 45, distance: 0.5 },
  });
}

function renderSourceAsset(
  slide: SlideLike,
  visual: SlideVisual,
  inputs: RenderInputs,
  box: Box,
): void {
  const asset = inputs.visuals.assets.find((item) => item.asset_id === visual.source_ref);
  if (!asset) {
    throw new RendererError(`Unknown source asset ${visual.source_ref}`);
  }
  const assetPath = path.resolve(inputs.workspace, asset.output_path);
  let dimensions: { width: number; height: number };
  try {
    const measured = imageSize(readFileSync(assetPath));
    if (!measured.width || !measured.height) {
      throw new Error("missing dimensions");
    }
    dimensions = { width: measured.width, height: measured.height };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new RendererError(`Unable to measure visual ${assetPath}: ${message}`);
  }
  const imageBox = contain(dimensions.width, dimensions.height, {
    x: box.x + 0.12,
    y: box.y + 0.12,
    w: box.w - 0.24,
    h: box.h - (visual.caption ? 0.52 : 0.24),
  });
  slide.addImage({ path: assetPath, ...imageBox });
  if (visual.caption) {
    slide.addText(visual.caption, {
      x: box.x + 0.18,
      y: box.y + box.h - 0.32,
      w: box.w - 0.36,
      h: 0.22,
      fontFace: inputs.theme.fontFamily,
      fontSize: 9.5,
      italic: true,
      color: inputs.theme.muted,
      align: "center",
      margin: 0,
      fit: "shrink",
    });
  }
}

function renderTable(
  slide: SlideLike,
  visual: SlideVisual,
  table: PaperTable,
  theme: ThemeTokens,
  box: Box,
): void {
  let rows = parseLatexTable(table);
  if (visual.treatment === "highlight" && rows.length > 8) {
    const columns = Math.max(...rows.map((row) => row.length));
    rows = [
      ...rows.slice(0, 2),
      ["…", ...Array(Math.max(0, columns - 1)).fill("")],
      ...rows.slice(-4),
    ];
  }
  if (visual.table_column_labels) {
    if (visual.table_column_labels.length !== rows[0]?.length) {
      throw new RendererError(`Table ${table.table_id} column labels do not match source data`);
    }
    rows[0] = [...visual.table_column_labels];
  }
  const tableRows: unknown[][] = rows.map((row, rowIndex) =>
    row.map((text) => ({
      text,
      options: {
        bold: rowIndex === 0,
        color: theme.text,
        fill: rowIndex === 0 ? theme.accentSoft : rowIndex % 2 === 0 ? theme.surface : theme.background,
        align: rowIndex === 0 ? "center" : "left",
        valign: "mid",
      },
    })),
  );
  const columnCount = Math.max(...rows.map((row) => row.length));
  const tableFontSize = Math.max(
    8,
    Math.min(
      13,
      13 - Math.max(0, rows.length - 5) * 0.35 - Math.max(0, columnCount - 4) * 0.4,
    ),
  );
  slide.addTable(tableRows, {
    x: box.x + 0.25,
    y: box.y + 0.3,
    w: box.w - 0.5,
    h: box.h - 1.0,
    fontFace: theme.fontFamily,
    fontSize: tableFontSize,
    color: theme.text,
    border: { color: theme.accentSoft, width: 1 },
    margin: 0.06,
    rowH: Math.min(0.48, (box.h - 1.0) / rows.length),
    lang: "zh-CN",
  });
  if (visual.caption) {
    slide.addText(visual.caption, {
      x: box.x + 0.25,
      y: box.y + box.h - 0.28,
      w: box.w - 0.5,
      h: 0.2,
      fontFace: theme.fontFamily,
      fontSize: 9.5,
      italic: true,
      color: theme.muted,
      align: "center",
      margin: 0,
      lang: "zh-CN",
    });
  }
}

function equationRuns(equation: PaperEquation, theme: ThemeTokens): TextRun[] {
  let value = equation.latex;
  for (let index = 0; index < 4; index += 1) {
    value = value
      .replace(/\\sqrt\{([^{}]*)\}/g, "√($1)")
      .replace(/\\frac\{([^{}]*)\}\{([^{}]*)\}/g, "($1)/($2)")
      .replace(/\\(?:mathrm|mathbf|operatorname|text)\{([^{}]*)\}/g, "$1");
  }
  value = value
    .replace(/\\boxed\{|\\color\{[^{}]*\}/g, "")
    .replace(/\\(?:left|right)\b/g, "")
    .replace(/\\leq/g, "≤")
    .replace(/\\geq/g, "≥")
    .replace(/\\cdot/g, "·")
    .replace(/\\\\/g, "\n")
    .replace(/\^\{([^{}]*)\}/g, "^$1")
    .replace(/_\{([^{}]*)\}/g, "_$1")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return [{ text: value, options: { fontFace: theme.equationFontFamily } }];
}

function renderEquation(
  slide: SlideLike,
  visual: SlideVisual,
  equation: PaperEquation,
  theme: ThemeTokens,
  box: Box,
): void {
  slide.addText(equationRuns(equation, theme), {
    x: box.x + 0.35,
    y: box.y + 0.35,
    w: box.w - 0.7,
    h: box.h - 0.72,
    fontFace: theme.equationFontFamily,
    fontSize: 27,
    color: theme.text,
    align: "center",
    valign: "mid",
    margin: 0.08,
    fit: "shrink",
    lang: "zh-CN",
  });
  slide.addText(visual.caption ?? `Equation ${equation.number ?? ""}`.trim(), {
    x: box.x + 0.35,
    y: box.y + box.h - 0.3,
    w: box.w - 0.7,
    h: 0.2,
    fontFace: theme.fontFamily,
    fontSize: 9.5,
    italic: true,
    color: theme.muted,
    align: "center",
    margin: 0,
  });
}

export function addConceptualDiagram(
  slide: SlideLike,
  specSlide: SlideSpecSlide,
  theme: ThemeTokens,
  box: Box,
): void {
  const labels = specSlide.body.slice(0, 4);
  const gap = 0.24;
  const width = (box.w - gap * Math.max(0, labels.length - 1)) / labels.length;
  const y = box.y + box.h * 0.25;
  labels.forEach((label, index) => {
    const x = box.x + index * (width + gap);
    slide.addShape(index === labels.length - 1 ? RECT : CHEVRON, {
      x,
      y,
      w: width,
      h: box.h * 0.5,
      fill: { color: index === 0 ? theme.accentSoft : theme.surface },
      line: { color: index === 0 ? theme.accent : theme.secondary, width: theme.lineWidth },
    });
    slide.addText(label, {
      x: x + 0.12,
      y: y + 0.12,
      w: width - 0.24,
      h: box.h * 0.5 - 0.24,
      fontFace: theme.fontFamily,
      fontSize: Math.max(13, theme.bodySize - 2),
      bold: index === 0,
      color: theme.text,
      align: "center",
      valign: "mid",
      margin: 0.02,
      fit: "shrink",
      lang: "zh-CN",
    });
  });
}

function renderAnnotation(
  slide: SlideLike,
  annotation: string,
  theme: ThemeTokens,
  box: Box,
): void {
  slide.addShape(LINE, {
    x: box.x + 0.18,
    y: box.y + 0.18,
    w: 0.35,
    h: 0,
    line: { color: theme.warning, width: 2.5 },
  });
  slide.addText(annotation, {
    x: box.x + 0.62,
    y: box.y + 0.05,
    w: box.w - 0.82,
    h: 0.28,
    fontFace: theme.fontFamily,
    fontSize: 9.5,
    color: theme.warning,
    margin: 0,
    fit: "shrink",
    lang: "zh-CN",
  });
}

function renderOneVisual(
  slide: SlideLike,
  specSlide: SlideSpecSlide,
  visual: SlideVisual,
  inputs: RenderInputs,
  box: Box,
): void {
  addPanel(slide, inputs.theme, box);
  if (visual.kind === "source_asset") {
    renderSourceAsset(slide, visual, inputs, box);
  } else if (visual.kind === "source_table") {
    const table = inputs.paper.tables.find((item) => item.table_id === visual.source_ref);
    if (!table) throw new RendererError(`Unknown source table ${visual.source_ref}`);
    renderTable(slide, visual, table, inputs.theme, box);
  } else if (visual.kind === "source_equation") {
    const equation = inputs.paper.equations.find((item) => item.equation_id === visual.source_ref);
    if (!equation) throw new RendererError(`Unknown source equation ${visual.source_ref}`);
    renderEquation(slide, visual, equation, inputs.theme, box);
  } else {
    addConceptualDiagram(slide, specSlide, inputs.theme, box);
  }
  const annotation = visual.annotations[0];
  if (annotation && visual.kind !== "source_table") {
    renderAnnotation(slide, annotation, inputs.theme, box);
  }
}

export function addVisuals(
  slide: SlideLike,
  specSlide: SlideSpecSlide,
  inputs: RenderInputs,
  box: Box,
): void {
  if (specSlide.visuals.length === 0) return;
  const gap = 0.18;
  const height = (box.h - gap * (specSlide.visuals.length - 1)) / specSlide.visuals.length;
  specSlide.visuals.forEach((visual, index) => {
    renderOneVisual(slide, specSlide, visual, inputs, {
      x: box.x,
      y: box.y + index * (height + gap),
      w: box.w,
      h: height,
    });
  });
}
