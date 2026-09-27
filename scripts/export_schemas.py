from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from research2slides.models import (  # noqa: E402
    AnalysisDraft,
    EvidenceGraph,
    PaperStructure,
    PresentationPlan,
    QualityReport,
    SemanticQADraft,
    SemanticQAResult,
    ScientificUnderstanding,
    SlideSpecDraft,
    SlideSpec,
    SourceManifest,
    StorylineDraft,
    VisualManifest,
)


SCHEMAS = {
    "paper_structure.schema.json": PaperStructure,
    "visual_manifest.schema.json": VisualManifest,
    "source_manifest.schema.json": SourceManifest,
    "analysis_draft.schema.json": AnalysisDraft,
    "evidence_graph.schema.json": EvidenceGraph,
    "scientific_understanding.schema.json": ScientificUnderstanding,
    "storyline_draft.schema.json": StorylineDraft,
    "presentation_plan.schema.json": PresentationPlan,
    "slide_spec_draft.schema.json": SlideSpecDraft,
    "slide_spec.schema.json": SlideSpec,
    "quality_report.schema.json": QualityReport,
    "semantic_qa_draft.schema.json": SemanticQADraft,
    "semantic_qa.schema.json": SemanticQAResult,
}


def rendered_schema(model: type) -> str:
    return json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or verify checked-in JSON Schemas.")
    parser.add_argument("--check", action="store_true", help="Fail instead of updating stale schemas")
    args = parser.parse_args()
    schema_dir = PROJECT_ROOT / "schemas"
    schema_dir.mkdir(exist_ok=True)
    stale: list[str] = []
    for filename, model in SCHEMAS.items():
        target = schema_dir / filename
        expected = rendered_schema(model)
        actual = target.read_text(encoding="utf-8") if target.exists() else None
        if actual == expected:
            continue
        if args.check:
            stale.append(filename)
        else:
            target.write_text(expected, encoding="utf-8")
            print(f"wrote {target.relative_to(PROJECT_ROOT)}")
    if stale:
        print("stale or missing schemas: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
