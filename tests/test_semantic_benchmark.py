import json
from pathlib import Path

import pytest

from research2slides.qa.benchmark import run_semantic_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_three_paper_semantic_benchmark_detects_all_injected_failures(tmp_path: Path) -> None:
    config = PROJECT_ROOT / "examples" / "phase10" / "benchmark.json"
    config_payload = json.loads(config.read_text(encoding="utf-8"))
    missing_workspaces = [
        str((config.parent / paper["workspace"]).resolve())
        for paper in config_payload["papers"]
        if not (config.parent / paper["workspace"] / "data" / "slide_spec.json").is_file()
    ]
    if missing_workspaces:
        pytest.skip(
            "real-world benchmark workspaces are local validation artifacts; "
            f"missing: {', '.join(missing_workspaces)}"
        )
    report = run_semantic_benchmark(
        config,
        tmp_path / "output",
    )
    assert report["paper_count"] == 3
    assert report["slide_count"] == 26
    assert report["baseline_finding_count"] == 0
    assert report["detected_cases"] == report["mutation_cases"] == 12
    assert report["unexpected_finding_count"] == 0
    assert (tmp_path / "output" / "semantic_benchmark.json").is_file()
    assert (tmp_path / "output" / "semantic_benchmark.md").is_file()
