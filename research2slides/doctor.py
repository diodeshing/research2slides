from __future__ import annotations

import shutil
import sys

from research2slides import __version__
from research2slides.exceptions import Research2SlidesError
from research2slides.prompting import PROMPT_NAMES, prompt_path
from research2slides.rendering import resolve_renderer_root


def doctor_report() -> dict[str, object]:
    missing_prompts: list[str] = []
    prompt_location: str | None = None
    for name in PROMPT_NAMES:
        try:
            path = prompt_path(name)
            prompt_location = prompt_location or str(path.parent)
        except Research2SlidesError:
            missing_prompts.append(name)
    try:
        renderer_root = str(resolve_renderer_root())
        renderer_ready = shutil.which("node") is not None and shutil.which("npm") is not None
    except Research2SlidesError:
        renderer_root = None
        renderer_ready = False
    python_ready = sys.version_info >= (3, 11)
    core_ready = python_ready and not missing_prompts
    return {
        "version": __version__,
        "python": sys.version.split()[0],
        "python_ready": python_ready,
        "core_ready": core_ready,
        "prompt_assets_ready": not missing_prompts,
        "prompt_location": prompt_location,
        "missing_prompts": missing_prompts,
        "node": shutil.which("node"),
        "npm": shutil.which("npm"),
        "renderer_root": renderer_root,
        "renderer_ready": renderer_ready,
    }
