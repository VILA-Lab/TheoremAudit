---
name: counterexample-search
description: "Construct explicit examples that attack the current committed form of theorem candidates and lemmas. Distinguishes true counterexamples (satisfy all assumptions, violate the conclusion) from necessity and boundary examples, calibrates confidence, and records them via propose_counterexample. Venue- and domain-agnostic."
version: 2.0
used_by: counterexample_finder
inputs: discovery.json, theorem_state.json (skeptic_flags, decisions, statements), proofs/ if present
outputs: counterexamples (via propose_counterexample tool)
---

# Counterexample Search Skill

## Purpose
Stress-test each target statement before it is proved (or after it is committed) by trying to
build an explicit example that breaks it. A found example is valuable either way: a true
counterexample refutes the statement and saves wasted proof effort; a necessity or boundary
example sharpens the assumptions or the scope.

Be adversarial but honest: only record what you can actually construct, and label it precisely.

## Attack the CURRENT form, not an earlier one
Statements may have been weakened by the Arbiter. Always attack the **controlling committed
form** — use `new_form` → `governed_form` → `form` (first non-empty), and the current
`decisions`/`statements` in `theorem_state`. Do NOT attack the original ambitious version:
"refuting" a claim the paper no longer makes is a false positive.

## Three kinds of example — label them correctly
This is the single most important distinction, and it maps to `example_type`:

- **`counterexample`** — the construction satisfies **every** assumption of the target yet
  **violates its conclusion**. This *refutes* the statement. `satisfies_all_assumptions`
  must be true.
- **`necessity`** — the construction **violates one assumption** and then breaks the
  conclusion. This does NOT refute the theorem; it shows that assumption is *needed*.
- **`boundary`** — an in-scope extreme case that probes how *tight* the result is (e.g.
  approaches an inequality with equality) without violating it.

If you cannot make the construction satisfy all assumptions, it is not a counterexample —
record it as `necessity` or `boundary`.

Field settings per type (note: `violates` is a STRING describing what is broken, NOT a
boolean; the true/false logic is carried by `satisfies_all_assumptions`):

- `counterexample`: `satisfies_all_assumptions=true`; `violates` = the conclusion/inequality
  it breaks and by how much.
- `necessity`: `satisfies_all_assumptions=false`; `violates` = the conclusion it breaks
  (which happens only after violating an assumption — name that assumption too).
- `boundary`: `satisfies_all_assumptions=true`; `violates` = "" (leave empty — a boundary
  example shows tightness/extremal behavior, it does not break the conclusion).


## When to use
After the Senior Skeptic has written assumption flags. Read
`theorem_state → skeptic_flags → assumption_flags` first: high-severity flags point to the
weakest parts of the argument, which is where refuting or necessity examples most likely live.

## Search strategy (domain-agnostic)
1. **Start from the flagged weak points**, then the assumptions the conclusion most depends on.
2. **Try the simplest explicit construction first.** Prefer the smallest, most concrete
   instance of the paper's OWN setting in which the relevant quantities can be computed in
   closed form. What counts as "simple" is set by the paper's domain — do not assume a
   particular model family, kernel, or distribution.
3. **Compute, don't gesture.** A construction is a counterexample only if you can actually
   exhibit both the assumption-satisfaction and the conclusion-violation concretely.
4. **Escalate** to less trivial constructions only if the simple ones fail.

## Using prior work (optional, fetched-only)
Searching the literature for known counterexamples is useful but NOT required, and must never
rely on memory:
- Use `web_search`/`web_fetch` only if they are available in this run.
- You may reference a known counterexample only if you fetched it from a real URL this session.
- If search is unavailable or returns nothing, proceed with your own constructions — never
  invent a "known" counterexample from memory.

## Confidence calibration — define sharply
- **`verified`** — you carried out the construction and *checked* both that it satisfies the
  assumptions and that it violates (or tightly meets) the conclusion, with explicit values or
  a complete elementary argument.
- **`plausible`** — a strong analytic argument that the construction works, but at least one
  step is not fully computed (e.g. a constant or limit left implicit).
- **`speculative`** — a heuristic or partial idea, not yet checked. Record these only when
  they point at a real risk worth investigating; never present them as refutations.

## Severity
- **`fatal`** — a `verified` counterexample that refutes the committed statement.
- **`major`** — forces a new assumption or a scope restriction (typical for necessity
  examples), or a plausible-but-unverified counterexample worth blocking on.
- **`minor`** — a boundary/tightness observation, or a speculative lead.

## Procedure
1. Read the committed targets and the assumption flags.
2. For each target, in flag-severity order, attempt a construction per the strategy above.
3. For each construction, determine `example_type` honestly (does it satisfy ALL assumptions?).
4. Set `confidence` and `severity` per the definitions above.

Use only the allowed values:
- `example_type`: `counterexample`, `necessity`, `boundary`
- `confidence`: `verified`, `plausible`, `speculative`
- `severity`: `fatal`, `major`, `minor`

5. Call `propose_counterexample(target_id, example_type, construction, confidence,
   violates, satisfies_all_assumptions, severity, suggested_action)`.
6. If nothing breaks a target after honest effort, record no example for it — that is a valid,
   useful outcome (it supports proving the statement).

## Hard rules
- Attack the current/committed form only.
- A `counterexample` MUST satisfy all assumptions; otherwise label it `necessity`/`boundary`.
- Only `verified` examples justify `fatal` severity.
- No memory-sourced "known counterexamples" — fetched from a real URL, or your own construction.
- Do not fabricate a construction to force a refutation.
- Do not hardcode a model family, notation, or statement IDs from any one paper — read them
  from the current `discovery.json`/`theorem_state`.

## What NOT to do
- Do not call a construction a counterexample when it violates an assumption.
- Do not attack the pre-weakening ambitious form.
- Do not rate a speculative lead as fatal.
- Do not skip a target just because the Skeptic did not flag its assumptions — check the
  conclusion-critical assumptions too.
- Do not depend on `web_search` being present.
