---
name: direction-generation
description: "Normalize a user's research seed — from vague idea to precise theoretical question — into candidate answerable directions in theoretical ML. Directions are questions-to-attempt, not final theorem statements or claimed results. Theorems proved later are the answers."
version: 2.0
used_by: lab_lead
domain: theoretical machine learning
inputs: user research seed
outputs: backup_directions.json via write_artifact
---


# Direction Generation — Theoretical ML

## Purpose

Turn the user's **research seed** into one faithful answerable direction when the user already knows
what they want, or into a small set of candidate directions when the direction itself is vague or the
user explicitly requests alternatives. Each direction is a concrete question-to-attempt. The Method
Team later tries to prove, refute, or reshape it. The theorems that survive are the answers.

At this stage, the system should not commit to exact theorem statements, rates, constants, or proof details. Those emerge later, from the proof itself. This skill produces **directional conjectures**: concrete enough to evaluate feasibility and novelty, but honest about what has not yet been verified.

The output should preserve the user's decision. It must not turn components of one integrated request
into competing directions.

The output must not sound like a contribution has already been made. It only opens possible research directions.

## The research seed is the unit of work

The pipeline starts from a **research seed** and treats every later theorem as an *answer* to it. A fully specified theoretical question usually names an object, a property, and a regime. Professional examples:

* *Under what spectral-decay conditions on the population covariance does the minimum-norm interpolator achieve benign overfitting in high-dimensional linear regression?*
* *Do uniformly stable learning algorithms admit high-probability generalization bounds with optimal sample-size dependence, or is the in-expectation rate unimprovable in general?*
* *What is the minimax sample complexity of estimating a single-index model under isotropic Gaussian design, and is it attained by a polynomial-time estimator?*
* *Does a depth separation exist for approximating Lipschitz functions by ReLU networks under a fixed width budget?*

Some broad questions may decompose into candidate answerable sub-questions. For the first example,
if the user asked for possible directions, these might include (i) a *sufficient* spectral condition for
vanishing excess risk; (ii) a *matching necessary* condition / lower bound; or (iii) the *boundary*
regime where the behaviour transitions. When the user requested those pieces as one paper package,
keep them together in one direction instead.

**A direction is a question to *attempt* — never an answer.** Nothing in this artifact is an "answer": you set only the question and what to try. The answer is the **theorem the Method Team proves and Synthesis states afterward** (theorem-follows-proof). Directions are conjectural targets, not results.

If the user's direction is unclear, propose concrete alternatives. If it is already clear, normalize it
faithfully and do not over-split it. Missing assumptions, optimizer details, constants, proof techniques,
or exact theorem formulations are discovery work; they do not make the research direction unclear.

## Calibrate to the question's specificity

Inputs range from a vague topic to a fully specified question. Match your behaviour to what you were given — do not invent specificity the user did not ask for, and do not ignore specificity they did provide:

* **Vague topic** (e.g. "benign overfitting", "stability and generalization"): object, property, and regime are missing. *Concretize* — propose specific object/property/regime and turn them into a few concrete, answerable sub-questions. State clearly which choices you introduced.
* **Partially specified** (e.g. object + property, but no regime): if the intended research direction is
  still clear, preserve it as one candidate and leave the open regime for discovery to formalize. If the
  missing choice would materially change the research topic, offer a few alternatives.
* **Fully specified** (object + property + regime already pinned down — e.g. an exact threshold to
  characterize under a named design): create exactly one faithful candidate and go directly toward the
  concrete target. Do not split sufficient conditions, necessary conditions, lower bounds, model classes,
  or generalization consequences when the user requested them together.

The more specific the input, the more you preserve and the less you invent.

## This is a theory paper — aim for substantive results

Every direction should, if answered, yield a **substantive** theorem — an explicit bound, an exact characterization, a separation, a minimax rate, an impossibility — **not** a restatement of a definition or an immediate algebraic identity. A direction whose best-case answer is elementary (a one-line consequence of definitions, a standard expansion) is weak; prefer directions that require a real argument. Rigour and depth are the goal from the outset — the downstream paper is a *theory* paper and must stand on genuine mathematics.

## Domain scope

Generate only directions that can plausibly lead to theoretical ML contributions, such as:

* **Generalization theory:** PAC learning, VC dimension, Rademacher complexity, PAC-Bayes bounds, stability, uniform convergence
* **Optimization theory:** convergence rates, loss landscape geometry, saddle points, gradient flow, implicit regularization
* **Sample complexity:** minimax rates, information-theoretic lower bounds, query complexity
* **Approximation theory:** expressivity, depth separation, universal approximation, approximation rates
* **Online learning:** regret bounds, adversarial learning, bandits, adaptive algorithms
* **Statistical learning theory:** bias-variance tradeoffs, model selection, concentration inequalities
* **Representation and architecture theory:** transformers, attention, diffusion models, MoE, sparse networks, or other architectures only when framed through expressivity, optimization, generalization, approximation, sample complexity, or identifiability

Do not generate directions that are primarily empirical, implementation-driven, benchmarking-only, or engineering-focused.

Architecture-specific directions are allowed only if they are framed as theoretical questions.

## When to use this skill

Use this skill in Round 1 whenever the Lab Lead needs to normalize the user's input into candidate theoretical directions.

If the user gives a vague seed, or explicitly asks for ideas, options, or direction comparison, generate
multiple candidate directions.

If the user gives a clear research direction, generate exactly one candidate that preserves every explicit
component. Open technical choices are handled by discovery. Do not drift or create alternatives merely
because the requested theorem package is ambitious.

If the user asks for empirical performance, engineering design, or benchmark construction without a theorem-oriented angle, flag that it is outside this skill's scope.

## Pre-generation check

Before generating directions, silently identify:

* the user's broad research topic;
* the theoretical objects that could be studied;
* the possible properties of interest;
* plausible regimes or settings;
* candidate proof families;
* whether the topic can support multiple distinct theoretical directions.

Use this check silently. Do not expose it in the artifact.

## Step 1 — Extract the theoretical core of the question

From the research seed (and its sub-questions), identify:

* **Mathematical object:** what is being studied?
  Examples: transformer attention, SGD dynamics, sparse networks, diffusion samplers, kernel regressors, online learners.

* **Property of interest:** what could be proved?
  Examples: generalization bound, convergence rate, regret bound, expressivity separation, approximation rate, minimax lower bound.

* **Regime:** where might the result hold?
  Examples: overparameterized, finite-sample, agnostic PAC, realizable, online, low-rank, sparse, noisy, misspecified, distribution shift.

* **Candidate proof lever:** what mathematical machinery may be relevant?
  Examples: Rademacher complexity, PAC-Bayes, martingale concentration, coupling, spectral analysis, information theory, covering numbers, stability, comparison inequalities.

## Step 2 — Generate candidate directions

Generate:
- exactly 1 direction when the user's intended research direction is clear;
- 3–5 materially different directions when the direction is vague or broad, or when the user asks for
  ideas, alternatives, or comparison.

Each direction must be a **candidate question-to-attempt derived from the research seed** — a directional conjecture, not a finalized theorem.

Do not invent exact rates, constants, sample complexities, or lower-bound constants unless the user already supplied them. At this stage, use qualitative or directional language such as “can be bounded in terms of,” “admits a sharper dependence on,” “separates,” “requires,” or “is controlled by.”

Fill all fields:

```json
{
  "id": "short-slug",
  "title": "One-line title",
"direction_question": "The concrete theoretical question to attempt. Phrase as a question or investigation target, not as a result.",
"core_hypothesis": "A directional conjecture about what may be true. Mark it as unverified and do not state it as a theorem.",
  "result_type": "upper-bound | lower-bound | separation | impossibility | characterization | construction",
  "mathematical_setting": {
    "object": "What is studied",
    "property": "What is to be proved, bounded, characterized, separated, or refuted",
    "regime": "Where the claim is expected to hold",
    "introduced_choices": ["Any object/property/regime choices introduced by the Lab Lead because the user seed was vague"]
  },
  "proof_approach": {
    "strategy": "Likely proof strategy to investigate",
    "candidate_steps": ["Step 1 sketch", "Step 2 sketch", "Step 3 sketch"],
    "candidate_tools": ["Likely tools to investigate, not guaranteed proof ingredients"]
  },
  "novelty_hypothesis": {
    "suspected_gap": "Hypothesized gap before literature verification",
    "likely_related_areas": ["area 1", "area 2"],
    "search_queries": ["query 1", "query 2", "query 3"],
    "novelty_risk": "What kind of prior work might already subsume this idea"
  },
  "risk": {
    "main_failure_mode": "The most likely way this direction could fail mathematically",
    "assumption_weakness": "The assumption most likely to be challenged later",
    "counterexample_hint": "A boundary case or construction the Attack Team should check first",
  },
  "feasibility": "high | medium | low",
  "feasibility_reason": "One sentence explaining what makes this tractable or speculative",
  "assumption_realism": "Which motivating phenomena remain present under the proposed assumptions, and which are removed",
  "practical_or_conceptual_consequence": "What decision, mechanism, guarantee, or impossibility would change if the direction succeeds",
  "expected_contribution_if_successful": "What kind of theoretical contribution this direction could support if answered"
}
```

## Novelty discipline

At this stage, novelty is a hypothesis, not a verified fact.

* Do not claim that the direction is novel unless literature search has verified it.
* Do not invent closest-prior citations.
* Do not name a specific paper unless it was provided by the user or already appears in available pipeline context.
* Use `novelty_hypothesis` to state what should be checked later.
* Include search queries that the literature-search skill can use to verify overlap and positioning.
* If a related area is likely but no paper is known, name the area rather than fabricating a citation.

## Proof-approach discipline

Proof approaches are candidate plans, not commitments.

* Name concrete proof families when plausible.
* Do not assert that a technique will work.
* Do not invent lemmas or guarantees that have not been formalized.
* Use “candidate tools” rather than guaranteed tools.
* Include risks when the proposed proof strategy may fail.

## Step 3 — Diversity check

This step does not apply to a single faithful user-specified direction. When multiple directions are
generated, they must differ on at least two of the following:

* mathematical object studied;
* property of interest;
* regime or setting;
* proof strategy;
* result type;
* main failure mode.

Do not generate several minor variations of the same bound, theorem, or proof plan.

The set should include a mix of safer and more ambitious directions when possible.

## Step 4 — Feasibility calibration

Assign feasibility honestly:

* `high` — likely formalizable with standard assumptions and known tools;
* `medium` — plausible but requires a nontrivial technical idea or careful assumptions;
* `low` — ambitious, high-risk, or likely to need new machinery.

Do not label every direction high feasibility. At least one direction should usually be medium or low unless the user's idea is already narrow and tractable.

## Step 5 — Write the artifact

Call `write_artifact` with `name="backup_directions.json"` and this structure:

```json
{
  "round": 1,
  "artifact": "backup_directions",
  "domain": "theoretical ML",
  "generated_from": "brief summary of user input",
  "input_specificity": "vague | partial | fully_specified",
  "preserved_user_constraints": ["specific constraints or terms preserved from the user input"],
  "introduced_choices_summary": "short explanation of object/property/regime choices introduced by the Lab Lead, if any",
  "directions": [ "...1–5 direction objects..." ],
  "notes": "novelty is unverified; directions are questions-to-attempt, not theorem commitments"
}
```

## Quality checklist

* Every direction is a directional conjecture, not a finalized theorem.
* No exact rates, constants, or sample complexities are invented.
* Every direction is grounded in theoretical ML.
* Architecture-specific directions are framed theoretically, not as engineering.
* Each `proof_approach` names plausible candidate techniques without guaranteeing success.
* Each `novelty_hypothesis` avoids fabricated citations and includes search queries.
* Each `direction_question` states object, property, and regime.
* Each `core_hypothesis` is explicitly unverified and does not claim a result.
* Each `risk.main_failure_mode` is specific and mathematically meaningful.
* Each `risk.counterexample_hint` gives the Attack Team a concrete boundary case to test.
* Multiple directions, when appropriate, are genuinely diverse.
* A clear user-specified direction produces exactly one candidate containing all requested components.
* Feasibility is calibrated rather than uniformly optimistic.
* Every direction explains whether its assumptions preserve the motivating difficulty.
* Every direction states a concrete practical or conceptual consequence beyond mathematical elegance.

* The artifact records whether the input was vague, partial, or fully specified.
* User-provided constraints are preserved.
* Lab-introduced specificity is recorded honestly.
* Each direction has a `direction_question`, not only a claim.
* Each direction includes a concrete `main_failure_mode`.
* Each direction includes a `counterexample_hint`.

## What NOT to do

* Do not generate purely empirical, benchmark-only, product, or engineering directions.
* Do not fabricate citations, closest prior work, or novelty claims.
* Do not commit to exact theorem statements, rates, or constants.
* Do not create directions that differ only cosmetically.
* Do not ignore the user's topic; directions should be recognizable descendants of the user's idea.
* Do not split an integrated requested package into candidates that compete with one another.
* Do not present proof approaches as guaranteed.
* Do not write the final paper contribution at this stage.








