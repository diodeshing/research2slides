from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
EQUATION_TEXT = re.compile(r"(?:=.+(?:√|\^|/)|(?:softmax|max|sum)\s*\()", re.IGNORECASE)


def numbered_parts(names: list[str], prefix: str, suffix: str) -> list[str]:
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+){re.escape(suffix)}$")
    parts: list[tuple[int, str]] = []
    for name in names:
        match = pattern.match(name)
        if match:
            parts.append((int(match.group(1)), name))
    return [name for _, name in sorted(parts)]


def validate(
    path: Path,
    expected_slides: int | None,
    require_notes: bool,
    require_table: bool,
    require_equation: bool = False,
    require_svg: bool = False,
) -> list[str]:
    errors: list[str] = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"invalid PPTX package: {exc}"]
    with archive:
        names = archive.namelist()
        slides = numbered_parts(names, "ppt/slides/slide", ".xml")
        notes = numbered_parts(names, "ppt/notesSlides/notesSlide", ".xml")
        if expected_slides is not None and len(slides) != expected_slides:
            errors.append(f"expected {expected_slides} slides, found {len(slides)}")
        if require_notes and len(notes) != len(slides):
            errors.append(f"expected notes for every slide, found {len(notes)} for {len(slides)} slides")
        for note_name in notes:
            root = ElementTree.fromstring(archive.read(note_name))
            text = " ".join(node.text or "" for node in root.iter(f"{{{DRAWING_NS}}}t"))
            for marker in ("Purpose:", "Main Message:", "Speaking Script:", "Sources:"):
                if marker not in text:
                    errors.append(f"{note_name} is missing {marker}")
        native_tables = 0
        editable_equations = 0
        for slide_name in slides:
            root = ElementTree.fromstring(archive.read(slide_name))
            native_tables += len(list(root.iter(f"{{{DRAWING_NS}}}tbl")))
            text = " ".join(node.text or "" for node in root.iter(f"{{{DRAWING_NS}}}t"))
            if EQUATION_TEXT.search(text):
                editable_equations += 1
        if require_table and native_tables == 0:
            errors.append("no editable native PowerPoint table was found")
        if require_equation and editable_equations == 0:
            errors.append("no editable equation text was found")
        if require_svg and not any(name.endswith(".svg") for name in names if name.startswith("ppt/media/")):
            errors.append("no source SVG was preserved in the PPTX media package")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Research2Slides Phase 5 PPTX structure.")
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--expected-slides", type=int)
    parser.add_argument("--require-notes", action="store_true")
    parser.add_argument("--require-native-table", action="store_true")
    parser.add_argument("--require-editable-equation", action="store_true")
    parser.add_argument("--require-svg", action="store_true")
    args = parser.parse_args()
    errors = validate(
        args.pptx,
        args.expected_slides,
        args.require_notes,
        args.require_native_table,
        args.require_editable_equation,
        args.require_svg,
    )
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print(f"OK {args.pptx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
