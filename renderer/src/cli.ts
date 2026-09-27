import path from "node:path";

import { RendererError } from "./errors.js";
import { renderWorkspace } from "./index.js";

interface CliArgs {
  workspace: string;
  output?: string;
  slides?: number[];
  force: boolean;
}

function usage(): string {
  return [
    "Usage: node renderer/dist/src/cli.js WORKSPACE [options]",
    "",
    "Options:",
    "  --output PATH     Output PPTX path (default: WORKSPACE/output/presentation.pptx)",
    "  --slides 2,4,5   Render only selected original slide numbers",
    "  --force           Ignore a matching render manifest",
  ].join("\n");
}

function parseArgs(argv: string[]): CliArgs {
  if (argv.includes("--help") || argv.includes("-h")) {
    console.log(usage());
    process.exit(0);
  }
  const workspace = argv[0];
  if (!workspace || workspace.startsWith("-")) {
    throw new RendererError(usage());
  }
  let output: string | undefined;
  let slides: number[] | undefined;
  let force = false;
  for (let index = 1; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--force") {
      force = true;
    } else if (arg === "--output") {
      const next = argv[++index];
      if (!next) throw new RendererError("--output requires a path");
      output = next;
    } else if (arg === "--slides") {
      const next = argv[++index];
      if (!next) throw new RendererError("--slides requires a comma-separated list");
      slides = next.split(",").map((value) => Number(value.trim()));
    } else {
      throw new RendererError(`Unknown argument: ${arg}`);
    }
  }
  const result: CliArgs = { workspace, force };
  if (output !== undefined) result.output = output;
  if (slides !== undefined) result.slides = slides;
  return result;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const workspace = path.resolve(args.workspace);
  const suffix = args.slides ? `.slides-${args.slides.join("-")}` : "";
  const output = args.output
    ? path.resolve(args.output)
    : path.join(workspace, "output", `presentation${suffix}.pptx`);
  const selection = args.slides ? { slideNumbers: args.slides } : {};
  const result = await renderWorkspace(workspace, output, selection, args.force);
  console.log(JSON.stringify({
    status: result.reused ? "reused" : "generated",
    output: result.outputPath,
    slides: result.renderedSlideIds,
    theme: result.theme,
    source_spec: result.sourceSpecPath,
  }, null, 2));
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`error: ${message}`);
  process.exitCode = error instanceof RendererError ? 2 : 1;
});
