# Research2Slides Semantic QA 2.0

Evaluate every slide in the supplied JSON context. Treat only the supplied Evidence Graph nodes,
source excerpts, slide content, and slide order as authoritative. Do not use outside knowledge and
do not rewrite the presentation.

For each slide, in exact Slide Spec order:

1. Judge whether every material clause in `main_claim` is entailed by the cited evidence.
   - `entailed`: all material clauses follow directly from the evidence.
   - `partially_supported`: some clauses follow, but at least one meaningful clause does not.
   - `unsupported`: the claim conflicts with or is unrelated to the cited evidence.
   - `insufficient_evidence`: the supplied evidence is too vague to decide safely.
2. Judge claim strength. Mark `overstated` when causal, statistical-significance, universal,
   superlative, SOTA, or certainty language is stronger than the evidence. Use `understated` only
   when the evidence clearly supports a materially stronger conclusion; otherwise use `calibrated`.
3. List only essential prerequisite concepts needed to understand the slide. A prerequisite slide
   must introduce that concept before the current slide. If an essential concept has no available
   prerequisite, set `required=true` and return an empty `prerequisite_slide_ids` list.

Every evaluation must cite a non-empty subset of that slide's own evidence IDs. Do not invent slide
IDs, evidence IDs, significance tests, causal relations, missing experiments, or prerequisite claims.
When uncertain, prefer `insufficient_evidence` and explain the exact evidence boundary.
