from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MAPPING = {
    "paper_structure.json": "paper_structure.schema.json",
    "visual_manifest.json": "visual_manifest.schema.json",
    "source_manifest.json": "source_manifest.schema.json",
    "evidence_graph.json": "evidence_graph.schema.json",
    "scientific_understanding.json": "scientific_understanding.schema.json",
    "presentation_plan.json": "presentation_plan.schema.json",
    "presentation_plan.full.json": "presentation_plan.schema.json",
    "slide_spec.json": "slide_spec.schema.json",
    "quality_report.json": "quality_report.schema.json",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_artifacts.py <data-directory>", file=sys.stderr)
        return 2
    data_dir = Path(sys.argv[1]).resolve()
    if not data_dir.is_dir():
        print(f"not a directory: {data_dir}", file=sys.stderr)
        return 2
    found = 0
    failures = 0
    for artifact, schema_name in MAPPING.items():
        artifact_path = data_dir / artifact
        if not artifact_path.exists():
            continue
        found += 1
        schema = json.loads((PROJECT_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        instance = json.loads(artifact_path.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda error: list(error.path))
        if errors:
            failures += 1
            for error in errors:
                location = ".".join(str(item) for item in error.path) or "<root>"
                print(f"FAIL {artifact}:{location}: {error.message}")
        else:
            print(f"OK   {artifact}")
    if found == 0:
        print(f"no recognized artifacts in {data_dir}", file=sys.stderr)
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
