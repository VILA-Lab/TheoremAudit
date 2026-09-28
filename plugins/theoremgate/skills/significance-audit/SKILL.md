---
name: significance-audit
description: Independently audit whether accepted theory has enough technical depth, operational assumptions, application evidence, baselines, and empirical validation for its claimed significance. Use after novelty review and before contribution framing or paper routing.
---

# Significance Audit

Audit accepted statements independently of their authors and the contribution developer. Read the
theory inputs, `artifacts/novelty_audit.json`, experiment evidence, and the significance schema in
`../theoremgate/references/artifacts.md`. Do not repair proofs, invent experiments, or choose a tier.

Separate correctness from significance. Classify the theory as a direct specialization, nontrivial
extension, new method, new lower bound, or new framework. Identify the obstacle overcome and whether
the bound is practically informative.

Evaluate the importance of the question separately from the elegance of the proof. Record whether the
central result changes understanding, improves a practically relevant quantity, enables a new method,
or merely characterizes a convenient restricted model. Compare the accepted result with the strongest
feasible alternative direction considered earlier; do not reward a result only because it was safer to
prove. Treat stacked restrictions such as shared minimizers plus simultaneous diagonalization as a
major significance burden unless the result clearly justifies what is learned despite them.

For every application-facing assumption, record its operational meaning, observability, supporting
evidence, and misspecification risk. Do not infer that observed answer labels are Markov merely
because latent states are Markov. Treat known mixing parameters, stationarity, reversibility,
independence, oracle access, and initialization as strong burdens unless operationalized.

Distinguish exact-model synthetic checks, semi-synthetic evidence, and real-system evidence. Audit
calibration, error versus compute, parameter misspecification, nonstationary starts, multi-state or
heterogeneous cases, and baseline strength. Simulations drawn from the theorem's assumptions do not
validate the motivating real system.

Write `artifacts/significance_audit.json` using the exact schema. Use major blockers for missing
evidence that prevents the claimed route; use fatal only when the application or significance is
contradicted. The deterministic router decides the tier.
