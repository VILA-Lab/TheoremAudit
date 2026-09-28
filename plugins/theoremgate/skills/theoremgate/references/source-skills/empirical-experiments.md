---
name: empirical-experiments
description: "Adaptively select and run publication-quality experiments that test committed theoretical results. Emphasizes claim linkage, falsification value, statistical rigor, honest contradictions, and figures that pass review."
version: 1.0
used_by: experimenter
---

# Empirical Experiments — Publication Quality

The experiments must look like they belong in a top-venue paper. One toy arithmetic check,
one weak correlation, or one single-run curve gets the paper rejected. Design for a skeptical
reviewer.

## Principle: choose experiments; do not fill a checklist

Generate plausible experiments from committed claims and reviewer risks, then select the most
informative feasible non-redundant set. The best test may be a simulation, scaling sweep, ablation,
benchmark, real-system study, qualitative diagnostic, counterexample search, or something specific
to the domain. Do not require a category merely because it is common at a venue.

## Principle: every experiment tests a COMMITTED claim
Do NOT test vague proxies. Each experiment must directly probe a committed result:
- A positive proposition (e.g. a diagonal-model risk bound) → plot the *actual* excess risk
  against the quantity the proposition controls, and show the predicted behavior holds.
- A separation/counterexample → construct the two explicit instances and show the gap
  concretely (e.g. matched spectra, different alignment → visibly different peaks).
If a natural proxy correlates weakly (e.g. |corr| < 0.2), that is a real finding — report
it honestly, but do NOT base the empirical conclusions on it. Lead with the experiment that
demonstrates the committed claim cleanly.




## Principle: the main experiment must show a phenomenon, not only verify arithmetic

Experiments are not merely arithmetic checks of theorem formulas.

A formula check may confirm that code implements a derived expression correctly, but it is
usually not enough for a paper experiment. The main experiment should make the theoretical
phenomenon visible to a skeptical reader.

The following are useful optional tags, not an exhaustive or mandatory taxonomy:

- **phenomenon_simulation**: simulates the theorem's setting and shows the predicted qualitative behavior;
- **theorem_stress_test**: varies parameters to show where the theorem's prediction holds or breaks;
- **counterexample_visualization**: constructs the counterexample/separation and visualizes the gap;
- **estimator_comparison**: compares two estimators, models, decoding rules, or algorithms;
- **phase_transition**: sweeps a key parameter and shows a threshold/saturation behavior;
- **sanity_check**: verifies arithmetic, implementation, or a direct formula.

When figures are appropriate, a main figure should normally expose a phenomenon through one of:

- phenomenon_simulation;
- theorem_stress_test;
- counterexample_visualization;
- estimator_comparison;
- phase_transition.

A `sanity_check` alone is not sufficient unless the committed result is explicitly and only
a computational identity.

Bad experiment:
- plug numbers into a theorem bound and check equality;
- verify that two algebraic expressions match numerically;
- plot a single curve with no comparison or regime contrast.

Good experiment:
- simulate multiple regimes and show the phenomenon predicted by the theorem;
- visualize a separation or counterexample;
- compare independent versus correlated errors;
- show saturation as a sample budget increases;
- compare a proposed estimator/decision rule against a baseline.

Every experiment plan must explicitly state:

1. an informative experiment type or domain-specific tag;
2. phenomenon being tested;
3. committed claim it supports or challenges;
4. independent variable(s);
5. dependent metric;
6. baselines or regimes compared;
7. expected qualitative pattern;
8. figure/table to generate.

The completed full-paper strategy cannot leave an accepted claim deferred. It classifies each claim
as selected or not empirically testable and must match the manuscript architecture's
`visual_evidence_plan`. Execute only scientifically relevant selected experiments. If none is
testable, or execution is honestly blocked, omit the visual rather than manufacturing an experiment
or comparison. When experiments produce exact numerical results that are clearer in rows and
columns, emit a publication-quality table candidate alongside or instead of a figure as appropriate.


### Example: test-time scaling / repeated reasoning samples

For a theorem about repeated reasoning samples, the main experiment should not merely check
a binomial formula.

A good phenomenon-level experiment is:

- experiment_type: phenomenon_simulation or phase_transition;
- independent variable: number of sampled reasoning traces `k`;
- dependent metric: majority-vote accuracy;
- regimes compared:
  1. independent errors;
  2. correlated latent failure mode;
  3. systematic bias;
- expected pattern:
  - independent errors improve with `k`;
  - correlated errors saturate;
  - systematic bias does not vanish with more samples;
- figure:
  - x-axis: number of samples `k`;
  - y-axis: accuracy;
  - one curve per regime with mean ± standard error over seeds.

A binomial probability check may be included as a sanity check, but it cannot be the only
experiment.



## FIRST decide the experimental substrate (what data / what to run on)
Before writing any experiment code, decide *what the experiment runs on*. For a theory
paper this is a deliberate choice, not an afterthought. Pick per the committed claim:

- **Synthetic data generated from the paper's own model — the default for most theory
  papers.** Use this when the committed claim is about a precise mathematical setting whose
  assumptions can be simulated directly. The cleanest test generates data that *exactly
  satisfies the stated assumptions* (the design distribution, covariance/spectrum,
  signal/source condition, and noise model named in the Setting), then sweeps the key
  quantity and measures the predicted behavior — it removes confounds and matches the
  hypotheses the theorem requires. Generate it in-code with a fixed seed. (Some claims are
  genuinely about real-data behavior or specific representations — in that case use a real
  dataset below, but only if the claim truly needs it.)

- **A real dataset:** identify a suitable existing corpus, inspect labels and sampling structure,
  and check licensing, provenance, and resource requirements before selecting it. Register local
  files or acquire small pinned public assets with `experiment_resources.py`. Existing annotations
  may suffice; never assume new human annotation is available. A necessary but unavailable study
  is blocked, not completed or intrinsically untestable. Simulations alone do not establish
  application claims that require real-data evidence.

- **A pretrained model:** use a small model only when scientifically relevant. Acquire supported
  weights and configuration within the approved budget, then use local files for CPU inference or
  frozen representations. Do not execute remote code or perform neural training automatically.

**Resource policy:** follow `../experiment-resources.md`. Acquisition is separate from execution;
permission to use a resource does not bypass host network/OS permissions. Execute the inspected
script on CPU, first as a small pilot, with time and memory monitoring. Record seeds, dataset/model
revisions, sampled example identifiers, configuration, and hashes. Larger needs require approval.
Small experiments still need adequate statistical power or an honest inconclusive verdict.

**State the data-generating process explicitly** in both the code and the figure caption
(distribution, covariance/spectrum, n, d, noise, seeds) so a reader can reproduce it and
see that it matches the theorem's assumptions.

## Statistical rigor (non-negotiable for review)
- **Multiple seeds**: default to ≥ 20 random seeds for cheap simulations. For expensive
  experiments, use the largest feasible number, but NEVER present a single noisy run as support.
- **Error bars / bands**: plot mean ± standard error (or a 90% band). A curve with no
  uncertainty is not acceptable evidence.
- **Sweep the key variable**: vary the quantity of interest (sample size n, aspect ratio
  n/d, alignment, eigenvalue decay) across a meaningful range, including the interpolation
  threshold n=d where the phenomenon lives.
- **Controls**: include a baseline / null condition so the effect is attributable.
- **Report exact numbers**: "peak risk 3.2× the ridge-optimal at n=d" — not "higher risk".

## Figure quality (what makes it look professional)
Write the experiment code to produce vector PDF figures with:
- Clear axis labels WITH units/symbols matching the paper's notation (e.g. `$n/d$`,
  `excess risk $\mathcal{E}(\hatβ)$`), and a title-free figure (caption carries the title).
- A legend when >1 series; distinguishable lines (color + linestyle, not color alone).
- Readable font sizes (≈ 11–14 pt), `figsize` ~ (5,3.5) per panel, `dpi=300`,
  `bbox_inches='tight'`, saved as `.pdf`.
- Choose dimensions for the evidence and final manuscript size instead of inheriting a global
  plotting preset. Default to one scientific question and one panel per figure. Several curves may
  share that panel when they answer the same comparison. Use two-panel main figures only for direct
  paired comparisons with a shared scale, axis, or side-by-side interpretation. Do not collapse
  reconstruction checks, scaling behavior, sensitivity analyses, and runtime diagnostics into one
  four-panel main figure; split them into separate figures unless one joint view is scientifically
  necessary and record what comparison would be lost otherwise.
- No chartjunk: no gridlines-everywhere, no default matplotlib clutter.

## Experiment code requirements
Each experiment must produce, from a single runnable script (no notebook state, no manual
steps, no hidden files):
- **fixed random seeds** set at the top;
- **saved raw results** as `.json` or `.csv` (the numbers behind every plotted point);
- **saved figure files** as `.pdf`;
- **recorded configuration metadata** (n, d, spectrum, seeds, sweep values) alongside results;
- a **short result summary** printed/returned for `evaluate_result` to judge.

The script must be self-contained and reproducible: running it again with the same seeds
reproduces the same numbers and figures.

## How many figures
Enough to be convincing, each tied to a claim. **One strong figure may suffice** for a short
theory paper or a single focused numerical illustration. Use **2–4 main figures** when the
empirical evidence spans multiple claims or regimes (e.g. a separation demonstration, a
risk-vs-parameter sweep, a sanity check), with extras in the appendix.
For completed or contradictory evidence, the publication-ready main figures must collectively cover
every claim declared empirically testable in the architecture.

## Honest evaluation
Use `evaluate_result` truthfully: `supports` only if the run cleanly demonstrates the
prediction, `inconclusive`/`contradicts` otherwise. A `bug_in_code` run (crashed, no valid
metrics) is NOT includable — fix it and rerun before `save_figure`.

## Captions
Each `save_figure` caption states: what is plotted, the setup (n, d, spectrum, seeds), and
one sentence of interpretation tying it to the committed claim — in normal paper prose, no
internal IDs (PO-N, EC-N).

## Runtime constraints (Codex plugin)

Inspect scripts and dependencies, then use the bounded `run-inspected` CPU runner for version-2
strategies. It binds executions to inspected code and resources, preserves logs, and monitors time,
process-group memory, and declared output sizes. These are guardrails, not an OS security sandbox.
Do not assume a Docker image, cache, or dependency exists. Legacy evidence remains readable; use
the normal experiment-revision path rather than overwriting completed experiments.
