from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research2slides.artifacts import read_model, write_text
from research2slides.exceptions import QualityAssuranceError
from research2slides.models import EvidenceGraph, SemanticQADraft, SlideSpec
from research2slides.qa.semantic import inspect_semantic_draft


def _load_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityAssuranceError(f"Invalid semantic benchmark config {path}: {exc}") from exc
    if payload.get("schema_version") != "1.0" or not payload.get("papers"):
        raise QualityAssuranceError("Semantic benchmark config requires schema_version 1.0 and papers")
    return payload


def _mutate(draft: SemanticQADraft, case: dict[str, Any]) -> SemanticQADraft:
    changed = draft.model_copy(deep=True)
    evaluation = next(
        (item for item in changed.evaluations if item.slide_id == case["slide_id"]),
        None,
    )
    if evaluation is None:
        raise QualityAssuranceError(f"Unknown benchmark slide: {case['slide_id']}")
    operation = case["operation"]
    if operation == "claim_evidence":
        evaluation.claim_evidence = case["value"]
    elif operation == "claim_strength":
        evaluation.claim_strength = case["value"]
    elif operation == "dependency_order":
        if not evaluation.dependencies:
            raise QualityAssuranceError(f"{case['slide_id']} has no dependency to mutate")
        evaluation.dependencies[0].prerequisite_slide_ids = list(case["value"])
    else:
        raise QualityAssuranceError(f"Unsupported benchmark mutation: {operation}")
    return changed


def _render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Semantic QA Benchmark Report",
            "",
            f"- Papers: {report['paper_count']}",
            f"- Human-reviewed slides: {report['slide_count']}",
            f"- Baseline semantic findings: {report['baseline_finding_count']}",
            f"- Injected cases detected: {report['detected_cases']}/{report['mutation_cases']}",
            f"- Detection recall: {report['detection_recall']:.1%}",
            f"- Unexpected findings: {report['unexpected_finding_count']}",
            "",
            "## Per paper",
            "",
            "| Paper | Slides | Baseline findings |",
            "|---|---:|---:|",
            *[
                f"| {paper['paper_id']} | {paper['slides']} | {paper['baseline_findings']} |"
                for paper in report["papers"]
            ],
            "",
            "## Boundary",
            "",
            "This benchmark calibrates deterministic gates against human-reviewed offline drafts and "
            "injected failures. It does not measure a remote model evaluator's real-world accuracy.",
            "",
        ]
    )


def run_semantic_benchmark(config_path: Path, output_dir: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    root = config_path.parent
    config = _load_config(config_path)
    loaded: dict[str, tuple[SlideSpec, EvidenceGraph, SemanticQADraft]] = {}
    paper_results: list[dict[str, Any]] = []
    baseline_finding_count = 0
    slide_count = 0

    for paper in config["papers"]:
        workspace = (root / paper["workspace"]).resolve()
        draft_path = (root / paper["semantic_draft"]).resolve()
        spec = read_model(workspace / "data" / "slide_spec.json", SlideSpec)
        graph = read_model(workspace / "data" / "evidence_graph.json", EvidenceGraph)
        draft = SemanticQADraft.model_validate_json(draft_path.read_text(encoding="utf-8"))
        findings, _ = inspect_semantic_draft(draft, spec, graph)
        loaded[paper["paper_id"]] = (spec, graph, draft)
        baseline_finding_count += len(findings)
        slide_count += len(spec.slides)
        paper_results.append(
            {
                "paper_id": paper["paper_id"],
                "slides": len(spec.slides),
                "baseline_findings": len(findings),
            }
        )

    detected = 0
    unexpected = 0
    case_results: list[dict[str, Any]] = []
    for case in config.get("mutations", []):
        try:
            spec, graph, draft = loaded[case["paper_id"]]
        except KeyError as exc:
            raise QualityAssuranceError(f"Unknown benchmark paper: {case['paper_id']}") from exc
        findings, _ = inspect_semantic_draft(_mutate(draft, case), spec, graph)
        codes = {finding.code for finding in findings}
        matched = case["expected_code"] in codes
        detected += int(matched)
        unexpected += len(codes - {case["expected_code"]})
        case_results.append(
            {
                "case_id": case["case_id"],
                "expected_code": case["expected_code"],
                "observed_codes": sorted(codes),
                "detected": matched,
            }
        )

    mutation_count = len(case_results)
    report = {
        "schema_version": "1.0",
        "paper_count": len(paper_results),
        "slide_count": slide_count,
        "baseline_finding_count": baseline_finding_count,
        "mutation_cases": mutation_count,
        "detected_cases": detected,
        "detection_recall": detected / mutation_count if mutation_count else 0.0,
        "unexpected_finding_count": unexpected,
        "papers": paper_results,
        "cases": case_results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        output_dir / "semantic_benchmark.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    write_text(output_dir / "semantic_benchmark.md", _render_markdown(report))
    return report
