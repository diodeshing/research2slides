from __future__ import annotations

import re
from collections.abc import Iterable

from research2slides.exceptions import PlanningError, SlideSpecError


CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def require_plan_chinese(texts: Iterable[tuple[str, str]]) -> None:
    for field, text in texts:
        if not contains_cjk(text):
            raise PlanningError(
                f"Chinese-first language profile requires Chinese wording in {field}"
            )


def require_slide_chinese(texts: Iterable[tuple[str, str]]) -> None:
    for field, text in texts:
        if not contains_cjk(text):
            raise SlideSpecError(
                f"Chinese-first language profile requires Chinese wording in {field}"
            )
