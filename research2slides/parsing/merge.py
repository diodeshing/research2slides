from __future__ import annotations

from research2slides.models import PaperMetadata, PaperStructure
from research2slides.parsing.latex_parser import LatexParseResult


def merge_pdf_and_latex(pdf: PaperStructure, latex: LatexParseResult) -> PaperStructure:
    warnings = list(pdf.provenance.warnings)
    if pdf.metadata.title and latex.title and pdf.metadata.title.casefold() != latex.title.casefold():
        warnings.append("PDF and LaTeX titles differ; LaTeX title selected")
    pdf.provenance.latex_backend = "research2slides-regex-latex-v1"
    pdf.provenance.warnings = warnings
    pdf.metadata = PaperMetadata(
        title=latex.title or pdf.metadata.title,
        authors=latex.authors or pdf.metadata.authors,
        abstract=latex.abstract,
        language=pdf.metadata.language,
    )
    pdf_section_ids = {section.section_id for section in pdf.sections}
    latex_section_ids = {section.section_id for section in latex.sections}
    if latex.sections:
        for paragraph in pdf.paragraphs:
            if paragraph.section_id in pdf_section_ids and paragraph.section_id not in latex_section_ids:
                paragraph.section_id = None
    pdf.sections = latex.sections or pdf.sections
    pdf.paragraphs = latex.paragraphs + pdf.paragraphs
    pdf.figures = latex.figures
    pdf.tables = latex.tables
    pdf.equations = latex.equations
    return pdf
