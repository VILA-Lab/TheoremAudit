---

name: main-results
description: "Write the main results section of a theoretical ML paper. States committed theorem/proposition-level results formally, includes body proof ideas, sketches, or roadmaps, and avoids promoting assumptions, conjectures, or unresolved claims to results. Detailed proofs are placed in the appendix by default, with a carve-out for genuinely short central proofs."
version: 1.8
used_by: manuscript_compiler
----------------------------

# Main Results Writing Skill

## Purpose

Present the paper's mathematical contributions precisely, confidently, and faithfully. Every formal statement in this section must correspond to a committed result in `theorem_state`.

This section should read like the main-results section of a theoretical ML paper: formal statements, clear assumptions, proof intuition, and interpretation. It should not read like an internal proof audit, theorem-state dump, or list of proof obligations.

Detailed proofs belong in the appendix, but the main text must contain enough mathematics for the
reader to reconstruct the core mechanism behind each result. Follow the claim's
`main_text_math_plan`: define its setup objects, typeset the planned labeled derivations, state any
planned supporting lemma, give the justified proof roadmap, interpret the result technically, and
link to the complete appendix proof. A complete proof may also appear in the main body when it is
short, self-contained, central, and improves readability; the appendix still provides the complete
review copy required by the manuscript contract.

## Pre-writing check

Before writing, silently identify:

* which statements are genuine result contributions;
* which entries are assumptions, definitions, estimator conventions, notation, or scope restrictions and therefore belong in the Setting section;
* which results are committed and eligible for the Main Results section;
* each result's `paper_label`, public label, statement form, and proof source;
* whether any result was weakened before commitment;
* whether a proof draft or proof sketch exists for each committed result;
* which result is the primary/central contribution, and which are secondary, such as supporting lemmas, corollaries, or auxiliary propositions;
* whether the primary result should use short-proof mode or proof-roadmap mode;
* logical dependencies among results, so they can be ordered correctly.

Use this check silently. Do not expose it in the manuscript.

## Result inclusion gate

Include a statement in the Main Results section only if all of the following hold:

1. It is a genuine mathematical contribution, such as a theorem, proposition, lemma, corollary, construction, bound, impossibility result, example, or reduction.
2. It is committed in `theorem_state` through either a committed decision or a committed statement.
3. Its status is compatible with inclusion, such as `theorem_ready` or `proposition_ready`, or it has a valid `paper_label` indicating a committed result.
4. It is not merely an assumption, definition, estimator convention, notation choice, regularity condition, or scope restriction.

Do not promote assumptions, definitions, estimator conventions, or scope restrictions to main results unless `theorem_state` explicitly marks them as result contributions.

Always exclude from Main Results:

* `repair_requested` items;
* `blocked` statements;
* `conjecture_only` statements;
* aspirational claims;
* planned results;
* statements without committed mathematical content.

Blocked or conjecture-only statements may be routed to the Discussion as open problems or future directions if they are scientifically meaningful, but they do not belong in Main Results.

## Environment selection

The LaTeX environment depends on `paper_label` from decisions. `paper_label` is authoritative when present.

| `paper_label`   | LaTeX environment             |
| --------------- | ----------------------------- |
| `"theorem"`     | `\begin{theorem}`             |
| `"proposition"` | `\begin{proposition}`         |
| `"lemma"`       | `\begin{lemma}`               |
| `"corollary"`   | `\begin{corollary}`           |
| `"result"`      | `\begin{theorem}[Result]`     |
| `""` or missing | fall back to committed status |

If `paper_label` is empty or missing, fall back to committed status:

* `theorem_ready` → `\begin{theorem}`
* `proposition_ready` → `\begin{proposition}`
* `conjecture_only` → do not include in Main Results
* `repair_requested` → do not include in Main Results
* `blocked` → do not include in Main Results

Never choose a stronger environment than the committed label supports. Do not upgrade a proposition to a theorem, or a lemma to a theorem, unless `paper_label` explicitly says so.

Use the nouns “theorem,” “proposition,” “lemma,” or “corollary” only when the formal environment requires them or when they aid clarity.

## Preamble requirement

The venue template or preamble skill must declare every theorem-like environment used here, including `theorem`, `lemma`, `proposition`, `corollary`, `conjecture`, and `remark` if they appear.

`amsthm` provides theorem machinery, but it does not automatically define manuscript-specific environments. Missing environment declarations will cause LaTeX compilation errors.

## Controlling statement

For each included result, choose the controlling mathematical content in this order:

1. `new_form`, if non-empty;
2. `governed_form`, if non-empty;
3. `form`, if non-empty.

Use the first non-empty field as the authoritative version of the result. If the selected field is rough prose rather than valid LaTeX, rewrite it into a precise formal statement while preserving the exact claim strength, assumptions, and scope.

Do not introduce new assumptions, rates, constants, asymptotic regimes, estimators, datasets, or conclusions that are not present in the controlling statement or its supporting context.

## Structure for each result

For each included result, write:

1. **Informal intuition paragraph**
   Explain the role of the result and why it matters. Keep this short and mathematical.

2. **Formal statement**
   State the result in the environment dictated by `paper_label`. Include the assumptions needed for the statement, preferably by referencing the Setting section if the assumptions are already defined.

3. **Key derivations and proof roadmap in the main body**
   Every result receives its labeled derivations and justified roadmap from
   `main_text_math_plan`; a prose-only sketch is insufficient.

   The **primary result** should receive the most detailed explanation. If its proof is short, self-contained, central to the paper's technical contribution, and improves readability, include the full proof in the main body. Otherwise, include a substantive proof roadmap and place the full proof in the appendix.

   A substantive proof roadmap states the core technical idea, the main decomposition or
   construction, the source-backed key inequalities, the main obstacle, and why the ingredients
   imply the result. The primary result includes at least two labeled displayed derivations;
   secondary selected results include at least one.

   **Secondary results** receive shorter sketches in the main body. Their full proofs should be placed in the appendix by default, even when they are short, unless the venue or template explicitly requests more proofs in the body.

   Detailed proofs belong in the appendix unless they are short, central, and improve readability in the main body.

4. **Interpretation paragraph**
   Explain what question the result answers, why it is nontrivial, what controls the phenomenon,
   whether the statement is tight, how it differs from the closest verified result, which assumption
   is most restrictive, and what consequence follows. Omit an item only when it genuinely does not
   apply; do not replace interpretation with a restatement of the theorem.

Do not place all proof intuition in the appendix. A theory paper whose main body contains formal statements but no explanation of the core argument reads as incomplete, even when detailed proofs are deferred.

## Proof placement policy

Detailed proofs belong in the appendix by default.

For the primary result, choose one of two modes:

1. **Short-proof mode**
   Use only when the proof is genuinely short, self-contained, central to the paper's technical idea, and clearer in the main body than in the appendix. In this mode, the main body may include a complete `\begin{proof}`.

2. **Proof-roadmap mode**
   Use when the proof is long, technical, routine, or requires substantial auxiliary machinery. In this mode, the main body must include a substantive proof roadmap, and the full proof is deferred to the appendix.

Secondary results receive proof sketches in the main body and full proofs in the appendix by default.

Do not choose short-proof mode merely because a proof can be compressed. If compression would hide important technical steps, use proof-roadmap mode.

## Ordering multiple results

Order results by logical dependency and narrative importance:

1. central result, if it does not require later statements;
2. prerequisites needed for the central result;
3. supporting propositions or lemmas;
4. corollaries and consequences;
5. examples or constructions.

If one result is used to prove another, state the prerequisite first unless doing so would seriously harm readability. In that case, explain the dependency clearly.

## Proof rules

Use the actual proof material available from the proof draft, proof blueprint, or `read_proof(po_id)` output.

* Do not invent proof steps, equations, inequalities, constants, or lemmas.
* Reproduce real mathematical ingredients from the proof source when available.
* If equations are available, include the key equation or inequality driving the argument.
* If only a high-level proof sketch is available, write only a high-level proof sketch.
* When a result's full proof is deferred to the appendix, the main-body sketch must still convey the actual argument: the technique, key step, and reason the conclusion follows.
* Do not write a placeholder sketch and rely on the appendix to carry all the mathematical content.
* If no proof material is available for a committed result, do not fabricate a proof. Flag this outside the manuscript-generation path rather than pretending the result is proved.
* End proof sketches with a pointer to the full proof only if the appendix proof actually exists.

Proof sketches should usually be 2–4 sentences. The primary result may receive a longer proof roadmap if needed for clarity.

Proof sketches and roadmaps should mention:

* the main technique or decomposition;
* the key mathematical obstacle, if recorded;
* the main reason the conclusion follows;
* the appendix pointer, if applicable.

Do not describe unresolved proof gaps as if they were proof techniques.

## Appendix proof placement

Detailed proofs should be placed in the appendix by default.

* Main Results contains formal statements and proof ideas, sketches, or roadmaps.
* Appendix contains full technical proofs.
* The main text may include a central equation, decomposition, or inequality when it is essential to understanding the proof mechanism.
* The main text should not duplicate the full appendix proof unless short-proof mode is explicitly chosen for the primary result.
* Do not point to an appendix proof unless that proof exists and has a valid label.

## Weakened statements

If the controlling statement comes from `new_form`, treat that weakened form as authoritative.

Add a short reader-facing remark only when the weakening affects interpretation. The remark should describe the mathematical scope of the final statement, not the internal revision process.

Prefer:

```latex
\begin{remark}
The statement is formulated at the expectation level; extending the argument to high-probability control would require a sharper concentration estimate in this regime.
\end{remark}
```

Avoid:

```latex
\begin{remark}
The Arbiter weakened this result because the previous proof obligation failed.
\end{remark}
```

Do not expose internal repair, governance, or proof-obligation language.

## Claim-strength calibration

Every statement in this section is a committed result, so the language should be assertive. Still, calibrate strength to `paper_label`.

* `paper_label="theorem"` → strong verbs are permitted: “we prove,” “we establish,” “we show.”
* `paper_label="proposition"` → measured but assertive verbs: “we show,” “we establish under the stated assumptions,” “we give a construction showing.”
* `paper_label="lemma"` → supporting language: “the following lemma controls...,” “we first show...”
* `paper_label="corollary"` → consequence language: “as a consequence,” “this yields...”

Avoid aspirational language:

* “one would like”
* “the natural goal is”
* “conjecturally”
* “it is plausible that”
* “we expect”
* “we hope to show”

If a statement can only be written aspirationally, it is not a committed result and does not belong in Main Results.

## Labels and references

Use the public labels assigned by the main-results or manuscript compiler. Do not expose internal IDs such as proof-obligation IDs, decision IDs, or gap IDs.

When referencing a formal result, use the environment type and label consistently:

* `Theorem~\ref{...}`
* `Proposition~\ref{...}`
* `Lemma~\ref{...}`
* `Corollary~\ref{...}`

Do not invent labels. Do not use internal IDs as labels.

## What to draw from inputs

* `theorem_state.decisions` for committed status and `paper_label`
* `theorem_state.statements` for formal statement content
* the controlling statement selected from `new_form`, `governed_form`, or `form`
* proof drafts, proof blueprints, or `read_proof(po_id)` output for proof sketches and proof roadmaps
* self-critique only to identify real technical scope boundaries, not to expose proof-audit language
* Setting section assumptions and definitions, so they can be referenced rather than restated
* appendix proof metadata, if available, so proof sketches can point to existing detailed proofs

## What NOT to do

* Do not present assumptions, definitions, notation, estimator conventions, or scope restrictions as main results.
* Do not present `repair_requested` obligations as results.
* Do not present blocked or conjecture-only statements as results.
* Do not include aspirational or conjectural claims in this section.
* Do not use hedging language that makes committed results sound unproved.
* Do not strengthen a statement beyond what `paper_label` and the controlling form support.
* Do not invent proof details or mathematical claims.
* Do not hide that a statement was weakened when the weakening affects interpretation.
* Do not expose internal IDs, governance labels, proof-obligation names, or repair-process language.
* Do not omit body-level proof intuition for the main result.
* Do not give a secondary result a full body proof merely because it happens to be short; sketch it in the body and place the full proof in the appendix by default.
* Do not write a thin placeholder sketch for a result whose full proof is deferred to the appendix.
