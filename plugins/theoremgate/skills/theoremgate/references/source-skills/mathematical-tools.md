---
name: mathematical-tools
description: "Find, fetch, and condition-check external theorems needed for proof obligations. Called by the Analyst stage of the Method Team. Every external theorem must be verified with write_tool_check before the Proof Writer can use it."
version: 2.2
used_by: method_team
domain: theoretical machine learning
inputs: discovery.json, theorem_state.json if available, proof_obligations.json if available, reference_bank.json if available
outputs: tool_checks via write_tool_check
---

# Mathematical Tools Skill

## Purpose

Find external mathematical results that can discharge proof obligations, then verify whether their conditions are satisfied by the current paper's assumptions.

This skill does not write the final proof. It checks whether a published theorem, lemma, inequality, or standard result is safe to use.

The Proof Writer may only rely on an external theorem after this skill has called `write_tool_check` and the tool has determined that the theorem is safe to use.

## Critical rules

* You do **not** provide `safe_to_use`; the tool computes it from `condition_checks`.
* You **must** provide `theorem_statement`.
* Provide the exact theorem statement if short. If the theorem is long, provide a faithful formal paraphrase preserving all assumptions, quantifiers, parameter dependencies, constants/rates when relevant, and conclusions.
* You **must** provide `source_type`.
* Keys of `condition_checks` must exactly match entries of `required_conditions`.
* There must be no extra or missing `condition_checks`.
* `assumption_used` must be a single valid assumption ID from the current `discovery.json` or `theorem_state.json`, or the empty string `""`.
* Never use `assumption_used: "MISSING"`.
* Never use multiple IDs such as `"A1, A2"`.
* If several assumptions are needed, put the primary assumption ID in `assumption_used` and mention the others in `reason`.
* If no current assumption implies the condition, use `assumption_used: ""` and explain what is missing in `reason`.
* Do not assume that `A1`, `A2`, etc. have fixed meanings across papers. Always read the current plan.

## Search strategy

Prefer high-quality and official sources.

Priority order:

1. Current local bibliography or `reference_bank.json`
2. Known dependencies from `discovery.json`
3. arXiv official page or PDF
4. PMLR proceedings
5. JMLR
6. Official NeurIPS, ICLR, ICML, COLT, AISTATS, or other venue proceedings
7. Publisher or author-hosted official PDF
8. Semantic Scholar — discovery source only
9. General web — discovery source only

Final citation must come from an official or stable scholarly source: local bibliography, arXiv, PMLR, JMLR, official venue proceedings, publisher page, or official PDF.

Semantic Scholar and general web may help find papers, but they are not final theorem sources unless they link to an official source that is fetched.

Search via the `run_search_script` tool when available. It runs the real API scripts and is preferred over general web search.

Examples:

```text
run_search_script(script="search_arxiv", args="--query '[theorem name or proof obligation]' --max_results 5")
run_search_script(script="fetch_paper", args="--id [ARXIV_ID] --full")
run_search_script(script="search_semantic", args="--query '[theorem name or proof obligation]' --max_results 5")
```

If `run_search_script` is unavailable, fails, or returns malformed output, record the failure and use other available search tools. Do not pretend the source was checked.

## Direct result check — do this first

Before attempting to prove a proof obligation from scratch, ask:

```text
Does this proof obligation follow directly from a published theorem or standard result?
```

If yes:

1. Find the exact source.
2. Identify theorem, lemma, proposition, corollary, or equation number if available.
3. Fetch the source.
4. Extract the theorem statement.
5. List every required condition.
6. Map each condition to the current assumptions.
7. Use `proof_type: "direct_citation"` in the downstream proof blueprint if the theorem is safe.
8. Call `write_tool_check`.

This check can eliminate unnecessary proof work.

## External theorem categories

Depending on the proof obligation, search for tools from the relevant mathematical family.

Possible families include:

* concentration inequalities;
* matrix concentration;
* operator concentration;
* empirical process theory;
* PAC-Bayes and generalization bounds;
* Rademacher complexity, covering numbers, VC dimension, and uniform convergence;
* martingale inequalities;
* minimax lower bounds and information-theoretic inequalities;
* optimization convergence theorems;
* convex analysis and variational inequalities;
* stochastic approximation and SGD theory;
* online learning and regret bounds;
* reinforcement-learning sample-complexity or regret theorems;
* spectral theory and functional analysis;
* probability in Hilbert, Banach, or metric spaces;
* perturbation theory and matrix analysis;
* kernel, RKHS, or integral-operator theory when the current plan requires it;
* graph, network, or random matrix theory when the current plan requires it;
* causal identifiability or graphical-model theory when the current plan requires it;
* privacy, robustness, fairness, or constrained-learning theory when the current plan requires it.

Do not assume any domain-specific theorem family is relevant unless the current proof obligation requires it.

## `write_tool_check` call format

This is the required structure. Follow it precisely.

```json
{
  "po_id": "PO-3",
  "theorem_name": "Matrix Bernstein inequality",
  "theorem_statement": "Faithful formal statement of the theorem, preserving all assumptions and conclusions.",
  "source": "Tropp 2012, Theorem 1.4",
  "source_url": "https://arxiv.org/abs/1004.4389",
  "source_type": "arxiv",
  "needed_for": "PO-3 Step 4: variance control",
  "required_conditions": [
    "independent random matrices",
    "zero mean",
    "bounded operator norm R",
    "variance proxy sigma squared"
  ],
  "condition_checks": {
    "independent random matrices": {
      "satisfied": true,
      "reason": "The summands are functions of independent samples under the current sampling assumption.",
      "assumption_used": "A1"
    },
    "zero mean": {
      "satisfied": true,
      "reason": "Each summand is explicitly centered; this follows from the current mean-zero noise assumption.",
      "assumption_used": "A1"
    },
    "bounded operator norm R": {
      "satisfied": false,
      "reason": "The current plan does not include a bounded feature norm or bounded operator norm condition.",
      "assumption_used": ""
    },
    "variance proxy sigma squared": {
      "satisfied": false,
      "reason": "The variance proxy bound would require additional boundedness or moment assumptions not currently present.",
      "assumption_used": ""
    }
  },
  "alternative_if_unsafe": "Search for a theorem requiring only the available moment conditions, or flag to the Lab Lead that an additional boundedness assumption may be needed."
}
```

## Condition-checking discipline

For each external theorem:

### Step 1 — Fetch the source

Find and fetch the source containing the theorem.

Do not rely on memory, title alone, or secondary summaries.

### Step 2 — Extract the theorem statement

Record:

* theorem name or number;
* source;
* source URL;
* source type;
* formal statement or faithful formal paraphrase;
* relevant notation translation if needed.

### Step 3 — List all required conditions

Be exhaustive.

Required conditions may include:

* independence;
* identical distribution;
* zero mean;
* boundedness;
* sub-Gaussian, sub-exponential, finite-moment, or tail assumptions;
* measurability;
* compactness;
* convexity;
* smoothness;
* strong convexity;
* Lipschitzness;
* finite dimension;
* separability;
* trace-class or Hilbert-Schmidt conditions;
* positive definiteness;
* invertibility;
* regularization parameter restrictions;
* sample-size restrictions;
* rank conditions;
* noise assumptions;
* distributional assumptions;
* realizability or misspecification assumptions;
* algorithmic conditions such as step-size schedules;
* initialization conditions;
* mixing or Markov assumptions;
* privacy/robustness/fairness constraints;
* asymptotic regime assumptions.

Do not omit inconvenient conditions.

### Step 4 — Map conditions to current assumptions

For every required condition:

* identify which current assumption implies it;
* use exactly one assumption ID in `assumption_used`;
* if multiple assumptions are jointly needed, choose the primary one and mention the rest in `reason`;
* if none applies, mark `satisfied: false` and use `assumption_used: ""`;
* explain the mapping in normal mathematical language.

### Step 5 — Call `write_tool_check`

Call `write_tool_check` only after all conditions have been checked.

The tool computes whether the result is safe to use.

### Step 6 — If unsafe, provide an alternative

If the theorem is unsafe, do not use it in the proof.

Provide a concrete `alternative_if_unsafe`, such as:

* search for a theorem under weaker assumptions;
* use an expectation-level or high-probability weaker bound;
* reduce to a finite-dimensional subproblem;
* add a lemma to prove the missing condition;
* flag to Lab Lead that a new assumption may be required;
* weaken the target theorem.

Do not silently add assumptions yourself.

## Handling dimension or space mismatch

If a theorem is unsafe because it is stated for a different space than the proof obligation, do not immediately force it.

Examples:

* finite-dimensional theorem vs. infinite-dimensional Hilbert space;
* Euclidean result vs. Banach-space setting;
* scalar concentration vs. matrix/operator-valued quantities;
* independent samples vs. dependent or Markov samples;
* bounded variables vs. heavy-tailed variables.

First try one of:

1. search for an analogue in the correct space;
2. reduce the proof obligation to a setting where the theorem applies;
3. prove an auxiliary reduction lemma;
4. weaken the statement to match the available theorem.

Only flag a gap if no appropriate analogue, reduction, or weakening is available.

## Standard theorem examples

The examples below are illustrative only. Do not use them unless the current proof obligation requires them and their conditions are verified.

### Matrix Bernstein inequality

Typical use: controlling sums of random matrices.

Common conditions:

* independent random matrices;
* zero mean;
* finite-dimensional matrices;
* bounded operator norm or suitable tail condition;
* variance proxy.

Warning: finite-dimensional matrix Bernstein is not automatically valid for infinite-dimensional operators. If the proof uses Hilbert-space operators, search for an operator or intrinsic-dimension analogue, or reduce to finite rank.

### Hoeffding / Bernstein / Bennett inequalities

Typical use: scalar concentration.

Common conditions:

* independence;
* boundedness or moment/tail assumptions;
* zero mean or centered variables;
* sample-size parameter.

Warning: do not apply bounded-variable concentration to heavy-tailed variables unless truncation or boundedness is proven.

### Rademacher complexity or uniform-convergence bounds

Typical use: generalization bounds.

Common conditions:

* specified hypothesis class;
* bounded loss or sub-Gaussian loss;
* i.i.d. samples;
* measurability;
* capacity measure such as covering number, VC dimension, or Rademacher complexity.

Warning: verify the loss and function class match the theorem.

### PAC-Bayes bounds

Typical use: generalization bounds for randomized predictors or posterior distributions.

Common conditions:

* prior independent of training data;
* posterior distribution over predictors;
* bounded or sub-Gaussian loss;
* KL divergence finite;
* i.i.d. data;
* confidence parameter restrictions.

Warning: data-dependent priors need specialized PAC-Bayes results.

### Martingale concentration

Typical use: adaptive algorithms, online learning, RL, or stochastic processes.

Common conditions:

* martingale difference sequence;
* filtration;
* bounded increments or conditional variance control;
* stopping-time conditions if optional stopping is used.

Warning: independence is not enough; verify the filtration and conditional mean-zero property.

### Convex optimization convergence theorem

Typical use: convergence rates for gradient descent, mirror descent, proximal methods, or stochastic optimization.

Common conditions:

* convexity or strong convexity;
* smoothness or Lipschitz gradients;
* feasible set geometry;
* step-size schedule;
* bounded gradients or variance;
* exact or stochastic oracle assumptions.

Warning: do not use a convex theorem for a nonconvex objective unless the proof reduces to a convex surrogate.

### Fano / Le Cam / Assouad inequalities

Typical use: minimax lower bounds or impossibility results.

Common conditions:

* construction of a packing or testing family;
* KL, TV, Hellinger, or chi-square divergence control;
* separation in the target metric;
* prior or mixture construction;
* sample model.

Warning: the lower-bound construction must satisfy the same model assumptions as the theorem statement.

### Functional-analysis or spectral theorem

Typical use: operator decompositions, compact operators, RKHS/integral operators, perturbation arguments.

Common conditions:

* self-adjointness or normality;
* compactness;
* positivity;
* separability;
* trace-class or Hilbert-Schmidt properties when needed;
* domain and boundedness conditions.

Warning: verify whether the theorem is for bounded operators, compact operators, unbounded operators, or finite matrices.

## Assumption ID discipline

Use only assumption IDs defined in the current `discovery.json` or `theorem_state.json`.

Do not assume that `A1`, `A2`, etc. have fixed meanings across papers.

If the current plan includes assumptions such as `A1`, `A2`, and `A3`, use those exact IDs only after verifying their meaning in the current plan.

If no assumption covers a theorem condition, use:

```json
"assumption_used": ""
```

and explain what is missing in `reason`.

## Quality checklist

* The source was fetched before the theorem was used.
* The theorem statement was copied or faithfully formalized.
* The source URL is official or stable.
* `source_type` is provided.
* All required conditions are listed.
* `condition_checks` keys exactly match `required_conditions`.
* Each condition has a boolean `satisfied`.
* Each condition has a non-empty `reason`.
* Each `assumption_used` is one valid current assumption ID or `""`.
* No missing condition is hidden.
* No theorem is treated as safe unless `write_tool_check` determines it.
* Unsafe theorems include a concrete alternative.
* Domain-specific theorems are used only when relevant to the current proof obligation.

## What NOT to do

* Do not provide `safe_to_use` in the `write_tool_check` call.
* Do not use `assumption_used: "MISSING"`.
* Do not use multiple assumption IDs in `assumption_used`.
* Do not add extra keys to `condition_checks`.
* Do not omit any required condition.
* Do not use Semantic Scholar or general web as the final theorem source.
* Do not call `write_tool_check` without fetching and reading the actual source.
* Do not assume a theorem is safe because it is famous.
* Do not silently add assumptions to make a theorem applicable.
* Do not use a theorem outside its dimensional, probabilistic, or geometric setting.
* Do not hardcode kernel/RKHS tools unless the current plan requires them.
