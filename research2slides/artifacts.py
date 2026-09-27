from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from research2slides.exceptions import ArtifactError


ModelT = TypeVar("ModelT", bound=BaseModel)


def write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep unavailable locators as explicit nulls so downstream QA can
    # distinguish “not recoverable yet” from “field was never modeled”.
    payload = model.model_dump_json(indent=2, exclude_none=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def read_model(path: Path, model_type: type[ModelT]) -> ModelT:
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"Invalid artifact {path}: {exc}") from exc
