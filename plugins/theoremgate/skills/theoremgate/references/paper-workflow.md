# Post-theory paper workflow

## Manuscript authorization boundary

Do not create manuscript prose before `manuscript_workflow.py init` succeeds. That command verifies
the completed theory bundle and deterministic paper route, then issues
`paper/manuscript_authorization.json`. Every packaged
manuscript-writing tool must verify this authorization. The authorized output root is only the exact
run's `paper/` directory; never create a substitute `papers/*.md` or standalone draft elsewhere.

The paper controller is separate from the governed theory controller. It binds its manifest to the
SHA-256 hash of the immutable theory bundle and refuses to start if its deterministic route does not
permit writing. The paper manifest stores the route so every later stage can enforce it.

For a full run, the start or resume action authorizes paper writing for any deterministic route with
`writing_allowed: true`. Do not request a separate publication-route or `write` decision, including
when the original-research acceptance goal is not yet supported. The route's claim policy and
submission-readiness status remain binding.

| Stage | Actor | Artifact | Specialist skill |
|---|---|---|---|
| `literature_audit` | `literature_auditor` | `paper/literature_audit.json` | `$literature-audit` |
| `exemplar_study` | `manuscript_architect` | `paper/writing_exemplars.json` | `$manuscript-writing` |
| `venue_selection` | `venue_formatter` | `paper/venue_selection.json` | `$venue-formatting` |
| `content_architecture` | `manuscript_architect` | `paper/content_architecture.json` | `$contribution-development`, `$manuscript-writing` |
| `empirical_validation` | `experimenter` | `paper/empirical_validation.json` | `$empirical-validation` |
| `section_writing` | `manuscript_writer` | `paper/sections/index.json` | `$manuscript-writing` |
| `compilation` | `manuscript_compiler` | `paper/compile_report.json` | `$manuscript-writing`, `$venue-formatting` |
| `independent_review` | `paper_reviewer` | `paper/review.json` | `$paper-review` |
| `revision` | `manuscript_writer` | `paper/revision.json` | `$manuscript-writing` |
| `final_package` | `paper_reviewer` | `paper/final_package.json` | `$paper-review`, `$venue-formatting` |

At venue selection, the venue-formatting agent compares the evidence-compatible packaged venues and
selects the strongest scholarly fit without a fixed ranking, numeric score, or list-order preference.
The decision is hash-bound to the candidate set and records concrete contribution, theorem/proof,
empirical, length/appendix, and rule-status factors. Every accepted-result manuscript then uses the
selected named venue's locally integrity-checked template for full-length development. An unverified or stale
venue snapshot may be used for development only and must retain `submission_ready: false`, its audit
warnings, and its verification notice. Submission-ready packages prefer a best-fit template with
verified, fresh official rules and `submission_ready: true`. Evidence reports use the neutral
`Research-Draft` template. Never ask for a venue choice. Venue selection is completed before
architecture so the actual snapshot, page limit, anonymity rules, and formatting constraints
determine the manuscript plan.

Before venue selection and architecture, study three to six verified full-text exemplars matched to the area, contribution,
and likely venue family. Record cross-paper structural principles and originality safeguards; learn
organization and exposition, never sentences or an individual author's style. The content architecture
is hash-bound to that study and records the principles it adopts.

The content architecture must use schema v3 and exactly copy the routed `manuscript_kind`, primary statement IDs, and
selected statement IDs, acknowledge the claim policy, and fix the scientific title, narrative arc, ordered
section names, dynamic titles, purposes, claim mapping, and page plan after venue selection. It must
bind `venue_selection_sha256` to the completed venue artifact. The
page plan is mandatory on the first manuscript and on every full rewrite. It allocates a target to
every section and records optional-minimum/target/maximum total pages; minimum/target/maximum main-text
pages; minimum/target appendix pages; target/maximum reference pages; the venue hard limit or null;
the exact page-limit scope; references-before-appendix placement; and the explicit Appendix heading.
Hard-limit venues target the full permitted main-text allowance. No-limit venues derive their target
from measured page profiles of three to six matched full-text exemplars. For a no-limit journal,
`minimum_total_pages` is null, the main text is at least 10 pages excluding references and appendices,
and `target_main_pages` is the larger of 10 and the largest observed exemplar main-text length. The
target guides section allocation but is not itself an underfill threshold. Compilation records and
enforces rendered main, reference, appendix, and total page counts, including the 10-page journal
main-text floor and the planned proof-appendix minimum. An accepted-result
architecture is always full length even when novelty is partial or unverified. Related Work goes
immediately after Introduction by default; any later position requires `nonstandard_placement: true`
and an explicit argumentative rationale. It is never placed according to drafting order. Every paper uses the universal
Abstract, Introduction, Related Work, and Conclusion frame. Limitations coverage is required, but
its placement is flexible: set `limitations_section` to the planned `limitations`, `conclusion`, or
`discussion` section. Preserve a separate section when required by the selected venue; otherwise
choose a concise standalone or integrated treatment. Integrated plans omit a separate limitations
section and page allocation. Existing standalone plans may omit this field. Review checks the
actual coverage and venue compliance, not just the presence of a heading. The model designs all
contribution-specific sections and titles from the accepted results; each primary statement must
appear in at least one such section. Required empirical evidence may use any clear section title and
is identified with `evidence_types: ["empirical", "visual"]`.
Core sections use their conventional scholarly headings. For the remaining hierarchy, conventional
titles such as `Main Results`, `Method`, `Analysis`, or `Experiments`; technical titles naming the
scientific object; and combined titles such as `Main Results: Anchored Clipping Bounds` are all valid.
A conventional parent section may also contain technical subsections. Choose the form that makes the
paper easiest to navigate, and reject only titles that are empty, unclear in context, rhetorical,
casual, promotional, needlessly elaborate, or inconsistent with the manuscript's terminology.
For every manuscript with accepted selected statements, architecture schema v3 must include a dedicated appendix
section with `evidence_types: ["proof"]`, `proof_mode: "appendix_full"`, and
`complete_proof: true`. It must cover every selected statement, not only the primary statement, and
carry the supporting lemmas needed by their proof dependency chains. Choose a clear proof-section
title that fits the hierarchy; `Proofs`, `Proofs of the Main Results`, and a technical or combined
variant are all valid when appropriate. Every selected result must have
a labeled formal statement in the main paper, a labeled complete proof in the appendix, and an exact
two-way entry in `proof_appendix_map`. A roadmap, sketch, restatement, omitted central step, or
equation padding is not a proof. This requirement applies to every `full_paper`.
Schema v3 also requires one `proof_detail_plan` entry per selected result: strategy, explicit
assumption uses, supporting results, at least three justified critical steps, a boundary or edge-case
check, and the exact concluding inference. The page plan reserves at least three appendix-proof pages
for one result and at least 1.5 pages per result for a multi-result package. Section validation rejects
compressed or omission-based mapped proofs, while independent review checks mathematical substance
against the governed proof closure.
It also requires one `main_text_math_plan` entry per selected result. The plan binds a main
contribution section and formal statement label to explicit setup objects, source-backed labeled key
derivations, supporting lemmas where needed, a justified proof roadmap, technical interpretation,
and the complete-proof appendix. Primary results require at least two labeled main-text derivations;
other selected results require at least one.
Every accepted-result architecture also requires a `visual_evidence_plan`. It classifies every
selected statement as empirically testable or not empirically testable, forbids deferred coverage,
and assigns all testable claims to a main empirical/visual section and scientific question. It does
not prescribe a table or table schema. If testable claims exist, empirical validation
must finish as completed, contradictory, or honestly blocked. Completed or contradictory programs
require publication-ready main figures collectively covering every declared testable claim. A table
is never a substitute for missing evidence. Tables are optional and paper-dependent: include one
only when it communicates substantive content more clearly than prose, equations, or figures, and
design it around the paper rather than a fixed schema. Render and inspect every included table at
publication size; revise it, split it, convert it to prose, or remove it when it is not
publication-ready.

If no statement was accepted, write an `evidence_report` using architecture schema v3. It
must include a dedicated appendix evidence section with `evidence_types: ["audit"]`,
`complete_evidence: true`, and the persisted source artifacts. Explain the attempted proof, the exact
audited blocker, and the supported next research step. Do not create a theorem environment or fake proof.
The neutral report has no minimum total, main-text, or appendix page count. Choose evidence-based
targets and never pad the report to resemble a full paper.

The current manuscript may state as established only the accepted results named in
`paper_route.selected_statement_ids`. A coherent paper may combine a positive theorem with its
supporting lemmas, lower bounds, counterexamples, boundary cases, or negative results. Other valid
accepted results remain in the theory bundle with `paper_placement: separate_paper` or `deferred`;
they are not discarded. Entries in `retained_nonfinal_statements` may appear only with their true
status, such as a conjecture, open problem, repair direction, or limitation. Entries in
`excluded_statements` are mathematically invalid or fatally refuted and must not be presented as
results.
The empirical stage may record `not_required` only when the route does not require experiments. It
first compares candidate experiments and selects those with the strongest claim relevance,
falsification value, reviewer value, feasibility, and non-redundancy. Experiment types are flexible;
the controller validates the claim-evidence chain rather than imposing a universal checklist.
A contradictory experiment remains visible and must be addressed in review. Compilation may complete
without a PDF when LaTeX is unavailable, but the report must record that warning.
When the route requires experiments, `planned` does not complete the gate: selected experiments must
be executed, evaluated, and persisted before section writing. Never add a “validation plan” section
merely to satisfy an empirical architecture field.

The empirical artifact has `status`, `reason`, `strategy`, `experiments`, `coverage_tags`, and
`limitations`. Its strategy records candidates, decisions, reviewer risks, and coverage of every
accepted claim. Every selected experiment records a theory prediction, design, falsification
criteria, uncertainty, raw-result path and hash, verdict, limitations, and allowed claim. See
`empirical-evidence.md`.

```json
{
  "coverage_tags": ["scaling", "strong_baseline"]
}
```

The independent review records `recommendation`, structured findings, `summary`, `confidence`,
`route_consistent`, `application_evidence_sufficient`, and 1–5 scores for `technical_quality`,
`clarity`, `novelty`, `significance`, `empirical_validation`, and `reproducibility`. Each finding has
`id`, `severity`, `criterion`, `description`, and `required_action`.
It also assesses every section on clarity, narrative function, evidence alignment, and scholarly
exposition, and records proofreading checks for references, citations, LaTeX artifacts, figures,
layout, title rendering, visual-evidence readability, and visual-evidence alignment. Acceptance
requires every section to pass at 4/5 or better.
Scores must remain consistent with upstream evidence: partial novelty, narrow significance, absent
experiments, major route blockers, or compile warnings preclude a clean accept and cap the
corresponding criterion scores.

Recoverable manuscript presentation findings do not terminate the paper workflow. The controller
archives the compile and automatically returns to section writing for at most two repair rounds
after the initial compile. Review-originated presentation findings consume the same two-round
budget. After exhaustion, restore the lowest-penalty archived PDF and review it with
`package_with_warnings`; the final package must enumerate every remaining finding and set
`ready_for_submission_check: false`. Mathematical-correctness and unsupported-claim findings never
enter this presentation-repair path.

Minimum JSON fields are enforced by `scripts/manuscript_workflow.py`. Section files and `paper.tex`
must exist before their indexes can be completed. The final package records the exact theory-bundle
hash, included files, remaining warnings, and whether it is ready for a final submission check.
Evidence reports can never set that submission flag to true.
Candidate packages marked submission-ready also require an accept/minor-revision review, route
consistency, no unresolved major/fatal review finding, and completed required experiments.
Clean non-submission packages use the `draft_ready` recommendation and proceed directly to
`final_package` with `ready_for_submission_check: false`, even when upstream novelty or significance
blockers remain. Those blockers constrain submission framing; they must not force empty revision
cycles. The web interface preserves completed-cycle history when a paper stage is reopened.
An exhausted presentation-repair package instead uses `package_with_warnings`, preserves every
remaining review finding in `final_package.remaining_warnings`, and remains explicitly not ready for
a submission check.

For post-package revisions, use `revision_router.py plan` and `start`. A prose-only revision resumes
at `section_writing`; an experiment rerun resumes at `empirical_validation`; and any request that
changes citations, bibliography, closest-work evidence, or Related Work coverage uses
`revise_literature` and resumes at `literature_audit`. The controller archives the routed stage and
every downstream paper artifact. Never emulate this transition by editing `paper_run.json` or by
overwriting a completed upstream artifact from the ordinary `revision` stage.
A free-form custom researcher paper request is classified automatically and recorded once as a typed
user comment. Persisted reviewer findings are not copied into that registry or presented as a user
choice. When review produces actionable findings, continue automatically through one combined
revision cycle, preserve a separate response for each finding ID, and invalidate from the earliest
stage required by any finding before rebuilding the downstream paper once. The web interface Paper view
must not present an intermediate pre-revision PDF as the current manuscript.
A request for a new manuscript or renewed paper/venue selection uses `rewrite_manuscript`, resumes
at `venue_selection`, and must rewrite every section rather than reuse the old section hashes.
