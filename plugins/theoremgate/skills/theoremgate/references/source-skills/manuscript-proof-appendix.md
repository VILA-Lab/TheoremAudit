---
name: proof-appendix
description: "Write the proof appendix for a theoretical ML paper. Includes full sanitized proofs for committed results whose detailed proofs are not already complete in the main body. Coordinates with main-results short-proof/proof-roadmap mode, strips internal IDs, preserves mathematical content, and avoids presenting unresolved proof gaps as complete proofs."
version: 1.2
used_by: manuscript_compiler
----

# Proof Appendix Writing Skill

## Purpose

Provide the detailed technical proofs supporting the paper's committed formal results.

The proof appendix should read like a normal mathematical appendix: precise, complete, and self-contained enough for reviewers to verify the main claims. It should not read like an internal proof audit, a proof-obligation log, or a transcript of the proof-generation process.

Only include proofs for results that appear in the paper. Do not include proofs for abandoned claims, blocked statements, conjectures, repair-requested obligations that were not committed, or internal proof attempts that do not support a public result.

## Pre-writing check

Before writing the appendix, silently identify:

* which formal results appear in the Main Results section;
* each result's public label, such as `Theorem~\ref{...}` or `Proposition~\ref{...}`;
* whether each result used short-proof mode, proof-roadmap mode, or sketch-only mode in the Main Results section;
* which proof obligations or proof drafts support each public result;
* whether the proof source is complete, partial, weakened, or explicitly dependent on an assumption stated in the paper;
* whether any proof material is already fully included in the main body;
* the logical dependency order among proof obligations, lemmas, and results;
* any internal IDs that must be stripped before writing.

Use this check silently. Do not expose it in the manuscript.

## Coordinating with main-body proofs

Before including a proof in the appendix, inspect the corresponding main-text statement,
derivations, and roadmap so notation and labels remain consistent.

* Include a complete appendix proof for every selected result even when a concise complete proof also
  appears in the main body; the appendix version is the self-contained review copy and may share
  equations by exact cross-reference instead of repeating paragraphs verbatim.
* If the main-body proof explicitly develops a technical lemma, calculation, auxiliary claim, or
  algebraic step, integrate it by reference while preserving a logically complete appendix proof.
* If the main body contains only a proof sketch, proof idea, or proof roadmap, include the full sanitized proof in the appendix.
* If it is unclear whether the main-body text is a complete proof or only a sketch, treat it as a sketch and include the appendix proof, but avoid repeating paragraphs verbatim.
* Do not present the appendix proof as an alternative proof unless it genuinely uses a different argument.

The default pattern is:

* Main Results: formal statement + proof idea/sketch/roadmap.
* Appendix: full technical proof.

Short-proof mode does not remove the appendix requirement; it changes how much can be shared through
cross-references while retaining a complete appendix verification path.

## Which proofs to include

Include a proof only if it supports a formal result that appears in the paper.

Include:

* proofs of committed theorem-ready or proposition-ready results that appear in Main Results;
* proofs of lemmas, corollaries, or auxiliary results that appear in the paper;
* deferred technical lemmas or calculations explicitly referenced by a main-body proof or proof sketch;
* proof details for weakened committed statements, using the weakened form as authoritative.

Exclude:

* proofs for blocked statements;
* proofs for conjecture-only statements;
* proofs for repair-requested statements that were not committed;
* proofs for abandoned proof routes;
* proofs for assumptions, definitions, notation, estimator conventions, or scope restrictions;
* internal proof attempts that do not support a public result.

A proof obligation should appear in the appendix only through the public result it supports. Do not organize the appendix around internal proof-obligation IDs.

## Inclusion gate

For each candidate proof, include it only if all of the following hold:

1. The target statement appears in the manuscript as a formal result or deferred auxiliary claim.
2. The target statement is committed, not blocked, conjecture-only, or unresolved.
3. The proof source contains enough mathematical content to support a real proof.
4. The appendix version supplies a complete verification path without unnecessary prose duplication.
5. The proof can be sanitized into reader-facing mathematical prose without exposing internal IDs or audit language.

If these conditions fail, do not fabricate a proof. Flag the issue outside the manuscript-generation path.

## Ordering proofs

Order proofs by logical dependency, not by internal ID or generation order.

Use this default ordering:

1. preliminary technical lemmas needed by later proofs;
2. proof of the main theorem or central proposition;
3. proofs of supporting propositions;
4. proofs of corollaries;
5. deferred calculations, auxiliary bounds, or examples.

If the paper's narrative is clearer with the main result first, you may state the main proof first and defer supporting lemmas within it, but dependencies must be clearly referenced.

Do not order proofs by proof-obligation names such as `PO-3`, `PO-4`, or decision IDs.

## Proof format

Each appendix proof should have a public heading tied to the manuscript label.

Use forms such as:

```latex
\subsection{Proof of Theorem~\ref{thm:main}}
```

or:

```latex
\paragraph{Proof of Proposition~\ref{prop:construction}.}
```

Then write a standard mathematical proof:

```latex
\begin{proof}
...
\end{proof}
```

Use the same public theorem/proposition/lemma/corollary labels as the Main Results section.

Do not use internal IDs in headings, labels, proof text, or comments.

## Required level of detail

For each selected result, follow its architecture `proof_detail_plan` and make every logical bridge
reviewable. A detailed proof contains:

1. a short strategy paragraph identifying the main decomposition or reduction;
2. the assumptions used at the exact steps where they enter;
3. all auxiliary definitions and lemmas needed by the dependency chain;
4. at least three explicit critical steps, each with the inequality, identity, coupling,
   concentration argument, or reduction that justifies it;
5. constant, event, conditioning, and quantifier bookkeeping;
6. boundary, endpoint, degenerate, and measurability checks relevant to the statement; and
7. a final inference that matches the public theorem statement exactly.

Do not replace a derivation by “standard,” “routine,” “straightforward,” “details omitted,” or
“left to the reader.” A citation may justify a named external theorem, but the appendix must state
that theorem's applicable conditions and verify them locally. Simple algebra may be compressed only
after writing the identity from which it follows. The goal is not length by repetition: every
paragraph or display must discharge a dependency, justify a transition, or check scope.

## Sanitization rules

Sanitize proof drafts into polished mathematical prose while preserving the proof's mathematical content.

Allowed edits:

* remove internal IDs, audit labels, proof-obligation names, and debugging comments;
* improve grammar, notation consistency, and mathematical flow;
* replace internal references with public theorem, lemma, equation, or appendix labels;
* compress repeated explanation when it does not change the argument;
* rewrite rough prose into standard mathematical proof style;
* align notation with the Setting and Main Results sections.

Not allowed:

* inventing missing proof steps;
* adding new lemmas, assumptions, rates, constants, or inequalities not supported by the proof source;
* silently strengthening a claim;
* turning an unresolved proof gap into a completed proof;
* deleting a caveat that materially affects the proof's validity;
* changing the target statement beyond the controlling committed form.

Sanitization is a mathematical editing step, not a new proof-generation step.

## Present only the final construction — never the derivation process

The proof source (blueprint, draft, self-critique) often records the trial-and-error path
that produced a construction: a first attempt that failed, a retreat to a restricted form, a
corrected variant. NONE of that process may appear in the appendix. Reproduce ONLY the clean,
final, working construction, as if it were the first and only thing written.

Forbidden in the appendix (these expose the generation process, not mathematics):

* "first attempt", "second attempt", "this does not work", "this fails", "does not flip",
  "we therefore retreat", "corrected variant";
* "minimal viable form" and any other internal retreat vocabulary — the restricted statement
  is simply THE statement you prove; do not label it as a retreat or a fallback;
* any narration of what was tried before the version you present.

If an earlier attempt failed and you present a restricted construction, state that restricted
construction directly and prove it. The reader must see a finished proof, not a lab notebook.

## Handling proof gaps and caveats

Do not present unresolved gaps as complete proofs.

If the proof source contains a recorded gap, self-critique, or caveat, handle it according to its status:

* If the result was weakened and the weakened form has a valid proof, prove the weakened form.
* If the gap is resolved by an assumption stated in the paper, make that assumption explicit in the proof.
* If the gap is a minor omitted calculation and the proof source contains enough information to complete it, include the calculation.
* If the gap is material and unresolved, do not write a complete proof. Flag the issue outside the manuscript-generation path.
* If a limitation must be mentioned to interpret the result, state it in reader-facing mathematical language, not as an internal failure.

Use remarks sparingly. A proof appendix should not become a limitations section.

Prefer:

```latex
\begin{remark}
The argument uses the spectral alignment condition stated in Assumption~\ref{assump:alignment}; removing this condition would require a different control of the resolvent term.
\end{remark}
```

Avoid:

```latex
\begin{remark}
PO-4 still has GAP-PO4-02, so this proof is incomplete.
\end{remark}
```

## Weakened statements

If a result's controlling statement came from `new_form`, prove that weakened form.

Do not prove the older, stronger statement. Do not mention that an internal arbiter weakened the result.

If the weakening affects interpretation, include at most one short mathematical remark explaining the final scope of the statement.

Prefer:

```latex
The following proof establishes the expectation-level statement used in Proposition~\ref{prop:risk}. High-probability control would require an additional concentration estimate.
```

Avoid:

```latex
The previous theorem was downgraded after repair failed.
```

## Referencing assumptions and definitions

Use assumptions and definitions from the Setting section rather than restating them in full, unless restatement improves readability.

Use public references such as:

* `Assumption~\ref{assump:source}`
* `Definition~\ref{def:estimator}`
* `Equation~\eqref{eq:population-risk}`
* `Lemma~\ref{lem:resolvent}`

Do not reference internal assumption IDs unless they are also public manuscript labels.

If the proof requires an assumption not stated in the manuscript, do not silently introduce it in the appendix. Flag the issue outside the manuscript-generation path.

## Equation and label policy

Use stable public labels for important equations, lemmas, and claims.

* Label only equations or intermediate claims that are referenced later.
* Do not over-label every displayed equation.
* Do not use internal IDs as LaTeX labels.
* Keep labels descriptive and manuscript-facing, such as `eq:resolvent-decomposition` or `lem:variance-control`.

If an equation label already exists in the manuscript, reuse it consistently.

If a definition, notation, or auxiliary object is needed only for an appendix proof and is not used in the Main Results or Setting sections, introduce it locally in the relevant appendix proof before first use. Keep such definitions scoped to that proof or appendix subsection. Do not move appendix-only notation into the Setting section unless it is needed by a committed result or main-body proof roadmap.

## Internal IDs — never expose them

The proof sources may contain internal identifiers such as:

* `PO-3`
* `GAP-PO5-01`
* `CLAIM-PO3-01` (and any `CLAIM-PO*-*` tag)
* `LEMMA-PO3-01` (and any `LEMMA-PO*-*` tag — this is the internal tag form, not the public word "Lemma")
* `CHECK-PO-4-02`
* `D1`, `D4`
* `repair_requested`
* `proposition_ready`
* `theorem_ready`
* `new_status`
* `paper_label`
* `Arbiter`
* `TheoremAudit`
* the words `safe` / `unsafe` used to qualify a mathematical object (internal tool-check
  vocabulary — e.g. "safe restricted-head regime"). The ordinary English word is fine in
  normal prose; never use it as a mathematical qualifier or definition.

Never print these identifiers in the proof appendix.

The raw proof drafts routinely carry `GAP-PO*-*`, `CLAIM-PO*-*`, and `LEMMA-PO*-*` tags and
occasional `safe`/`unsafe` tool-check wording. Strip every such tag and qualifier: a claim
tagged `CLAIM-PO3-01` becomes a plainly stated mathematical claim or is folded into the
proof; a `LEMMA-PO3-01` becomes a properly numbered public lemma or an inline step. A
leaked `CLAIM-PO3-01` or `safe` in the final appendix is exactly the internal-ID leak this
section exists to prevent.

Translate every internal reference into a public mathematical description, public theorem label, public assumption label, or ordinary prose.

## Relation to Main Results

The appendix should support, not duplicate, the Main Results section.

* If Main Results contains a proof roadmap, the appendix provides the full technical proof.
* If Main Results contains a full short proof, the appendix omits that proof unless additional deferred material is needed.
* If Main Results references an appendix proof, make sure the appendix contains a matching public heading and label.
* If the appendix contains a proof, the corresponding result should be referenced from the main body.
* Do not introduce a new main theorem in the appendix that was not stated in Main Results.

## What to draw from inputs

* Main Results section output or metadata indicating whether each result used short-proof mode, proof-roadmap mode, or sketch-only mode
* `theorem_state.decisions` for committed status and `paper_label`
* `theorem_state.statements` for target statements and public labels
* controlling statements selected from `new_form`, `governed_form`, or `form`
* proof drafts, proof blueprints, or `read_proof(po_id)` output
* self-critique files only to identify genuine unresolved gaps or caveats that affect proof validity
* Setting section assumptions and definitions
* appendix metadata for labels and section organization
* appendix-only definitions, notation, or auxiliary objects needed to make local proof arguments self-contained

## What NOT to do

* Do not duplicate a full proof that already appears in the Main Results section.
* Do not write an appendix proof for a result whose body proof is already complete, except for auxiliary material explicitly deferred from the body.
* Do not include proofs for blocked, conjecture-only, abandoned, or repair-requested statements that were not committed.
* Do not invent proof steps, assumptions, constants, equations, lemmas, or rates.
* Do not silently strengthen a result beyond the controlling committed statement.
* Do not prove an older stronger statement when the paper uses a weakened one.
* Do not expose internal IDs, proof-obligation names, audit labels, governance statuses, or tool names.
* Do not organize the appendix by internal proof-obligation order.
* Do not point from the main text to an appendix proof that does not exist.
* Do not include raw self-critique text.
* Do not turn the appendix into a discussion of failures or limitations.
* Do not require appendix-only definitions or notation to appear in the Setting section unless they are needed in the main body.
