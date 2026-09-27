from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = (".pdf", ".svg", ".eps", ".png", ".jpg", ".jpeg")


def resolve_graphic(root: Path, main_file: Path, reference: str) -> Path | None:
    raw = Path(reference)
    candidates = [main_file.parent / raw, root / raw]
    if raw.suffix == "":
        candidates = [candidate.with_suffix(ext) for candidate in candidates for ext in SUPPORTED_EXTENSIONS]
    root_resolved = root.resolve()
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            continue
        if resolved.is_file() and resolved.suffix.lower() in SUPPORTED_EXTENSIONS:
            return resolved
    return None

