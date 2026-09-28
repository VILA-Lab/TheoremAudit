# Adaptive empirical evidence

The empirical stage chooses experiments from the accepted theory, significance risks, available
resources, and intended paper framing. It does not require a fixed taxonomy. Categories such as
scaling, ablation, calibration, real-system evaluation, counterexample search, or misspecification
are optional tags selected only when scientifically relevant.

## Strategy contract

New programs use strategy `schema_version: 2` and a concrete `preflight` on every candidate,
specified in [experiment-resources.md](experiment-resources.md). Add that contract to the common
fields illustrated below. Historical version-1 records remain valid and must not be rewritten.
Version-2 programs require bounded execution receipts; pilot-only evidence is not a completed
experiment. Resource snapshots and hashes are validated again at manuscript handoff.

Record the decision before interpreting results:

```json
{
  "objective": "Test the most important consequences of the accepted claims.",
  "selection_criteria": ["claim relevance", "falsification value", "reviewer value", "feasibility", "non-redundancy"],
  "reviewer_risks": ["..."],
  "candidate_experiments": [{
    "id": "EXP-1", "claim_ids": ["TH-1"], "purpose": "...",
    "expected_information": "...", "feasibility": "...", "selected": true,
    "decision_reason": "..."
  }],
  "selected_experiment_ids": ["EXP-1"],
  "claim_coverage": [{
    "claim_id": "TH-1", "status": "selected", "experiment_ids": ["EXP-1"],
    "rationale": "..."
  }]
}
```

Every accepted claim is accounted for. During candidate comparison a claim may be deferred, but a
completed full-paper strategy may classify it only as `selected` or `not_empirically_testable`.
The selected claim IDs must exactly match `content_architecture.json`'s
`visual_evidence_plan.empirical_claim_ids`; a non-selected claim needs an honest rationale and cannot
claim empirical support.

## Experiment contract

```json
{
  "id": "EXP-1",
  "claim_ids": ["TH-1"],
  "purpose": "...",
  "theoretical_prediction": "...",
  "assumptions_tested": ["A1"],
  "selection_rationale": "...",
  "tags": ["scaling"],
  "design": {
    "substrate": "...",
    "independent_variables": ["..."],
    "dependent_metrics": ["..."],
    "baselines": ["..."],
    "controls": ["..."],
    "seeds": 20,
    "uncertainty_method": "mean plus or minus standard error",
    "falsification_criteria": ["..."]
  },
  "status": "evaluated",
  "evaluation": {
    "verdict": "supports",
    "summary": "...",
    "uncertainty": "...",
    "raw_results_path": "experiments/results/exp-1.json",
    "raw_results_sha256": "...",
    "configuration": {},
    "limitations": ["..."],
    "claim_assessment": "Evidence supports the prediction only in the tested regime."
  }
}
```

Verdicts are `supports`, `contradicts`, `inconclusive`, or `failed`. Experiments can support or
challenge interpretation but never prove a theorem. Final `coverage_tags` are derived from selected
supporting evaluated experiment tags; they are descriptive rather than a universal checklist.

## Evidence registry and execution contract

The mutable working state is `paper/experiments/index.json` with schema version 2. Its strategy,
proposals, script inspections, execution records, evaluations, figures, revisions, and append-only
events form one hash-linked evidence registry. An evaluation is admissible only when:

- the latest safe inspection binds the exact script SHA-256;
- every imported local helper is listed as an inspection dependency and hash-bound;
- the recorded execution refers to that inspection and records command, environment, timestamps,
  exit status, stdout/stderr, outputs, and hashes;
- for strategy v2, a managed receipt binds resources and CPU execution; the final report includes
  `resource_evidence` and `resource_registry_sha256`;
- the selected raw JSON/CSV result is non-empty, structurally valid, declared by that execution,
  and unchanged;
- the evaluation configuration agrees with the planned seed count;
- replacements retain the prior evaluation and state a reason.

`empirical_validation.json` schema version 2 embeds the experiment, inspection, execution, and
figure records and binds itself to the working registry hash.

## Figure contract

Every registered figure records its experiment, evaluated-result hash, file hash, caption, alt
text, panel count, placement, role, and paper size class. Publication masters are PDF or SVG.
Single-panel figures are the default. A multi-panel registration requires a substantive scientific
justification explaining why the panels must be interpreted jointly.
Structural audit checks format, dimensions, paper-scale height, scaling factor, aspect ratio, panel
density, SVG font sizes when available, and effective DPI for PNG. A separate visual review checks
paper-size legibility, correct labels, accessible palette, clipping, and notation consistency.
Schema-v2 visual review also binds at least two vector design candidates and a paper-size PNG rendering
of each by SHA-256, records the selected candidate and rationale, applies at least two visual principles
from the writing exemplars, and declares an independent review mode. Each rendering must bind to its
source vector hash and include a substantive inspection note from viewing it at the declared manuscript
width. It scores visual hierarchy, typography, color design,
layout balance, data-ink efficiency, statistical communication, caption alignment, and cross-figure
consistency. Only a vector master with every design score at least 4, a mean score at least 4.25, and
all structural checks passing is `publication_ready`. Crowded legends, unbalanced panels, tiny axes or
text, or excessive whitespace force revision.

For a completed or contradictory full-paper empirical program, publication-ready main figures must
collectively cover every claim declared empirically testable by the architecture. If no accepted
claim is testable, the empirical artifact is `not_required`. If an experiment is honestly blocked,
preserve completed evaluations and use a blocked-draft handoff only when the existing paper route
explicitly permits incomplete evidence. Do not manufacture an experiment or visual to fill an empty slot.
During manuscript writing, experimental tables may be used when they present recorded results more
clearly than prose or an additional figure.

Application or operational claims may create specific obligations. A real-system claim cannot be
validated only by simulation, and a method requiring an unknown parameter may need a
misspecification study. If the best experiment is unavailable, record `blocked` and narrow the claim
instead of substituting an irrelevant experiment.
