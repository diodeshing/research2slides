from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from research2slides.exceptions import RenderError


def resolve_renderer_root() -> Path:
    configured = os.environ.get("RESEARCH2SLIDES_RENDERER_ROOT")
    candidates = [Path(configured).expanduser().resolve()] if configured else []
    candidates.append(Path(__file__).resolve().parents[1])
    for candidate in candidates:
        if (candidate / "package.json").is_file() and (candidate / "renderer" / "tsconfig.json").is_file():
            return candidate
    raise RenderError(
        "Renderer assets are unavailable. Run from a source checkout or set "
        "RESEARCH2SLIDES_RENDERER_ROOT to the project directory containing package.json."
    )


def _parse_slides(value: str | None) -> list[int] | None:
    if value is None:
        return None
    try:
        slides = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise RenderError("slide selection must be a comma-separated list of integers") from exc
    if not slides or any(number < 1 for number in slides):
        raise RenderError("slide selection must contain positive integers")
    return slides


def run_renderer(
    workspace: Path,
    *,
    output: Path | None = None,
    slides: str | None = None,
    force: bool = False,
) -> dict[str, object]:
    root = resolve_renderer_root()
    npm = shutil.which("npm")
    node = shutil.which("node")
    if npm is None or node is None:
        raise RenderError("Node.js 20+ and npm are required for Phase 5 rendering")
    build = subprocess.run(
        [npm, "run", "build", "--silent"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if build.returncode != 0:
        raise RenderError(f"Renderer TypeScript build failed: {build.stderr.strip() or build.stdout.strip()}")
    command = [
        node,
        str(root / "renderer" / "dist" / "src" / "cli.js"),
        str(workspace.resolve()),
    ]
    selected = _parse_slides(slides)
    if output is not None:
        command.extend(["--output", str(output.resolve())])
    if selected:
        command.extend(["--slides", ",".join(str(number) for number in selected)])
    if force:
        command.append("--force")
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RenderError(result.stderr.strip() or result.stdout.strip() or "Renderer failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RenderError("Renderer returned an invalid machine-readable summary") from exc
    if not isinstance(payload, dict):
        raise RenderError("Renderer returned an invalid summary object")
    return payload
