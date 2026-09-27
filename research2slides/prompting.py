from __future__ import annotations

import os
import sys
from pathlib import Path

from research2slides.exceptions import ArtifactError


PROMPT_NAMES = (
    "own-research-slides.md",
    "own-research-storyline.md",
    "paper-reading-slides.md",
    "paper-reading-storyline.md",
    "plan-slides.md",
    "qa.md",
    "semantic-qa.md",
    "understand-paper.md",
)


def prompt_directories() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("RESEARCH2SLIDES_PROMPT_DIR")
    if configured:
        candidates.append(Path(configured).expanduser().resolve())
    candidates.extend(
        [
            Path(__file__).resolve().parents[1] / "prompts",
            Path(sys.prefix) / "share" / "research2slides" / "prompts",
        ]
    )
    return list(dict.fromkeys(candidates))


def prompt_path(name: str) -> Path:
    if name not in PROMPT_NAMES:
        raise ArtifactError(f"Unknown prompt asset: {name}")
    for directory in prompt_directories():
        candidate = directory / name
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(path) for path in prompt_directories())
    raise ArtifactError(f"Prompt asset {name} is unavailable; searched: {searched}")


def load_prompt(name: str) -> str:
    try:
        return prompt_path(name).read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactError(f"Unable to read prompt asset {name}: {exc}") from exc
