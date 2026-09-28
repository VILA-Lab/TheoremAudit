---
name: manuscript-writing
description: Turn a completed TheoremAudit theory bundle into a complete, citation-grounded theoretical ML manuscript without exceeding proved evidence. Use for paper planning, section writing, full proof or evidence appendices, bibliography, and manuscript assembly.
---

# Manuscript Writing

Start only from a completed theory bundle and contribution assessment. Read the global source rules in
`../theoremgate/references/source-skills/manuscript-compiler.md`, then load the matching preserved
section reference `manuscript-<section>.md` when one fits, or the closest applicable reference for a
model-designed contribution section.

Require a successfully initialized paper workflow and a valid `paper/manuscript_authorization.json`
before writing prose. Never create a substitute manuscript outside the selected run's `paper/`
directory, and never use ordinary file-writing tools to bypass `manuscript_tools.py`.

Before content architecture or prose, read `../theoremgate/references/writing-exemplar-study.md` and
complete `paper/writing_exemplars.json`. Study three to six verified full-text papers matched to the
contribution, area, and likely venue family. Extract cross-paper structural principles only; never copy
sentences or imitate an author's individual style. Bind `content_architecture.json` to this study and
record which principles the architecture adopts.

Read `../theoremgate/references/paper-routing.md` and obey the bundle's deterministic `paper_route`.
Do not confuse the required `full_paper` with submission readiness, and never describe an attributed
or standard result as novel.

When at least one selected statement is accepted, write a full-length manuscript aimed at the venue
selected by the venue-formatting agent in `paper/venue_selection.json`, regardless of whether novelty
is supported, partial, or unverified. Use `paper_route.novelty_positioning` to calibrate contribution language: uncertain
overlap permits describing the proved technical contribution and its candidate distinction, but not
first, unique, or definitive novelty claims. Keep manuscript completeness, provisional venue
formatting, and final submission readiness as separate decisions.

Use only `paper_route.selected_statement_ids` as established results in this manuscript. Use
`result_roles` to integrate positive, supporting, lower-bound, counterexample, and boundary results
into one argument. Statements under `retained_nonfinal_statements` may appear only as clearly labeled
conjectures, open questions, repair directions, or limitations when relevant; never state them as
proved. Ignore `excluded_statements` except when a refutation itself is an accepted result.

Write a normal scholarly paper: never expose workflow, agent, proof-obligation, governance, or Arbiter
terminology. State only accepted claims as results. Keep assumptions, constants, attribution, caveats,
and proof scope exactly aligned with the theory bundle. Conjectures belong in an explicitly labeled
discussion, never among theorems.

Treat every instruction and reference file as private editorial guidance. Use it to make decisions,
but never copy, lightly paraphrase, or expose its wording in the manuscript. Compose reader-facing
sentences directly from the paper's mathematical definitions, results, verified literature, and
recorded experiments. Internal labels and planning language are not scholarly prose.

Use formal reader-facing prose throughout. Name mathematical objects explicitly instead of using
deictic "here"; state the proved scope positively instead of writing "this paper does not claim";
and never expose novelty-verification, submission-readiness, or evidence-gathering status in the
manuscript. Conclusions must synthesize the scientific implication and end with a precise technical
question or direction, not instructions to verify literature or run experiments. Limitations must
describe mathematical or empirical boundaries rather than audit outcomes.

Never insert manual page-control commands such as `\clearpage`, `\newpage`, or `\pagebreak` in
section files. Page boundaries are controlled only by the manuscript assembler at the bibliography
and appendix transitions. If a page or section looks sparse, revise the scholarly substance,
derivations, comparisons, interpretation, or proof detail; do not force layout with page breaks or
padding.

For every accepted result, treat `effective_statement.standalone_formal` as the controlling source
and read `effective_statement.assumption_closure` before drafting. Render every condition explicitly
in the theorem setup or immediately preceding formal context. An assumption ID alone is not
manuscript text. Do not shorten an assumption in a way that drops a range, boundary condition,
initialization rule, dependence condition, or known-parameter requirement.

After the exemplar study, select and stage the best-fit venue before designing the manuscript
architecture. Every first manuscript and every `rewrite_manuscript` pass then uses architecture
schema v3 with a `length_plan` hash-bound to `paper/venue_selection.json`. Derive the scientific
title, logical structure, section order, and page budget from the accepted contribution, matched
exemplars, and the selected venue's verified or provisional rules. Record target and maximum total
pages plus a minimum total only when the venue has a formal scoped limit or the neutral format needs
one; record minimum, target, and maximum main-text pages; minimum and target appendix
pages; target and maximum reference pages; a target for every planned section; the venue hard limit
or null; the exact `page_limit_scope`; `references_before_appendix: true`; and
`appendix_heading: "Appendix"`. At a hard main-text-limit venue, target the full allowance and permit
at most one page of underfill. At a no-limit journal, set `minimum_total_pages: null`, require at
least 10 main-text pages excluding references and appendices, copy page profiles for three to six
inspected exemplars into `exemplar_page_basis`, and set the main-text target to the larger of 10 and
their largest observed main-text length. Treat that exemplar-derived target as planning guidance,
not a minimum or a reason to pad the manuscript. Write and revise to that plan; changing a
template without reworking section content is not a manuscript rewrite.

For a neutral `Research-Draft` evidence report, derive the target from the evidence that must be
explained, not from full-paper exemplars. Use `planning_basis: provisional_venue_target`, set
`minimum_total_pages`, `minimum_main_pages`, and `minimum_appendix_pages` to `null`, and treat every
target as organization guidance only. Never add prose, blank pages, repeated equations, or an
oversized appendix to reach a draft length.

Place Related Work immediately after the introduction by default. Move it later only when
substantial notation or setup is genuinely required to explain the comparison, and record that as an
explicit nonstandard placement with a rationale. Its
drafting time must never determine its assembled position. Venue formatting may compress or style the
architecture but may not silently reorder, rename, or remove scientific content.

Use conventional core headings: `Introduction`, `Related Work`, and `Conclusion`. Limitations may
be a separate section or a concise passage in the conclusion or discussion. Follow the selected
venue's verified requirements: if it requires a standalone `Limitations` section, keep it separate.
Otherwise choose the placement that avoids repetition and fits the paper. In content architecture,
set `limitations_section` to `limitations`, `conclusion`, or `discussion`, naming its planned section.
Record the material scope boundaries in that section's purpose. When integrated, omit the standalone
section and its page allocation; `Conclusion` or `Conclusion and Limitations` are valid closing
headings. Existing plans with a standalone section remain valid without the new field.
For integrated limitations, load `manuscript-discussion.md` as well as the relevant section guide.
State material restrictions and evidence gaps precisely, without blanket judgments about the
work's quality. Prefer one or two compact paragraphs, grouping related issues and referring back to
the setup or experiments instead of repeating them. This is guidance, not a word or page quota.
Never hide unfavorable evidence, move necessary theorem assumptions only to the conclusion, or
present an unresolved proof defect as a harmless limitation; preserve the claim-acceptance rules.

Choose every other section title for reader clarity and navigation. Conventional titles such as
`Main Results`, `Method`, `Analysis`, or `Experiments` are valid when they are the clearest description
of the section; technical titles such as `Anchored Clipping Bounds` are equally valid. Combined
titles may communicate both role and content, for example `Main Results: Anchored Clipping and Private
Estimation` or `Experiments: Dimension and Tail-Index Scaling`. Use sections and subsections together
when a conventional parent heading and technical child headings create the clearest hierarchy.
Choose among conventional, technical, and combined forms from the paper's argument, terminology,
matched exemplars, venue conventions, and neighboring headings. Do not prefer one form mechanically.
Reject titles only when they are empty, unclear in context, rhetorical, casual, promotional,
needlessly elaborate, or inconsistent with the manuscript's terminology.

Verify every citation with `$literature-audit`. Ingest every paper into the run literature registry
before adding it to `paper/literature_audit.json`; register its claim/section use, cite only the
registry-generated key, and let manuscript assembly generate `references.bib`. Build the manuscript in a separate paper directory;
never edit the completed theory artifacts. The universal section set is Abstract, Introduction,
Related Work, and Conclusion; limitations coverage is required, but its placement is flexible as
described above. Design the remaining section hierarchy from the actual
contribution and choose conventional, technical, or combined headings according to clarity. Every primary
accepted statement must appear in at least one substantive model-designed contribution section.
When empirical evidence is required, mark an appropriately named section with
`evidence_types: ["empirical", "visual"]`.
For every paper containing accepted selected statements, use architecture schema v3 and plan a dedicated appendix
section with `evidence_types: ["proof"]`, `location: "appendix"`,
`proof_mode: "appendix_full"`, and `complete_proof: true`. The appendix must give a complete proof
for every result in `paper_route.selected_statement_ids`, including supporting lemmas from its proof
dependency chain. Typeset every selected result in a theorem-like environment in the main paper and
record a `proof_appendix_map` entry with its unique `statement_label` and
`appendix_proof_label`. The main statement must refer to the exact appendix proof, and that proof
must refer back to the exact statement. Choose a clear proof-section title that fits the paper's
hierarchy; a conventional title such as `Proofs`, a technical title, or a combined title such as
`Proofs of the Main Results` may be used. Assembly must emit the bibliography first, then `\appendix`, an
explicit `Appendix` heading, and the proof sections.

Architecture must also include one `proof_detail_plan` entry per selected result. Each entry records
the proof strategy, every assumption and where it is used, supporting results, at least three
critical steps with their justifications, at least one boundary or edge-case check with its
resolution, and the final concluding inference. Allocate at least three appendix-proof pages for one
selected result and at least 1.5 pages per selected result when there are several; increase this when
the dependency chain is longer. The appendix proof itself must follow this plan: introduce local
notation, state auxiliary lemmas, derive rather than merely cite the key inequalities, track constants
and probability events, handle endpoints and degenerate cases, and explicitly close the claimed
conclusion. A
proof roadmap, sketch, restatement, slogan, omitted central calculation, or arbitrary equation
padding is not a complete proof. This applies to every `full_paper` regardless of its contribution
shape or submission readiness.

Architecture must additionally include one `main_text_math_plan` entry per selected result. Assign
the result to a main contribution section; bind its theorem label to `proof_appendix_map`; name its
setup objects; and plan labeled key derivations, supporting lemmas when needed, a justified
three-step proof roadmap, technical interpretation, and the exact appendix connection. A primary
result requires at least two source-backed displayed derivations in the main text; every other
selected result requires at least one. Section validation checks those labels in rendered LaTeX
structures. Do not satisfy this contract with decorative equations or by copying the appendix into
the main paper: expose the mathematical mechanism needed to understand and assess the theorem.

Every accepted-result architecture must also include a `visual_evidence_plan`. Classify each
selected statement as empirically testable or not empirically testable. Put the testable statement
IDs in `empirical_claim_ids`, assign them to one main-text section whose `evidence_types` include
both `empirical` and `visual`, and state the scientific question the figure will answer. Do not leave
claims deferred. Do not prescribe a table or table schema in the architecture.

When empirical validation completes or contradicts a prediction, include the emitted LaTeX snippet
for every publication-ready main figure in the assigned empirical section. The included main figures
must collectively cover every `empirical_claim_id`. Tables are optional and paper-dependent. Include
one only when rows and columns communicate substantive theoretical or empirical information more
clearly than prose, equations, or figures. Choose its structure from the paper's scientific needs
and venue conventions rather than a fixed schema. Every included table must be publication-ready
and legible at final manuscript size; otherwise revise it, split it, convert it to prose, or remove
it.

When `paper_route.selected_statement_ids` is empty, write an `evidence_report` rather than
inventing a result. Use architecture schema v3 and plan a dedicated appendix with
`evidence_types: ["audit"]`, `location: "appendix"`, `complete_evidence: true`, and non-empty
`source_artifacts`. Explain the attempted claims, exact audit failure, preserved proof evidence,
limitations, and strongest supported next step. Do not use theorem-like environments for rejected or
unproved claims.

Treat bibliography size as a coverage gate rather than decoration. For a mature area, require at
least 20 relevant audited references. Apply the same 20-reference floor to an original-conference
research goal. Every other paper requires at least 15. These are hard cited-source floors: do not
waive them through a narrow-theorem classification, route downgrade, or search-saturation claim.
Do not turn a validator floor into the search target or assemble a compact audit from whichever
records are already present. Before drafting Related Work, consume the
audited closest-work comparison records. The introduction must name the nearest technical boundary
concisely; Related Work must compare assumptions, result type, tightness, scope, and remaining overlap;
result sections should make local comparisons only where they clarify a theorem.
The reference floor applies to relevant sources actually cited in section files and exported into
`paper/references.bib`, not merely records collected by the literature audit.

Give every major result a motivation paragraph, formal statement, real proof roadmap, and an
interpretation paragraph explaining the question answered, nontrivial obstacle, tightness,
closest-work difference, binding assumption, and consequence. Do not compress all interpretation
into the abstract or conclusion.

Use `../../scripts/manuscript_tools.py` to write indexed sections, assemble `paper.tex`, run the fixed
LaTeX compiler when available, and persist an independent review. Assembly follows
`paper/content_architecture.json`, not section-file creation order.
Compilation records rendered main-text, reference, appendix, and total page counts from
assembler-inserted page-boundary labels. Every hard venue constraint, the 10-page no-limit-journal
main-text floor, and the proof-appendix minimum must be satisfied. Exemplar-derived targets guide
balance but are not underfill failures. If an enforced component is short or long, revise section substance and
balance before review; do not merely
change margins, font size, or the venue template.
Page targets guide allocation and reveal potentially missing substance; they never authorize
padding. Once the scientific argument and required evidence are complete, do not increase length by
restating contributions, repeating motivation or limitations, adding filler transitions or
boilerplate roadmaps, duplicating equations, or paraphrasing material already established elsewhere.
When an enforced minimum is unmet, add only genuinely missing scholarly substance—such as a needed
derivation, interpretation, comparison, experiment, or proof detail—or report the unresolved length
constraint. Never satisfy it through repetition.
The controller treats layout, LaTeX presentation, and planned-exposition deficiencies as
recoverable manuscript findings. Preserve the compile, return to `section_writing`, revise the
affected mathematics or exposition, and recompile automatically. Permit at most two such repair
rounds after the initial compile. If the third compile still has presentation findings, restore the
best archived PDF and continue to independent review with explicit warnings. Never use this policy
to package an unsupported claim or unresolved mathematical-correctness finding.
Required experiments must be completed before prose drafting. A future experiment plan belongs in
limitations or future work and cannot occupy an empirical-evidence section or satisfy the route.

Treat user feedback as manuscript evidence, not informal chat context. Record each custom requested
change exactly once with `add-user-comment`, including its edit type, scope, target, and priority.
Reviewer findings are already persisted evidence and must not be duplicated as user comments. When
independent review returns actionable findings, address all of them automatically in one revision
cycle while retaining an explicit response for every finding ID. During revision, use `write-revision`
to answer every reviewer finding and every open user comment. Each response must state its disposition
and bind the changed paper files by SHA-256. Keep edits within the requested targets unless a linked
downstream change is required for consistency, and explain every such expansion in the revision
response. Replacing an existing section requires a reason and preserves the prior section record in
history.

Revision is iterative: edit the indexed sections, record the response artifact, reassemble,
recompile, and request a fresh independent review. Never package the pre-revision PDF. A clean
`accept` must refer to the latest compile report for a submission-ready package. A clean manuscript
whose submission evidence is incomplete uses `draft_ready` as an internal review disposition,
proceeds to final packaging, and keeps `ready_for_submission_check: false`. This does not rename or
downgrade the `full_paper`. New user feedback after review reopens the revision cycle.
For every review finding that concerns a recoverable manuscript presentation issue, record
`repair_class` as one of `layout`, `exposition`, `figure_presentation`, `table_presentation`,
`citation_presentation`, or `latex_presentation`. Do not assign one of these classes to a mathematical-correctness or
claim-evidence defect.
