import { readFile, rename, writeFile } from "node:fs/promises";

import JSZip from "jszip";

import { RendererError } from "./errors.js";

const CONTENT_TYPES = "[Content_Types].xml";
const MASTER_OVERRIDE = /<Override\s+PartName="\/ppt\/slideMasters\/(slideMaster\d+\.xml)"\s+ContentType="application\/vnd\.openxmlformats-officedocument\.presentationml\.slideMaster\+xml"\s*\/>/g;

export async function sanitizePptxContentTypes(pptxPath: string): Promise<number> {
  const archive = await JSZip.loadAsync(await readFile(pptxPath));
  const contentPart = archive.file(CONTENT_TYPES);
  if (!contentPart) {
    throw new RendererError("Generated PPTX is missing [Content_Types].xml");
  }
  const xml = await contentPart.async("string");
  let removed = 0;
  const sanitized = xml.replace(MASTER_OVERRIDE, (match, fileName: string) => {
    if (archive.file(`ppt/slideMasters/${fileName}`)) return match;
    removed += 1;
    return "";
  });
  if (removed === 0) return 0;
  archive.file(CONTENT_TYPES, sanitized);
  const temporary = `${pptxPath}.sanitize.tmp`;
  const buffer = await archive.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  await writeFile(temporary, buffer);
  await rename(temporary, pptxPath);
  return removed;
}
