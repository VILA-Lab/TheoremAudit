---
name: discovery
description: "Build discovery.json from a selected theoretical ML research direction. Produces a rigorous mathematical research MAP (a discovery, not a fixed plan) including: formal setting, notation, definitions, assumption set, theorem targets (one designated primary), supporting lemmas, claim graph, proof obligation tree, proof outline, counterexample candidates, novelty hypothesis, empirical checks, and falsifiable validation criteria. This is the core Round 1 output that gates the Method Team and Attack Team. Must be called after direction-selection."
version: 2.0
used_by: lab_lead
domain: theoretical machine learning
inputs: selected_direction.json
outputs: discovery.json (via write_artifact)
---

# Discovery — ML Theory

## Why this skill exists
The **discovery** (written to `discovery.json`) is the mathematical research **map** between Round 1 and all downstream agents — a *living document, not a fixed contract*. Its setting, notation, and definitions are stable ground; its theorem **targets** and assumptions are provisional and get revised as proving proceeds. The Method Team reads it to formalize definitions and discharge proof obligations. The Attack Team reads it to find counterexamples and challenge assumptions. The Manuscript Compiler and later synthesis stages use it only after claims survive proof, validation, and Arbiter commitment.

If the setting is vague, the Method Team will formalize the wrong object. If assumptions are informal, the Attack Team cannot challenge them. If proof obligations are missing, nothing gets discharged. If novelty is not stated, the Literature Lead has nothing to check.

This skill forces the Lab Lead to be mathematically precise and epistemically honest before formalization begins.

## The discovery mindset — the theorem follows the proof
You are drawing a **research map**, not signing a contract. In a real theory paper the final
theorem is written to *fit the proof that succeeded* — it is an **output** of proving, not a fixed
target you must hit. So the map has three kinds of content, and they are treated differently:

- **Stable ground** — `setting`, `notation`, `definitions`. Fixed for the whole investigation.
- **Provisional targets** — theorem `targets` and `assumptions`. Directional aims the Method Team
  will reshape, narrow, or drop as proofs and counterexamples arrive. Never a promise.
- **The primary target** — the ONE concrete, tractable statement we commit to landing FIRST: the
  positive core that avoids the hardest open step. Everything else is secondary.

Start lean. A research map begins small and **grows** as proving reveals what is true. Do not pad
it with ambitious structure you cannot reach — an over-planned map of unprovable theorems is
exactly why nothing ever gets committed.


### Explorer-guided branch selection

Discovery may open multiple plausible branches when the selected direction naturally contains
several routes, such as:
- upper-bound versus lower-bound;
- noise alignment versus misspecification;
- exact support versus approximate alignment;
- finite-sample versus asymptotic;
- construction/separation versus characterization.

However, Discovery must not silently hand all branches to the Method Team at once.

If the primary target contains multiple plausible proof branches, Discovery must add an
`exploration_hooks` item whose purpose is to choose the first Method-Team scope.

That hook must ask Explorer to recommend exactly one of:
- prove the favorable upper-bound branch first;
- prove the harmful lower-bound branch first;
- prove the full separation directly;
- restrict to the well-specified noise-only version;
- restrict to the misspecification version;
- retreat to the `min_viable_form`.

Explorer's recommendation should determine the initial Method-Team scope.

### Primary-target branch discipline

Discovery may describe a primary target that contains multiple plausible proof branches, but it
must not let the Method Team attempt all branches blindly.

If the first proof branch is already obvious, Discovery may narrow the primary target to exactly
one tractable branch.

If the first proof branch is not obvious, Discovery must keep the alternatives explicit and add
an `exploration_hooks` item that asks Explorer to recommend exactly one initial Method-Team scope.

Put unresolved alternatives into:
- stretch theorem targets,
- fallback paths,
- risks / weakening paths,
- exploration hooks.

The Method Team should follow the Explorer-recommended scope, not the entire broad target.

## Core distinction
You are opening obligations, not discharging them.
- A proof discharges: "By McDiarmid's inequality applied to f(S), we get..."
- A discovery opens: "We need to show f(S) satisfies bounded differences with c = O(1/n)"

The Method Team discharges. You open. Never discharge an obligation yourself.

## Epistemic honesty rule
Everything here is a draft, target, or conjecture — nothing is verified. Mark status explicitly.
Theorems are `status: "target"` (a directional aim); never write "the theorem holds".


Use the selected direction's `handoff_to_discovery` if present. Preserve:
- `what_discovery_should_preserve`;
- `what_discovery_should_be_careful_about`;
- `first_weakening_to_try_if_needed`;
- user constraints and introduced choices from earlier artifacts.

---

## Step-by-step instructions

### Step 1 — Establish the formal setting
Before any assumptions or theorems, ground the mathematical universe. This is what the Method Team needs to write down the first definition.

```json
{
  "objects": "What mathematical objects are central? e.g. hypothesis class H ⊆ {h: X→Y}, distribution D over X×Y, loss ℓ: Y×Y→[0,M], algorithm A: (X×Y)^n → H",
  "regime": "What is the target regime? e.g. agnostic PAC, realizable, online, overparameterized, finite-sample",
  "target_quantity": "What is being bounded or characterized? e.g. generalization gap R(h)-R̂(h), convergence rate ||w_t - w*||, sample complexity n(ε,δ)",
  "known_special_cases": "What does the result reduce to in known settings? This is a sanity check for the Method Team"
}
```

### Step 2 — Declare notation
List every symbol needed before theorem statements. Downstream agents cannot formalize without this.

```json
[
  {"symbol": "H", "meaning": "Hypothesis class"},
  {"symbol": "D", "meaning": "Unknown data distribution over X×Y"},
  {"symbol": "S", "meaning": "Training sample S = {(x_i, y_i)}_{i=1}^n ~ D^n"},
  {"symbol": "R(h)", "meaning": "True risk: E_{(x,y)~D}[ℓ(h(x),y)]"},
  {"symbol": "R̂(h)", "meaning": "Empirical risk: (1/n)∑ℓ(h(x_i),y_i)"},
  {"symbol": "Rad_n(H)", "meaning": "Rademacher complexity of H on n samples"}
]
```

### Step 3 — State formal definitions
Every non-standard concept used in the theorem must be defined here. Standard concepts (e.g. VC dimension, Rademacher complexity) do not need redefinition — reference them by name.

```json
[
  {
    "id": "D1",
    "name": "Effective rank",
    "formal": "For a matrix A, the effective rank is r(A) = (||A||_F / ||A||_op)^2",
    "why_needed": "The main theorem bound depends on r(A) rather than full dimension d"
  }
]
```

### Step 4 — State assumptions formally
Every assumption must have both informal and formal versions. Be honest — non-standard assumptions are Attack Team targets.

```json
{
  "id": "A1",
  "informal": "The loss function is bounded",
  "formal": "For all h ∈ H and (x,y) ∈ X×Y: 0 ≤ ℓ(h(x),y) ≤ M for some M > 0",
  "type": "boundedness | smoothness | convexity | independence | realizability | sub-gaussianity | lipschitz | spectral | margin | stability",
  "standard": true,
  "justification": "Why this is reasonable in the target setting",
  "failure_mode": "How this assumption could fail, be too strong, or exclude important cases — e.g. 'squared loss is unbounded; M-boundedness excludes standard regression'",
  "if_violated": "What the theorem becomes if this fails — e.g. 'result requires truncation argument, weakening to sub-Gaussian losses'",
  "editable": true
}
```

Mark `standard: true` only for completely standard assumptions (i.i.d. samples, bounded loss). `standard: false` assumptions are high-priority Attack Team targets and must have strong justifications.

The assumption set is a **provisional starting set, not a fixed frame.** `editable: true` (the default) tells downstream agents that the Method Team may legitimately tighten, narrow, drop, or add an assumption as the proof reveals what it actually needs — e.g. restricting to Gaussian design, or conditioning on an event. Set `editable: false` only for an assumption that *defines the problem itself* (without it, the object under study changes). Reshaping an editable assumption to make a proof go through is expected, not a violation.

### Step 5 — State theorem targets, and designate ONE primary target
Produce 1–3 theorem **targets**. A target is a *directional aim*, not a proven or promised result
— the Method Team decides what actually survives, and the final statement is written to fit the
proof (see "The discovery mindset" above). Tag each target's `role`:

- exactly ONE `role: "primary"` — the ONE concrete, tractable statement we attempt FIRST;
- the rest `role: "stretch"` — ambitious directions that would be nice but must never block the
  primary target.

**The primary target MUST be provable without the hardest open step — this is the single most
important decision in the discovery.** Good venues reject papers whose main contribution is a
conjecture, so The primary target should be plausibly provable and self-contained: small enough that a capable Method Team has a visible route to a proof without needing the hardest open step: a
positive theorem (explicit bound / exact formula / construction in a tractable regime such as
isotropic or diagonal-covariance, where the hard step has a closed form) or, if no positive core
is reachable, a PROVED separation/impossibility (an explicit counterexample IS a firm theorem). A
capable prover must be able to finish it WITHOUT the hardest open step (e.g. without random-matrix
concentration at the interpolation hard edge). If your primary target still depends on that one
open step, it is a stretch target — pick a smaller primary.

If the selected direction contains multiple scientific branches, either:
- narrow the primary target to one branch if the first proof route is already obvious; or
- keep the alternatives explicit and add an `exploration_hooks` item asking Explorer to recommend exactly one initial Method-Team scope.

For example, if the selected direction mentions both misspecification and heteroscedastic noise,
Discovery may keep both as alternatives only if an exploration hook asks Explorer which one should
be attempted first. The Method Team should not attempt all branches blindly.

```json
{
  "id": "T1",
  "role": "primary | stretch",
  "status": "target",
  "type": "upper-bound | lower-bound | tight-bound | separation | equivalence | impossibility | existence | necessity | stability | adaptation | characterization | construction | exact-formula",
  "informal": "Plain language version",
  "sketch": "For any h ∈ H satisfying [conditions], under A1-A3, with probability 1-δ over S~D^n: [bound expression]",
  "dependencies": ["A1", "A2", "D1"],
  "bound_type": "high-probability | in-expectation | minimax | instance-dependent",
  "rate_conjecture": "Conjectured asymptotic rate e.g. O(sqrt(r(A) log(1/δ) / n)) — mark as conjecture, not fact",
  "tightness": "known-tight | conjectured-tight | not-tight | unknown",
  "min_viable_form": "Simplest still-publishable version reachable WITHOUT the hardest open step"
}
```

Then record the primary target as a first-class top-level field, so every downstream agent knows
what to prove first and which hard step it deliberately sidesteps:

```json
"primary_target": {
  "statement_id": "T1",
  "informal": "the concrete result we attempt to prove first",
  "result_type": "upper-bound | lower-bound | separation | impossibility | exact-formula | construction",
  "why_tractable": "Why a capable prover should have a visible route to finishing it — e.g. closed form in the diagonal regime",
  "avoids": "The hardest open step it deliberately sidesteps — e.g. 'no RMT hard-edge concentration'",
  "fallback": "If even this fails, the proved negative/impossibility that still stands as a result"
}
```

For a full run targeting original research or a workshop paper, also record a publication-strength
gate. This is a scientific-content requirement, not a formatting field:

```json
"publication_strength": {
  "technical_obstacle": "The genuinely nontrivial obstruction the primary theorem resolves",
  "novelty_delta": "The exact theorem-level improvement over the closest verified result",
  "closest_work_boundary": "What the closest result proves and the precise boundary crossed here",
  "nonvacuity_check": "A concrete regime or example where the assumptions hold and the conclusion is informative",
  "complete_proof_route": "The full critical path from assumptions through lemmas to the primary theorem",
  "companion_result_id": "T2",
  "exceptional_depth_justification": ""
}
```

Exactly one of `companion_result_id` and `exceptional_depth_justification` must be nonempty. Normally,
the package includes a distinct supporting theorem—such as a lower bound, necessity result,
separation, characterization, or matching construction—with its own proof obligation. A single
headline theorem is allowed only when the recorded exceptional-depth justification explains why its
proof and conclusion alone supply comparable theoretical depth. Reject packages whose apparent
strength comes from renaming a standard result, assuming the conclusion, restricting to a direct
special case without a new obstacle, or adding vacuous companion claims.

### Step 6 — State supporting lemmas
List the technical subgoals that the Method Team must establish before the main theorem. These are not proof obligations yet — they are the structural decomposition of the proof.

```json
{
  "id": "L1",
  "status": "conjectural",
  "claim": "The function class F_A = {x ↦ ⟨a, Ax⟩ : ||a||≤1} has Rademacher complexity bounded by O(sqrt(r(A)/n))",
  "role": "This is the core complexity bound that feeds into T1 via the standard Rademacher generalization theorem",
  "proof_hint": "Use the matrix trace norm and the connection between effective rank and operator norm",
  "depends_on": ["A1", "D1"]
}
```

### Step 7 — Build the claim graph
Express dependencies between all components as a list of edges. This lets the Method Team see the proof structure at a glance.

```json
[
  {"from": "A1", "to": "L1", "type": "assumption-used"},
  {"from": "D1", "to": "L1", "type": "definition-used"},
  {"from": "L1", "to": "T1", "type": "lemma-supports-theorem"},
  {"from": "A2", "to": "T1", "type": "assumption-used"}
]
```

### Step 8 — Open proof obligations
For every non-trivial step in the proof, open an obligation. Obligations are finer-grained than lemmas — a single lemma may have multiple obligations.

```json
{
  "id": "PO-1",
  "supports": "L1",
  "claim": "For the function class F_A, the covering number satisfies log N(ε, F_A, ||·||_∞) ≤ r(A) log(2/ε)",
  "why_nontrivial": "Covering number for matrix-parametrized classes requires a non-standard argument based on low-rank structure",
  "proof_strategy": "Decompose A = UΣV^T, bound covering number of the low-rank factor, apply standard composition",
  "key_tools": ["Maurey's empirical method", "Low-rank matrix approximation", "Dudley's entropy integral"],
  "dependencies": ["A1", "D1"],
  "blocks": ["PO-2"],
  "difficulty": "routine | moderate | hard | open",
  "status": "open",
  "failure_mode": "How this obligation could fail or require a narrower assumption",
  "repair_hint": "First repair or weakening to try if this obligation fails"
}
```

Difficulty guide:
- **routine**: standard application of a known tool
- **moderate**: non-trivial computation or combination of tools
- **hard**: requires a new technical idea
- **open**: no clear path — flag for Lab Lead after Method Team attempt

**Keep the obligation set lean and primary-first.** List the obligations on the critical path to
the PRIMARY target first — that chain is the initial worklist and it must be *complete* (every
non-trivial step to reach the primary target has an obligation) and *minimal* (no steps that only
serve stretch targets). Obligations that support only stretch targets are optional; include them
sparingly and never let them crowd out the primary path. A short reachable chain beats a long
ambitious one — unreached obligations are exactly why nothing gets committed.

### Step 9 — Write the proof outline
3-7 bullet points describing the proof roadmap in order. This is for human orientation, not formal verification.

```json
[
  "Step 1: Symmetrize the generalization gap using a ghost sample",
  "Step 2: Bound the Rademacher complexity of F_A using the effective rank (L1)",
  "Step 3: Apply the standard Rademacher generalization theorem to convert complexity to generalization gap",
  "Step 4: Optimize over δ to get the high-probability bound"
]
```

### Step 10 — Document possible counterexamples
Where might the claim fail? What boundary cases or degenerate regimes should the Attack Team check first?

```json
[
  {
    "id": "CE1",
    "description": "When the effective rank r(A) = d (full-rank matrix), the bound reduces to O(sqrt(d/n)) which is no better than standard dimension-dependent bounds",
    "implication": "The result is only interesting when r(A) << d; the Attack Team should check whether this regime is achievable under the stated assumptions",
    "severity": "medium"
  }
]
```

### Step 11 — State the novelty hypothesis
What may be new — explicitly marked as unverified. The Literature Lead will check this.

```json
{
  "claim": "The possible novelty is ...",
  "closest_known_from_selection": ["Only include fetched/known sources from selected_direction.json; otherwise leave empty"],
  "what_we_may_add": "The hypothesized distinction or gap",
  "verification_status": "unverified | partially_checked | conflict_possible",
  "literature_queries_to_recheck": ["..."]
}
```

### Step 12 — Propose exploration hooks and empirical checks

Discovery may open multiple plausible branches, but it must not silently hand all branches to
the Method Team at once. If the primary target contains multiple scientific branches, include
an exploration hook whose explicit purpose is to choose the first proof branch for the Method
Team.

Examples of branches:
- favorable upper-bound versus harmful lower-bound;
- full separation versus one-sided result;
- noise-only alignment versus misspecification alignment;
- exact support versus approximate alignment;
- finite-sample construction versus asymptotic theorem.

When branches exist, include an `exploration_hooks` item like this:

```json
{
  "id": "EX-branch",
  "target": "T1",
  "modality": "simulate",
  "finite_proxy": "Compare candidate first proof branches: favorable upper bound, harmful lower bound, full separation, noise-only alignment, and misspecification alignment. Recommend exactly one initial Method-Team scope.",
  "instance_family": "Small explicit instances matching the selected direction's minimum viable setting.",
  "sweep": "Vary the minimal parameters needed to distinguish branches.",
  "expected_signal": "A clear recommendation of which branch is most tractable and least likely to collapse under counterexamples.",
  "fallback_if_refuted": "Retreat to the selected direction's minimum_viable_result or first_weakening_to_try_if_needed."
  
}
```

Then propose lightweight empirical checks that probe, communicate, or stress-test the theoretical
claim. These are not the main contribution — the proof is. But they help diagnose assumptions,
choose a proof branch, and illustrate the bound or separation.

Rules:
- Prefer controlled synthetic experiments or small public-data subsets.
- Must produce interpretable figures or metrics.
- Must not replace the proof as evidence.
- If an empirical check is meant to guide Explorer, set `early_exploration_compatible: true`.

```json
[
  {
    "id": "EC1",
    "description": "Synthetic experiment probing the primary target on small controlled instances.",
    "purpose": "Diagnose whether the proposed phenomenon appears before proof effort escalates.",
    "data": "Synthetic data, no downloads required.",
    "compute": "CPU-only, runs in less than a few minutes.",
    "expected_output": "Interpretable plot, table, or metric comparing the relevant regimes.",
    "early_exploration_compatible": true
  }
]```


### Step 13 — State validation criteria
Each criterion must be checkable by the Method Team or Attack Team.

```json
{
  "success": [
    "All proof obligations PO-1 through PO-N discharged by Method Team",
    "Bound is non-vacuous: plugging in r(A) = O(log d), n = 1000, δ = 0.05 gives bound < 0.1",
    "No counterexample found by Attack Team within stated assumption set",
    "Literature Lead confirms no prior result achieves same rate under same assumptions"
  ],
  "partial_success": [
    "If PO-3 (hard) cannot be discharged: T1 weakens to T1' under stronger assumption A4 (explicit low-rank factorization)",
    "If CE1 materializes as a real attack: restrict claim to r(A) ≤ sqrt(d) regime, state as proposition"
  ],
  "failure": [
    "Attack Team finds concrete D and H satisfying A1-A3 where the bound is violated",
    "Method Team shows PO-2 is false as stated, not just hard to prove",
    "Literature check finds prior result that subsumes T1 without gap"
  ],
  "min_viable_validation": "Prove T1 under stronger assumption A4 (explicit rank-k factorization with known k) as a proposition — this is publishable as a restricted result"
}
```

### Step 14 — Write discovery.json
Call write_artifact with name="discovery.json":

```json
{
  "round": 1,
  "artifact": "discovery",
  "domain": "theoretical ML",
  "selected_direction": { "...from selected_direction.json...": "..." },

  "handoff_from_selection": {
    "selected_direction_id": "direction-id",
    "input_specificity": "vague | partial | fully_specified",
    "preserved_user_constraints": ["..."],
    "introduced_choices_summary": "...",
    "what_discovery_preserved": ["..."],
    "known_risks_from_selection": ["..."],
    "first_weakening_to_try_if_needed": "..."
  },

  "setting": { "...from Step 1...": "..." },
  "notation": ["...from Step 2..."],
  "definitions": ["...from Step 3..."],
  "assumptions": ["...from Step 4..."],

  "theorem_targets": ["...from Step 5 — each tagged role + status: target..."],
  "primary_target": { "...from Step 5 — the first target to attempt...": "..." },

  "lemmas": ["...from Step 6..."],
  "claim_graph": ["...from Step 7..."],
  "proof_obligations": ["...from Step 8..."],
  "proof_obligation_order": ["PO-1", "PO-2", "PO-3"],
  "proof_outline": ["...from Step 9..."],

  "possible_counterexamples": ["...from Step 10..."],
  "novelty_hypothesis": { "...from Step 11...": "..." },

  "exploration_hooks": [
  {
    "id": "EX1",
    "target": "T1",
    "modality": "compute | simulate | enumerate | search-construct | symbolic",
    "finite_proxy": "What finite/small-instance quantity probes the target or chooses the first proof branch",
    "instance_family": "Small parametrized instances to test",
    "sweep": "Parameters or branches to vary",
    "expected_signal": "Pattern, threshold, failure, invariant, or branch recommendation to look for",
    "fallback_if_refuted": "How to narrow, reshape, or choose the first Method-Team scope"
  }
],

  

  "empirical_checks": ["...from empirical-check step; early exploration compatibility field..."],
  "validation_criteria": { "...from validation step...": "..." },

  "risks": [
    {
      "id": "R1",
      "description": "Specific risk.",
      "type": "vacuous-in-regime | counterexample | assumption-too-strong | prior-art | proof-gap | scope-too-broad | exploration-refutes-target | notation-ambiguity",
      "likelihood": "high | medium | low",
      "target": "T1 | L1 | PO-1 | assumption-id",
      "weakening_path": {
        "from": "current target form",
        "to": "weaker but still substantive form",
        "cost": "what is lost"
      }
    }
  ],

  "verification_status": {
    "setting": "draft",
    "notation": "draft",
    "definitions": "draft",
    "assumptions": "draft",
    "theorem_targets": "tentative_targets",
    "primary_target": "attempt_first",
    "lemmas": "conjectural",
    "claim_graph": "unverified",
    "proof_obligations": "open",
    "proof_outline": "sketch_only",
    "novelty": "unverified | partially_checked | conflict_possible | clear_from_selection",
    "exploration_hooks": "not_run",
    "empirical_checks": "not_run_early_exploration"
  },

  "metadata": {
    "generated_by": "lab_lead",
    "round": 1,
    "status": "round_1_complete",
    "non_standard_assumptions": ["list assumption ids that are non-standard"],
    "hard_obligations": ["list PO ids rated hard"],
    "open_obligations": ["list PO ids rated open"],
    "primary_target": "T1",
    "theorem_candidates": ["T1", "T2"]
  }
}
```

---

## Quality checklist
- [ ] setting.objects names every mathematical object precisely
- [ ] Every symbol used in theorem targets appears in notation
- [ ] Every non-standard concept has a definition in definitions
- [ ] Every assumption has both informal and formal fields with proper mathematical notation
- [ ] Non-standard assumptions (`standard: false`) have strong justifications
- [ ] Theorem targets are marked `status: "target"` with a `role`, not stated as facts
- [ ] rate_conjecture is marked as conjecture — not stated as a proven rate
- [ ] Every lemma has a role explaining how it connects to the theorem
- [ ] Claim graph covers all dependencies between assumptions, definitions, lemmas, theorem targets, and proof obligations
- [ ] Every non-trivial proof step has a proof obligation
- [ ] Every obligation has difficulty rating, proof_strategy, and key_tools
- [ ] Proof obligation dependencies form a valid DAG (no cycles)
- [ ] Exactly ONE theorem target is tagged `role: "primary"`
- [ ] `primary_target` is filled in; its `avoids` names the hard step it deliberately sidesteps
- [ ] The obligations on the primary target's critical path form a complete, minimal chain
- [ ] The map is lean — no ambitious structure padded beyond what supports a stated target
- [ ] At least 2 risks with weakening paths
- [ ] At least 2 possible counterexamples
- [ ] novelty_hypothesis.verification_status is "unverified"
- [ ] Empirical checks are CPU-only and produce interpretable outputs
- [ ] Every risk has a weakening_path
- [ ] verification_status fields are filled in for all sections
- [ ] min_viable_validation states a concrete restricted result

## What NOT to do
- Do NOT discharge any proof obligation — that is the Method Team's job
- Do NOT state any theorem as proven or true — use `status: "target"`
- Do NOT use informal language in assumption.formal fields
- Do NOT omit hard or open obligations to make the plan look cleaner
- Do NOT propose GPU experiments or large-scale model training in empirical_checks
- Do NOT leave weakening_path empty on any high-likelihood risk
- Do NOT invent citations — novelty_hypothesis says "unverified" and the Literature Lead checks
- Do NOT skip notation or definitions — the Method Team cannot formalize without them
- Do NOT let the primary target depend on the hardest open step — if it does, pick a smaller primary target
- Do NOT pad the map — start lean; it grows during proving. An over-planned map of unprovable theorems is exactly why nothing gets committed
