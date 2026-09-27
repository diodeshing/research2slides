import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { RendererError } from "./errors.js";
import type {
  PaperStructure,
  RenderInputs,
  SlideSpec,
  ThemeName,
  ThemeTokens,
  VisualManifest,
} from "./types.js";
import { validateSlideSpec } from "./validate.js";

async function readJson(filePath: string): Promise<unknown> {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new RendererError(`Unable to read JSON ${filePath}: ${message}`);
  }
}

function projectRoot(): string {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
}

function validateTheme(value: unknown, requested: ThemeName): asserts value is ThemeTokens {
  if (typeof value !== "object" || value === null) {
    throw new RendererError(`Theme ${requested} must be a JSON object`);
  }
  const record = value as Record<string, unknown>;
  if (record.name !== requested) {
    throw new RendererError(`Theme file name does not match ${requested}`);
  }
  for (const key of [
    "fontFamily",
    "equationFontFamily",
    "background",
    "surface",
    "text",
    "muted",
    "accent",
    "accentSoft",
    "secondary",
    "warning",
  ]) {
    if (typeof record[key] !== "string" || String(record[key]).trim() === "") {
      throw new RendererError(`Theme ${requested}.${key} must be a non-empty string`);
    }
  }
  if (
    !Array.isArray(record.fontFallbacks)
    || record.fontFallbacks.length === 0
    || record.fontFallbacks.some((font) => typeof font !== "string" || font.trim() === "")
  ) {
    throw new RendererError(`Theme ${requested}.fontFallbacks must contain font names`);
  }
}

const WINDOWS_FONT_FILES: Record<string, string[]> = {
  "Microsoft YaHei": ["msyh.ttc", "msyhbd.ttc", "msyhl.ttc"],
  "Noto Sans CJK SC": ["NotoSansCJK-Regular.ttc", "NotoSansCJKsc-Regular.otf"],
  "Source Han Sans SC": ["SourceHanSansSC-Regular.otf"],
  Arial: ["arial.ttf"],
};

export function resolveThemeFont(theme: ThemeTokens): string {
  const override = process.env.RESEARCH2SLIDES_FONT_FAMILY?.trim();
  if (override) return override;
  if (process.platform !== "win32") return theme.fontFamily;
  const fontsDir = path.join(process.env.WINDIR ?? "C:\\Windows", "Fonts");
  return theme.fontFallbacks.find((family) =>
    (WINDOWS_FONT_FILES[family] ?? []).some((filename) => existsSync(path.join(fontsDir, filename))))
    ?? theme.fontFamily;
}

export async function loadRenderInputs(workspacePath: string): Promise<RenderInputs> {
  const workspace = path.resolve(workspacePath);
  const dataDir = path.join(workspace, "data");
  const specValue = await readJson(path.join(dataDir, "slide_spec.json"));
  validateSlideSpec(specValue);
  const spec: SlideSpec = specValue;
  const visuals = (await readJson(path.join(dataDir, "visual_manifest.json"))) as VisualManifest;
  const paper = (await readJson(path.join(dataDir, "paper_structure.json"))) as PaperStructure;
  if (visuals.paper_id !== spec.paper_id || paper.paper_id !== spec.paper_id) {
    throw new RendererError("Renderer lookup artifacts do not match slide_spec.paper_id");
  }
  if (!Array.isArray(visuals.assets) || !Array.isArray(paper.tables) || !Array.isArray(paper.equations)) {
    throw new RendererError("Renderer lookup artifacts have an invalid shape");
  }
  const themePath = path.join(projectRoot(), "themes", spec.theme, "theme.json");
  const themeValue = await readJson(themePath);
  validateTheme(themeValue, spec.theme);
  const theme = { ...themeValue, fontFamily: resolveThemeFont(themeValue) };
  return { workspace, spec, visuals, paper, theme };
}

export function resolveProjectRoot(): string {
  return projectRoot();
}
