import { createHash } from "node:crypto";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import PptxGenJSModule from "pptxgenjs";

import { RendererError } from "./errors.js";
import { loadRenderInputs, resolveProjectRoot } from "./load.js";
import { renderSlide } from "./renderSlide.js";
import { sanitizePptxContentTypes } from "./sanitize.js";
import type { RenderResult, RenderSelection } from "./types.js";

const RENDERER_VERSION = "phase5.1-v1";

interface RenderManifest {
  renderer_version: string;
  input_fingerprint: string;
  source_spec: string;
  output_path: string;
  slide_ids: string[];
  theme: string;
}

async function fileExists(filePath: string): Promise<boolean> {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function selectedSlides<T extends { order: number }>(slides: T[], selection: RenderSelection): T[] {
  if (!selection.slideNumbers) return slides;
  const requested = [...new Set(selection.slideNumbers)];
  if (requested.length === 0 || requested.some((value) => !Number.isInteger(value) || value < 1)) {
    throw new RendererError("--slides must contain positive slide numbers");
  }
  const requestedSet = new Set(requested);
  const selected = slides.filter((slide) => requestedSet.has(slide.order));
  if (selected.length !== requestedSet.size) {
    const found = new Set(selected.map((slide) => slide.order));
    const missing = requested.filter((value) => !found.has(value));
    throw new RendererError(`Unknown slide numbers: ${missing.join(", ")}`);
  }
  return selected;
}

async function fingerprint(workspace: string, assetPaths: string[], slideIds: string[]): Promise<string> {
  const digest = createHash("sha256");
  const files = [
    path.join(workspace, "data", "slide_spec.json"),
    path.join(workspace, "data", "visual_manifest.json"),
    path.join(workspace, "data", "paper_structure.json"),
    ...assetPaths,
  ];
  for (const filePath of files) {
    digest.update(path.basename(filePath));
    digest.update(await readFile(filePath));
  }
  digest.update(await readFile(path.join(resolveProjectRoot(), "themes", JSON.parse(await readFile(files[0]!, "utf8")).theme, "theme.json")));
  digest.update(slideIds.join(","));
  digest.update(RENDERER_VERSION);
  return digest.digest("hex");
}

export async function renderWorkspace(
  workspacePath: string,
  outputPath: string,
  selection: RenderSelection = {},
  force = false,
): Promise<RenderResult & { reused: boolean }> {
  const inputs = await loadRenderInputs(workspacePath);
  const slides = selectedSlides(inputs.spec.slides, selection);
  const assetPaths = slides
    .flatMap((slide) => slide.visuals)
    .filter((visual) => visual.kind === "source_asset")
    .map((visual) => {
      const asset = inputs.visuals.assets.find((item) => item.asset_id === visual.source_ref);
      if (!asset) throw new RendererError(`Unknown source asset ${visual.source_ref}`);
      return path.resolve(inputs.workspace, asset.output_path);
    });
  const resolvedOutput = path.resolve(outputPath);
  const manifestPath = resolvedOutput.replace(/\.pptx$/i, ".render.json");
  const inputFingerprint = await fingerprint(inputs.workspace, assetPaths, slides.map((slide) => slide.slide_id));

  if (!force && await fileExists(resolvedOutput) && await fileExists(manifestPath)) {
    const manifest = JSON.parse(await readFile(manifestPath, "utf8")) as RenderManifest;
    if (manifest.input_fingerprint === inputFingerprint && manifest.output_path === resolvedOutput) {
      return {
        outputPath: resolvedOutput,
        renderedSlideIds: slides.map((slide) => slide.slide_id),
        theme: inputs.spec.theme,
        sourceSpecPath: path.join(inputs.workspace, "data", "slide_spec.json"),
        reused: true,
      };
    }
  }

  await mkdir(path.dirname(resolvedOutput), { recursive: true });
  const PptxGenJS = PptxGenJSModule as unknown as new () => any;
  const presentation = new PptxGenJS();
  presentation.layout = "LAYOUT_WIDE";
  presentation.author = "Research2Slides";
  presentation.company = "Research2Slides";
  presentation.subject = `${inputs.spec.mode} research presentation`;
  presentation.title = inputs.spec.title;
  presentation.theme = {
    headFontFace: inputs.theme.fontFamily,
    bodyFontFace: inputs.theme.fontFamily,
  };
  slides.forEach((specSlide, index) => {
    const slide = presentation.addSlide();
    renderSlide(slide, specSlide, inputs, index + 1);
  });
  await presentation.writeFile({ fileName: resolvedOutput, compression: true });
  await sanitizePptxContentTypes(resolvedOutput);

  const manifest: RenderManifest = {
    renderer_version: RENDERER_VERSION,
    input_fingerprint: inputFingerprint,
    source_spec: path.join(inputs.workspace, "data", "slide_spec.json"),
    output_path: resolvedOutput,
    slide_ids: slides.map((slide) => slide.slide_id),
    theme: inputs.spec.theme,
  };
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  return {
    outputPath: resolvedOutput,
    renderedSlideIds: manifest.slide_ids,
    theme: inputs.spec.theme,
    sourceSpecPath: manifest.source_spec,
    reused: false,
  };
}

export { loadRenderInputs, resolveThemeFont } from "./load.js";
export { validateSlideSpec } from "./validate.js";
export { boxesFor } from "./layouts/index.js";
export { latexToText, parseLatexTable } from "./components/visuals.js";
export { RendererError } from "./errors.js";
export { sanitizePptxContentTypes } from "./sanitize.js";
