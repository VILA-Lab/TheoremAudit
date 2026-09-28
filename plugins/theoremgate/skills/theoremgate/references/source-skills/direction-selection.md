---
name: direction-selection
description: "Evaluate candidate theoretical ML directions from backup_directions.json and select the strongest one. Scores feasibility, novelty, failure-resistance, impact, assumption realism, consequence, and seed alignment. Performs fetched-only literature checks before finalizing."
version: 2.0
used_by: lab_lead
domain: theoretical machine learning
inputs: backup_directions.json, optional user constraints, optional literature-search tools
outputs: selected_direction.json via write_artifact
---

# Direction Selection — Theoretical ML

## Purpose

Audit and carry forward a single user-specified direction, or select the strongest theoretical ML
direction when `direction-generation` produced genuine alternatives.

The goal is not to choose the most impressive-sounding idea. The goal is to choose a direction that is:

* faithful to the user's research seed;
* mathematically meaningful;
* plausibly provable;
* resistant to obvious mathematical failure modes;
* not already subsumed by prior work;
* strong enough to support a substantive theory contribution if it succeeds.

This skill runs before `discovery`. It selects a direction; it does **not** write `discovery.json`, prove results, or commit to exact theorem statements, rates, constants, or assumptions.

The selected direction remains a **question-to-attempt**, not a theorem or claimed result. The final theorem is written later by synthesis to fit what is actually proved.

## Single-candidate path

When `backup_directions.json` contains one candidate because the user specified a clear direction:

* do not invent alternatives or perform a comparative contest;
* check literature, feasibility, falsifiability, assumption risk, and likely proof routes;
* select that same candidate and preserve every explicit user-requested component in the handoff;
* use prior-work conflicts to calibrate novelty and guide discovery, not to replace the topic;
* if the complete request may be infeasible or already known, record that limitation and let discovery,
  proof development, and later audits determine the strongest supported form transparently.

Scoring may still summarize risk for the audit record, but it must not be used to drop or split the
user's direction. Comparative scoring and winner selection apply only when multiple alternatives were
appropriately generated.

## Inputs

Use:

* `backup_directions.json`;
* user constraints, if provided;
* `input_specificity`, `preserved_user_constraints`, and `introduced_choices_summary` from `backup_directions.json`;
* each direction's `direction_question`, `core_hypothesis`, `mathematical_setting`, `proof_approach`, `novelty_hypothesis`, `risk`, `feasibility`, and `expected_contribution_if_successful`;
* available literature-search tools, if present.

Do not assume fields that do not exist. In particular:

* use `novelty_hypothesis.search_queries` and `novelty_hypothesis.suspected_gap`;
* do not require a `novelty.closest_prior` field;
* do not assume novelty is verified unless search/fetch has actually verified it.

## Pre-selection check

Before scoring, silently identify:

* the user's original research seed and intent;
* the input specificity: vague, partial, or fully specified;
* which user-provided constraints must be preserved;
* whether each direction stays faithful to the user's seed;
* whether each direction introduces unnecessary drift;
* whether introduced choices are justified for vague inputs;
* the mathematical object, property, regime, and result type of each direction;
* the likely proof path and main technical risk;
* the main mathematical failure mode for each direction;
* which directions are too vague to evaluate;
* which directions require literature checking before selection.

Use this check silently. Do not expose it in the artifact except through scores, justifications, and selection rationale.

## Evaluation framework

Score each direction on seven axes from 1 to 5.

### 1. Mathematical feasibility

Is there a visible path toward a theorem using known or plausibly adaptable tools?

* `5` — standard techniques clearly apply.
* `4` — requires a nontrivial combination of known tools, but the path is plausible.
* `3` — requires a new technical idea, but the direction of the idea is visible.
* `2` — would require major new machinery with no clear route.
* `1` — no plausible proof strategy is visible.

Directions with feasibility `<= 2` are normally disqualified unless the user explicitly requested high-risk exploration.

### 2. Novelty evidence

Does the direction appear to add something not already covered by known literature?

* `5` — search finds no close coverage of the setting/result type and the gap appears clear.
* `4` — related work exists, but the direction targets a genuinely different regime, object, assumption set, or result type.
* `3` — partially overlaps with known work but may still offer a meaningful refinement, extension, restriction, or new framing.
* `2` — likely marginal; prior work appears to cover most of the contribution.
* `1` — literature check suggests the direction is already known or only superficially different.

Novelty is evidence-based, not guessed. If no literature search is available, mark novelty as provisional and avoid overconfident claims.

### 3. Failure-resistance

How likely is the direction to survive obvious mathematical failure modes, assumption challenges, and counterexample search?

* `5` — carefully scoped; assumptions likely standard or defensible; no obvious counterexample regime.
* `4` — one visible vulnerability, but a clear weakening or scope path exists.
* `3` — assumptions are aggressive or fragile; likely needs weakening.
* `2` — likely counterexample, vacuity, or major scope issue; needs restructuring.
* `1` — almost certainly false, circular, vacuous, or impossible in the intended regime.

Do not select a direction with failure-resistance `<= 2` unless there is a clear repair or weakening path and no better option.

### 4. Theoretical impact

Would the result matter if true?

* `5` — resolves an important open question, establishes a tight bound, proves a strong separation, gives a sharp characterization, or enables downstream theory.
* `4` — significant theoretical contribution in an active area.
* `3` — solid contribution that advances understanding in a sub-area.
* `2` — technically valid but narrow or unlikely to influence later work.
* `1` — true but uninteresting, mostly cosmetic, or unlikely to be useful.

Avoid venue-specific claims such as “would be accepted at ICML.” Judge scientific contribution, not acceptance probability.

### 5. Seed alignment

Does the direction preserve the user's original intent and constraints?

* `5` — directly preserves the user's object, property, regime, or clearly stated intent.
* `4` — faithful to the seed with minor introduced specificity.
* `3` — plausible descendant of the seed but with noticeable narrowing or reframing.
* `2` — weakly related; may be a drift from the user's intent.
* `1` — mostly ignores the seed or replaces it with a different problem.

For vague seeds, introduced specificity is acceptable if it is recorded and justified. For fully specified questions, unnecessary drift should sharply reduce this score.

### 6. Assumption realism

Do the assumptions preserve the phenomenon that motivates the question, and can they be interpreted or
tested in the intended application? A technically convenient assumption bundle should score poorly when
it removes the central source of difficulty. Stacked restrictions require a clear scientific payoff.

### 7. Practical or conceptual consequence

If successful, would the result change an algorithmic decision, explain an important mechanism, sharpen
a widely used guarantee, rule out a plausible approach, or reorganize how the problem is understood?
Distinguish a useful negative result from a technically correct curiosity.

## Weighted scoring

Use:

```text
weighted_total =
  1.5 * feasibility
+ 1.5 * novelty_evidence
+ 1.5 * failure_resistance
+ 2.0 * theoretical_impact
+ 1.5 * assumption_realism
+ 1.5 * practical_or_conceptual_consequence
+ 1.0 * seed_alignment
```

Maximum score is `52.5`.

Feasibility and failure-resistance remain hard constraints, but impact and consequence must distinguish
a substantive contribution from a safe restricted exercise. Assumption realism prevents mathematical
convenience from silently erasing the motivating phenomenon.

## Step 1 — Preliminary scoring

Score every direction on all seven axes using the information in `backup_directions.json`.

For a single user-specified candidate, these scores are diagnostic only. They do not authorize replacing,
splitting, or silently narrowing the direction before discovery.

For each score, give a one-sentence justification.

If a direction is too vague to score, assign lower feasibility and explain what is missing.

If a direction drifts away from the user's seed, lower `seed_alignment` and explain the drift.

If a direction has a clear failure mode without a repair path, lower `failure_resistance`.

## Step 2 — Select top candidates for literature checking

If there is one user-specified candidate, check that candidate and continue to Step 3.

If there are multiple genuine alternatives, select the top 2 candidates by preliminary weighted score.

If preliminary scores are close, or a third candidate has higher novelty/impact but uncertain feasibility, include the third candidate in the literature check.

Do not finalize selection before the literature check unless no search/fetch tools are available.

## Step 3 — Literature check

Use available search/fetch tools only. Do not rely on memory.

For each checked candidate, use:

* `novelty_hypothesis.search_queries`;
* the mathematical object + property + regime;
* the proof strategy + setting;
* the suspected gap and likely related areas;
* the expected contribution if successful.

Search for:

* closest prior theoretical results;
* lower bounds or impossibility results;
* results in the same model/regime;
* results using similar proof tools;
* surveys or canonical papers, if helpful.

Fetch relevant results before using them. A paper may affect novelty scoring only if it was actually fetched or already exists in trusted pipeline context.

For each fetched paper, check:

* Does it study the same object?
* Does it prove the same type of result?
* Does it cover the same regime?
* Are the assumptions comparable?
* Does it subsume, partially overlap with, or merely relate to the direction?
* Does it leave a smaller but still meaningful gap?

If no search/fetch tool is available, record that the novelty check is provisional and set the literature-check conclusion to `unknown`. Do not pretend novelty is verified.

## Step 4 — Update novelty and total scores

After the literature check, update the novelty score for checked candidates.

Use:

* `clear` — no close overlap found; direction appears viable.
* `partial-overlap` — related work exists, but the direction may still be distinct.
* `conflict` — a fetched result appears to cover the proposed direction.
* `unknown` — search/fetch was unavailable or inconclusive.

If a conflict is found, either disqualify the direction or rewrite its selection rationale around a clear distinction. Do not ignore the conflict.

If only a narrower gap remains after the literature check, lower the novelty score and record the narrowed gap.

Recompute `weighted_total` after updating novelty.

## Step 5 — Apply selection rules

For a single user-specified candidate, select it after the checks above. Record conflicts, risks, and likely
weakening paths without changing the requested direction; later governed stages decide what is provable.

For multiple genuine alternatives, use the following rules:

Use the following rules:

1. Disqualify directions with feasibility `<= 2`, unless the user explicitly requested high-risk exploration.
2. Disqualify directions whose literature check yields an unresolved `conflict`.
3. Avoid selecting directions with failure-resistance `<= 2` unless a clear weakening path exists and no better option is available.
4. Avoid selecting directions with seed alignment `<= 2` unless the user's seed was extremely vague and the introduced specificity is well justified.
5. Do not select a direction with theoretical impact or practical/conceptual consequence `<= 2` for a full paper when a feasible higher-impact alternative remains.
6. A direction with assumption realism `<= 2` requires an explicit explanation of why the restricted regime still teaches something important and a credible extension path.
7. Among remaining candidates, select the highest weighted total after novelty update.
8. Tiebreaker 1: prefer higher theoretical impact and consequence.
9. Tiebreaker 2: prefer higher assumption realism.
10. Tiebreaker 3: prefer higher failure-resistance and feasibility.
11. Tiebreaker 4: prefer higher seed alignment and a clear minimum viable result.
12. If the best direction has a known weakness, include the first weakening or repair path.
13. Candidate ID and list position carry zero weight. Mentally permute candidate order and confirm the
    same winner; if the winner changes only because it appeared first, rescore before selection.

The selected direction must remain a direction-to-attempt, not a claimed theorem.

## Step 6 — Write selected_direction.json

Call `write_artifact` with `name="selected_direction.json"` and this structure:

```json
{
  "round": 1,
  "artifact": "selected_direction",
  "domain": "theoretical ML",
  "input_specificity": "vague | partial | fully_specified",
  "preserved_user_constraints": ["constraints inherited from backup_directions.json"],
  "introduced_choices_summary": "summary inherited from backup_directions.json, if any",
  "selected": {
    "...": "full selected direction object"
  },
  "scores": {
    "direction-id": {
      "feasibility": 4,
      "novelty_evidence": 4,
      "failure_resistance": 3,
      "theoretical_impact": 4,
      "assumption_realism": 4,
      "practical_or_conceptual_consequence": 4,
      "seed_alignment": 5,
      "weighted_total": 42.5,
      "justifications": {
        "feasibility": "one sentence",
        "novelty_evidence": "one sentence",
        "failure_resistance": "one sentence",
        "theoretical_impact": "one sentence",
        "assumption_realism": "one sentence",
        "practical_or_conceptual_consequence": "one sentence",
        "seed_alignment": "one sentence"
      },
      "selection_status": "selected | runner_up | disqualified",
      "disqualified": false,
      "disqualification_reason": null
    }
  },
  "literature_checks": {
    "direction-id": {
      "queries_run": ["query 1", "query 2"],
      "papers_fetched": [
        {
          "title": "paper title",
          "url": "fetched URL",
          "relationship": "closest prior | partial overlap | background | lower bound | unrelated after inspection"
        }
      ],
      "finding": "What was found for this candidate",
      "conclusion": "clear | partial-overlap | conflict | unknown",
      "overlap_detail": "If partial-overlap or conflict, describe exactly what is already known",
      "remaining_gap": "If distinct after overlap, describe the remaining gap precisely"
    }
  },
  "why_selected": "One paragraph explaining why the selected direction is strongest.",
  "why_not_others": "One paragraph explaining why runner-up directions were not selected.",
  "weakening_note": "If the selected direction has known risks, note the first weakening or repair path.",
  "minimum_viable_result": "The smallest still-substantive result this direction could support if the ambitious form fails.",
  "novelty_caveat": "State whether novelty is verified by fetched sources or still provisional.",
  "handoff_to_discovery": {
    "selected_direction_id": "direction-id",
    "what_discovery_should_preserve": ["object", "property", "regime", "user constraints"],
    "what_discovery_should_be_careful_about": ["main failure mode", "fragile assumption", "possible prior-work overlap"],
    "first_weakening_to_try_if_needed": "repair path"
  }
}
```

## Quality checklist

* Every candidate direction was scored on all seven axes.
* Scores are calibrated, not uniformly optimistic.
* Feasibility and failure-resistance are treated as hard constraints.
* Seed alignment is considered, especially for fully specified user inputs.
* Literature check uses fetched sources only.
* Novelty is updated after literature checking.
* Conflicts are not ignored.
* If novelty is unknown, the artifact says so clearly.
* The selected direction is still a question-to-attempt, not a finalized theorem.
* The output does not write `discovery.json`.
* The output preserves enough information for `discovery` to build a formal research map.
* The selected direction remains recognizable from the user's research seed.
* A single user-specified candidate is passed through intact after literature and feasibility checks.
* Any introduced specificity is justified.
* The selected direction has a plausible minimum viable result or weakening path.
* The handoff to discovery identifies what to preserve and what to be careful about.

## What NOT to do

* Do not select a direction because it sounds impressive.
* Do not skip literature checking when search/fetch tools are available.
* Do not fabricate prior work, citations, or novelty claims.
* Do not rely on memory for novelty judgments.
* Do not assume nonexistent fields such as `novelty.closest_prior` or `core_claim`.
* Do not select a direction with feasibility `<= 2` unless explicitly doing high-risk exploration.
* Do not select a direction with an unresolved literature conflict.
* Do not select a direction with failure-resistance `<= 2` without a clear repair path.
* Do not select a direction that drifts away from the user's seed without justification.
* Do not write `discovery.json`; that belongs to the discovery skill.
* Do not commit to exact rates, constants, final theorem statements, or assumptions at this stage.
* Do not present the selected direction as already novel unless fetched sources support that claim.
* Do not present the selected direction as already true.
* Do not replace or split a clear user-specified direction because another topic appears easier.







<!-- ---
name: direction-selection
description: "Evaluate candidate theoretical ML research directions and select the strongest one. Scores directions on feasibility, novelty evidence, attack-resistance, and theoretical impact. Performs fetched-only literature checks for top candidates before finalizing. Must be called after direction-generation."
version: 1.1
used_by: lab_lead
domain: theoretical machine learning
inputs: backup_directions.json, optional user constraints, optional literature-search tools
outputs: selected_direction.json via write_artifact
---

# Direction Selection — Theoretical ML

## Purpose

Select the strongest theoretical ML research direction from the candidate directions produced by `direction-generation`.

The goal is not to choose the most impressive-sounding idea. The goal is to choose a direction that is mathematically meaningful, plausibly provable, resistant to obvious attacks, and not already subsumed by prior work.

This skill runs before theoretical planning. It selects a direction; it does not write `discovery.json` or commit to exact theorem statements, rates, constants, or assumptions.

## Inputs

Use:

* `backup_directions.json`;
* user constraints, if provided;
* each direction's `core_claim`, `mathematical_setting`, `proof_approach`, `novelty_hypothesis`, `risk`, and `feasibility`;
* available literature-search tools, if present.

Do not assume fields that do not exist. In particular, use `novelty_hypothesis.search_queries` and `novelty_hypothesis.suspected_gap`; do not require a `novelty.closest_prior` field.

## Pre-selection check

Before scoring, silently identify:

* the user's original research intent;
* whether each direction stays faithful to that intent;
* the mathematical object, property, regime, and result type of each direction;
* the likely proof path and main technical risk;
* which directions are too vague to evaluate;
* which directions require literature checking before selection.

Use this check silently. Do not expose it in the artifact except through scores and justifications.

## Evaluation framework

Score each direction on four axes from 1 to 5.

### 1. Mathematical feasibility

Is there a visible path toward a theorem using known or plausibly adaptable tools?

* `5` — standard techniques clearly apply.
* `4` — requires a nontrivial combination of known tools, but the path is plausible.
* `3` — requires a new technical idea, but the direction of the idea is visible.
* `2` — would require major new machinery with no clear route.
* `1` — no plausible proof strategy is visible.

Directions with feasibility `<= 2` are normally disqualified unless the user explicitly wants a high-risk direction.

### 2. Novelty evidence

Does the direction appear to add something not already covered by known literature?

* `5` — search finds no close coverage of the setting/result type and the gap appears clear.
* `4` — related work exists, but the direction targets a genuinely different regime, object, or assumption set.
* `3` — partially overlaps with known work but may still offer a meaningful refinement, extension, or new framing.
* `2` — likely marginal; prior work appears to cover most of the contribution.
* `1` — literature check suggests the direction is already known or only superficially different.

Novelty is evidence-based, not guessed. If no literature search is available, mark novelty as provisional and avoid overconfident claims.

### 3. Attack-resistance

How likely is the direction to survive assumption attack and counterexample search?

* `5` — carefully scoped; assumptions likely standard or defensible; no obvious counterexample regime.
* `4` — one visible vulnerability, but a clear weakening or scope path exists.
* `3` — assumptions are aggressive or fragile; likely needs weakening.
* `2` — likely counterexample or major scope issue; needs restructuring.
* `1` — almost certainly false, circular, or vacuous in the intended regime.

Do not select a direction with attack-resistance `<= 2` unless there is a clear repair or weakening path and no better option.

### 4. Theoretical impact

Would the result matter if true?

* `5` — resolves an important open question, establishes a tight bound, proves a strong separation, or enables downstream results.
* `4` — significant theoretical contribution in an active area.
* `3` — solid contribution that advances understanding in a sub-area.
* `2` — technically valid but narrow or unlikely to influence later work.
* `1` — true but uninteresting, mostly cosmetic, or unlikely to be useful.

Avoid venue-specific claims such as “would be accepted at ICML.” Judge scientific contribution, not acceptance probability.

## Weighted scoring

Use:

```text
weighted_total =
  2.0 * feasibility
+ 1.5 * novelty_evidence
+ 2.0 * attack_resistance
+ 1.0 * theoretical_impact
```

Maximum score is `32.5`.

Feasibility and attack-resistance are weighted heavily because an exciting direction is not useful if it is unprovable or immediately falsifiable.

## Step 1 — Preliminary scoring

Score every direction on all four axes using the information in `backup_directions.json`.

For each score, give a one-sentence justification.

If a direction is too vague to score, assign lower feasibility and explain what is missing.

## Step 2 — Select top candidates for literature checking

Select the top 2 candidates by preliminary weighted score.

If the preliminary scores are close or a third candidate has higher novelty/impact but uncertain feasibility, include the third candidate in the literature check.

Do not finalize selection before the literature check unless no search/fetch tools are available.

## Step 3 — Literature check

Use available search/fetch tools only. Do not rely on memory.

For each checked candidate, use:

* `novelty_hypothesis.search_queries`;
* the mathematical object + property + regime;
* the proof strategy + setting;
* the suspected gap and likely related areas.

Search for:

* closest prior theoretical results;
* lower bounds or impossibility results;
* results in the same model/regime;
* results using similar proof tools;
* surveys or canonical papers, if helpful.

Fetch relevant results before using them. A paper may affect novelty scoring only if it was actually fetched or already exists in trusted pipeline context.

For each fetched paper, check:

* Does it study the same object?
* Does it prove the same type of result?
* Does it cover the same regime?
* Are the assumptions comparable?
* Does it subsume, partially overlap, or merely relate to the direction?

If no search/fetch tool is available, record that the novelty check is provisional and select based on internal scoring with caution.

## Step 4 — Update novelty and total scores

After the literature check, update the novelty score for checked candidates.

Use:

* `clear` — no close overlap found; direction appears viable.
* `partial-overlap` — related work exists, but the direction may still be distinct.
* `conflict` — a fetched result appears to cover the proposed direction.
* `unknown` — search/fetch was unavailable or inconclusive.

If a conflict is found, either disqualify the direction or rewrite its selection rationale around a clear distinction. Do not ignore the conflict.

## Step 5 — Apply selection rules

Use the following rules:

1. Disqualify directions with feasibility `<= 2`, unless the user explicitly requested high-risk exploration.
2. Disqualify directions whose literature check yields an unresolved `conflict`.
3. Avoid selecting directions with attack-resistance `<= 2` unless a clear weakening path exists.
4. Among remaining candidates, select the highest weighted total after novelty update.
5. Tiebreaker 1: prefer higher attack-resistance.
6. Tiebreaker 2: prefer higher feasibility.
7. Tiebreaker 3: prefer better alignment with the user's original intent.
8. If the best direction has a known weakness, include the first weakening or repair path.

## Step 6 — Write selected_direction.json

Call `write_artifact` with `name="selected_direction.json"` and this structure:

```json
{
  "selected": {
    "...": "full selected direction object"
  },
  "scores": {
    "direction-id": {
      "feasibility": 4,
      "novelty_evidence": 4,
      "attack_resistance": 3,
      "theoretical_impact": 4,
      "weighted_total": 24.0,
      "justifications": {
        "feasibility": "one sentence",
        "novelty_evidence": "one sentence",
        "attack_resistance": "one sentence",
        "theoretical_impact": "one sentence"
      },
      "disqualified": false,
      "disqualification_reason": null
    }
  },
  "literature_checks": {
    "direction-id": {
      "queries_run": ["query 1", "query 2"],
      "papers_fetched": [
        {
          "title": "paper title",
          "url": "fetched URL",
          "relationship": "closest prior | partial overlap | background | lower bound | unrelated after inspection"
        }
      ],
      "finding": "What was found for this candidate",
      "conclusion": "clear | partial-overlap | conflict | unknown",
      "overlap_detail": "If partial-overlap or conflict, describe exactly what is already known"
    }
  },
  "why_selected": "One paragraph explaining why the selected direction is strongest.",
  "why_not_others": "One paragraph explaining why runner-up directions were not selected.",
  "weakening_note": "If the selected direction has known risks, note the first weakening or repair path.",
  "novelty_caveat": "State whether novelty is verified by fetched sources or still provisional."
}
```

## Quality checklist

* Every candidate direction was scored on all four axes.
* Scores are calibrated, not uniformly optimistic.
* Feasibility and attack-resistance are treated as hard constraints.
* Literature check uses fetched sources only.
* Novelty is updated after literature checking.
* Conflicts are not ignored.
* The selected direction is still a directional conjecture, not a finalized theorem.
* The output does not write `discovery.json`.
* The output preserves enough information for theoretical planning to formalize the selected direction.

## What NOT to do

* Do not select a direction because it sounds impressive.
* Do not skip literature checking when search/fetch tools are available.
* Do not fabricate prior work, citations, or novelty claims.
* Do not rely on memory for novelty judgments.
* Do not assume nonexistent fields such as `novelty.closest_prior`.
* Do not select a direction with feasibility `<= 2` unless explicitly doing high-risk exploration.
* Do not select a direction with an unresolved literature conflict.
* Do not select a direction with attack-resistance `<= 2` without a clear repair path.
* Do not write `discovery.json`; that belongs to theoretical-planning.
* Do not commit to exact rates, constants, or final theorem statements at this stage. -->
