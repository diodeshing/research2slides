from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from research2slides.exceptions import ParseError
from research2slides.models import (
    PaperMetadata,
    PaperStructure,
    Paragraph,
    ParserProvenance,
    Section,
)


SECTION_PATTERN = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9 ,:&/\-]{2,80}$")


class PdfParser:
    name = "pypdf"

    def parse(self, pdf_path: Path, paper_id: str) -> PaperStructure:
        try:
            reader = PdfReader(str(pdf_path))
        except Exception as exc:  # pypdf exposes several format-specific errors
            raise ParseError(f"Unable to open PDF {pdf_path}: {exc}") from exc
        if not reader.pages:
            raise ParseError(f"PDF has no pages: {pdf_path}")

        metadata = reader.metadata or {}
        title = str(metadata.get("/Title") or pdf_path.stem).strip()
        author_text = str(metadata.get("/Author") or "").strip()
        authors = [part.strip() for part in re.split(r";|\band\b", author_text) if part.strip()]
        paragraphs: list[Paragraph] = []
        sections: list[Section] = []
        current_section: Section | None = None
        warnings: list[str] = []

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                warnings.append(f"page {page_number}: text extraction failed: {exc}")
                text = ""
            chunks = [re.sub(r"\s+", " ", chunk).strip() for chunk in re.split(r"\n\s*\n|\n", text)]
            for chunk in (item for item in chunks if item):
                if SECTION_PATTERN.fullmatch(chunk) and len(chunk.split()) <= 10:
                    section_id = f"sec_pdf_{len(sections) + 1:03d}"
                    current_section = Section(
                        section_id=section_id,
                        title=chunk,
                        level=1,
                        order=len(sections),
                        page_start=page_number,
                    )
                    sections.append(current_section)
                    continue
                paragraph_id = f"para_pdf_{len(paragraphs) + 1:05d}"
                paragraphs.append(
                    Paragraph(
                        paragraph_id=paragraph_id,
                        text=chunk,
                        section_id=current_section.section_id if current_section else None,
                        page=page_number,
                        source="pdf",
                    )
                )
                if current_section:
                    current_section.paragraph_ids.append(paragraph_id)

        return PaperStructure(
            paper_id=paper_id,
            metadata=PaperMetadata(title=title, authors=authors),
            page_count=len(reader.pages),
            sections=sections,
            paragraphs=paragraphs,
            provenance=ParserProvenance(pdf_backend=self.name, warnings=warnings),
        )

