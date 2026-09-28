---
name: research-direction
description: Generate and select theoretical machine-learning research directions with explicit novelty, feasibility, and falsifiability checks. Use for ideation, direction comparison, problem selection, or reframing before formal theorem discovery.
---

# Research Direction

Use the active Codex model; never call the legacy model API. Read the source guidance in
`../theoremgate/references/source-skills/direction-generation.md` and
`../theoremgate/references/source-skills/direction-selection.md`.

If the user gives a clear research direction, create exactly one faithful normalized candidate. Keep
every explicit object, regime, and requested result together; unresolved assumptions or proof details
belong to discovery and are not reasons to invent alternatives. Generate multiple materially different
candidates only when the direction itself is vague or the user explicitly asks for ideas or options.
For each candidate, record the question, candidate claim, assumptions, closest known result, novelty
risk, proof route, falsification test, expected contribution, and estimated difficulty. Search primary
literature before claiming novelty.

For multiple candidates, select with an explicit comparison rather than intuition alone. For one
user-specified candidate, audit literature, feasibility, and falsifiability, then pass that same direction
to discovery without replacing it, splitting it, or dropping explicit components. Later proof and audit
stages may narrow unsupported claims transparently. When running inside the governed workflow, write
only the current stage artifact and use its exact schema.
