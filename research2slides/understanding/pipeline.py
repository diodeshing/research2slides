from __future__ import annotations

import hashlib
from pathlib import Path

from research2slides.artifacts import read_model, write_model
from research2slides.models import (
    EvidenceGraph,
    PaperStructure,
    ScientificUnderstanding,
    UnderstandingProvenance,
    VisualManifest,
)
from research2slides.understanding.catalog import SourceCatalog
from research2slides.understanding.context import build_analysis_context
from research2slides.understanding.evidence_graph import (
    build_evidence_graph,
    build_scientific_understanding,
)
from research2slides.understanding.providers import PROMPT_VERSION, UnderstandingProvider


def _fingerprint(data_dir: Path, provider: UnderstandingProvider) -> str:
    digest = hashlib.sha256()
    for name in ("paper_structure.json", "visual_manifest.json"):
        digest.update(name.encode("utf-8"))
        digest.update((data_dir / name).read_bytes())
    digest.update(provider.cache_key().encode("ascii"))
    return digest.hexdigest()


def run_understanding(
    workspace: Path,
    provider: UnderstandingProvider,
    force: bool = False,
) -> tuple[ScientificUnderstanding, EvidenceGraph, bool]:
    data_dir = workspace.resolve() / "data"
    paper = read_model(data_dir / "paper_structure.json", PaperStructure)
    visuals = read_model(data_dir / "visual_manifest.json", VisualManifest)
    fingerprint = _fingerprint(data_dir, provider)
    understanding_path = data_dir / "scientific_understanding.json"
    graph_path = data_dir / "evidence_graph.json"

    if not force and understanding_path.is_file() and graph_path.is_file():
        understanding = read_model(understanding_path, ScientificUnderstanding)
        graph = read_model(graph_path, EvidenceGraph)
        if understanding.provenance.input_fingerprint == fingerprint and graph.paper_id == paper.paper_id:
            return understanding, graph, True

    catalog = SourceCatalog.from_paper(paper)
    context = build_analysis_context(paper, visuals, catalog)
    draft = provider.analyze(context)
    graph = build_evidence_graph(paper.paper_id, draft, catalog)
    provenance = UnderstandingProvenance(
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=PROMPT_VERSION,
        input_fingerprint=fingerprint,
    )
    understanding = build_scientific_understanding(paper.paper_id, draft, graph, provenance)
    write_model(graph_path, graph)
    write_model(understanding_path, understanding)
    return understanding, graph, False

