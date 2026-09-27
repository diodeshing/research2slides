from __future__ import annotations

import re
from dataclasses import dataclass

from research2slides.exceptions import EvidenceError
from research2slides.models import PaperStructure, SourceLocator


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


@dataclass(frozen=True)
class SourceRecord:
    source_type: str
    source_id: str
    text: str
    page: int | None
    section: str | None
    figure: str | None = None
    table: str | None = None
    equation: str | None = None
    label: str | None = None

    def locator(self, excerpt: str) -> SourceLocator:
        if normalize_text(excerpt) not in normalize_text(self.text):
            raise EvidenceError(
                f"Evidence excerpt for {self.source_id!r} is not present in the source artifact"
            )
        return SourceLocator(
            source_type=self.source_type,
            source_id=self.source_id,
            page=self.page,
            section=self.section,
            figure=self.figure,
            table=self.table,
            equation=self.equation,
            label=self.label,
            excerpt=excerpt.strip(),
        )


class SourceCatalog:
    def __init__(self, records: list[SourceRecord]) -> None:
        self._records = {record.source_id: record for record in records}
        if len(self._records) != len(records):
            raise EvidenceError("Source artifacts contain duplicate source IDs")

    @classmethod
    def from_paper(cls, paper: PaperStructure) -> "SourceCatalog":
        section_titles = {section.section_id: section.title for section in paper.sections}
        records: list[SourceRecord] = []
        for paragraph in paper.paragraphs:
            records.append(
                SourceRecord(
                    source_type="paragraph",
                    source_id=paragraph.paragraph_id,
                    text=paragraph.text,
                    page=paragraph.page,
                    section=section_titles.get(paragraph.section_id),
                )
            )
        for figure in paper.figures:
            text = figure.caption or figure.source_file or figure.figure_id
            records.append(
                SourceRecord(
                    source_type="figure",
                    source_id=figure.figure_id,
                    text=text,
                    page=figure.page,
                    section=section_titles.get(figure.related_section),
                    figure=figure.number,
                    label=figure.label,
                )
            )
        for table in paper.tables:
            text = "\n".join(item for item in (table.caption, table.latex) if item) or table.table_id
            records.append(
                SourceRecord(
                    source_type="table",
                    source_id=table.table_id,
                    text=text,
                    page=table.page,
                    section=section_titles.get(table.related_section),
                    table=table.number,
                    label=table.label,
                )
            )
        for equation in paper.equations:
            records.append(
                SourceRecord(
                    source_type="equation",
                    source_id=equation.equation_id,
                    text=equation.latex,
                    page=equation.page,
                    section=section_titles.get(equation.related_section),
                    equation=equation.number,
                    label=equation.label,
                )
            )
        return cls(records)

    def resolve(self, source_id: str) -> SourceRecord:
        try:
            return self._records[source_id]
        except KeyError as exc:
            raise EvidenceError(f"Unknown evidence source ID: {source_id}") from exc

    def as_prompt_catalog(self) -> list[dict[str, object]]:
        return [
            {
                "source_type": record.source_type,
                "source_id": record.source_id,
                "page": record.page,
                "section": record.section,
                "figure": record.figure,
                "table": record.table,
                "equation": record.equation,
                "label": record.label,
                "text": record.text,
            }
            for record in self._records.values()
        ]

