from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from research2slides.artifacts import read_model, write_model, write_text
from research2slides.exceptions import ProviderError, QualityAssuranceError
from research2slides.models import (
    EvidenceGraph,
    PresentationPlan,
    QACategory,
    QAIssue,
    QASeverity,
    Repairability,
    SemanticQADraft,
    SemanticQAProvenance,
    SemanticQAResult,
    SlideSpec,
)
from research2slides.providers.responses import StructuredResponsesClient, Transport
from research2slides.qa.common import issue


PROMPT_VERSION = "semantic-qa-v1"


class SemanticQAProvider(Protocol):
    provider_name: str
    model_name: str

    def cache_key(self) -> str: ...

    def evaluate(self, context: str) -> SemanticQADraft: ...


class JsonSemanticQAProvider:
    provider_name = "json-semantic-qa"
    model_name = "offline-fixture"

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    def cache_key(self) -> str:
        try:
            return hashlib.sha256(self.path.read_bytes()).hexdigest()
        except OSError as exc:
            raise ProviderError(f"Unable to read semantic QA draft {self.path}: {exc}") from exc

    def evaluate(self, context: str) -> SemanticQADraft:
        del context
        try:
            return SemanticQADraft.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise ProviderError(f"Invalid semantic QA draft {self.path}: {exc}") from exc


class OpenAISemanticQAProvider:
    provider_name = "openai-responses"

    def __init__(
        self,
        prompt: str,
        model: str = "gpt-5.6-sol",
        reasoning_effort: str = "high",
        base_url: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        timeout_seconds: int = 180,
        transport: Transport | None = None,
    ) -> None:
        self.prompt = prompt
        self.model_name = model
        self._client = StructuredResponsesClient(
            model=model,
            reasoning_effort=reasoning_effort,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )

    def cache_key(self) -> str:
        return self._client.cache_key(self.prompt)

    def evaluate(self, context: str) -> SemanticQADraft:
        return self._client.generate(
            self.prompt,
            context,
            SemanticQADraft,
            "research2slides_semantic_qa_draft",
        )


def _fingerprint(
    spec: SlideSpec,
    plan: PresentationPlan,
    graph: EvidenceGraph,
    provider: SemanticQAProvider,
) -> str:
    digest = hashlib.sha256()
    digest.update(PROMPT_VERSION.encode("utf-8"))
    digest.update(provider.cache_key().encode("ascii"))
    for model in (spec, plan, graph):
        digest.update(
            json.dumps(model.model_dump(mode="json"), ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
    return digest.hexdigest()


def _context(spec: SlideSpec, plan: PresentationPlan, graph: EvidenceGraph) -> str:
    nodes = {node.id: node for node in graph.nodes}
    units = {unit.unit_id: unit for unit in plan.units}
    slides: list[dict[str, object]] = []
    for slide in spec.slides:
        unit = units.get(slide.unit_id)
        slides.append(
            {
                "slide_id": slide.slide_id,
                "order": slide.order,
                "role": unit.role if unit else None,
                "question": slide.question,
                "title": slide.title,
                "main_claim": slide.main_claim,
                "body": slide.body,
                "takeaway": slide.takeaway,
                "evidence": [
                    (
                        nodes[evidence_id].model_dump(mode="json")
                        if evidence_id in nodes
                        else {"id": evidence_id, "missing": True}
                    )
                    for evidence_id in slide.evidence_ids
                ],
            }
        )
    return json.dumps(
        {
            "paper_id": spec.paper_id,
            "mode": spec.mode.value,
            "slides": slides,
            "evidence_edges": [edge.model_dump(mode="json") for edge in graph.edges],
        },
        ensure_ascii=False,
        indent=2,
    )


def _validate_draft(
    draft: SemanticQADraft,
    spec: SlideSpec,
    graph: EvidenceGraph,
) -> None:
    expected_slide_ids = [slide.slide_id for slide in spec.slides]
    actual_slide_ids = [evaluation.slide_id for evaluation in draft.evaluations]
    if actual_slide_ids != expected_slide_ids:
        raise QualityAssuranceError(
            "Semantic QA evaluations must match Slide Spec order exactly: "
            f"expected {expected_slide_ids}, got {actual_slide_ids}"
        )
    nodes = {node.id for node in graph.nodes}
    slides = {slide.slide_id: slide for slide in spec.slides}
    for evaluation in draft.evaluations:
        slide = slides[evaluation.slide_id]
        unknown_evidence = set(evaluation.evidence_ids) - nodes
        outside_slide = set(evaluation.evidence_ids) - set(slide.evidence_ids)
        if unknown_evidence or outside_slide:
            raise QualityAssuranceError(
                f"Semantic QA {evaluation.slide_id} references evidence outside the slide: "
                f"{sorted(unknown_evidence | outside_slide)}"
            )
        for dependency in evaluation.dependencies:
            unknown_slides = set(dependency.prerequisite_slide_ids) - set(expected_slide_ids)
            if unknown_slides:
                raise QualityAssuranceError(
                    f"Semantic QA {evaluation.slide_id} references unknown prerequisite slides: "
                    f"{sorted(unknown_slides)}"
                )


def _issues(result: SemanticQAResult, spec: SlideSpec) -> tuple[list[QAIssue], dict[QACategory, int]]:
    findings: list[QAIssue] = []
    slide_order = {slide.slide_id: slide.order for slide in spec.slides}
    factual_checks = 0
    storyline_checks = 0
    for evaluation in result.evaluations:
        factual_checks += 2
        if evaluation.claim_evidence == "unsupported":
            findings.append(
                issue(
                    QACategory.FACTUAL,
                    "CLAIM_EVIDENCE_UNSUPPORTED",
                    QASeverity.ERROR,
                    f"{evaluation.slide_id} 的 main claim 不能由所列 evidence 推出："
                    f"{evaluation.claim_evidence_rationale}",
                    slide_ids=[evaluation.slide_id],
                    evidence_ids=evaluation.evidence_ids,
                    repairability=Repairability.NONE,
                    suggested_action="回到 Evidence Graph 或 Slide Spec 人工修正 claim/证据映射，禁止 QA 自动改写。",
                )
            )
        elif evaluation.claim_evidence == "partially_supported":
            findings.append(
                issue(
                    QACategory.FACTUAL,
                    "CLAIM_EVIDENCE_PARTIAL",
                    QASeverity.WARNING,
                    f"{evaluation.slide_id} 的 main claim 只有部分内容被 evidence 支持："
                    f"{evaluation.claim_evidence_rationale}",
                    slide_ids=[evaluation.slide_id],
                    evidence_ids=evaluation.evidence_ids,
                    repairability=Repairability.NONE,
                    suggested_action="人工缩窄 claim 或补充已有证据；不要让 evaluator 自行生成新事实。",
                )
            )
        elif evaluation.claim_evidence == "insufficient_evidence":
            findings.append(
                issue(
                    QACategory.FACTUAL,
                    "CLAIM_EVIDENCE_INSUFFICIENT",
                    QASeverity.WARNING,
                    f"{evaluation.slide_id} 的 evidence 不足以完成语义判断："
                    f"{evaluation.claim_evidence_rationale}",
                    slide_ids=[evaluation.slide_id],
                    evidence_ids=evaluation.evidence_ids,
                    repairability=Repairability.NONE,
                    suggested_action="人工复核原文定位并决定补充证据、缩窄 claim 或保留显式不确定性。",
                )
            )

        if evaluation.claim_strength == "overstated":
            findings.append(
                issue(
                    QACategory.FACTUAL,
                    "CLAIM_STRENGTH_OVERSTATED",
                    QASeverity.ERROR,
                    f"{evaluation.slide_id} 的措辞强于证据允许的结论："
                    f"{evaluation.claim_strength_rationale}",
                    slide_ids=[evaluation.slide_id],
                    evidence_ids=evaluation.evidence_ids,
                    repairability=Repairability.NONE,
                    suggested_action="人工校准因果、显著性、普遍性或 SOTA 等措辞，保持原始证据不变。",
                )
            )
        elif evaluation.claim_strength == "understated":
            findings.append(
                issue(
                    QACategory.FACTUAL,
                    "CLAIM_STRENGTH_UNDERSTATED",
                    QASeverity.INFO,
                    f"{evaluation.slide_id} 的措辞可能弱于现有证据："
                    f"{evaluation.claim_strength_rationale}",
                    slide_ids=[evaluation.slide_id],
                    evidence_ids=evaluation.evidence_ids,
                    suggested_action="仅在人工确认不改变论文原意时增强措辞；该提示不要求修改。",
                )
            )

        for dependency in evaluation.dependencies:
            storyline_checks += 1
            if not dependency.required:
                continue
            if not dependency.prerequisite_slide_ids:
                findings.append(
                    issue(
                        QACategory.STORYLINE,
                        "STORYLINE_PREREQUISITE_MISSING",
                        QASeverity.WARNING,
                        f"{evaluation.slide_id} 使用概念“{dependency.concept}”前缺少必要铺垫："
                        f"{dependency.rationale}",
                        slide_ids=[evaluation.slide_id],
                        repairability=Repairability.NONE,
                        suggested_action="人工补充受证据支持的前置解释，或降低本页对该概念的依赖。",
                    )
                )
                continue
            late = [
                slide_id
                for slide_id in dependency.prerequisite_slide_ids
                if slide_order[slide_id] >= slide_order[evaluation.slide_id]
            ]
            if late:
                findings.append(
                    issue(
                        QACategory.STORYLINE,
                        "STORYLINE_DEPENDENCY_ORDER",
                        QASeverity.WARNING,
                        f"{evaluation.slide_id} 依赖的概念“{dependency.concept}”出现在本页之后或本页："
                        f"{', '.join(late)}。{dependency.rationale}",
                        slide_ids=[evaluation.slide_id, *late],
                        repairability=Repairability.NONE,
                        suggested_action="在 Presentation Plan 中调整顺序或增加前置解释，再重新生成 Slide Spec。",
                    )
                )
    return findings, {
        QACategory.FACTUAL: factual_checks,
        QACategory.STORYLINE: storyline_checks,
    }


def inspect_semantic_draft(
    draft: SemanticQADraft,
    spec: SlideSpec,
    graph: EvidenceGraph,
) -> tuple[list[QAIssue], dict[QACategory, int]]:
    """Apply local Phase 9 gates to an evaluator draft without writing artifacts."""
    _validate_draft(draft, spec, graph)
    result = SemanticQAResult(
        paper_id=spec.paper_id,
        evaluations=draft.evaluations,
        provenance=SemanticQAProvenance(
            provider="benchmark",
            model="offline",
            prompt_version=PROMPT_VERSION,
            input_fingerprint="0" * 64,
        ),
    )
    return _issues(result, spec)


def run_semantic_qa(
    workspace: Path,
    spec: SlideSpec,
    plan: PresentationPlan,
    graph: EvidenceGraph,
    provider: SemanticQAProvider,
    *,
    force: bool = False,
) -> tuple[SemanticQAResult, list[QAIssue], dict[QACategory, int], bool]:
    data_dir = workspace / "data"
    result_path = data_dir / "semantic_qa.json"
    manifest_path = data_dir / "semantic_qa.manifest.json"
    fingerprint = _fingerprint(spec, plan, graph, provider)
    if not force and result_path.is_file() and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QualityAssuranceError(f"Invalid semantic QA manifest {manifest_path}: {exc}") from exc
        if manifest.get("input_fingerprint") == fingerprint:
            result = read_model(result_path, SemanticQAResult)
            findings, counts = _issues(result, spec)
            return result, findings, counts, True

    draft = provider.evaluate(_context(spec, plan, graph))
    _validate_draft(draft, spec, graph)
    result = SemanticQAResult(
        paper_id=spec.paper_id,
        evaluations=draft.evaluations,
        provenance=SemanticQAProvenance(
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=PROMPT_VERSION,
            input_fingerprint=fingerprint,
        ),
    )
    write_model(result_path, result)
    write_text(
        manifest_path,
        json.dumps(
            {
                "semantic_qa_version": PROMPT_VERSION,
                "input_fingerprint": fingerprint,
                "provider": provider.provider_name,
                "model": provider.model_name,
                "semantic_qa": str(result_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    findings, counts = _issues(result, spec)
    return result, findings, counts, False
