from pathlib import Path

from research2slides.parsing.latex_parser import LatexParser


FIXTURES = Path(__file__).parent / "fixtures"


def test_latex_parser_extracts_structure_and_references() -> None:
    result = LatexParser().parse(FIXTURES / "attention_is_all_you_need" / "source")
    assert result.title == "Attention Is All You Need"
    assert [section.title for section in result.sections] == [
        "Introduction",
        "Model Architecture",
        "Attention",
        "Experiments",
    ]
    assert result.sections[2].parent_id == result.sections[1].section_id
    assert result.figures[0].source_file == "figures/architecture"
    assert result.figures[0].label == "fig:architecture"
    assert result.tables[0].label == "tab:results"
    assert result.equations[0].label == "eq:attention"


def test_latex_parser_normalizes_formatting_and_zero_arg_macros_in_title(tmp_path: Path) -> None:
    source = tmp_path / "main.tex"
    source.write_text(
        r"""\documentclass{article}
\newcommand{\model}{Wrong Prefix}
\newcommand{\modelname}{DeepSeek-V3}
\title{\centering \modelname{} Technical Report\vspace{-3mm}}
\begin{document}
\section{Introduction}
Grounded content for the parser.
\end{document}
""",
        encoding="utf-8",
    )
    result = LatexParser().parse(tmp_path)
    assert result.title == "DeepSeek-V3 Technical Report"


def test_latex_parser_extracts_starred_float_environments(tmp_path: Path) -> None:
    (tmp_path / "figure.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "main.tex").write_text(
        r"""\documentclass{article}
\begin{document}
\section{Method}
\begin{figure*}\includegraphics{figure.pdf}\caption{Wide figure.}\label{fig:wide}\end{figure*}
\begin{table*}\caption{Wide table.}\label{tab:wide}\begin{tabular}{cc}A&B\\\end{tabular}\end{table*}
\begin{align*}x &= y\end{align*}
\end{document}
""",
        encoding="utf-8",
    )
    result = LatexParser().parse(tmp_path)
    assert result.figures[0].label == "fig:wide"
    assert result.tables[0].label == "tab:wide"
    assert result.equations[0].latex == "x &= y"
