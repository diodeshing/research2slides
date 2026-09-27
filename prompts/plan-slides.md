# Slide Spec Shared Invariants — v2

Return JSON matching the provided schema. Convert each selected presentation unit into exactly one slide, preserving unit order, question, main claim, evidence IDs, and estimated speaking time.

Each slide must contain one main idea and make this structure explicit:

Question -> Claim -> Evidence / Visual -> Explanation -> Takeaway

Use the available source asset, Table, or Equation when it materially explains the claim. Do not invent experimental visuals or use an unavailable asset. A conceptual diagram may only reference an existing evidence ID and must explain a mechanism rather than pretend to be measured evidence. Do not reuse the same source visual on multiple slides.

Use a direct topic title for setup/mechanism slides or a supported claim title for finding slides. Never use generic titles such as Method, Experiments, Results, Ablation Study, Motivation, or Conclusion. Avoid em dashes, semicolons, vertical bars, arrows, slogan-like wording, and unnecessary terminal punctuation in titles.

Keep body copy concise and factual. Use no more than five body lines. Avoid dense paragraphs, repeated UI cards, decorative evidence, and small-text solutions to overcrowding.

Apply `zh_cn_bilingual_terms` while authoring the Slide Spec itself. Do not author English slides for a translation post-process.

- Chinese is the primary reading language for titles, section labels, body copy, annotations, takeaway, and speaker-note content.
- Introduce a technical term once as `中文名称（English Term）`, then use its Chinese name, abbreviation, or established English name. Do not translate model, algorithm, module, Dataset, Metric, Loss, formula, mathematical variable, abbreviation, or author-defined component names mechanically.
- Keep claim-based titles natural and concise. Rephrase crowded Chinese titles instead of shrinking them. Avoid word-by-word Chinese-English mixing.
- Keep original source Figure labels, arrows, legends, axes, Table screenshots, and Equation notation unchanged. Explain them with Chinese text outside the source visual. Never redraw or translate a source Figure merely to localize it.
- For a reconstructed editable table, generic column labels may be supplied through `table_column_labels` in Chinese, while model, Dataset, and Metric names and all values remain unchanged.
- Equation notation remains unchanged. Explain the roles of Q, K, V, Softmax, and other symbols in Chinese.
- Every takeaway must be a short Chinese conclusion, preferably one line and never more than two.
- Fixture-only numbers must remain explicitly qualified as software-test data that cannot support a scientific conclusion.

Speaker notes must include Purpose, Main Message, Speaking Script, Visual Guidance, Transition, and Estimated Time. The field names remain English in the schema, but all five text values must be natural Chinese. The script should add explanation rather than read the slide verbatim. `main_message` must equal the slide's `main_claim`; `estimated_seconds` must equal the presentation unit estimate.
