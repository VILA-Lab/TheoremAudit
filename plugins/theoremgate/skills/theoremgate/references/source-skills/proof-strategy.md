---
name: proof-strategy
description: "Select the correct primary proof technique for each proof obligation type. Called by the Strategist stage of the Method Team. Provides a taxonomy of proof types with exact enum names matching the write_blueprint tool."
version: 2.1
used_by: method_team
domain: theoretical machine learning
inputs: discovery.json, theorem_state.json if available, proof_obligations.json if available, skeptic_flags.json if available, tool_checks if available
outputs: blueprint.md via write_blueprint
---

# Proof Strategy Skill

## Purpose

Select the primary proof strategy for each proof obligation and produce an executable proof blueprint for the Proof Writer.

This skill does not prove the result. It decides how the proof should be attempted, which assumptions are expected to be used, which external theorems the Analyst must check, and where the main proof risks are.

The output must use proof-type enum names exactly matching the `write_blueprint` tool.

## Critical rules

* Use exact enum names from the taxonomy below. These must match the `write_blueprint.proof_type` field exactly.
* Do not modify the canonical proof-obligation DAG. Report expected dependencies only.
* Expected assumptions are not verified here. The Analyst and Proof Writer confirm actual usage.
* Check `may_follow_directly_from` for every obligation before attempting a full proof strategy.
* If external theorems are needed, list them for Analyst verification. Do not assume they are safe.
* A blueprint must be executable: every step should be a concrete mathematical operation, not a vague instruction.
* If `skeptic_flags.json` or assumption-attack results are available, consult them before selecting the strategy.
* Do not build a strategy whose central step relies on an unresolved assumption flagged as circular, theorem-shaped, too-strong, unverifiable, inconsistent, or redundant without explicitly marking the risk.

## Skeptic-flag awareness

If assumption-attack, counterexample-search, or other skeptic outputs are available, inspect them before writing the blueprint.

Use them as follows:

* If an expected assumption was flagged as `circular` or `theorem-shaped`, do not rely on it as the central proof engine unless no alternative exists. Mark the obligation `hard` or `open`, and suggest a retreat or weakening.
* If an expected assumption was flagged as `too-strong`, use it only if the paper world explicitly accepts that restriction. Otherwise, suggest a strategy under a weaker or more standard condition.
* If an expected assumption was flagged as `too-weak`, identify the missing condition in `Dangerous Steps` and mark Analyst follow-up.
* If an expected assumption was flagged as `unverifiable`, avoid strategies that require checking it empirically or informally unless it is stated as a formal assumption.
* If an assumption is flagged as `inconsistent`, do not use it. Mark the obligation `open` until the assumption set is repaired.
* If an assumption is flagged as `redundant`, prefer a strategy that avoids it.

If no skeptic outputs are available, write the blueprint normally and do not invent flags.

## Compute, do not gesture

A blueprint of the form "decompose; bound the spectral sums; control the head block" is not a proof strategy. It is a wish list.

Each step must be a concrete, checkable mathematical operation that the Proof Writer can execute.

Good blueprint steps name:

* the exact quantity to rewrite;
* the exact decomposition, inequality, or identity to apply;
* the variable or parameter being swept, optimized, or bounded;
* the theorem or lemma needed;
* the condition that must be verified;
* the form of the resulting bound or equality;
* the dependency on key parameters.

Bad blueprint steps use vague phrases such as:

* "control the error";
* "handle the difficult term";
* "use concentration" without naming the random object and condition;
* "bound the spectral sum" without saying which sum and by what inequality;
* "work in a favorable regime" without stating explicit inequalities.

In a restricted, finite, diagonal, low-rank, linear, tabular, or otherwise simplified model, hard quantities are often directly computable. In such cases, plan to compute the relevant quantity explicitly rather than vaguely bound it.

If a step can only be gestured at and not computed, decomposed, or explicitly bounded, mark the obligation difficulty as `hard` or `open` and suggest a retreat target where the step becomes executable.

## Proof type taxonomy

### Type 1 — Decomposition

**Enum:** `decomposition`

**What:** Split a complex quantity into manageable terms.

**Typical use:** bias-variance decompositions, residual decompositions, objective decompositions, error splitting.

**Technique:** algebraic decomposition, orthogonality, projection identities, resolvent identity, triangle inequality.

**Structure:**

```text
Step 1: Define the target quantity exactly.
Step 2: Rewrite it as a sum of named terms.
Step 3: Identify which terms vanish, are orthogonal, or require separate bounds.
Step 4: Assign each remaining term to a lemma or sub-obligation.
Step 5: State the final recombination inequality or identity.
```

**Dangerous step:** Cross-terms are not automatically zero. Orthogonality, independence, or centering must be proved.

---

### Type 2 — Concentration

**Enum:** `concentration`

**What:** Control random fluctuations of a stochastic quantity.

**Typical use:** empirical covariance control, empirical process bounds, sample averages, random matrices, quadratic forms.

**Technique:** Bernstein, Hoeffding, McDiarmid, Efron-Stein, Hanson-Wright, matrix concentration, martingale concentration.

**Structure:**

```text
Step 1: Identify the random object exactly.
Step 2: Express it as a sum, martingale difference sequence, empirical process, or quadratic form.
Step 3: Verify independence, conditional independence, or filtration structure.
Step 4: Compute the variance proxy, envelope, Lipschitz constant, or norm bound.
Step 5: Apply the appropriate concentration theorem.
Step 6: Track dimension, effective dimension, confidence, and union-bound factors.
```

**Dangerous step:** Inverse operators, small regularization, or ill-conditioned matrices can amplify concentration errors.

---

### Type 3 — Bias Bound

**Enum:** `bias_bound`

**What:** Control systematic error from approximation, regularization, misspecification, truncation, or model bias.

**Typical use:** approximation error, regularization bias, source-condition bias, projection bias.

**Technique:** source conditions, spectral filters, approximation theory, projection arguments, truncation analysis.

**Structure:**

```text
Step 1: Write the bias term as an explicit functional or residual.
Step 2: State the structural assumption controlling the target object.
Step 3: Apply the approximation, source, projection, or filter argument.
Step 4: Derive an explicit bound in terms of the relevant parameter.
Step 5: Verify the norm in which the bias is controlled.
```

**Dangerous step:** A rate may depend on the chosen norm, regularity scale, or saturation phenomenon.

---

### Type 4 — Rate Balancing

**Enum:** `rate_balancing`

**What:** Choose a parameter that balances multiple error terms.

**Typical use:** regularization choice, bandwidth choice, truncation level, sample-complexity rate, step-size optimization.

**Technique:** monotonicity, calculus, comparison of leading terms, explicit optimization.

**Structure:**

```text
Step 1: Write the total bound as a sum of named terms.
Step 2: Identify how each term depends on the tunable parameter.
Step 3: Check monotonicity or dominance relations.
Step 4: Solve the balancing equation or optimize the upper bound.
Step 5: Verify all remainder terms are lower order at the chosen parameter.
```

**Dangerous step:** Hidden parameter-dependent remainders can dominate the balanced rate.

---

### Type 5 — Assembly

**Enum:** `assembly`

**What:** Combine component lemmas into a main theorem.

**Typical use:** final sufficiency proof, main theorem proof after lemmas, combining high-probability events.

**Technique:** triangle inequality, union bound, event intersection, substitution of lemmas, deterministic implication.

**Structure:**

```text
Step 1: List all component lemmas and their conclusions.
Step 2: Define the event or condition under which all lemmas hold.
Step 3: Show the event has the claimed probability if needed.
Step 4: Substitute component bounds into the main target.
Step 5: Verify every term and remainder is accounted for.
Step 6: State the final theorem in the promised form.
```

**Dangerous step:** Missing remainder terms, incompatible events, or inconsistent parameter choices.

---

### Type 6 — High Probability

**Enum:** `high_probability`

**What:** Upgrade expectation, average-case, or deterministic conditional bounds to high-probability bounds.

**Typical use:** confidence bounds, probability statements, uniform-over-parameters results.

**Technique:** bounded differences, Azuma, Bernstein, peeling, union bounds, concentration around expectation.

**Structure:**

```text
Step 1: Identify the random quantity to upgrade.
Step 2: Verify the concentration condition.
Step 3: Apply the high-probability inequality.
Step 4: Track confidence parameter dependence explicitly.
Step 5: Verify confidence factors do not break the target rate.
```

**Dangerous step:** Confidence factors may interact badly with dimension, regularization, or inverse operators.

---

### Type 7 — Lower Bound

**Enum:** `lower_bound`

**What:** Show a result cannot be improved, or prove impossibility, necessity, or minimax lower bound.

**Typical use:** counterexamples, separations, impossibility results, minimax lower bounds, necessity claims.

**Technique:** explicit construction, Fano, Le Cam, Assouad, packing, two-point testing, adversarial example.

**Structure:**

```text
Step 1: Specify the model or instance class explicitly.
Step 2: Verify every assumption of the target setting.
Step 3: Compute or lower-bound the target quantity.
Step 4: Show the desired improvement or guarantee is impossible.
Step 5: State exactly which claim, rate, or assumption is shown necessary.
```

**Dangerous step:** A lower-bound construction is invalid if it violates the assumptions of the theorem it attacks.

---

### Type 8 — Stability

**Enum:** `stability`

**What:** Control perturbation under changes in data, operators, distributions, algorithms, or parameters.

**Typical use:** algorithmic stability, operator perturbation, distribution shift, leave-one-out arguments.

**Technique:** resolvent identity, Lipschitz bounds, perturbation theory, coupling, stability recursion.

**Structure:**

```text
Step 1: Write the perturbed quantity minus the original quantity.
Step 2: Apply a perturbation identity or stability inequality.
Step 3: Bound the perturbation magnitude.
Step 4: Track amplification through inverses, iterations, or recursions.
Step 5: Convert the perturbation bound into the target statement.
```

**Dangerous step:** Small denominators, long time horizons, or repeated updates can amplify perturbations.

---

### Type 9 — Generalization

**Enum:** `generalization`

**What:** Transfer empirical, sample-level, or training-level control to population-level control.

**Typical use:** generalization bounds, sample-to-population transfer, excess-risk bounds.

**Technique:** uniform convergence, Rademacher complexity, PAC-Bayes, stability, compression, concentration.

**Structure:**

```text
Step 1: Write the population quantity minus the empirical quantity.
Step 2: Choose the generalization mechanism.
Step 3: Verify the hypothesis class, loss, data, and complexity assumptions.
Step 4: Apply the generalization theorem or derive the sample-to-population bound.
Step 5: Substitute into the final risk or performance claim.
```

**Dangerous step:** Complexity, dimension, loss boundedness, or data-dependence assumptions may be hidden.

---

### Type 10 — Existence

**Enum:** `existence`

**What:** Show an estimator, minimizer, solution, equilibrium, fixed point, or sequence exists.

**Typical use:** well-posedness, existence of minimizers, representer arguments, compactness arguments.

**Technique:** compactness, coercivity, lower semicontinuity, representer theorem, fixed-point theorem, measurable selection.

**Structure:**

```text
Step 1: Identify the object whose existence is needed.
Step 2: State the space in which it should exist.
Step 3: Apply the appropriate existence theorem or constructive argument.
Step 4: Verify compactness, closedness, coercivity, continuity, or measurability.
Step 5: Record any uniqueness or non-uniqueness implications.
```

**Dangerous step:** Existence may require compactness, closedness, or measurability assumptions not present in the plan.

---

### Type 11 — Equivalence

**Enum:** `equivalence`

**What:** Prove two conditions or statements are equivalent.

**Typical use:** if-and-only-if results, characterizations, necessary-and-sufficient conditions.

**Technique:** prove both directions separately, possibly with different tools.

**Structure:**

```text
Step 1: State the two directions separately.
Step 2: Prove the forward direction.
Step 3: Prove the backward direction.
Step 4: Check whether the two directions require different assumptions.
Step 5: Combine into the equivalence statement.
```

**Dangerous step:** One direction may require stronger assumptions than the other.

---

### Type 12 — Direct Citation

**Enum:** `direct_citation`

**What:** The proof obligation may follow directly from a known published theorem.

**Typical use:** standard concentration theorem, known minimax lower bound, known convergence theorem, known spectral theorem.

**Technique:** notation translation and condition checking.

**Structure:**

```text
Step 1: Identify the known theorem precisely.
Step 2: Map the known theorem's notation to the current paper's notation.
Step 3: List every condition of the known theorem.
Step 4: Send the theorem to the Analyst for write_tool_check.
Step 5: If safe, state the obligation as a corollary.
```

**Dangerous step:** A known theorem may look applicable but fail because one condition is missing or because the setting differs.

---

## Primary vs. secondary proof type

A proof obligation may require several techniques. However, `write_blueprint` accepts one primary `proof_type`.

Choose the primary proof type by the logical role of the obligation's conclusion, not by every tool used inside the proof.

Use these rules:

1. If the obligation is discharged almost entirely by a known theorem, choose `direct_citation`.
2. If the obligation proves an if-and-only-if statement, choose `equivalence`.
3. If the obligation proves impossibility, necessity, separation, or a minimax lower bound, choose `lower_bound`.
4. If the obligation only combines previous lemmas into a main result, choose `assembly`.
5. If the obligation's final claim is population-level control from sample-level evidence, choose `generalization`, even if concentration appears as a sub-step.
6. If the final claim is a tail/confidence statement, choose `high_probability`.
7. If the final claim is control of random fluctuation itself, choose `concentration`.
8. If the final claim is perturbation sensitivity, choose `stability`.
9. If the final claim is systematic approximation/regularization error, choose `bias_bound`.
10. If the final claim is parameter choice or optimized rate, choose `rate_balancing`.
11. If the final claim is existence or well-posedness, choose `existence`.
12. If the final claim is an identity or split that enables later bounds, choose `decomposition`.

List secondary techniques inside `Technique`, `Key Steps`, and `External Theorems for Analyst to Check`.

Example:

```text
A generalization theorem that uses Bernstein concentration internally should use:
Type: generalization
Technique: Rademacher complexity plus Bernstein concentration
```

Example:

```text
A stability proof that uses concentration to control a perturbation should use:
Type: stability
Technique: resolvent perturbation plus matrix concentration
```

## Decision guide

Given an obligation, decide in this order:

1. Could it follow directly from a published theorem? → consider `direct_citation`.
2. Is the conclusion an iff or characterization? → `equivalence`.
3. Is the conclusion negative, minimax, necessary, impossible, or a separation? → `lower_bound`.
4. Is the obligation only combining previously established statements? → `assembly`.
5. Is the final target population risk, sample-to-population transfer, or generalization? → `generalization`.
6. Is the final target a high-probability upgrade or confidence statement? → `high_probability`.
7. Is the final target concentration of a stochastic object? → `concentration`.
8. Is the final target perturbation or sensitivity? → `stability`.
9. Is the final target approximation, regularization, or misspecification bias? → `bias_bound`.
10. Is the final target an optimized parameter or rate choice? → `rate_balancing`.
11. Is the final target existence or well-posedness? → `existence`.
12. Is the final target a decomposition identity? → `decomposition`.

If still ambiguous, choose the type corresponding to the final statement being proved and list the other techniques as sub-steps.

## Output format for `blueprint.md`

```markdown
# Blueprint: PO-X

## Type
[exact enum: decomposition | concentration | bias_bound | rate_balancing | assembly | high_probability | lower_bound | stability | generalization | existence | equivalence | direct_citation]

## Technique
[primary proof technique plus important secondary techniques]

## Key Steps
1. [concrete, checkable mathematical operation]
2. [concrete, checkable mathematical operation]
3. [concrete, checkable mathematical operation]

## Expected Assumptions
- A1: expected use in [step/reason]
- A6: expected use in [step/reason]

List only assumptions actually expected to be used. Label them as expected, not used.

## Skeptic Flags Consulted
- [assumption/result ID]: [flag type] — [how the blueprint avoids, weakens, or explicitly risks relying on it]
If no skeptic flags are available, write: "No skeptic flags available."

## External Theorems for Analyst to Check
- [theorem name] ([source if known]): needed for [step N]
  Conditions Analyst must verify: [condition 1], [condition 2], ...

If none, write: "None identified — obligation may follow from first principles."

## May Follow Directly From
[known theorem/result name and source, or "Not applicable"]

Fill this if the obligation might follow directly from a published result.

## Expected Dependencies
- PO-Y appears needed because [reason]

Report only. Do not modify the canonical DAG.

## Dangerous Steps
- [step N]: [specific mathematical reason this step might fail]

## Difficulty
[routine | moderate | hard | open]

## Honest Assessment
[One paragraph naming the specific mathematical obstacle, the condition most likely to fail, and the fallback or retreat if the strategy does not work.]
```

## Difficulty calibration

Use difficulty labels honestly.

* `routine`: standard argument once assumptions and external tools are verified.
* `moderate`: requires nontrivial but standard combinations of known tools.
* `hard`: contains a genuinely delicate step, fragile assumption, or nonstandard argument.
* `open`: no executable path is currently visible, or the strategy depends on an unresolved flagged assumption or unverified conjecture.

Do not label everything `hard`. Do not label a proof `routine` merely because the high-level idea is familiar.

## Honest Assessment calibration

The Honest Assessment must be specific.

A good Honest Assessment names:

* the exact step most likely to fail;
* the mathematical reason it may fail;
* the assumption or external theorem most at risk;
* the fallback plan if it fails.

Bad Honest Assessment:

```text
The proof may be difficult and will require careful analysis.
```

Good Honest Assessment:

```text
The main risk is Step 3: the matrix Bernstein bound requires a uniform operator-norm envelope, but the current assumptions only give a second-moment condition. If Analyst cannot verify boundedness or an appropriate heavy-tailed analogue, the blueprint should retreat to an expectation-level bound or add truncation as a separate lemma.
```

The assessment should not be generic hedging or reviewer-style commentary. It should be actionable for the Analyst and Proof Writer.

## Quality checklist

* The proof type uses an exact enum name.
* The primary proof type matches the final conclusion of the obligation.
* Secondary techniques are listed without changing the primary enum.
* `may_follow_directly_from` was checked.
* The blueprint does not modify the canonical DAG.
* Expected dependencies are reported only.
* Expected assumptions are not presented as verified usage.
* Skeptic flags were consulted when available.
* Flagged assumptions are not silently used as central proof engines.
* Every key step is concrete and executable.
* External theorems are sent to Analyst for condition checking.
* Dangerous steps name specific mathematical failure modes.
* Difficulty is calibrated.
* Honest Assessment is specific, actionable, and non-generic.

## What NOT to do

* Do not use proof-type names outside the enum list.
* Do not modify or set dependencies.
* Do not label assumptions as "used"; they are only expected at this stage.
* Do not assume an external theorem is safe.
* Do not skip `may_follow_directly_from`.
* Do not ignore available skeptic flags.
* Do not rely centrally on a flagged circular, theorem-shaped, inconsistent, or too-strong assumption without marking the risk.
* Do not write vague proof plans such as "control the main term" or "bound the difficult part."
* Do not write `hard` for everything.
* Do not write generic Honest Assessments.
