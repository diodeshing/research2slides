"""Shared numeric-value comparison for claim and slide validation.

The pipeline must reject numbers that do not exist in the cited source, but the
source text rarely looks like the claim text:

* PDF text extraction glues numbers to words (`from42.2%to71.1%`).
* LaTeX keeps percent signs escaped (`$3.7\\%$`) or drops the unit entirely.
* Authors pad values differently (`3.7`, `3.70`, `.07`).

Comparing raw tokens therefore produced false negatives: a number that is
plainly present in the paper could be reported as unsupported. This module
compares numeric *values* instead: every run of digits is normalised through
:class:`~decimal.Decimal`, so formatting differences and the percent sign stop
mattering while invented values are still rejected.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

NUMBER_RE = re.compile(r"\d+\.\d+|(?<![\w.])\.\d+|\d+")


def number_keys(text: str) -> set[str]:
    """Return the canonical keys of every numeric value found in ``text``.

    The pattern deliberately has no "not preceded by a letter" guard: PDF text
    extraction produces ``from42.2%to71.1%``, and a guard would silently drop
    both values. Matching is greedy, so ``13.7`` still yields ``13.7`` and can
    never be reused as evidence for a claimed ``3.7``.
    """
    keys: set[str] = set()
    for match in NUMBER_RE.finditer(text):
        try:
            keys.add(format(Decimal(match.group(0)).normalize(), "f"))
        except InvalidOperation:  # pragma: no cover - defensive
            continue
    return keys


def missing_numbers(claim: str, sources: str) -> list[str]:
    """Return the claim values that do not appear in the source text."""
    return sorted(number_keys(claim) - number_keys(sources))
