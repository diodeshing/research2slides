# Paper Reading Storyline Prompt — v2

Create a `paper-reading` presentation storyline using only supported nodes from the supplied evidence graph. Return JSON matching the provided schema.

The audience wants to understand and critically assess another author's paper. Use third-person language such as “the authors propose / 作者提出.” Never say “we propose” or “our method.” Distinguish source claims from presenter analysis.

Default narrative logic:

Problem -> Background / Existing Approaches -> Research Gap -> Core Insight -> Method Overview -> Key Components -> Experiments -> Ablation / Analysis -> Limitations -> Takeaways

Adapt the sequence when the evidence does not support a section; do not invent a missing gap, ablation, or limitation. Each unit must answer one audience question, make one main claim, and cite one or more existing evidence IDs. Keep experiment units tied to the claim they validate.

Clarity First: include every information unit needed to explain the paper clearly. Do not target a slide count or time budget. Set realistic speaking estimates between 20 and 300 seconds; deterministic compression happens after the full plan is validated.

Use the supplied `zh_cn_bilingual_terms` policy. Write the title, audience description, section names, questions, claims, rationale, and transitions as natural Chinese presentation prose. Introduce an important technical term as `中文名称（English Term）` on first use, then use the Chinese name, abbreviation, or established English name without repeating parentheses. Keep model, algorithm, module, Dataset, Metric, Loss, variable, formula, abbreviation, and author-defined component names in their established English form.

Do not draft an English storyline for later translation. Reorganize the scientific meaning directly into Chinese presentation wording. Preserve the distinction between source claims and presenter analysis. Claim wording may synthesize cited nodes, but every number must occur in the cited evidence-node claims.
