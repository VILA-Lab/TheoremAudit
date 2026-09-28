---
name: theorem-synthesis
description: "Write the paper's theorem statements to FIT what was actually proven — the human move of stating the theorem last, after the proof. Reads the proof store (which obligations are drafted and their real proven scope: assumptions actually used, regime, one-sided vs full) and registers synthesized statements in theorem_state.statements. This is what lets a proved-but-smaller result become committable, instead of dying as a conjecture. Runs after proving, before the final arbiter."
version: 1.0
used_by: lab_lead
domain: theoretical machine learning
inputs: discovery.json, theorem_state.json, state/proofs/*
outputs: theorem_state.statements (via commit)
---

# Theorem synthesis — state the theorem to fit the proof

## Why this skill exists
In a real theory paper the final theorem is written *last*, to match exactly what the proof
delivered — scope, assumptions, and even the type of result (upper bound vs iff) are settled by
what actually held. TheoremAudit's discovery only holds *targets*; the Method Team then proves
whatever it could. This skill closes the loop: it reads what was genuinely proved and writes the
statements the paper will actually claim.

Without this step, a smaller-but-real proved result has nowhere to live — the arbiter can only
weaken the ambitious target to a conjecture, and nothing commits. Synthesis is what makes the
theorem an OUTPUT of proving.

## What counts as "proven"
Only obligations whose proof draft is `drafted` (referee-grade, complete) count. A `partial`,
`failed`, `blocked`, or `conditional_draft` obligation is NOT proven — do not synthesize a
statement that rests on it. For each drafted obligation, read its actual proof (read_proof) and
extract the **true scope**:
- which assumptions the proof *actually used* (the assumption-usage table) — not the discovery's
  full assumption list, only what the proof needed;
- the regime it actually covers (e.g. Gaussian design only, conditional on rank(X)=n, finite p);
- the direction/strength actually established (one-sided bound? exact constant? existence only?).

## How to synthesize
1. Read the proof store: for every `drafted` obligation, read_proof(po_id) and note what it proves
   and under what scope. Use the discovery's `supports` map to see which lemma/target each
   obligation feeds.
2. Find the strongest TRUE statement the connected set of drafted proofs supports. Start from the
   `primary_target`: state the exact form the proofs establish (usually the narrowed/reshaped
   form, not the ambitious original).
3. For each such statement, register it with `commit`:
   `commit(section="statements", key="TH-1", value={ ...schema below... })`.
   Number them TH-1, TH-2, … Synthesize a statement ONLY if drafted proofs actually support it.
4. If NOTHING is fully drafted, write no statements — that is an honest empty result (the
   submission gate will report NO-GO). Do not fabricate a statement to fill the gap.

### Statement schema
```json
{
  "id": "TH-1",
  "informal": "Plain-language statement of what was actually proved",
  "formal": "The precise statement, with the assumptions and regime the proof truly needs",
  "assumptions_used": ["A1", "A3"],
  "proven_scope": "e.g. Gaussian design only; conditional on rank(X)=n; upper bound only",
  "result_type": "upper-bound | lower-bound | separation | impossibility | exact-formula | construction",
  "synthesized_from": ["PO-1", "PO-2"],
  "based_on": "T1",
  "status": "synthesized",
  "honest_caveats": "Anything the proof does NOT establish (what a referee must not be misled about)"
}
```

## Honesty rules — the whole point is a truthful statement
- State ONLY what the drafted proofs establish. If the proof is one-sided, the statement is
  one-sided. If it needs Gaussian design, say Gaussian design.
- `assumptions_used` lists what the proof actually invoked — usually a SUBSET of the discovery's
  assumptions. Narrower is more honest and stronger.
- Never restore the ambitious original if only the narrowed form was proved.
- Do NOT synthesize from `partial`/`failed`/`conditional` proofs.
- A synthesized statement is a candidate for the arbiter to commit — not yet committed. Keep
  `status: "synthesized"`.

## What NOT to do
- Do NOT prove anything here — proving is done; you only state what holds.
- Do NOT overclaim scope beyond the drafted proofs.
- Do NOT invent a statement when nothing is drafted — an empty result is honest.
- Do NOT edit the discovery or the proofs — only write theorem_state.statements.
