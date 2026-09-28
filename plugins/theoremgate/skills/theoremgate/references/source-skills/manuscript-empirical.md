---
name: empirical
description: "Write the empirical, numerical, or simulation section for a theoretical ML paper. The section title is chosen from the available evidence rather than fixed to Empirical Illustration. Presents valid experimental figures as supporting evidence or sanity checks, without overstating them as proof."
version: 1.3
used_by: manuscript_compiler
---

# Empirical / Numerical Section Writing Skill

## Purpose

Present valid empirical, numerical, or simulation results that help readers interpret the theoretical claims. This section may illustrate a phenomenon, sanity-check a prediction, or show that the theoretical behavior appears in a controlled experiment. It supports interpretation of the results, but it does not replace proof.

Do not force the section to sound weak or apologetic. Use confident but accurate language: experiments can support, illustrate, corroborate, or provide numerical evidence for a phenomenon, but they do not prove a theorem.

## Section title policy

Choose the section title from the actual experimental evidence and venue style. Do not always use "Empirical Illustration."

Conventional, technical, and combined forms are all valid. Use a conventional title such as
`Experiments` when the hierarchy already makes its scope clear; use a technical or combined title
when naming the varied parameter or mechanism helps navigation. For example:

* **Validation-Block Sensitivity Under Heavy Tails** — a controlled parameter sweep.
* **Numerical Separation Between Mean and Median-of-Means Validation** — a theorem-linked simulation.
* **Stopping-Path Length and Certificate Tightness** — an analysis across path sizes.

Do not mechanically elaborate a conventional heading. Reject a title only when it is unclear in
context, inconsistent with the evidence, rhetorical, casual, or promotional.

## Which results may appear

The experiment verdict and figure-quality gate are authoritative. A registered file is not
sufficient on its own.

Gate on `verdict` first:

* `supports` → present it as supporting numerical or empirical evidence.
* `inconclusive` → present it as an informative stress test or uncertainty result when it targets a
  claim declared empirically testable; never present it as support.
* `contradicts` → report it honestly when it targets a declared testable claim. Explain the regime
  carefully and do not spin it as positive.
* `failed` → exclude entirely. This is a failed run, not a scientific result.

The architecture's `visual_evidence_plan` is binding. When it declares empirical claim IDs and the
empirical artifact is `completed` or `contradictory`, the assigned main-text empirical/visual section
must include publication-ready main figures that collectively cover every declared testable claim.
Do not omit that section or move its required visual evidence to the appendix. If no accepted claim
is empirically testable, or every selected experiment is honestly `blocked`, do not fabricate an
experiment or automatically substitute a comparison table. Use experimental tables when they
communicate recorded results, uncertainty, ablations, or regime comparisons effectively.

## Placement policy for non-supporting results

Non-supporting results should be handled transparently and proportionately.

* An `inconclusive` result targeting a declared testable claim belongs in the assigned main-text
  empirical/visual section. Peripheral inconclusive results outside that required coverage may move
  to the appendix.
* A scientifically meaningful `contradicts` result belongs in the main text if it bears on a committed statement's stated scope, challenges the interpretation of a main result, or identifies a regime where the claimed behavior does not appear.
* A `contradicts` result may move to the appendix only if it concerns a peripheral exploratory claim
  outside `visual_evidence_plan.empirical_claim_ids`.
* Do not hide a contradicting result in the appendix merely because it is inconvenient.
* When reporting a contradicting result, describe the regime precisely and state what interpretation it limits. Do not use it to invalidate more general theory unless the recorded result supports that conclusion.

## Do not assume the data type

Do not hardcode "synthetic data." Describe the experimental setup only as recorded in the experiment's `result_summary`, `explanation`, or metadata.

Use words such as "synthetic," "real," "simulation," "benchmark," or "controlled experiment" only if the record supports them.

If the setup is not described in the state, describe only what is known. Do not invent parameters, sample sizes, datasets, model sizes, compute, or data sources.

## Content rules

* Include only figures whose experiment passed the verdict gate and whose figure status is
  `publication_ready`; diagnostic or unreviewed figures never enter the manuscript.
* Include the emitted LaTeX snippet for each required main figure rather than reconstructing its
  path, size, caption, or label by hand.
* Connect each figure explicitly to its experiment's accepted `claim_ids`; the included main figures
  must collectively cover every claim in `visual_evidence_plan.empirical_claim_ids`.
* Use the registered `size_class`, `placement`, `path`, caption, and alt text. Do not silently resize
  a single-column figure into an unreadable multi-panel layout.
* Use empirical results to support interpretation, not to prove theoretical claims.
* Be honest about inconclusive or contradicting results; do not hide them if they materially affect interpretation.
* Describe the setup clearly using recorded fields only.
* Do not overstate the strength of small or diagnostic experiments.
* Do not include experimental infrastructure details such as Docker, runtime systems, or internal pipeline behavior.

## Pre-writing check

Before writing the section, silently identify:

* which empirical results pass the verdict gate;
* which figures are registered and usable;
* which committed statement each result targets;
* whether any inconclusive or contradicting result materially affects the paper's main claims;
* whether non-supporting results belong in the main text or appendix under the placement policy;
* which scientific object, varied parameter, and theoretical phenomenon the title should name;
* whether the included main figures collectively cover every declared testable claim;
* whether any included experimental table is accurate, concise, and readable at final manuscript size.

Do not expose this check in the paper.

## Structure

Use the following structure flexibly:

1. Setup paragraph — describe the model, data, regime, and varied quantities actually recorded.
2. Results paragraph or figure discussion — for each qualifying figure, explain what is plotted and how it relates to the target statement.
3. Interpretation paragraph — summarize what the experiments support, using calibrated language.

For short theory papers, one compact paragraph plus one figure may be enough. Do not inflate the section.

## Figure citation format

Cite each figure with `\ref{<label>}` using the figure entry's actual `label` field. Do not assume a `fig:ecN` naming scheme.

Each figure caption must:

* describe what is plotted, using the figure's `caption` or the result's `suggested_caption`;
* state which committed statement or theoretical phenomenon it relates to, without exposing internal IDs if they are not reader-facing;
* give one sentence of interpretation;
* avoid claiming that the figure proves the theorem or proposition.


## Internal IDs — never expose them

The proof sources may contain internal identifiers such as:

* `PO-3`
* `GAP-PO5-01`
* `CHECK-PO-4-02`
* `D1`, `D4`
* `repair_requested`
* `proposition_ready`
* `theorem_ready`
* `new_status`
* `paper_label`
* `Arbiter`
* `TheoremAudit`

Never print these identifiers in the proof appendix.

Translate every internal reference into a public mathematical description, public theorem label, public assumption label, or ordinary prose.

## Language calibration

Use:

* "the numerical results support..."
* "the simulation illustrates..."
* "the observed trend is consistent with..."
* "the experiment provides a sanity check for..."
* "the figure shows the predicted qualitative behavior..."
* "in this regime, the observed behavior differs from the predicted trend..."
* "this suggests that the phenomenon is sensitive to..."

Avoid:

* "the experiment proves..."
* "we verify the theorem experimentally..."
* "this confirms the theory in general..."
* "state-of-the-art empirical performance..."
* "comprehensive experiments..." unless the section truly contains them.
* "the contradictory result is merely noise" unless the record supports that interpretation.

## What to draw from inputs

* `experiments` — use `purpose`, `theoretical_prediction`, `design`, `evaluation`, and `claim_ids`
* `figures` — use only `publication_ready` records and preserve `path`, `caption`, `label`,
  `size_class`, `placement`, and `results_sha256`
* committed statements from `theorem_state` — use them to explain what each empirical result supports or challenges
* venue/template metadata — use it to decide whether the title should be fixed or chosen dynamically

## What NOT to do

* Do not include any `failed` experiment.
* Do not claim experiments prove mathematical statements.
* Do not hide inconclusive or contradicting results if they target a declared testable claim or
  materially affect interpretation.
* Do not omit a planned empirical/visual section whose completed or contradictory evidence covers
  declared testable claims.
* Do not substitute an irrelevant experiment or an automatic comparison table for honestly absent
  empirical evidence.
* Do not bury a central contradicting result in the appendix.
* Do not label data "synthetic," "real," or "simulation" unless the record says so.
* Do not use figures not registered in `figures`.
* Do not invent experimental settings, parameters, datasets, sample sizes, compute, or model details.
* Do not describe internal experimental infrastructure.
* Do not force the section title to be "Empirical Illustration."
