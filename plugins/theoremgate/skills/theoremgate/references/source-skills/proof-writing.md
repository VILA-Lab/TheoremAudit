---
name: proof-writing
description: "Write structured LaTeX proof drafts with explicit gap/claim/lemma tagging. Called by the Proof Writer stage of the Method Team. Status rules match write_proof_draft.py exactly."
version: 2.0
used_by: method_team (proof writer stage)
---

# Proof Writing Skill

## Core principle
The Method Team produces **proof drafts**, not verified proofs.
A proof draft is honest about what is known, what is assumed, and what is uncertain.
Gaps must be tagged explicitly — never hidden or glossed over.

---

## Tag format — exact convention

Tags use the obligation ID with hyphens removed:
- `PO-1` → tags are `GAP-PO1-XX`, `CLAIM-PO1-XX`, `LEMMA-PO1-XX`
- `PO-3` → tags are `GAP-PO3-XX`, `CLAIM-PO3-XX`, `LEMMA-PO3-XX`
- `PO-10` → tags are `GAP-PO10-XX`, `CLAIM-PO10-XX`, `LEMMA-PO10-XX`

Number sequentially within each obligation: `GAP-PO3-01`, `GAP-PO3-02`, etc.

---

## LaTeX proof structure

```latex
\begin{lemma}[PO-3: Variance Control]
\label{lem:po3}
Under assumptions A1, A2, A6, ...
\end{lemma}

% ASSUMPTION USAGE TABLE
% A1 (i.i.d. sampling): Step 2 — independence of samples
% A2 (trace-class): Step 3 — Tr(T) finite for effective dimension
% A6 (effective dimension): Step 4 — N(lambda) control
% HIDDEN ASSUMPTIONS INTRODUCED: none

\begin{proof}
% Step 1: Decompose variance term
[proof text]

% Step 2: Apply concentration — uses CHECK-PO3-01: Matrix Bernstein
% Uses CHECK-PO3-01: Matrix Bernstein condition check
By the Matrix Bernstein inequality...

% [GAP-PO3-01]: Step 3 requires bounded operator norm.
% This requires a bounded kernel assumption not currently in discovery.json.
% Severity: major
% Required fix: Lab Lead must approve bounded kernel or Analyst must find an alternative.
[incomplete step clearly marked]

% [CLAIM-PO3-01]: E[||T_hat - T||^2] <= Tr(T)^2 / n.
% Confidence: high. Standard result but not yet derived as a lemma here.
[claim text]

\end{proof}
```

---

## Tagging conventions

### [GAP-PON-XX] — A step that cannot be justified
```latex
% [GAP-PO3-01]: description of missing step
% Severity: minor | major | fatal
% Required fix: what would make this step valid
```
- minor: proof mostly complete, small technical detail missing
- major: significant step missing, repairable with effort
- fatal: proof cannot proceed, theorem may be false or assumption set insufficient

### [CLAIM-PON-XX] — A plausible claim stated without full proof
```latex
% [CLAIM-PO3-01]: statement of claim
% Confidence: high | medium | low
% Evidence: why you believe this is true
```

### [LEMMA-PON-XX] — An auxiliary result needed but not proved here
```latex
% [LEMMA-PO3-01]: statement of lemma
% Proof status: assumed | deferred | proved_in_POY
```

---

## Tool check usage

Every external theorem used in the proof must be referenced by its `check_id` from `tool_checks.json`.

```
tool_check_ids_used = ["CHECK-PO3-01", "CHECK-PO3-02"]
```

Inside the LaTeX proof, cite the check ID near the theorem use:
```latex
% Uses CHECK-PO3-01: Matrix Bernstein condition check
By Matrix Bernstein (Tropp 2012)...
```

If no external theorem is used, pass explicitly:
```
tool_check_ids_used = []
```

**Do NOT use any theorem whose tool check has `computed_safe_to_use=false`.**
An unsafe theorem can only be mentioned as a failed attempt or motivation for a GAP tag.

---

## Do NOT hide the hard step behind a vague "regime"
The retreat-to-minimal-form is only valid if the restricted setting makes the hard step
COMPUTABLE — not merely assumed away. A named condition like "safe restricted-head regime"
or "stable head-controlled decomposition" is NOT a definition; writing it as a hypothesis
is just a `[GAP]` in disguise, and a reviewer will see straight through it. For every
condition you place in a proposition:
- Define it PRECISELY as an explicit inequality on the plan's objects (e.g. eigenvalue
  decay `mu_k <= c/k^a`, split index `k = floor(n/2)`, `sum_{j>k} mu_j <= ...`), OR
- Restrict to a model concrete enough that the hard quantity is a DIRECT closed-form
  computation (e.g. fixed diagonal Sigma with named eigenvalues → the expected variance is
  an explicit finite spectral sum, no concentration needed).
If you can do neither, the step is a genuine GAP — tag it; do NOT dress it as a "regime".
NEVER use the words "safe"/"unsafe" (internal tool-check terms) inside the mathematics.

## Retreat to the minimal viable form (prefer a complete restricted proof)

Each theorem in the plan carries a `min_viable_form` field — a restricted version (a
diagonal-Sigma proposition, an explicit finite-dimensional construction, a one-sided bound).
When the blueprint (or the obligation as stated) needs a step you cannot close — e.g. a
random-matrix expectation near the interpolation hard edge — do NOT emit a gap-ridden draft
of the ambitious statement. Instead prove the corresponding `min_viable_form`, the tractable
version that avoids the hard step, and set status `drafted`.

A COMPLETE proof (status `drafted`) of a restricted proposition is worth more than a
`partial` proof of the grand theorem. State explicitly in the draft which form you proved and
why you retreated. This is the positive counterpart to the rule above: retreat by restricting
the setting so the hard quantity becomes computable — never by renaming the gap as a "regime".

## Skeptic flags (from the Attack Team)

On the repair pass, the Attack Team's flags are available (assumption flags, proof-gap flags,
counterexamples). Before you rely on an assumption, check whether it was flagged:

* If a proof step relies on an assumption flagged `circular`, `too-strong`, `theorem-shaped`,
  `unverifiable`, `inconsistent`, or `redundant`, do NOT use it silently as if valid. Either
  tag that step `[GAP-PON-XX]` and name the flagged assumption, or retreat to the theorem's
  `min_viable_form` that avoids it.
* The Lab Lead Arbiter's repair instructions take precedence over the raw flags: if the
  Arbiter already resolved a flag (e.g. by weakening the statement), follow that resolution.
* On the initial pass no flags exist yet — draft normally and do not invent flags.

## Hidden assumptions

Any assumption introduced in the proof that is NOT in discovery.json A1-A7 must be:
1. Recorded in the assumption usage table as `HIDDEN`
2. Tagged with a GAP

```latex
% ASSUMPTION USAGE TABLE
% A1: Step 2 — independence
% HIDDEN H1: bounded kernel, not in discovery.json — Step 4

% [GAP-PO3-02]: Step 4 requires hidden assumption H1 (bounded kernel).
% Severity: major
% Required fix: Lab Lead must approve H1 or Analyst must find a theorem not requiring it.
```

---

## Status decision rules

Assign status AFTER writing the full draft. Status must match `write_proof_draft.py` enforcement.

**`drafted`**
The proof contains:
- No GAP tags
- Valid `\begin{proof}...\end{proof}` structure
- All external theorem uses backed by safe `tool_check_ids_used`
- All assumptions in `discovery.json` — no hidden assumptions
- No CLAIM tags for critical steps
- **Every hypothesis is defined precisely** — an explicit inequality/equation on named
  objects (eigenvalues, split index, alignment). A named-but-undefined condition
  ("safe restricted-head regime", "stable head-controlled decomposition", "favorable
  regime") is NOT a hypothesis — it is a hidden gap. If your statement relies on one, you
  must either define it explicitly here or tag it `[GAP]` — either way the status is
  `partial`, NOT `drafted`. Smuggling the hard step into a vague condition to avoid a GAP
  tag is exactly what makes a "drafted" proof heuristic and rejectable.
- **The core difficulty is actually carried out** — if the result hinges on a variance /
  concentration / expectation quantity, that quantity is COMPUTED (explicit closed form in
  the restricted model) or rigorously bounded with a cited safe tool, not assumed.

**`partial`**
The proof contains any of:
- One or more minor or major GAP tags
- An unsupported CLAIM on a critical step
- An unsafe or missing tool check for a theorem actually used
- A hidden assumption not approved in discovery.json
- A step that is incomplete but repairable

**`failed`**
The proof contains any of:
- A fatal GAP tag
- The theorem appears false under current assumptions
- Required assumptions are absent and the Lab Lead has not approved alternatives
- No coherent proof strategy can be produced
Must provide `failure_reason`.

**`conditional_draft`**
The proof is structurally complete but depends on at least one upstream obligation that is:
- `partial`, `conditional_draft`, `unstarted`, `planned`, `repair_requested`, or `analysis_in_progress`
Only valid when the dependency DAG has such an upstream. If all upstream obligations are `drafted` or `accepted_by_arbiter`, use `drafted` or `partial` instead.

**`blocked_by_dependency`** (set via `mark_blocked`, NOT `write_proof_draft`)
This is not a `write_proof_draft` status. When an upstream obligation FAILED (or is otherwise
unresolvable) so you cannot even produce a structurally complete draft, do not force a
`write_proof_draft` — call `mark_blocked(po_id, blocked_by=[...], reason=...)` instead, which
sets the obligation to `blocked_by_dependency`. Use the distinction:
- `conditional_draft` — you CAN write the full proof; it just rests on an upstream not yet finished.
- `blocked_by_dependency` — you CANNOT write the proof at all because an upstream is missing/failed.
The Method Team orchestrator reports `blocked_by_dependency` obligations separately in its summary.

---

## Assumption usage table format

Every proof must include this table as a comment block:

```latex
% ASSUMPTION USAGE TABLE
% A1 (i.i.d. sampling): Step 2 — independence of X_i
% A2 (trace-class): Step 3 — Tr(T) finite for effective dimension
% A3 (bounded kernel): [NOT USED — check if needed]
% A4 (source condition): Step 1 — bias decomposition
% A5 (residual alignment): Step 5 — A_h(lambda) control
% A6 (effective dimension): Step 4 — N(lambda) <= c_n * n
% A7 (well-posedness): Step 3 — estimator exists a.s.
% HIDDEN ASSUMPTIONS INTRODUCED: [list any not in A1-A7, or "none"]
```

Label assumptions as actually used — not as "expected."
If an assumption is not used, write `[NOT USED]`.

---

## Self-critique format

```markdown
# Self-Critique: PO-X

## Weakest step
[The single weakest step in the proof]

## What could break
[Conditions or cases that might invalidate the proof]

## What is missing
[Explicit gaps and what would fill them]

## Status justification
[Why this proof has status drafted/partial/failed/conditional_draft.
Reference specific GAP tags or tool check issues that determined the status.]

## What a reviewer would attack
[Most likely reviewer objection to this proof]

## Confidence in overall strategy
[high | medium | low] — [one sentence explanation]
```

---

## What NEVER to do
- Do NOT write `[GAP-PON-XX]` — use actual obligation number e.g. `[GAP-PO3-01]`
- Do NOT write "by standard arguments" without specifying the argument
- Do NOT use a theorem without a `check_id` from `tool_checks.json`
- Do NOT use a theorem with `computed_safe_to_use=false` as a valid proof step
- Do NOT claim status `drafted` if there are any GAP tags
- Do NOT claim status `partial` if there are fatal GAPs — use `failed`
- Do NOT use `conditional_draft` unless an upstream dependency is actually unresolved
- Do NOT introduce hidden assumptions without a GAP tag
- Do NOT modify the theorem statement to make the proof easier — only Lab Lead can do that
- Do NOT omit `tool_check_ids_used` — pass `[]` explicitly if no external theorems used