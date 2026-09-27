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
    .replace(/(?<!\\)%.*$/gm, "")
    .replace(/\\(?:citep|citet|cite)\{[^{}]*\}/g, "")
    .replace(/\\(?:vspace|hspace)\*?\{[^{}]*\}/g, "")
    .replace(/\\rule\{[^{}]*\}\{[^{}]*\}/g, "")
    .replace(/\\(?:centering|boldmath|tiny|footnotesize|small|normalsize)\b/g, "")
    .replace(/\\#/g, "#")
    .replace(/\\\$/g, "$")
    .replace(/\\%/g, "%")
    .replace(/\\(?:cdot|times)/g, "×")
    .replace(/\\pm(?![A-Za-z])/g, "±")
    .replace(/\\(?:bar|overline)\s*\{([A-Za-z])\}/g, "$1\u0304")
    .replace(/\\(?:bar|overline)\s*([A-Za-z])/g, "$1\u0304")
    .replace(/\\uparrow(?![A-Za-z])/g, "↑")
    .replace(/\\downarrow(?![A-Za-z])/g, "↓")
    .replace(/~/g, " ")
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
  const beginMatch = /\\begin\{tabular\*?\}/.exec(table.latex);
  const beginToken = beginMatch?.[0] ?? "\\begin{tabular}";
  const beginIndex = beginMatch ? beginMatch.index : -1;
  const endMatch =
    beginIndex >= 0
      ? /\\end\{tabular\*?\}/.exec(table.latex.slice(beginIndex + beginToken.length))
      : null;
  const endIndex =
    endMatch && beginIndex >= 0 ? beginIndex + beginToken.length + endMatch.index : -1;
  if (beginIndex < 0 || endIndex < 0) {
    throw new RendererError(`Table ${table.table_id} cannot be converted to an editable table`);
  }
  // `tabular` carries one brace group (the column spec); `tabular*` prepends a
  // width argument, so every leading brace group has to be consumed before the
  // row data starts.
  let bodyStart = beginIndex + beginToken.length;
  for (let group = 0; group < 4; group += 1) {
    while (bodyStart < endIndex && /\s/.test(table.latex[bodyStart]!)) bodyStart += 1;
    if (table.latex[bodyStart] !== "{") break;
    let depth = 0;
    let index = bodyStart;
    for (; index < endIndex; index += 1) {
      if (table.latex[index] === "{") depth += 1;
      else if (table.latex[index] === "}") {
        depth -= 1;
        if (depth === 0) break;
      }
    }
    if (depth !== 0) {
      throw new RendererError(
        `Table ${table.table_id} has an invalid tabular column definition`,
      );
    }
    bodyStart = index + 1;
  }
  if (bodyStart >= endIndex) {
    throw new RendererError(`Table ${table.table_id} has an invalid tabular column definition`);
  }
  const body = table.latex.slice(bodyStart, endIndex)
    .replace(/(?<!\\)%.*$/gm, "")
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

const GREEK_SYMBOLS: Record<string, string> = {
  alpha: "α", beta: "β", gamma: "γ", delta: "δ", Delta: "Δ", epsilon: "ε", varepsilon: "ε",
  zeta: "ζ", eta: "η", theta: "θ", kappa: "κ", lambda: "λ", Lambda: "Λ", mu: "μ", nu: "ν",
  xi: "ξ", pi: "π", rho: "ρ", sigma: "σ", Sigma: "Σ", tau: "τ", phi: "φ", varphi: "φ",
  chi: "χ", psi: "ψ", omega: "ω", Omega: "Ω",
};

const TEXT_SYMBOLS: Record<string, string> = {
  pm: "±", mp: "∓", times: "×", cdot: "·", div: "÷", leq: "≤", le: "≤", geq: "≥", ge: "≥",
  neq: "≠", approx: "≈", equiv: "≡", propto: "∝", in: "∈", notin: "∉", subset: "⊂",
  mid: "|", star: "⋆", ast: "∗", to: "→", rightarrow: "→", mapsto: "↦", infty: "∞",
  partial: "∂", nabla: "∇", sum: "Σ", prod: "Π", int: "∫", min: "min", max: "max",
  log: "log", exp: "exp", det: "det", argmin: "arg min", argmax: "arg max", sg: "sg",
  quad: " ", qquad: "  ", ",": " ", ";": " ", ":": " ", "!": "", " ": " ", "%": "%",
  mathcal: "", mathbf: "", mathrm: "", mathit: "", mathsf: "", mathbb: "", boldsymbol: "",
  operatorname: "", text: "", textbf: "", texttt: "", displaystyle: "", textstyle: "",
  limits: "", nolimits: "", left: "", right: "", bm: "", sf: "", tt: "",
};

const ACCENT_PRECOMPOSED: Record<string, Record<string, string>> = {
  "\u0302": { a: "â", c: "ĉ", e: "ê", g: "ĝ", h: "ĥ", i: "î", j: "ĵ", o: "ô", s: "ŝ", u: "û", w: "ŵ", y: "ŷ", z: "ẑ" },
  "\u0304": { a: "ā", e: "ē", i: "ī", o: "ō", u: "ū" },
  "\u0303": { a: "ã", n: "ñ", o: "õ" },
};

function readGroup(text: string, start: number): { value: string; end: number } | null {
  let index = start;
  while (index < text.length && /\s/.test(text[index] ?? "")) index += 1;
  if (text[index] !== "{") return null;
  let depth = 0;
  for (let cursor = index; cursor < text.length; cursor += 1) {
    if (text[cursor] === "{") depth += 1;
    else if (text[cursor] === "}") {
      depth -= 1;
      if (depth === 0) return { value: text.slice(index + 1, cursor), end: cursor + 1 };
    }
  }
  return null;
}

function readBareToken(text: string, start: number): { value: string; end: number } | null {
  let index = start;
  while (index < text.length && /\s/.test(text[index] ?? "")) index += 1;
  const character = text[index] ?? "";
  if (character === "" || character === "}" || character === "{") return null;
  if (character === "\\") {
    const match = /^\\[A-Za-z]+/.exec(text.slice(index));
    if (!match) return null;
    return { value: match[0], end: index + match[0].length };
  }
  return { value: character, end: index + character.length };
}

function replaceCommand(
  text: string,
  command: string,
  arity: number,
  build: (args: string[]) => string,
): string {
  const token = `\\${command}`;
  let result = "";
  let cursor = 0;
  for (;;) {
    const found = text.indexOf(token, cursor);
    if (found < 0) {
      result += text.slice(cursor);
      return result;
    }
    const next = text[found + token.length] ?? "";
    if (/[A-Za-z]/.test(next)) {
      result += text.slice(cursor, found + token.length);
      cursor = found + token.length;
      continue;
    }
    const args: string[] = [];
    let scan = found + token.length;
    let matched = true;
    for (let index = 0; index < arity; index += 1) {
      const group = readGroup(text, scan);
      if (group) {
        args.push(group.value);
        scan = group.end;
        continue;
      }
      // Arguments are often written without braces, for example `\hat z_t`,
      // `\mathcal A`, `\tfrac12` or `\tfrac\beta2`.
      const bare = readBareToken(text, scan);
      if (bare) {
        args.push(bare.value);
        scan = bare.end;
        continue;
      }
      matched = false;
      break;
    }
    if (!matched) {
      result += text.slice(cursor, found + token.length);
      cursor = found + token.length;
      continue;
    }
    result += text.slice(cursor, found) + build(args);
    cursor = scan;
  }
}

function applyAccent(mark: string, base: string): string {
  const trimmed = base.trim();
  if (trimmed.length === 1) {
    const precomposed = ACCENT_PRECOMPOSED[mark]?.[trimmed.toLowerCase()];
    if (precomposed) return base.replace(trimmed, precomposed);
  }
  return `${trimmed}${mark}`;
}

export function latexToText(latex: string): string {
  let value = latex
    .replace(/(?<!\\)%.*$/gm, "")
    .replace(/\\(?:label|tag|nonumber)\{[^{}]*\}/g, "")
    .replace(/\\(?:begin|end)\{[^{}]*\}/g, "")
    .replace(/\\boxed(?=\s*\{)/g, "")
    .replace(/\\color\{[^{}]*\}/g, "")
    .replace(/\\!/g, "")
    .replace(/\\(?:[,;:>]|quad|qquad| )/g, " ")
    .replace(/\\(?:left|right|big|Big|bigg|Bigg)\b/g, "")
    .replace(/\\\\/g, "\n");

  // Zero-argument commands and text operators are resolved before structural
  // commands, otherwise a replacement can glue a control word to a following
  // letter (`\in\mathcal A` would otherwise be rescanned as `\inA`).
  value = value.replace(/\\([A-Za-z]+)/g, (match: string, name: string) => {
    const symbol = GREEK_SYMBOLS[name] ?? TEXT_SYMBOLS[name];
    return symbol ?? match;
  });

  for (let pass = 0; pass < 5; pass += 1) {
    value = replaceCommand(value, "frac", 2, ([top = "", bottom = ""]) => `(${latexToText(top)})/(${latexToText(bottom)})`);
    value = replaceCommand(value, "tfrac", 2, ([top = "", bottom = ""]) => `(${latexToText(top)})/(${latexToText(bottom)})`);
    value = replaceCommand(value, "dfrac", 2, ([top = "", bottom = ""]) => `(${latexToText(top)})/(${latexToText(bottom)})`);
    value = replaceCommand(value, "sqrt", 1, ([body = ""]) => `√(${latexToText(body)})`);
    value = replaceCommand(value, "hat", 1, ([body = ""]) => applyAccent("\u0302", latexToText(body)));
    value = replaceCommand(value, "bar", 1, ([body = ""]) => applyAccent("\u0304", latexToText(body)));
    value = replaceCommand(value, "overline", 1, ([body = ""]) => applyAccent("\u0304", latexToText(body)));
    value = replaceCommand(value, "tilde", 1, ([body = ""]) => applyAccent("\u0303", latexToText(body)));
    value = replaceCommand(value, "dot", 1, ([body = ""]) => applyAccent("\u0307", latexToText(body)));
    for (const wrapper of ["mathcal", "mathbf", "mathrm", "mathit", "mathsf", "operatorname", "text", "textbf", "texttt"]) {
      value = replaceCommand(value, wrapper, 1, ([body = ""]) => latexToText(body));
    }
  }

  value = value
    .replace(/\\\|/g, "‖")
    .replace(/\\([%#&_${}])/g, "$1")
    .replace(/&/g, "");
  value = applyScript(value);
  return value
    .replace(/[{}]/g, "")
    .replace(/[_^]\s+/g, (match: string) => match.trim())
    .replace(/[ \t]+/g, " ")
    .replace(/\s*\n\s*/g, " ")
    .replace(/\s+([,;.)\]])/g, "$1")
    .trim();
}

const SUPERSCRIPT_MAP: Record<string, string> = {
  "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷",
  "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾", i: "ⁱ", n: "ⁿ",
  T: "ᵀ",
};

const SUBSCRIPT_MAP: Record<string, string> = {
  "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇",
  "8": "₈", "9": "₉", "+": "₊", "-": "₋", "=": "₌", a: "ₐ", e: "ₑ", h: "ₕ", i: "ᵢ",
  j: "ⱼ", k: "ₖ", l: "ₗ", m: "ₘ", n: "ₙ", o: "ₒ", p: "ₚ", r: "ᵣ", s: "ₛ", t: "ₜ",
  u: "ᵤ", v: "ᵥ", x: "ₓ",
};

function toScript(content: string, map: Record<string, string>): string | null {
  let result = "";
  for (const character of content) {
    const mapped = map[character];
    if (mapped === undefined) return null;
    result += mapped;
  }
  return result;
}

function applyScript(value: string): string {
  const collapse = (content: string, map: Record<string, string>, prefix: string): string => {
    const trimmed = content.trim();
    if (/^[A-Za-z0-9]+$/.test(trimmed)) return `${prefix}${trimmed}`;
    const scripted = toScript(trimmed, map);
    return scripted ?? `${prefix}(${trimmed})`;
  };
  return value
    .replace(/\^\{([^{}]*)\}/g, (_match, content: string) => collapse(content, SUPERSCRIPT_MAP, "^"))
    .replace(/_\{([^{}]*)\}/g, (_match, content: string) => collapse(content, SUBSCRIPT_MAP, "_"))
    .replace(/\^([0-9+\-=])/g, (_match, character: string) => SUPERSCRIPT_MAP[character] ?? _match)
    .replace(/_([0-9+\-=])/g, (_match, character: string) => SUBSCRIPT_MAP[character] ?? _match);
}

function equationRuns(equation: PaperEquation, theme: ThemeTokens): TextRun[] {
  return [{ text: latexToText(equation.latex), options: { fontFace: theme.equationFontFamily } }];
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
