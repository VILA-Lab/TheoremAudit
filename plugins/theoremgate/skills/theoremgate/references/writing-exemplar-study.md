# Writing Exemplar Study

Before designing or drafting a submission-framed manuscript, inspect the full text of three to six
strong papers that match the contribution type, research area, and likely venue family. Select a
small diverse set: at least one closest technical paper, one especially clear exposition exemplar,
and one recent paper with a comparable theorem/experiment balance. Use only papers already present
in the validated literature registry with `fulltext_extracted` or `primary_source_verified` status.

Analyze structure rather than wording. For every exemplar, inspect the abstract, introduction,
related work, main-result exposition, transitions, figures or tables, limitations, and conclusion.
Record observations about information order, motivation-to-theorem transitions, contribution
hierarchy, comparison style, proof-roadmap depth, paragraph function, and visual density. Then derive
cross-paper principles for the new manuscript.

Write schema-v2 `paper/writing_exemplars.json` with:

- `schema_version`, `artifact`, `status`, `purpose`, and `selection_policy`;
- three to six exemplar records containing `record_id`, `selection_reason`, `sections_analyzed`, at
  least three `structural_observations`, and a `page_profile` with `main_pages`, `reference_pages`,
  `appendix_pages`, `total_pages`, and an exact `source_locator` in the inspected PDF;
- `cross_paper_patterns` for `abstract`, `introduction`, `related_work`, `result_exposition`,
  `transitions`, and `visual_presentation`;
- at least four `adopted_principles` and any `rejected_patterns`;
- `originality_safeguards` containing `no_sentence_copying`, `no_author_style_imitation`, and
  `cite_borrowed_technical_ideas`;
- limitations of the exemplar set.

Do not copy sentences, paraphrase distinctive passages, imitate a particular author, or treat an
exemplar's scientific claims as evidence for the current paper. Technical ideas still require normal
citation and literature verification. The study guides architecture and exposition; it never changes
the accepted theorem bundle. For a venue with no formal limit, copy these inspected profiles into
`length_plan.exemplar_page_basis`. For a no-limit journal, use the larger of 10 pages and the largest
observed main-text length as the manuscript's main-text target, while keeping the enforced main-text
minimum at 10 pages and leaving `minimum_total_pages` null. The target guides allocation and is not
an underfill threshold.
