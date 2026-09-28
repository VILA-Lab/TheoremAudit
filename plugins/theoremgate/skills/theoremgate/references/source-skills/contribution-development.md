---
name: contribution-development
description: "Turn verified but incomplete theory results into paper-ready contribution plans. Preserves correct seed lemmas and proposes the smallest theorem upgrade needed for a real paper."
version: 1.0
---

# Contribution Development Skill

## Purpose

This skill is used after the Arbiter has finalized a safe mathematical core.

The goal is not to reject correct-but-small results. The goal is to convert them
into a paper-ready contribution by identifying the next theorem, corollary,
counterexample, separation, impossibility result, estimator comparison, or
statistical consequence that should be built on top of the verified core.

This skill is constructive. It should preserve all correct results and use them
as seed lemmas.

## Core Rule

Do not use this logic:

```text
correct but weak -> reject
````

Use this logic:

```text
correct but weak -> seed lemma -> develop next theorem
```

Correct algebraic identities, decompositions, expansions, conditioning identities,
and projector formulas should not be discarded. They often become the lemma that
enables the real paper result.

However, a correct seed lemma should not automatically be treated as a full
conference-level contribution.

## When To Use This Skill

Use this skill after:

1. Method Team has produced proofs or partial proofs;
2. Attack Team has found gaps, obstructions, or counterexamples;
3. Arbiter has committed the safe core and weakened unsupported claims;
4. the project is about to move to manuscript writing.

This skill decides whether the project has sufficient acceptance evidence or should first receive
another bounded round of theorem development. Every accepted result still produces a full paper.

## Inputs To Consider

The Contribution Developer should inspect:

* committed statements;
* proof obligations and their statuses;
* Arbiter decisions;
* weakened or blocked proof routes;
* Attack Team flags;
* counterexamples and boundary examples;
* novelty audit;
* reviewer report, if available;
* related work summaries;
* current theorem state.

The agent should use the actual project state. Do not invent claims that are not
supported by the state.

## Contribution Maturity Labels

Classify the strongest committed result using exactly one of these labels.

### 1. `seed_lemma`

A correct but mostly algebraic or structural result, such as:

* exact decomposition;
* projector identity;
* pseudoinverse substitution;
* quadratic expansion;
* conditioning bookkeeping;
* equivalence between formulas;
* samplewise identity;
* definition-normalization lemma.

A `seed_lemma` is valuable, but usually insufficient for a full theory paper.

Examples:

* exact minimum-norm interpolation decomposition;
* exact excess-risk quadratic expansion;
* conditional cancellation of linear noise terms;
* proof that a residual term must be kept explicit.

### 2. `structural_corollary`

A meaningful consequence of a seed lemma, such as:

* a term vanishes under explicit structural conditions;
* a remainder becomes nonnegative under a stated covariance structure;
* a model class reduces to a simpler form;
* a special covariance or residual class is characterized;
* a coupling or interaction term is isolated and interpreted;
* an exact simplification holds under isotropy, block-invariance, or diagonal structure.

A `structural_corollary` is stronger than a seed lemma, but may still be too
limited unless the structural condition is meaningful.

### 3. `statistical_consequence`

A result that gives actual statistical content, such as:

* expectation bound;
* high-probability bound;
* asymptotic characterization;
* sufficient conditions for controlled risk;
* phase transition;
* scaling law;
* finite-sample performance guarantee;
* sign, magnitude, or concentration control for a remainder.

A `statistical_consequence` can support a full theory paper if it is nontrivial
and well positioned relative to prior work.

### 4. `separation_or_impossibility`

A negative, comparative, or obstruction-based theorem, such as:

* counterexample;
* lower bound;
* impossibility theorem;
* no-go theorem for a tempting simplification;
* estimator separation;
* ridge versus ridgeless comparison;
* proof that a class of summaries cannot control a quantity;
* proof that an assumption is necessary.

A `separation_or_impossibility` result can be paper-level if it reveals a real
obstruction or clarifies why a common intuition fails.

## Submission Evidence Labels

Classify submission evidence using exactly one of:

### `ready`

Use this only if the current committed results contain at least one substantial
contribution beyond seed lemmas.

A full paper normally needs at least one of:

* `statistical_consequence`;
* `separation_or_impossibility`;
* a strong `structural_corollary` with clear novelty and importance.

### `needs_strengthening`

Use this if the current result should not yet be written as a paper or note
because the next theorem is obvious enough to attempt first.

Use `needs_strengthening` when:

* the only committed result is a seed lemma;
* a failed proof route reveals a promising obstruction;
* counterexamples suggest a possible impossibility theorem;
* the reviewer or Arbiter identifies a missing statistical consequence;
* the manuscript would mostly consist of caveats and algebra.

## Manuscript Mode

Use `full_paper` for every accepted-result package. `needs_strengthening` may trigger a bounded
theorem-development pass before writing, but it does not change the eventual manuscript category.

## Upgrade Priority

When the current result is only a seed lemma, prefer upgrades in this order:

1. Turn a failed proof route into an impossibility theorem.
2. Turn a counterexample into a formal separation or lower bound.
3. Prove a structural corollary.
4. Prove an expectation or high-probability bound.
5. Compare two estimators.
6. Derive an asymptotic characterization or scaling law.

Do not recommend vague polishing.
Do not say only “write better.”
If the problem is missing mathematical substance, propose a mathematical upgrade.

## How To Use Failed Proof Routes

A failed proof route is not wasted.

If the Attack Team or Arbiter found that a simplification is invalid, ask whether
that invalidity can become the paper contribution.

Examples:

### Tail-only simplification fails

If a tail-only residual still creates top-coordinate fitted coefficients through

```math
X^\top(XX^\top)^{-1}r,
```

then propose a theorem showing that tail-only residual structure does not imply
tail-only interpolation effects.

This can become an impossibility theorem or separation result.

### Cross term has uncontrolled sign

If a term such as

```math
2a^\top \Sigma b
```

can be positive, negative, or dominant, propose a theorem showing sign
indefiniteness or constructing an example where the interaction term dominates
the positive quadratic term.

### Spectral summaries are insufficient

If a scalar or tail-block spectral summary cannot determine a remainder, propose
a no-go theorem showing that two instances can share the same summary but have
different remainder behavior.

### Noise simplification requires stronger assumptions

If a noise simplification works only under independence or homoscedasticity,
propose either:

* a general conditional-covariance formula; or
* a necessity example showing why the stronger assumption is needed.

## Common Upgrade Types

### A. Impossibility theorem

Use when a natural simplification failed.

Good form:

```text
There exist two problem instances with the same proposed summary but different
values/signs/scales of the target remainder.
```

or:

```text
Even when the residual is tail-dependent, the fitted residual lift need not lie
in the tail subspace.
```

### B. Counterexample theorem

Use when Attack Team found an example that breaks a tempting claim.

Good form:

```text
There exists an in-scope construction where the residual contribution is
negative / positive / large / nonzero despite satisfying the proposed
orthogonality conditions.
```

### C. Structural corollary

Use when the seed lemma simplifies under a clean condition.

Good form:

```text
If Sigma preserves Row(X) and Null(X), then the interaction term vanishes.
In particular, under isotropic covariance, the misspecification remainder
reduces to a nonnegative residual-lift term.
```

### D. Statistical bound

Use when a plausible controlled regime exists.

Good form:

```text
Under diagonal-Gaussian design and residual class ..., the expectation of the
remainder is bounded by ...
```

Only propose this if the proof path is realistic and assumptions are explicit.

### E. Estimator comparison

Use when the seed lemma can compare two estimators.

Good form:

```text
The misspecification remainder appears for the ridgeless interpolator but is
damped by ridge through the regularized resolvent.
```

## Good Behavior

A good Contribution Developer should write something like:

```text
The current result is correct and useful, but it is a seed lemma. The failed
tail-only simplification is the interesting obstruction. Turn that obstruction
into a formal impossibility theorem, then use the decomposition as Lemma 1.
```

or:

```text
The current exact decomposition is note-level by itself. The smallest upgrade is
a structural corollary: under isotropic covariance, the row/null interaction
vanishes exactly, so the residual-lift component is nonnegative. This is not
enough for a full paper alone, but it is a useful second result.
```

or:

```text
The Attack Team counterexample already demonstrates that broader orthogonal
residual classes cannot be controlled by a tail-only argument. Formalize this as
a necessity theorem for the tail-structured assumption.
```

## Bad Behavior

Do not:

* discard correct lemmas;
* mark a correct lemma as failed because it is small;
* pretend a seed lemma is a full paper contribution;
* recommend only writing changes when the issue is mathematical substance;
* propose broad vague theorems;
* create more than three new obligations;
* turn conjectures into claimed theorems;
* ignore Attack Team counterexamples;
* recommend full manuscript writing when the state says the main theorem is only
  an exact formula;
* compensate for weak results by adding long related work, extra experiments, or
  repeated caveats.

## Output Requirements

The contribution-development plan must contain all of the following fields:

```json
{
  "submission_evidence_status": "needs_strengthening",
  "maturity_label": "seed_lemma",
  "current_core": "...",
  "main_gap": "...",
  "recommended_upgrade": {
    "type": "...",
    "title": "...",
    "why": "..."
  },
  "new_obligations": [
    {
      "id": "PO-6",
      "claim": "...",
      "why_nontrivial": "...",
      "proof_strategy": "...",
      "dependencies": ["TH-1"],
      "difficulty": "moderate",
      "status": "open"
    }
  ],
  "manuscript_kind": "full_paper",
  "rationale": "..."
}
```

## Field Guidance

### `submission_evidence_status`

One of:

* `ready`
* `needs_strengthening`

### `maturity_label`

One of:

* `seed_lemma`
* `structural_corollary`
* `statistical_consequence`
* `separation_or_impossibility`

### `current_core`

Describe the strongest safe result already proved.

Example:

```text
Exact finite-sample decomposition of the minimum-norm interpolator and
conditional excess-risk identity relative to the best linear predictor.
```

### `main_gap`

Explain what is missing for a paper-level contribution.

Example:

```text
The current result does not control, characterize, separate, or bound the
misspecification remainder.
```

### `recommended_upgrade`

A concrete theorem direction, not vague advice.

Example:

```json
{
  "type": "impossibility_theorem",
  "title": "Tail-structured residuals do not imply tail-only interpolation effects",
  "why": "The failed PO-3 route revealed leakage through the full interpolation operator."
}
```

### `new_obligations`

Create at most three obligations.

Each obligation should be concrete enough for Method Team to attempt.

Each obligation must include:

* `id`
* `claim`
* `why_nontrivial`
* `proof_strategy`
* `dependencies`
* `difficulty`
* `status`

Use IDs continuing after the current proof obligations when possible, e.g.
`PO-6`, `PO-7`, `PO-8`.

### `manuscript_kind`

Always `full_paper` for an accepted-result package.

### `rationale`

Explain why this plan is the right next step.

## Example Output: Exact Decomposition Only

If the current project has only an exact decomposition, output something like:

```json
{
  "submission_evidence_status": "needs_strengthening",
  "maturity_label": "seed_lemma",
  "current_core": "Exact finite-sample decomposition of minimum-norm interpolation error and conditional excess-risk expansion under misspecification.",
  "main_gap": "The result does not yet control or characterize the misspecification remainder; it only identifies it.",
  "recommended_upgrade": {
    "type": "impossibility_theorem",
    "title": "Tail-structured residuals do not imply tail-only interpolation effects",
    "why": "The attempted tail-block simplification failed because the full interpolation operator mixes top and tail coordinates."
  },
  "new_obligations": [
    {
      "id": "PO-6",
      "claim": "Construct an in-scope tail-dependent residual for which the fitted residual lift X^T(XX^T)^(-1)r has nonzero top-block coordinates with positive probability.",
      "why_nontrivial": "The residual is tail-only, but the interpolating coefficient vector is not tail-only.",
      "proof_strategy": "Use a small diagonal-Gaussian or discrete isotropic construction. Condition on a full-row-rank design and compute or characterize the top block of X^T(XX^T)^(-1)r.",
      "dependencies": ["TH-1"],
      "difficulty": "moderate",
      "status": "open"
    },
    {
      "id": "PO-7",
      "claim": "Show that no bound depending only on the tail residual norm and tail covariance block can determine the full misspecification remainder without additional assumptions.",
      "why_nontrivial": "This turns the failed simplification into a formal no-go theorem.",
      "proof_strategy": "Construct two designs or residual configurations with matching tail summaries but different top-block leakage or different interaction terms.",
      "dependencies": ["TH-1", "PO-6"],
      "difficulty": "hard",
      "status": "open"
    }
  ],
  "manuscript_kind": "full_paper",
  "rationale": "The current theorem is a useful seed lemma, but the obstruction discovered by the Attack Team can become a stronger negative result."
}
```

## Example Output: Structural Corollary Path

```json
{
  "submission_evidence_status": "needs_strengthening",
  "maturity_label": "structural_corollary",
  "current_core": "Exact decomposition plus row/null-space orthogonality.",
  "main_gap": "The project has a useful structural simplification but no general statistical control.",
  "recommended_upgrade": {
    "type": "structural_corollary",
    "title": "Vanishing interaction under covariance-invariant row/null decomposition",
    "why": "The decomposition shows that the interaction term vanishes when Sigma maps Row(X) and Null(X) into themselves."
  },
  "new_obligations": [
    {
      "id": "PO-6",
      "claim": "If Sigma preserves Row(X) and Null(X), then the interaction term between the null-space signal and residual lift vanishes. In particular, if Sigma = lambda I, the misspecification remainder reduces to a nonnegative quadratic term.",
      "why_nontrivial": "This gives a clean interpretable special case and clarifies when the remainder is nonnegative.",
      "proof_strategy": "Use a in Null(X), b in Row(X), and Sigma-invariance of the two subspaces to show a^T Sigma b = 0.",
      "dependencies": ["TH-1"],
      "difficulty": "easy",
      "status": "open"
    }
  ],
  "manuscript_kind": "full_paper",
  "rationale": "This upgrade makes the decomposition more informative, but may still be note-level unless paired with a stronger theorem."
}
```

## Final Decision Rule

At the end, decide:


If only seed lemmas exist:
    submission_evidence_status = needs_strengthening
    manuscript_kind = full_paper

If seed lemmas plus a useful structural corollary exist:
    submission_evidence_status = needs_strengthening
    manuscript_kind = full_paper

If a statistical consequence or impossibility/separation theorem exists:
    submission_evidence_status = ready
    manuscript_kind = full_paper
