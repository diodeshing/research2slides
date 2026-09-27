from research2slides.numbers import missing_numbers, number_keys


def test_pdf_glued_numbers_are_recognised() -> None:
    """PDF extraction writes `from42.2%to71.1%`; both values must survive."""
    source = "increasing basic pick-and-place success from42.2%to71.1%"
    assert {"42.2", "71.1"} <= number_keys(source)
    assert missing_numbers("basic success rises from 42.2% to 71.1%", source) == []


def test_escaped_percent_and_unit_differences_do_not_matter() -> None:
    assert missing_numbers("hard-start success 3.7% to 52.0%", r"from $3.7\%$ to $52.0\%$") == []
    assert missing_numbers("score 1.0", "score 1") == []
    assert missing_numbers("correlation 0.399", "at\u03c1=\u22120.399and with") == []


def test_leading_dot_decimals_are_matched() -> None:
    assert missing_numbers("weight 0.01", "the weight .01 is default") == []


def test_invented_values_are_still_rejected() -> None:
    assert missing_numbers("improves by 99.9 points", "improves by 11.0 points") == ["99.9"]


def test_greedy_match_cannot_borrow_digits_from_a_longer_number() -> None:
    assert missing_numbers("score 3.7", "score 13.7") == ["3.7"]


def test_page_and_figure_references_do_not_support_decimals() -> None:
    """`p.6` must not turn into evidence for a claimed 0.6."""
    assert missing_numbers("regret 0.6", "see p.6 for details") == ["0.6"]
