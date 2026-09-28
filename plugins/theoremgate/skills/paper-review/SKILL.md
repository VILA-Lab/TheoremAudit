---
name: paper-review
description: Independently review and revise a theory manuscript for mathematical correctness, claim-evidence alignment, novelty, citations, exposition, experiments, and venue compliance. Use after manuscript assembly and before final packaging.
---

# Paper Review

For version-2 empirical strategies, inspect resource provenance, sampling and annotation evidence,
managed execution receipts, and resource-limit failures. Pilots are feasibility checks, not the
completed study. Real data with injected noise does not establish natural annotation-noise behavior.
Check that reported uncertainty and application scope match the actual sample and reference labels.

Review the paper against the immutable theory bundle, proof artifacts, literature audit, experiment
records, and selected venue rules.

Issue findings by severity and section. Check that every headline claim is accepted, every theorem has
the same assumptions and scope as its source, proofs are complete, citations entail their claims,
limitations are honest, figures are reproducible, and internal workflow vocabulary is absent.
For each selected result, compare the appendix proof against its `proof_detail_plan`, governed proof
draft, dependency chain, and assumption closure. Verify every critical step, constant, probability
event, quantifier, endpoint, and boundary case. Treat “standard argument,” “routine calculation,”
“details omitted,” a proof sketch, or a long but repetitive derivation as a major proof-completeness
finding. Page count and equation count never substitute for mathematical closure.
Also compare each main contribution section against `main_text_math_plan`. Confirm that the formal
statement, source-backed key derivations, supporting results, proof roadmap, interpretation, and
appendix connection are present and mathematically useful. A complete appendix does not excuse a
main paper that hides the mechanism of its central theorem.
For every main figure, inspect the hash-bound paper-size rendering rather than trusting declared visual
scores; reject crowded legends, unbalanced panels, tiny axes or text, and excessive whitespace.
Inspect the active `visual_evidence_plan` as well. For an empirical plan, verify that the assigned
section includes publication-ready main figures covering every declared testable claim. Inspect every
table the manuscript contains at final rendered size, including theoretical and experimental tables.
Require accurate evidence-backed entries, publication-quality typography, meaningful headers, a
self-contained caption, concise cells, consistent notation, and legible hierarchy. Recommend
revision, splitting, conversion to prose, or removal when a table is crowded, decorative, redundant,
or scientifically uninformative.

Score every written section independently on clarity, narrative function, evidence alignment, and
scholarly exposition. Inspect the compiled PDF page by page. A clean accept requires every section to
score at least 4/5 and explicit checks for cross-references, citations, leaked LaTeX commands, figure
readability at final size, page layout, and title rendering. Treat malformed commands, manual
page-control commands inside section content, wrong equation references, unreadable figures, and
unexplained blank space as findings rather than cosmetic notes.
As part of `proofreading_checks.page_layout`, inspect the final main-text page separately. The check
passes only when the page is professionally occupied or its whitespace is structurally justified by an
explicit venue rule. A conclusion that spills a small amount onto an otherwise empty page, or an
unnecessary forced break before References, requires a layout finding and a natural rebalance. Permit
References to follow the Conclusion on the same page unless the staged venue explicitly requires a fresh
page. Do not repair page balance by shrinking fonts, adding negative spacing, or cutting substantive
content solely to make it fit.
Verify the compile report's rendered main/reference/appendix boundaries. Conference manuscripts must
respect the official page-limit scope. A no-limit journal manuscript must contain at least 10 pages
of main text, excluding references and appendices, and its proof appendix must meet its independent
minimum. Exemplar-derived target or total lengths are planning guidance: do not issue an underfill
finding or request padding merely because a sound manuscript is shorter than that target.

Audit prose as reader-facing scholarship rather than internal evaluation. Reject deictic "here,"
author task lists, publication-process language, novelty-audit verdicts, negative claim disclaimers
such as "this paper does not claim," and conclusions that instruct the authors to verify literature
or run experiments. Require limitations to state exact mathematical or empirical boundaries and
require conclusions to end with a substantive implication or precise open question. Treat repeated
audit-report prose as a major scholarly-exposition finding, not a cosmetic preference.

Check limitations in the section named by `content_architecture.limitations_section`, or in the
standalone section for legacy plans. A concise conclusion or discussion passage is sufficient
unless the selected venue requires a separate Limitations section. Do not request a new section
or extra length merely to satisfy a preferred format. Check that material restrictions and evidence
gaps are clear, accurate, and not repeated as a catalogue of every assumption or abandoned attempt.
Request precise scope statements instead of blanket self-criticism, but never suppress a genuine
weakness, negative result, or unresolved defect to make the paper sound stronger. An unproved
accepted claim remains a mathematical finding even if its proof gap is disclosed as a limitation.

Treat instruction and reference files as private editorial material. Reject sentences that copy or
lightly paraphrase their wording or expose internal planning terminology. Require paper-specific
scholarly prose grounded directly in definitions, results, citations, and recorded evidence.

Apply a professional-presentation gate before issuing a clean accept. A manuscript cannot receive
`accept` when any page looks visually unfinished, any section reads like a compressed outline rather
than a paper section, any figure combines unrelated diagnostics into an overloaded panel grid, any
caption fails to explain the plotted evidence, any table is decorative or hard to read, or any
paragraph sounds like generated boilerplate rather than contribution-specific scholarly writing.
Record each such defect as a finding with the appropriate presentation repair class and a concrete
required action, such as expanding the affected section with missing derivation or comparison,
splitting an overloaded figure, rewriting a caption, removing a redundant table, or rebalancing the
final page naturally.

Check that the title, abstract, contribution language, venue choice, and submission-readiness flag do
not exceed the bundle's `paper_route` or violate its allowed claims, prohibited claims, and required
attribution.

Act like a skeptical ML/NLP venue reviewer. Score technical quality, clarity, novelty, significance,
empirical validation, and reproducibility from 1–5; record confidence, route consistency, and whether
application evidence is sufficient. Exact-model simulations do not validate a real-system claim,
and required operational parameters need sensitivity analysis. Every finding must include ID,
severity, criterion, description, and required action.
Classify a finding with `repair_class: layout`, `exposition`, `figure_presentation`, `table_presentation`,
`citation_presentation`, or `latex_presentation` only when the accepted mathematics remains intact
and the defect can be repaired entirely inside the manuscript. Never classify an unsupported
theorem, invalid proof, scope mismatch, or claim-evidence defect as presentation repair.

Calibrate scores to the persisted route rather than to prose quality. Partial novelty or narrow
significance cannot receive 4/5; absent completed experiments cannot receive 4/5 empirical validation
or sufficient application evidence. A major route blocker, required-but-incomplete experiment,
compile warning, overflow, malformed citation, or missing proof forbids `accept`.

Audit Related Work as an argument, not a citation list. Confirm that every closest-work record is
compared along concrete axes such as assumptions, object, rate, tightness, generality, or computational
cost, and that the stated gap follows from verified evidence. Flag a mature-area bibliography below
20 relevant sources.

Revision is a separate pass: fix exposition and packaging directly, but route mathematical changes
back to a new governed theory run. Re-review after revision and retain an audit trail.

Before reviewing, load `paper/user_comments.json` and check that the manuscript addresses the user's
requested scope and intent in addition to venue-style findings. Do not silently reinterpret or drop a
comment. The revision response must answer every open comment and every review finding with an
explicit disposition, rationale, and hashes of any changed manuscript files. A declined request
remains open unless the user withdraws it. After revision, review only the newly compiled manuscript;
issue `accept` with no findings only when the latest evidence is clean enough to proceed to packaging.
Bind each revision response to the exact persisted finding ID and required action; do not duplicate
review findings in `user_comments.json` or wait for the researcher to choose among them. When the
review contains actionable findings, the controller must automatically open one revision cycle that
addresses all findings. Before reviewing the new compile, verify that the revision contains a separate
disposition for every previously open finding. The Paper view exposes the newly reviewed result, while
detailed review evidence remains available through the governed Issues and Evidence views.

For a clean non-submission route whose upstream novelty or significance blockers prevent submission
acceptance, use `draft_ready` when there are no actionable manuscript findings. This means the PDF is
ready to package with `ready_for_submission_check: false`; it does not waive route blockers. Never
issue `minor_revision` with an empty findings list, because that creates a no-op revision loop.

The manuscript controller permits the initial compile plus two automatic presentation-repair
rounds. When presentation findings remain after that budget, review the best preserved compile and
use `package_with_warnings`; retain every remaining nonfatal finding. This disposition produces a
non-submission-ready package with explicit warnings. It is invalid before the repair budget is
exhausted and invalid for any mathematical-correctness finding.

For every main figure, verify at rendered paper size that the claimed effect is visibly readable,
uncertainty does not swamp or clip the signal, and panel titles state their scientific content.
In one-column venue formats, reject single-panel figures that visually dominate the page without a
scientific need for full text width; request reduced-width placement, a simpler figure, or a true
spanning figure with a concrete justification.
Record unresolved blocking tradeoffs explicitly; any such tradeoff prevents publication-ready status
even if the average design score is high.
Set the proofreading checks `visual_evidence_readability` and `visual_evidence_alignment` only after
inspecting active figures and every included table at rendered manuscript size and matching their
content to the accepted evidence.
