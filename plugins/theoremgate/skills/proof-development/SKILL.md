---
name: proof-development
description: Design proof strategies and write auditable theorem proofs with dependency tracking, assumption accounting, tool checks, and explicit gaps. Use for TheoremAudit proof obligations or rigorous standalone proof development.
---

# Proof Development

Read `proof-strategy.md`, `proof-writing.md`, and `mathematical-tools.md` under
`../theoremgate/references/source-skills/`.

For each proof obligation, create a blueprint before drafting. Track dependencies, assumptions used,
key lemmas, fragile steps, boundary regimes, and attempted alternatives. Distinguish a complete proof
from a citation-backed specialization and from a conjectural argument. Tool output can verify algebra
or find counterexamples but never replaces a mathematical justification.

Before marking any obligation `drafted`, run an author preflight that is separate from the later
independent audit:

- test deterministic, zero-variance, zero-threshold, one-sample, endpoint, and extreme-scale cases;
- check location/scale shifts whenever a bound depends on variance, moments, clipping, or truncation;
- verify measurability, filtration, independence, and conditioning claims literally from assumptions;
- recompute every named concentration inequality and numerical constant;
- check dimensions, signs, denominators, `0/0`, `0^0`, and positivity conditions;
- confirm every theorem quantifier is supported by the proof and no comparator rate is merely assumed.

For a publishable theorem package, close the entire critical path for the primary target and then the
declared companion result. Do not treat a headline theorem as complete while a central constant,
probability event, limiting argument, or comparison step remains conditional. Prefer a complete
substantive fallback theorem over a grand partial claim, but do not retreat to a direct corollary or
vacuous special case merely to obtain a drafted status.

If a one-line counterexample defeats the claim, repair discovery or record a gap before audit. Do not
label a proof complete just because its main algebraic path looks plausible.

Use the proof DAG's drafting frontier to order work. Draft a downstream obligation
conditionally when an upstream obligation is merely unstarted, planned, partial, or under analysis,
and state the assumed dependency explicitly. Do not treat conditional work as final. A failed,
blocked, or Arbiter-rejected transitive dependency is a hard blocker until repaired or reformulated.

Never silently patch a false claim. Record the gap and propose a precise weakening or repair.
Use structured gaps with stable IDs, severity, description, open/resolved status, and an explicit
resolution when closed. Bind persisted blueprints and drafts by hash, state the exact proved scope,
and list every assumption actually used. Never assign an Arbiter proof status from the proof-team
tooling.

For governed runs, use `../../scripts/proof_tools.py` for proof-index scaffolding, blueprints, tool
checks, and drafts. Use its `frontier` command before ordering proof work, and use the
controller to validate and complete the stage. For an older unversioned proof index, run
`migrate-index --reason <explanation>` and preserve its migration integrity notice.
