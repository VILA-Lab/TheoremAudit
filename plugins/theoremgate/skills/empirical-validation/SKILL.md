---
name: empirical-validation
description: Adaptively select, design, run, and assess reproducible experiments that test accepted theoretical claims, including support, stress tests, falsification, contradictions, uncertainty, raw results, and publication-quality figures. Use for empirical strategy or validation after theory acceptance.
---

# Empirical Validation

If some selected experiments finish and another cannot run, retain the completed
evaluations and use `mark-blocked` for the unavailable experiment. A schema-v2
`blocked` summary may be finalized only when the existing paper route permits
writing, explicitly forbids submission framing, and records `evidence_incomplete`.
State the missing resource and unsupported application claims in the limitations.
Do not change the theory bundle, mark blocked evidence completed, or invent a
`real_system` coverage tag. Review figures from completed experiments normally.
After validation, complete the empirical workflow stage and continue writing the
restricted draft; empirical evidence remains blocked and submission remains disallowed.

Read `../theoremgate/references/source-skills/empirical-experiments.md` before designing an
experiment. Read `../theoremgate/references/empirical-evidence.md` for the enforced artifact schema.
Read `../theoremgate/references/figure-design.md` before designing or reviewing any main figure.
Read `../theoremgate/references/experiment-resources.md` for acquisition, version-2 feasibility
records, and bounded CPU execution. Use strategy schema version 2 for new programs; version 1
remains readable for historical evidence and unchanged legacy continuations.

First generate candidate experiments from accepted claims, assumptions and predictions,
significance blockers, reviewer objections, available substrates, and compute limits. Compare claim
relevance, discriminative and falsification value, reviewer value, feasibility, and redundancy.
Before selecting a runnable real-data experiment, identify actual sources, inspect required fields
and annotation provenance, check licensing/access, and estimate CPU time and memory. Acquire
permitted small resources and check a pilot before committing the full compute budget. First look
for suitable existing annotations. Record new annotation, unavailable reference labels, gated data,
or excess resource needs as a blocker or approval requirement, not as intrinsic untestability.
Select the smallest convincing program and record why alternatives were rejected. Experiment types
and coverage labels are flexible; never run an irrelevant experiment to satisfy a generic category.

Account for every accepted claim as selected or not empirically testable. A completed full-paper
strategy may not leave an accepted claim deferred. Align this classification with the manuscript
architecture's `visual_evidence_plan`: every claim listed in `empirical_claim_ids` must be selected,
and all remaining accepted claims must be recorded as not empirically testable. Every selected
experiment states its theory-derived prediction, assumptions, variables, metrics, informative
baselines or controls, uncertainty method, falsification criteria, and planned artifacts. Experiments
test, stress, or potentially contradict theory; they do not prove it.

Use synthetic data matching the theorem for theorem sanity checks, but never present it as validation
of a motivating real system. For application framing, include real-system trajectories or mark the
requirement blocked and narrow the claim. Address calibration, compute, misspecification,
initialization, regime breadth, or baselines only when the claim, significance audit, or selected
strategy makes them informative. Use fixed seeds, multiple trials, uncertainty estimates,
raw JSON/CSV results, recorded configuration, and vector figures. Small public datasets and model
weights may be acquired separately within the approved policy. Execute on CPU using verified local
assets. Existing annotations, lightweight classical fitting, frozen embeddings, and small-model
inference are allowed; new human annotation and neural training are not automatic steps. Synthetic,
real-data-with-artificial-noise, and naturally noisy real-data tests support different conclusions.

Write the strategy before proposals. Let each self-contained experiment choose dimensions suited to
its data and declared paper size; do not stage or depend on a global plotting profile. Propose only
selected experiments, and persist a safe inspection whose script hash exactly matches the code later run.
Execute only through the user's authorized workspace after inspection. Use `run-inspected` for a
pilot and then the full version-2 experiment; it records execution and enforces resource limits.
Use `experiment_resources.py` for acquisition, never a hidden download in an experiment script.
Do not execute unknown remote code or use the legacy arbitrary-command runner. Respect host network
and execution permissions; a policy or approval note cannot override them. Report null and contradictory
results honestly. Re-inspect after every script change.

Record adaptive `coverage_tags` derived from supporting evaluated experiments, not a fixed Boolean checklist.
Preserve contradictory and inconclusive results and state which manuscript claims remain allowed.

When at least one accepted claim is empirically testable, execute and evaluate the selected
experiment unless a concrete resource or feasibility blocker is recorded. A completed or
contradictory empirical program must provide at least one publication-ready main figure, and the
main figures collectively must cover every claim listed in
`visual_evidence_plan.empirical_claim_ids`. If no accepted claim is empirically testable, or all
selected experiments are honestly blocked, do not manufacture an experiment or automatically
substitute a comparison table. Whether the final manuscript benefits from a table is a later
paper-writing judgment, independent of experiment selection.

Use `../../scripts/experiment_tools.py` in this order: `write-strategy`, `propose`,
`inspect-script`, `run-inspected` (pilot, then full experiment), `evaluate`, `register-figure`,
`review-figure`, `emit-figure-tex`, and `finalize`. `audit-figure` may be used before registration. The tool validates
and hashes raw results, scripts, logs, execution outputs, and figures. It preserves replacement
history and performs atomic registry updates. The bounded runner accepts only an inspected Python
experiment, not arbitrary shell commands. Static inspection and offline-library/socket guards are
not an OS security sandbox. Retain manual `record-execution` only for legacy strategies.
Use `mark-blocked` when the selected experiment cannot honestly be run; record what was attempted,
the unavailable resource, and the resulting limitation instead of substituting a weaker experiment.
When a script imports another local helper, pass each file through
`inspect-script --dependency ...`; execution is rejected if any dependency hash changes.

Generate a vector PDF or SVG master and declare `single_column`, `double_column`, or `full_page`.
PNG is a preview or fallback, never a publication-ready master. Register each figure against the
exact evaluated result hash with a substantive caption and alt text. Default to one scientific
question and one panel per figure. Use two-panel main figures only for a direct paired comparison
with a shared scale or axis; do not combine a whole empirical program into one four-panel summary
figure. Split reconstruction checks, scaling behavior, sensitivity analyses, and runtime diagnostics
into separate figures unless their separation would obscure the specific comparison being tested.
Render every vector candidate to a hash-bound PNG at the declared manuscript size and create at
least two meaningfully different design candidates. Open and visually inspect every paper-size PNG
with the available local image-viewing tool; do not infer quality from plotting code, dimensions, or
self-declared scores. Then compare the renderings using the visual
principles extracted from the writing exemplars, then complete schema-v2 `review-figure` under a
fresh or independent reviewer role. Score hierarchy, typography, color, balance, data-ink efficiency,
statistical communication, caption alignment, and cross-figure consistency; every score must be at
least 4 and the mean at least 4.25. Reject crowded legends, unbalanced panels, tiny axes or text, and
excessive whitespace. Use `emit-figure-tex` so figure width is chosen from the venue and declared
size class: spanning figures use `\textwidth`, ordinary two-column papers use `\columnwidth` for
single-column figures, and one-column venues use a reduced text-width fraction for ordinary
single-panel figures. Do not finalize a completed or contradictory program while a main figure
still needs review or while a declared empirically testable claim lacks main-figure coverage.
