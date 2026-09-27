import json
import tomllib
from pathlib import Path

from research2slides import __version__
from research2slides.doctor import doctor_report
from research2slides.prompting import PROMPT_NAMES, load_prompt


def test_version_and_prompt_assets_are_available() -> None:
    assert __version__ == "0.2.0"
    assert len(PROMPT_NAMES) == 8
    assert all(load_prompt(name).strip() for name in PROMPT_NAMES)


def test_python_and_renderer_versions_match() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == package["version"] == __version__


def test_doctor_reports_source_checkout_ready() -> None:
    report = doctor_report()
    assert report["core_ready"] is True
    assert report["prompt_assets_ready"] is True
    assert report["renderer_ready"] is True
