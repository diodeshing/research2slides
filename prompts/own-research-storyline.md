# Own Research Storyline Prompt — v2

Create an `own-research` presentation storyline using only supported nodes from the supplied evidence graph. Return JSON matching the provided schema.

The presenter is explaining their own research for a progress review, defense, or conference talk. Use “we propose / 我们提出” only for claims whose evidence belongs to the user's work. Make motivation, novelty boundaries, contribution-to-evidence links, limitations, and incomplete results explicit.

Default narrative logic:

Problem -> Motivation -> Gap -> Our Idea -> Contributions -> Method -> Evidence -> Ablation -> Analysis -> Limitations -> Conclusion

Background and related work must serve the gap or a design decision; keep them shorter than in paper-reading mode. Do not inflate novelty or convert an unsupported interpretation into a contribution. If evidence for a gap, ablation, or limitation is absent, omit the unit instead of filling it from outside knowledge.

Clarity First: include every information unit needed to explain and defend the work. Do not target a slide count or time budget. Set realistic speaking estimates between 20 and 300 seconds; deterministic compression happens after validation.

Use the supplied `zh_cn_bilingual_terms` policy. Write the title, audience description, section names, questions, claims, rationale, and transitions as natural Chinese presentation prose. Introduce an important technical term as `中文名称（English Term）` on first use, then use the Chinese name, abbreviation, or established English name without repeating parentheses. Keep model, algorithm, module, Dataset, Metric, Loss, variable, formula, abbreviation, and author-defined component names in their established English form.

Do not draft an English storyline for later translation. Reorganize the scientific meaning directly into Chinese presentation wording. Each unit must have one audience question, one main claim, and one or more existing evidence IDs. Every number must occur in the cited evidence-node claims.
