from __future__ import annotations

import hashlib
import re
from pathlib import Path

from research2slides.models import (
    EvidenceGraph,
    PaperStructure,
    QACategory,
    QAIssue,
    QASeverity,
    Repairability,
    SlideSpec,
    VisualManifest,
)
from research2slides.qa.common import issue


NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")


def _numbers(text: str) -> set[str]:
    return set(NUMBER_RE.findall(text))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_factual(
    spec: SlideSpec,
    graph: EvidenceGraph,
    paper: PaperStructure,
    visuals: VisualManifest,
    workspace: Path,
) -> tuple[list[QAIssue], int]:
    issues: list[QAIssue] = []
    checks_run = 0
    nodes = {node.id: node for node in graph.nodes}
    assets = {asset.asset_id: asset for asset in visuals.assets}
    tables = {table.table_id: table for table in paper.tables}
    equations = {equation.equation_id: equation for equation in paper.equations}

    checks_run += 1
    if len({spec.paper_id, graph.paper_id, paper.paper_id, visuals.paper_id}) != 1:
        issues.append(
            issue(
                QACategory.FACTUAL,
                "PAPER_ID_MISMATCH",
                QASeverity.ERROR,
                "Slide Spec、Evidence Graph、Paper Structure 与 Visual Manifest 的 paper_id 不一致。",
                repairability=Repairability.NONE,
                suggested_action="重新运行上游阶段并确认所有 artifact 来自同一篇论文。",
            )
        )

    for slide in spec.slides:
        checks_run += 4
        unknown = [evidence_id for evidence_id in slide.evidence_ids if evidence_id not in nodes]
        if unknown:
            issues.append(
                issue(
                    QACategory.FACTUAL,
                    "UNKNOWN_EVIDENCE",
                    QASeverity.ERROR,
                    f"{slide.slide_id} 引用了不存在的 evidence ID：{', '.join(unknown)}。",
                    slide_ids=[slide.slide_id],
                    evidence_ids=unknown,
                    repairability=Repairability.NONE,
                    suggested_action="回到 Evidence Graph 或 Slide Spec 修正引用，禁止自动补造证据。",
                )
            )
            continue

        citation_by_evidence = {citation.evidence_id: citation for citation in slide.citations}
        missing_citations = [item for item in slide.evidence_ids if item not in citation_by_evidence]
        if missing_citations:
            issues.append(
                issue(
                    QACategory.FACTUAL,
                    "MISSING_CITATION",
                    QASeverity.ERROR,
                    f"{slide.slide_id} 的 evidence 没有完整映射到可见 citation。",
                    slide_ids=[slide.slide_id],
                    evidence_ids=missing_citations,
                    suggested_action="由 evidence node 的 source locator 重新生成 citation。",
                )
            )
        for evidence_id, citation in citation_by_evidence.items():
            node = nodes.get(evidence_id)
            if node is None:
                continue
            expected_sources = {source.source_id for source in node.sources}
            actual_sources = set(citation.source_ids)
            if not actual_sources or not actual_sources.issubset(expected_sources):
                issues.append(
                    issue(
                        QACategory.FACTUAL,
                        "CITATION_SOURCE_MISMATCH",
                        QASeverity.ERROR,
                        f"{slide.slide_id} 的 citation source 与 evidence locator 不一致。",
                        slide_ids=[slide.slide_id],
                        evidence_ids=[evidence_id],
                        source_ids=sorted(actual_sources),
                        repairability=Repairability.NONE,
                        suggested_action="使用 evidence node 中已有的 source locator，不能自由填写来源。",
                    )
                )

        slide_text = " ".join([slide.title, slide.main_claim, *slide.body, slide.takeaway])
        slide_numbers = _numbers(slide_text)
        supported_parts: list[str] = []
        for evidence_id in slide.evidence_ids:
            supported_parts.append(nodes[evidence_id].claim)
            supported_parts.extend(source.excerpt for source in nodes[evidence_id].sources)
        supported_flat = " ".join(supported_parts)
        unsupported = sorted(slide_numbers - _numbers(supported_flat))
        if unsupported:
            issues.append(
                issue(
                    QACategory.FACTUAL,
                    "UNSUPPORTED_NUMBER",
                    QASeverity.ERROR,
                    f"{slide.slide_id} 中的数字 {', '.join(unsupported)} 未由本页 evidence 支持。",
                    slide_ids=[slide.slide_id],
                    evidence_ids=slide.evidence_ids,
                    repairability=Repairability.NONE,
                    suggested_action="补充已有 evidence 引用或删除无来源数字；禁止 QA 自动改写数值。",
                )
            )

        for visual in slide.visuals:
            if visual.kind == "source_asset":
                asset = assets.get(visual.source_ref)
                if asset is None:
                    issues.append(
                        issue(
                            QACategory.FACTUAL,
                            "UNKNOWN_SOURCE_ASSET",
                            QASeverity.ERROR,
                            f"{slide.slide_id} 引用了不存在的 source asset {visual.source_ref}。",
                            slide_ids=[slide.slide_id],
                            source_ids=[visual.source_ref],
                            repairability=Repairability.NONE,
                            suggested_action="修正 visual_manifest 或 Slide Spec 的 source_ref。",
                        )
                    )
                else:
                    asset_path = (workspace / asset.output_path).resolve()
                    if not asset_path.is_file() or _sha256(asset_path) != asset.sha256:
                        issues.append(
                            issue(
                                QACategory.FACTUAL,
                                "SOURCE_ASSET_HASH_MISMATCH",
                                QASeverity.ERROR,
                                f"{slide.slide_id} 的源视觉文件缺失或哈希发生变化。",
                                slide_ids=[slide.slide_id],
                                source_ids=[visual.source_ref],
                                repairability=Repairability.NONE,
                                suggested_action="从原始论文重新提取视觉资产并更新 manifest。",
                            )
                        )
            elif visual.kind == "source_table" and visual.source_ref not in tables:
                issues.append(
                    issue(
                        QACategory.FACTUAL,
                        "UNKNOWN_SOURCE_TABLE",
                        QASeverity.ERROR,
                        f"{slide.slide_id} 引用了不存在的表格 {visual.source_ref}。",
                        slide_ids=[slide.slide_id],
                        source_ids=[visual.source_ref],
                        repairability=Repairability.NONE,
                        suggested_action="修正 Paper Structure 或表格引用。",
                    )
                )
            elif visual.kind == "source_equation" and visual.source_ref not in equations:
                issues.append(
                    issue(
                        QACategory.FACTUAL,
                        "UNKNOWN_SOURCE_EQUATION",
                        QASeverity.ERROR,
                        f"{slide.slide_id} 引用了不存在的公式 {visual.source_ref}。",
                        slide_ids=[slide.slide_id],
                        source_ids=[visual.source_ref],
                        repairability=Repairability.NONE,
                        suggested_action="修正 Paper Structure 或公式引用。",
                    )
                )
            if (
                visual.kind == "conceptual_diagram"
                and any(nodes[item].type in {"experimental_result", "ablation_result"} for item in slide.evidence_ids)
            ):
                issues.append(
                    issue(
                        QACategory.FACTUAL,
                        "GENERATED_EXPERIMENT_VISUAL",
                        QASeverity.ERROR,
                        f"{slide.slide_id} 使用 conceptual diagram 表达实验结果，可能被误认为原始证据。",
                        slide_ids=[slide.slide_id],
                        evidence_ids=slide.evidence_ids,
                        suggested_action="实验页改用论文原始 Figure/Table，或明确标注为解释性示意图。",
                    )
                )

        low_confidence = [item for item in slide.evidence_ids if nodes[item].confidence == "low"]
        if low_confidence:
            issues.append(
                issue(
                    QACategory.FACTUAL,
                    "LOW_CONFIDENCE_EVIDENCE",
                    QASeverity.WARNING,
                    f"{slide.slide_id} 的核心信息使用了 low-confidence evidence。",
                    slide_ids=[slide.slide_id],
                    evidence_ids=low_confidence,
                    suggested_action="人工核对原文并决定是否保留或降级该 claim。",
                )
            )
    return issues, checks_run
