---
name: exploration
description: "Explore a discovery's PRIMARY TARGET before any proving begins — probe tractable special cases analytically and with quick numerical sweeps to confirm the phenomenon is real, locate the boundary, and catch a special case that breaks the target early. Produces exploration.json seeding the proof effort. Runs after the discovery is written and before the Method Team. Distinct from empirical-experiments, which runs post-commit on already-committed claims."
version: 1.0
used_by: explorer
domain: theoretical machine learning
inputs: discovery.json
outputs: exploration.json (via write_artifact)
---

# Exploration — probe the primary target before proving

## Why this skill exists
A mathematician does not start proving a theorem cold. They first *play with it*: plug in the
easy special cases, run a quick simulation, and watch where the phenomenon appears and where it
breaks. Only then do they commit to a statement worth proving. This skill is that play stage.

You are handed a **discovery** with a designated **`primary_target`** — the one tractable result
the Method Team will try to prove first. Your job is to pressure-test that target *empirically and
analytically* so proving starts from something calibrated and real, not a guess. This runs
**before** the Method Team. It is NOT paper-figure generation (that is `empirical-experiments`,
which runs after commit on committed claims).

## What you are trying to learn
For the `primary_target` (and only the primary target — ignore stretch targets):

1. **Is the phenomenon real?** In the cleanest special case the target predicts a behavior — does
   it actually appear?
2. **Where is the boundary?** If the target is a threshold / regime statement, locate roughly
   where behavior transitions (the exponent, constant, or regime edge). This calibrates the
   statement the Method Team should aim at.
3. **Does a special case break it?** Actively look for a tractable instance *satisfying the stated
   assumptions* where the predicted behavior fails. Finding one now — before proving — is a win:
   it tells the Method Team to narrow the target or add an assumption.

## How to probe

### Analytical probes (always do these)
Work the special cases where the target quantity has a closed form or an obvious answer:
- degenerate signal (e.g. `θ* = 0`), isotropic / identity structure, tiny finite dimension,
  extreme parameter values.
Compute the target quantity by hand in each and compare to what the primary target predicts.
State the comparison explicitly. No code needed.

### Numerical probes (do 1–3 quick ones)
Use `run_experiment` for short synthetic sweeps that generate data **exactly satisfying the
discovery's stated assumptions** (the design distribution, covariance/spectrum, signal, noise from
the Setting), then sweep the key quantity and measure the predicted behavior.

Rules for numerical probes:
- **Quick and small**: each must run in well under a minute on CPU. Small dimensions, few seeds.
- **Self-contained**: the `code` imports everything, sets a fixed seed, prints a short summary,
  and exports a module-level `METRICS` dict with the key numbers.
- **Targeted**: each probe tests the primary target, not a vague proxy.
- Prefer the discovery's own `empirical_checks` as starting points if they probe the primary
  target; otherwise design your own.
- **Degrade gracefully**: if `run_experiment` returns an error (no sandbox, missing package,
  timeout), record the probe as `kind:"numerical"`, `result:"could not run: <error>"`, and fall
  back to the analytical probe for that question. NEVER let a failed experiment stop you from
  writing `exploration.json`.

## Reaching a verdict
After the probes, judge the primary target:
- **`reachable`** — special cases confirm it; proceed to prove it as stated.
- **`narrow`** — it holds only in a sub-regime; recommend the concrete restriction (e.g. "hold to
  Gaussian design", "state one-sided bound only").
- **`reshape`** — a special case within the assumptions breaks it; recommend the concrete change
  (add/tighten an assumption, or change the result type).
- **`blocked`** — even the cleanest special case fails and no restriction saves it; flag for the
  Lab Lead.

Be honest and specific. A `narrow`/`reshape` verdict with a concrete recommendation is the most
valuable outcome — it saves the Method Team from proving the wrong statement.

## Write exploration.json
Call `write_artifact` with `name="exploration.json"` and this shape, then call `task_complete`:

```json
{
  "primary_target": "T1",
  "probes": [
    {
      "id": "X1",
      "kind": "analytical | numerical",
      "special_case": "e.g. theta*=0, isotropic Sigma, p=200, n=100",
      "question": "what about the primary target this probe tests",
      "method": "closed-form computation | run_experiment sweep over alpha",
      "result": "what was observed (numbers / behavior)",
      "supports_primary_target": "yes | no | partial",
      "notes": "boundary location, constant, or caveat"
    }
  ],
  "boundary_findings": "Where behavior transitions, if located (else 'not located')",
  "verdict": "reachable | narrow | reshape | blocked",
  "recommendation": "Concrete next-step for the Method Team: keep as-is / narrow to <regime> / reshape to <form> / blocked because <reason>",
  "experiments_run": ["X2", "X3"],
  "notes_for_prover": "Anything that will make the proof easier (which special case to start from, which term dominates)"
}
```

## What NOT to do
- Do NOT try to prove anything — you explore, the Method Team proves.
- Do NOT run long or large experiments — quick CPU sweeps only.
- Do NOT test stretch targets — only the primary target.
- Do NOT skip the analytical probes just because a numerical one ran.
- Do NOT fail to write exploration.json — always produce it, even if every experiment errored
  (fall back to analytical reasoning and say so).
- Do NOT overclaim: a simulation that looks benign is evidence, not proof. Keep the verdict about
  what to *aim* at, never "the theorem holds".
