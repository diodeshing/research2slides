from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from research2slides.qa.benchmark import run_semantic_benchmark  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Research2Slides semantic QA benchmark")
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_semantic_benchmark(args.config, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["detected_cases"] == report["mutation_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
