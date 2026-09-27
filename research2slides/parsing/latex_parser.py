from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from research2slides.exceptions import ParseError
from research2slides.ingestion.latex import find_main_tex
from research2slides.models import EquationRef, FigureRef, Paragraph, Section, TableRef


COMMAND_LEVELS = {"section": 1, "subsection": 2, "subsubsection": 3, "paragraph": 4}
SECTION_RE = re.compile(r"\\(section|subsection|subsubsection|paragraph)\*?\s*\{([^{}]+)\}")
INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
CAPTION_RE = re.compile(r"\\caption(?:\[[^\]]*\])?\s*\{((?:[^{}]|\{[^{}]*\})*)\}", re.DOTALL)
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
GRAPHIC_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\s*\{([^{}]+)\}")
ZERO_ARG_MACRO_RE = re.compile(
    r"\\newcommand\*?\s*(?:\{\\([A-Za-z@]+)\}|\\([A-Za-z@]+))\s*\{([^{}]*)\}"
)


@dataclass
class LatexParseResult:
    title: str | None
    authors: list[str]
    abstract: str | None
    sections: list[Section]
    paragraphs: list[Paragraph]
    figures: list[FigureRef]
    tables: list[TableRef]
    equations: list[EquationRef]
    main_file: Path
    expanded_text: str


def _read_tree(path: Path, root: Path, visited: set[Path]) -> str:
    path = path.resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ParseError(f"LaTeX include escapes source root: {path}") from exc
    if path in visited:
        return ""
    visited.add(path)
    text = path.read_text(encoding="utf-8", errors="replace")

    def replace_input(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        included = (path.parent / name)
        if included.suffix == "":
            included = included.with_suffix(".tex")
        if not included.is_file():
            return match.group(0)
        return _read_tree(included, root, visited)

    return INPUT_RE.sub(replace_input, text)


def _macro(text: str, name: str) -> str | None:
    match = re.search(rf"\\{name}\s*\{{((?:[^{{}}]|\{{[^{{}}]*\}})*)\}}", text, re.DOTALL)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def _environment(text: str, name: str) -> list[tuple[int, str]]:
    pattern = re.compile(rf"\\begin\{{{name}\*?\}}(.*?)\\end\{{{name}\*?\}}", re.DOTALL)
    return [(match.start(), match.group(1).strip()) for match in pattern.finditer(text)]


def _clean_text(text: str) -> str:
    text = re.sub(r"(?m)%.*$", "", text)
    text = re.sub(r"\\(?:cite|ref|eqref|autoref)\s*\{[^{}]*\}", "", text)
    text = re.sub(r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title: str | None, source: str) -> str | None:
    if not title:
        return None
    macros = {
        (match.group(1) or match.group(2)): match.group(3)
        for match in ZERO_ARG_MACRO_RE.finditer(source)
    }
    for name, value in sorted(macros.items(), key=lambda item: len(item[0]), reverse=True):
        title = re.sub(
            rf"\\{re.escape(name)}(?![A-Za-z@])(?:\{{\}})?",
            lambda _match, replacement=value: replacement,
            title,
        )
    title = re.sub(r"\\(?:vspace|hspace)\*?\s*\{[^{}]*\}", " ", title)
    title = _clean_text(title)
    return title or None


def _section_at(position: int, section_spans: list[tuple[int, Section]]) -> str | None:
    current = None
    for start, section in section_spans:
        if start > position:
            break
        current = section.section_id
    return current


class LatexParser:
    name = "research2slides-regex-latex-v1"

    def parse(self, root: Path) -> LatexParseResult:
        main_file = find_main_tex(root)
        text = _read_tree(main_file, root, set())
        title = _clean_title(_macro(text, "title"), text)
        author = _macro(text, "author") or ""
        authors = [part.strip() for part in re.split(r"\\and|;", author) if part.strip()]
        abstracts = _environment(text, "abstract")
        abstract = _clean_text(abstracts[0][1]) if abstracts else None

        sections: list[Section] = []
        section_spans: list[tuple[int, Section]] = []
        parent_at_level: dict[int, str] = {}
        section_matches = list(SECTION_RE.finditer(text))
        for order, match in enumerate(section_matches):
            command, heading = match.groups()
            level = COMMAND_LEVELS[command]
            section_id = f"sec_tex_{order + 1:03d}"
            parent_id = parent_at_level.get(level - 1)
            section = Section(
                section_id=section_id,
                title=_clean_text(heading),
                level=level,
                order=order,
                parent_id=parent_id,
            )
            sections.append(section)
            section_spans.append((match.start(), section))
            parent_at_level[level] = section_id
            for deeper in [key for key in parent_at_level if key > level]:
                parent_at_level.pop(deeper, None)

        figures: list[FigureRef] = []
        for index, (position, block) in enumerate(_environment(text, "figure"), start=1):
            graphic = GRAPHIC_RE.search(block)
            caption = CAPTION_RE.search(block)
            label = LABEL_RE.search(block)
            figures.append(
                FigureRef(
                    figure_id=f"fig_{index:03d}",
                    number=str(index),
                    caption=_clean_text(caption.group(1)) if caption else None,
                    label=label.group(1) if label else None,
                    source_file=graphic.group(1).strip() if graphic else None,
                    related_section=_section_at(position, section_spans),
                )
            )

        tables: list[TableRef] = []
        for index, (position, block) in enumerate(_environment(text, "table"), start=1):
            caption = CAPTION_RE.search(block)
            label = LABEL_RE.search(block)
            tables.append(
                TableRef(
                    table_id=f"table_{index:03d}",
                    number=str(index),
                    caption=_clean_text(caption.group(1)) if caption else None,
                    label=label.group(1) if label else None,
                    latex=block,
                    related_section=_section_at(position, section_spans),
                )
            )

        equations: list[EquationRef] = []
        equation_blocks = _environment(text, "equation") + _environment(text, "align")
        for index, (position, block) in enumerate(sorted(equation_blocks), start=1):
            label = LABEL_RE.search(block)
            latex = LABEL_RE.sub("", block).strip()
            equations.append(
                EquationRef(
                    equation_id=f"eq_{index:03d}",
                    number=str(index),
                    label=label.group(1) if label else None,
                    latex=latex,
                    related_section=_section_at(position, section_spans),
                )
            )

        excluded = re.sub(
            r"\\begin\{(?:figure|table|equation|align|abstract)\*?\}.*?\\end\{(?:figure|table|equation|align|abstract)\*?\}",
            "\n\n",
            text,
            flags=re.DOTALL,
        )
        paragraphs: list[Paragraph] = []
        for raw in re.split(r"\n\s*\n", excluded):
            cleaned = _clean_text(raw)
            if len(cleaned) < 20 or cleaned.startswith("documentclass"):
                continue
            position = text.find(raw)
            paragraph_id = f"para_tex_{len(paragraphs) + 1:05d}"
            section_id = _section_at(max(position, 0), section_spans)
            paragraphs.append(
                Paragraph(
                    paragraph_id=paragraph_id,
                    text=cleaned,
                    section_id=section_id,
                    source="latex",
                )
            )
            if section_id:
                next(section for section in sections if section.section_id == section_id).paragraph_ids.append(paragraph_id)

        return LatexParseResult(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            paragraphs=paragraphs,
            figures=figures,
            tables=tables,
            equations=equations,
            main_file=main_file,
            expanded_text=text,
        )
