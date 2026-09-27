from pathlib import Path

from research2slides.qa.benchmark import run_semantic_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_three_paper_semantic_benchmark_detects_all_injected_failures(tmp_path: Path) -> None:
    report = run_semantic_benchmark(
        PROJECT_ROOT / "examples" / "phase10" / "benchmark.json",
        tmp_path / "output",
    )
    assert report["paper_count"] == 3
    assert report["slide_count"] == 26
    assert report["baseline_finding_count"] == 0
    assert report["detected_cases"] == report["mutation_cases"] == 12
    assert report["unexpected_finding_count"] == 0
    assert (tmp_path / "output" / "semantic_benchmark.json").is_file()
    assert (tmp_path / "output" / "semantic_benchmark.md").is_file()
