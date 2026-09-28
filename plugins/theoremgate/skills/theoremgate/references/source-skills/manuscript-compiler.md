---
name: manuscript-compiler
description: "Top-level contract for compiling the governed state into a publishable paper. Loaded first; every section skill inherits these global rules."
version: 1.0
used_by: manuscript_compiler
---

# Manuscript Compiler — Global Rules

These rules apply to every section. Load a section-specific reference when one fits; for a
model-designed contribution section, use the closest applicable reference and obey these globally.

## Write like a normal paper — NEVER use internal system vocabulary
The reader is a reviewer, not a TheoremAudit operator. The paper must read like an ordinary
theoretical ML paper. NEVER let internal machinery leak into the text.

Banned vocabulary (and how to handle it instead):
- "proof obligation", "PO-1"/"PO-N" → describe the mathematical claim itself, by name
- "governed record", "governance", "arbiter", "survive governance", "committed" (as a
  status) → just state the result, or omit
- "repair", "repair requested", "repair roadmap", "workflow annotations", "removing
  internal annotations" → say "open problem", "remains to be shown", or omit
- "non-defensively", "conjectural program", "governed form", "new_form"/"new_status" →
  plain mathematical English
- "safe" / "unsafe" (these are internal tool-check terms) → NEVER use them to qualify a
  mathematical object. "safe restricted-head regime" is not a definition. A regime/condition
  named in a hypothesis MUST be defined precisely (an explicit inequality on the eigenvalues
  / split index), or it is not a valid assumption. If the proof only names an undefined
  "regime", that is a gap, not a hypothesis — do not present it as a rigorous condition.
- section titles must be clear, scholarly, and consistent with the paper. Conventional headings,
  technical headings, and combined forms are all valid; never expose internal workflow labels or use
  rhetorical questions, casual slogans, promotional wording, or needlessly elaborate titles

If you catch yourself writing any internal term, rewrite the sentence in plain mathematics.

## Dynamic Section Titles

Internal section types are optional routing labels, not a required section taxonomy or final titles.

The compiler may receive labels such as `setting`, `main_results`, `empirical`, or `discussion`.
These labels only select nearby writing guidance. The model may design a different section name and
structure when that better expresses the accepted contribution.

Before writing each section, choose the title that makes its function and content easiest to
understand in the complete manuscript. Three forms are available without a fixed preference:

- conventional, such as `Main Results`, `Method`, `Analysis`, or `Experiments`;
- technical, such as `A Finite-Sample Excess-Risk Identity` or `Anchored Clipping Bounds`;
- combined, such as `Main Results: Anchored Clipping and Private Estimation` or
  `Experiments: Dimension and Tail-Index Scaling`.

Use a conventional parent section with technical subsections when that hierarchy is clearer than a
long parent title. Use a technical or combined parent title when it improves navigation without
becoming cumbersome. Base the choice on the paper's terminology, argument, section hierarchy,
matched exemplars, venue conventions, and neighboring headings. Do not force every title to be
generic, and do not force every title to sound distinctive. Reject only titles that are empty,
unclear in context, rhetorical, casual, promotional, needlessly elaborate, or inconsistent with the
scientific content.

Never expose skill names, tool names, agent names, or pipeline labels as section titles.

## Universal and contribution-specific sections

Every manuscript includes Abstract, Introduction, Related Work, and Conclusion. Cover material
limitations either in a separate section or briefly in the conclusion or discussion, as recorded
by `limitations_section` in the content architecture. Keep a standalone Limitations section when
the selected venue requires it; otherwise choose the clearest, least repetitive placement. State
specific mathematical or empirical boundaries without blanket self-criticism or softened disclosure
of material weaknesses. An unresolved proof defect must be repaired or the claim withheld, not
reclassified as a limitation of an accepted result. Beyond
that universal frame, choose sections from the scientific argument rather than a venue template.
Every primary accepted result must appear in at least one contribution-specific section, but that
section need not be called Setting, Main Results, Method, Proofs, or Experiments.

## State results assertively — NO hedging language for your own contributions
A committed result is a theorem/proposition. State it as one. NEVER weaken your own
contributions with wish/roadmap language. BANNED in the statement or framing of any result:
- "one would like…", "we would like to…", "the natural goal is…", "it is plausible that…",
  "conjecturally…", "we hope to…", "ideally…", "it would be desirable…"
Use assertive mathematical verbs instead: "We prove", "We establish", "We show",
"We construct". A proposition is stated flatly, not aspirationally.
This applies EVEN to negative/separation papers: a proved impossibility or separation is a
firm result — "We prove no coarse spectral summary determines the peak", NOT "one would
like to show that…". Hedging your own theorem is fatal at a theory venue.

## Formal academic register
Write in the register of a published theory paper, not a blog post or internal note.
- Do NOT call results "messages", "stories", "points", or "takeaways". Use "contributions",
  "results", "propositions", "our main result". (e.g. NOT "the two main mathematical
  messages of the paper" → "Our two main results are…" / "This paper makes two
  contributions:")
- Do NOT write weak fragment openings like "The closest prior work is X." Situate prior work
  in a full sentence with a citation: "Most closely related is the covariance-sensitive
  benign-overfitting analysis of \cite{...}, which establishes …; we differ in that …".
- Avoid conversational hedges ("basically", "essentially", "the point is", "we feel").
- Prefer precise, declarative sentences. State what is proved and under which hypotheses.

## Reader-facing prose, not an audit report

Translate evidence constraints into scientific scope; never narrate the manuscript-development or
publication-review process.

- Do not use the deictic word "here." Name the theorem, distribution, event, estimator, assumption,
  section, or inference explicitly.
- Do not write "the next step," "verify the closest work," "run baseline experiments," or
  "evidential rather than cosmetic." State a precise open mathematical problem, empirical question,
  or consequence of the established result.
- Do not write "this paper does not claim" or "we do not claim." State the contribution positively
  and delimit it through exact hypotheses and conclusions. For example, replace "we do not claim
  conditional coverage" with "the guarantee concerns marginal coverage under a fixed target law."
- Do not expose novelty-audit verdicts through sentences such as "novelty remains incomplete" or
  "originality is unverified." Express verified comparisons in Related Work and avoid priority
  language that the evidence does not support.
- Do not mention submission framing, readiness, routing, reviewer gates, missing verification tasks,
  or other publication-process status in the paper.
- A limitation must identify a mathematical or empirical boundary: a required independence
  condition, an unmodeled regime, a missing operational quantity, or an unresolved rate. It must not
  report that the paper lacks evidence, novelty, or permission to make a claim.

Conclusions end with a precise implication, technical question, or research direction stated in the
language of the problem. Limitations describe the domain of validity and the obstacles to extending
it. Neither section may read like instructions to the authors.

## Write like an experienced researcher (voice — applies to EVERY section)
Write as a senior author who has published in this area for years — confident, economical,
and specific. Concretely:
- **Keep editorial guidance out of the manuscript.** Use these references to make writing decisions,
  then compose original paper-specific prose from definitions, results, citations, and evidence.
  Never copy or lightly paraphrase instructional wording.
- **Present notation for fast reading.** Introduce a small number of symbols in the prose where they
  first appear. Use a compact reference table only when it measurably improves navigation through
  dense or recurring notation; avoid repeating definitions already clear from the text.
- **No templated section/paragraph openings.** Never begin with "The most closely related
  work is…", "There are several lines of work…", "In this section we…", "It is well known
  that…". Open with a substantive claim and let the citations serve it.
- **Never write an annotated bibliography** ("[A] did X. [B] did Y."). Make a point per
  paragraph and cite works as evidence for it; compare works to each other.
- **Vary sentence structure and length.** Uniform, formulaic sentences read like a template.
- **Motivate before formalizing.** One or two sentences of "why this matters / why it is hard"
  before a definition or theorem, the way strong papers do.
- **Commit to claims.** State results and positions flatly; do not hedge your own work.

## Only committed content is a result
Only statements the Arbiter committed appear as results. Non-committed statements are not
theorems: route them to Discussion/Limitations or omit — never dress them up.
Genuine conjectures live ONLY in a clearly-labeled "Conjectures / Future work" part of the
Discussion — NEVER interleaved into Main Results as if they were results.

## Honesty without exposing the machine
Be honest about scope and limitations, but express them as a normal paper would ("under the
stated assumptions", "we do not address the fully adaptive setting") — not by narrating the
internal process that produced them.
Deferring to future work is acceptable ONLY for a genuinely peripheral extension. A paper's
CENTRAL result must be fully stated and proved — never write that the main theorem, its
proof, or its key construction is "left to future work" / "beyond the scope of this
manuscript" / "structural rather than theorem-driven". If the central result cannot be
proved, it is not a result: it belongs in Discussion as a labeled conjecture, and the paper
is framed around what WAS proved (or around the barriers, for a negative-result paper).

## Paper-dependent visual evidence

Follow the architecture's `visual_evidence_plan`. When the empirical program is completed or
contradictory, include the emitted snippets for publication-ready main figures in the assigned
empirical section and ensure that the included figures collectively cover every declared testable
claim. When no accepted claim is empirically testable or the selected experiment is honestly
blocked, do not force a visual. Tables are optional and paper-dependent. Include one only when rows
and columns communicate substantive theoretical or empirical information more clearly than prose,
equations, or figures. Choose its structure from the paper's scientific needs and venue conventions
rather than a fixed schema. Every included table must be publication-ready and legible at final
manuscript size; otherwise revise it, split it, convert it to prose, or remove it. Inspect every
included figure and table at final size.

## Full proof or evidence appendix for every paper

Every paper with accepted selected statements includes a dedicated appendix containing the complete proof
of every selected accepted statement, not only the headline theorem. Carry into that appendix every
supporting lemma needed by the governed proof dependency chain. State each selected result formally
in the main paper with a unique label, give its appendix proof a unique label, and cross-reference
the two in both directions. The content architecture records these bindings in
`proof_appendix_map`. Main-text intuition and proof roadmaps remain useful, but they never replace
the appendix derivation. Do not inflate the appendix with repeated formulas or irrelevant algebra;
completeness means every logical step and binding assumption is present.
Follow `main_text_math_plan` in the body: each selected result needs its planned formal statement,
setup objects, source-backed labeled derivations, supporting results where required, justified proof
roadmap, technical interpretation, and exact appendix link. The primary result has at least two key
displayed derivations in its assigned contribution section. This is mathematical exposition, not an
equation-count target; every display must advance the argument.
Follow the claim-level `proof_detail_plan`: expose the strategy, assumption uses, supporting lemmas,
at least three justified critical steps, constant and event bookkeeping, relevant boundary cases,
and the exact final inference. Do not use “standard,” “routine,” or “details omitted” to bridge a
substantive step.

Write to the component page contract selected before architecture. For hard-limit venues, fill the
main text to within one page of the full applicable allowance. For no-limit venues, use the largest
main-text page count among the inspected matched exemplars as the target. After compilation, inspect
the reported rendered main, reference, appendix, and total page counts; revise substance whenever a
component is outside its range.
Treat every page target as an editorial diagnostic, never as permission to pad. If a manuscript or
section is already scientifically complete, do not lengthen it through repeated motivation,
restated contributions, redundant scope paragraphs, filler transitions, boilerplate roadmaps,
duplicated equations, or paraphrases of established material. When a genuine enforced minimum is
unmet, add only missing scientific substance or report the remaining constraint; repetition is not a
valid repair.
The controller archives an imperfect compile and automatically returns to section writing for at
most two presentation-repair rounds. Expand or rebalance substantive mathematics, exposition,
figures, citations, or LaTeX layout according to the recorded finding. After the second repair
round, preserve and review the best archived PDF even if a nonfatal presentation warning remains.
Do not apply this bounded packaging path to unsupported claims or mathematical-correctness defects.
Let References follow the Conclusion on the current page unless the staged venue metadata explicitly
sets `references_start_new_page: true`. During rendered review, inspect the final main-text page for
an avoidable short spill or unexplained blank area. Repair such imbalance through natural pagination
and scholarly editing; never use font shrinking, negative vertical space, or deletion of substantive
content merely to fit a page.

If the route contains no accepted statement, replace the proof appendix with a complete evidence
appendix. Trace the attempted claims to their proof drafts and audit findings, explain why no theorem
is established, and state only supported limitations or future directions. Never manufacture a proof
to satisfy the document-completion requirement.

## Section skills
Load the matching section skill before writing each section (abstract, introduction,
setting, related-work, main-results, empirical, discussion, conclusion, proof-appendix).
Each adds specifics on top of these global rules.
