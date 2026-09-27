import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import JSZip from "jszip";

import {
  boxesFor,
  loadRenderInputs,
  latexToText,
  parseLatexTable,
  renderWorkspace,
  validateSlideSpec,
} from "../src/index.js";
import type { PaperStructure, SlideLayout, SlideSpec } from "../src/types.js";

const ROOT = process.cwd();
const WORKSPACE = path.join(ROOT, "examples", "phase5", "paper-reading");
const OWN_WORKSPACE = path.join(ROOT, "examples", "phase5", "own-research");
const CJK = /[\u3400-\u4dbf\u4e00-\u9fff]/;

async function archiveFor(workspace: string, label: string): Promise<JSZip> {
  const output = path.join(tmpdir(), `research2slides-${process.pid}-${label}.pptx`);
  await renderWorkspace(workspace, output, {}, true);
  return JSZip.loadAsync(await readFile(output));
}

async function slideXml(archive: JSZip, number: number): Promise<string> {
  return archive.file(`ppt/slides/slide${number}.xml`)!.async("string");
}

test("slide spec validates and rejects order drift", async () => {
  const raw = JSON.parse(await readFile(path.join(WORKSPACE, "data", "slide_spec.json"), "utf8")) as SlideSpec;
  validateSlideSpec(raw);
  const invalid = structuredClone(raw);
  invalid.slides[1]!.order = 1;
  assert.throws(() => validateSlideSpec(invalid), /order must be 2/);
});

test("all declared layouts resolve to reusable geometry", () => {
  const layouts: SlideLayout[] = [
    "minimal_text",
    "visual_left_text_right",
    "text_left_visual_right",
    "full_visual",
    "comparison",
    "equation_focus",
    "table_focus",
    "process",
  ];
  for (const layout of layouts) {
    const boxes = boxesFor(layout);
    for (const box of Object.values(boxes)) {
      assert.ok(box.x >= 0 && box.y >= 0 && box.w > 0 && box.h >= 0);
      assert.ok(box.x + box.w <= 13.34);
      assert.ok(box.y + box.h <= 7.5);
    }
  }
});

test("LaTeX table becomes editable row and column data", async () => {
  const paper = JSON.parse(await readFile(path.join(WORKSPACE, "data", "paper_structure.json"), "utf8")) as PaperStructure;
  const rows = parseLatexTable(paper.tables[0]!);
  assert.deepEqual(rows, [
    ["System", "Score"],
    ["Fixture baseline", "10.0"],
    ["Fixture model", "11.0"],
  ]);
});

test("complex LaTeX table commands are removed without losing values", () => {
  const rows = parseLatexTable({
    table_id: "table_complex",
    number: "1",
    caption: "Complex table",
    latex: String.raw`\begin{tabular}{l@{\extracolsep{\fill}}cc}
\toprule
\multirow{2}{*}{\vspace{-2mm}\textbf{Model}} & \multicolumn{2}{c}{\textbf{BLEU}} \\
\cmidrule{2-3}
& EN-DE & EN-FR \\
\midrule
Transformer \citep{paper} & \textbf{28.4} & $41.8$ \\
\bottomrule
\end{tabular}`,
  });
  assert.deepEqual(rows, [
    ["Model", "BLEU", ""],
    ["", "EN-DE", "EN-FR"],
    ["Transformer", "28.4", "41.8"],
  ]);
});

test("starred tabular environments parse with width arguments skipped", () => {
  const rows = parseLatexTable({
    table_id: "table_starred",
    number: "2",
    caption: "Starred tabular",
    latex: String.raw`\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llrr@{}}
\toprule
\rowcolor{ADHeader}
Method & Inference & HS (\%) & P04 \\
\midrule
LeWM & CEM & $3.7{\pm}1.4$ & $0.0{\pm}0.0$ \\
\rowcolor{ADDefault}
\textbf{AD-WM} & CEM & $52.0{\pm}3.1$ & $25.3{\pm}3.4$ \\
\bottomrule
\end{tabular*}`,
  });
  assert.deepEqual(rows, [
    ["Method", "Inference", "HS (%)", "P04"],
    ["LeWM", "CEM", "3.7±1.4", "0.0±0.0"],
    ["AD-WM", "CEM", "52.0±3.1", "25.3±3.4"],
  ]);
});

test("table cells map math symbols to readable Unicode", () => {
  const rows = parseLatexTable({
    table_id: "table_symbols",
    number: "3",
    caption: "Symbols",
    latex: String.raw`\begin{tabular}{lrrr}
\toprule
Metric & $\bar R_{30}\downarrow$ & HS (\%) $\uparrow$ & One-step MSE $\downarrow$ \\
\midrule
LeWM & $0.074\pm0.006$ & $3.7\pm1.4$ & $2.72\pm0.06$ \\
\bottomrule
\end{tabular}`,
  });
  assert.deepEqual(rows, [
    ["Metric", "R̄_30↓", "HS (%) ↑", "One-step MSE ↓"],
    ["LeWM", "0.074±0.006", "3.7±1.4", "2.72±0.06"],
  ]);
});

test("LaTeX equations convert to readable Unicode text", () => {
  assert.equal(
    latexToText(String.raw`\hat z_{t+1}=z_t+\Delta\hat z_t.`),
    "ẑₜ₊₁=z_t+Δẑ_t.",
  );
  assert.equal(
    latexToText(String.raw`\tfrac12\|\bar e_t-\mu_\eta\|_2^2`),
    "(1)/(2)‖ē_t-μ_η‖₂²",
  );
  assert.equal(
    latexToText(String.raw`\min_{a\in\mathcal A}c^\star(a)`),
    "min_(a∈ A)c^⋆(a)",
  );
  assert.equal(latexToText("Attention(Q,K,V)=softmax(QK^T)V"), "Attention(Q,K,V)=softmax(QK^T)V");
});

test("renderer writes, reuses, and partially renders a PPTX", async () => {
  const stamp = `${process.pid}-${Date.now()}`;
  const full = path.join(tmpdir(), `research2slides-${stamp}.pptx`);
  const first = await renderWorkspace(WORKSPACE, full, {}, true);
  assert.equal(first.reused, false);
  assert.equal(first.renderedSlideIds.length, 6);
  assert.ok((await stat(full)).size > 10_000);
  const archive = await JSZip.loadAsync(await readFile(full));
  const contentTypes = await archive.file("[Content_Types].xml")!.async("string");
  const masterTargets = [...contentTypes.matchAll(/PartName="\/(ppt\/slideMasters\/slideMaster\d+\.xml)"/g)];
  assert.ok(masterTargets.length >= 1);
  assert.ok(masterTargets.every((match) => archive.file(match[1]!) !== null));
  const reused = await renderWorkspace(WORKSPACE, full);
  assert.equal(reused.reused, true);

  const partial = path.join(tmpdir(), `research2slides-${stamp}-partial.pptx`);
  const selected = await renderWorkspace(WORKSPACE, partial, { slideNumbers: [2, 4] }, true);
  assert.deepEqual(selected.renderedSlideIds, ["S02", "S04"]);
  assert.ok((await stat(partial)).size > 8_000);
});

test("Chinese titles are authored directly in slide_spec", async () => {
  const raw = JSON.parse(await readFile(path.join(WORKSPACE, "data", "slide_spec.json"), "utf8")) as SlideSpec;
  assert.equal(raw.language_profile, "zh_cn_bilingual_terms");
  assert.ok(raw.slides.every((slide) => CJK.test(slide.title)));
});

test("Chinese copy preserves English technical terminology", async () => {
  const raw = JSON.parse(await readFile(path.join(WORKSPACE, "data", "slide_spec.json"), "utf8")) as SlideSpec;
  const core = raw.slides[1]!;
  assert.ok(core.body.every((line) => CJK.test(line)));
  assert.match(core.body.join(" "), /Query/);
  assert.match(core.body.join(" "), /Key/);
  assert.match(core.body.join(" "), /Value/);
});

test("CJK text keeps intact runs and zh-CN language metadata", async () => {
  const archive = await archiveFor(WORKSPACE, "cjk-wrap");
  const xml = await slideXml(archive, 2);
  assert.match(xml, /注意力机制通过 Query、Key 与 Value 建立信息交互/);
  assert.match(xml, /lang="zh-CN"/);
  assert.doesNotMatch(xml, /注<\/a:t>\s*<a:t>意/);
});

test("bilingual annotations render as Chinese explanation around English terms", async () => {
  const archive = await archiveFor(WORKSPACE, "annotations");
  const xml = await slideXml(archive, 2);
  assert.match(xml, /突出 Attention 连接/);
  assert.match(xml, /原始架构图保持论文中的英文标签/);
});

test("every takeaway is Chinese-first", async () => {
  const raw = JSON.parse(await readFile(path.join(WORKSPACE, "data", "slide_spec.json"), "utf8")) as SlideSpec;
  assert.ok(raw.slides.every((slide) => CJK.test(slide.takeaway)));
  assert.ok(raw.slides.every((slide) => slide.takeaway.startsWith("核心结论：")));
});

test("speaker notes contain Chinese scripts", async () => {
  const raw = JSON.parse(await readFile(path.join(WORKSPACE, "data", "slide_spec.json"), "utf8")) as SlideSpec;
  assert.ok(raw.slides.every((slide) => CJK.test(slide.speaker_notes.script)));
  const archive = await archiveFor(WORKSPACE, "notes");
  const notes = await archive.file("ppt/notesSlides/notesSlide2.xml")!.async("string");
  assert.match(notes, /Query 表示当前希望查找的信息/);
});

test("original English Figure labels remain unchanged", async () => {
  const source = await readFile(path.join(WORKSPACE, "assets", "figures", "fig_001.svg"), "utf8");
  assert.match(source, /Encoder/);
  assert.match(source, /Decoder/);
  const archive = await archiveFor(WORKSPACE, "source-figure");
  const media = Object.keys(archive.files).filter((name) => /ppt\/media\/.*\.svg$/i.test(name));
  assert.ok(media.length > 0);
  const embedded = await archive.file(media[0]!)!.async("string");
  assert.match(embedded, /Encoder/);
  assert.match(embedded, /Decoder/);
});

test("editable table localizes generic headers and preserves model names", async () => {
  const archive = await archiveFor(WORKSPACE, "table-labels");
  const xml = await slideXml(archive, 4);
  assert.match(xml, /方法/);
  assert.match(xml, /得分/);
  assert.match(xml, /Fixture baseline/);
  assert.match(xml, /Fixture model/);
});

test("conference-minimal supports the bilingual CJK profile", async () => {
  const inputs = await loadRenderInputs(OWN_WORKSPACE);
  assert.equal(inputs.spec.theme, "conference-minimal");
  assert.equal(inputs.spec.language_profile, "zh_cn_bilingual_terms");
  assert.ok(inputs.theme.fontFallbacks.includes("Microsoft YaHei"));
  assert.ok(inputs.spec.slides.every((slide) => CJK.test(slide.title)));
});

test("group-meeting supports the bilingual CJK profile", async () => {
  const inputs = await loadRenderInputs(WORKSPACE);
  assert.equal(inputs.spec.theme, "group-meeting");
  assert.equal(inputs.spec.language_profile, "zh_cn_bilingual_terms");
  assert.ok(inputs.theme.fontFallbacks.includes("Noto Sans CJK SC"));
  assert.ok(inputs.spec.slides.every((slide) => CJK.test(slide.title)));
});
