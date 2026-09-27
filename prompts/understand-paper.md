# Scientific Understanding Prompt — v1

Analyze only the supplied structured paper artifacts. Return JSON matching the provided schema.

For every claim:

- choose one of the twelve requested categories;
- choose the narrowest supported evidence-node type;
- cite one or more exact `source_id` values from the evidence catalog;
- copy a short exact excerpt from each cited source into `excerpt`;
- use `high` confidence only when the source states the claim directly;
- use `medium` or `low` for bounded interpretation;
- omit a claim when the artifacts do not support it.

Do not use outside knowledge. Do not infer experimental numbers. For quantitative experimental or ablation claims, every number in the claim must appear in the cited source. Do not turn fixture disclaimers, references, or captions into research conclusions.

The twelve categories correspond to:

1. problem — What problem does the paper solve?
2. importance — Why is it important?
3. existing_approaches — What do existing approaches do?
4. gap — What limitation remains?
5. central_insight — What is the central insight?
6. contributions — What are the actual contributions?
7. method — How does the method work?
8. design_rationale — Why are the design choices necessary?
9. experiment_findings — Which experiments validate which claims?
10. ablation_findings — Which ablations are informative?
11. limitations — What limitations remain?
12. audience_takeaways — What should the audience remember?

Relations refer to zero-based claim indexes in the returned `claims` array. Add only relations supported by the meaning of the claims. Empty `claims` and `relations` arrays are valid when the material is insufficient.

