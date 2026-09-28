---
name: theory-discovery
description: Formalize a theoretical ML question into definitions, assumptions, theorem targets, proof obligations, dependency structure, and exploratory probes. Use for discovery and exploration stages before proof writing.
---

# Theory Discovery

Read the preserved guidance in `../theoremgate/references/source-skills/discovery.md`,
`exploration.md`, and `mathematical-tools.md` in the same source-skills directory.

Produce a self-contained mathematical setting. Give every assumption, target, and proof obligation
a stable ID. Quantifiers, conditioning, domains, boundary cases, and dependencies must be explicit.
Separate established facts, proposed claims, empirical hints, and conjectures.

For a full run targeting original research or a workshop paper, design a theorem package rather than
a thin isolated claim. Record the primary result's nonstandard technical obstacle, precise
hypothesized novelty delta, closest-work boundary, concrete nonvacuity check, and an executable proof
route with no central open step. Include a distinct supporting theorem target—such as a lower bound,
necessity result, tightness statement, separation, or meaningful extension—and give it its own proof
obligation. Omit the companion only when the primary theorem is exceptionally deep and record a
specific justification. Reject renamed standard theorems, direct specializations without a new
obstacle, assumption-shaped conclusions, and results that are vacuous in the intended regime.

Explore with small cases, symbolic or numerical checks, and counterexample probes. Such probes guide
proof strategy but are not proofs. Finish with one of `continue`, `narrow`, `reshape`, or `blocked`,
with a concrete rationale.
