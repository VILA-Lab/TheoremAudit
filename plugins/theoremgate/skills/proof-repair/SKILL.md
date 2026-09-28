---
name: proof-repair
description: "Correct a repairable mathematical defect found by a TheoremAudit local adversarial audit, then rebuild and independently re-audit the affected proof closure in the same governed run. Use when Governance records major or fatal findings as repair_requested, including false assumptions, missing measurability, invalid concentration constants, boundary failures, dependency gaps, or theorem/proof scope mismatches. Do not use for novelty or significance weakness, a rejected research direction, post-bundle strengthening, or a change of topic."
---

# Proof Repair

Repair audited mathematics without hiding the failed attempt or creating an unnecessary child run.
The controller preserves the previous pass under `corrections/round-XX/` and returns the same run to
discovery so assumptions, targets, proof obligations, and audits stay aligned.

## Trigger boundary

Use this skill only when all of the following are true:

- the current stage is `discovery` because `workflow.py complete` routed a governed correction;
- `run.json.correction_state.status` is `in_progress`;
- the correction record names one or more local-audit findings;
- Governance classified at least one serious mathematical finding as `repair_requested`; any other
  serious findings have explicit `deferred`, `excluded`, `invalidated`, or `cleared` dispositions;
- the research question and selected direction remain unchanged.

Do not invoke it merely because a proof is difficult. Do not use it to improve novelty, significance,
experiments, or writing. Those require their own stages or an explicitly authorized research revision.

## Correction procedure

1. Bind every command to the exact run ID. Read `run.json`, the current correction record, and the
   archived `local_audit.json`, `governance_review.json`, discovery artifact, proof index, and cited
   proof sources from the correction archive.
   If `nonrepair_dispositions` is nonempty, preserve those decisions: remove deferred, excluded, or
   invalidated targets from the repaired theorem package instead of letting them suppress repair of
   an independent closure.
2. Restate each finding as a concrete failed implication: identify the assumption, proof step,
   conclusion, and counterexample or missing condition.
3. Choose the smallest scientifically honest repair:
   - correct a definition or endpoint convention;
   - strengthen or operationalize an assumption;
   - weaken the theorem conclusion to the proved rate or scope;
   - replace an invalid lemma or concentration argument;
   - split an unsupported target from an independently provable result.
4. Reject repairs that make the theorem vacuous, assume the conclusion, silently change the topic,
   or rely on an unverified literature claim.
5. Rewrite discovery first. Every changed assumption must propagate to theorem targets and proof
   obligations. Then rerun exploration, including the counterexample that broke the previous pass.
6. Rebuild every proof in the affected transitive dependency closure. Reusing unchanged reasoning is
   allowed only after checking it under the repaired assumptions; write new proof artifacts and hashes.
7. Enter local adversarial audit with a fresh reasoning pass. The auditor must inspect only persisted
   repaired artifacts and must explicitly replay the original attack plus assumption, boundary,
   dependency, counterexample, and scope attacks.
8. Complete Governance. If the repair passes, continue to synthesis. If another repairable serious
   defect appears, the controller may start another same-run correction. After three failed passes,
   stop repairing and automatically synthesize only independently supported proof closures, or
   persist a null-result bundle when none remain.

## Autonomous scope boundary

Never ask the researcher for confirmation, approval, or a choice during repair. Starting or resuming
the governed run authorizes all routine in-scope corrections and the strongest honest fallback.
The repair may narrow a theorem to what the evidence proves, but it must not lower the correctness
standard. It must not:

- change the central research question, application domain, or contribution type;
- choose among materially different papers by silently changing topic;
- make the theorem vacuous or assume its conclusion;
- continue repair after the three-pass budget;
- invent evidence or promote an unsupported publication route.

When one of these boundaries is reached, preserve the evidence and automatically complete the
strongest supported narrower or null outcome inside the existing research question. Report that
outcome at the end; do not pause and ask what to do next.

## Required outcome

Never report merely “blocked.” Leave the run in one of these explicit states:

- repaired and past fresh audit;
- undergoing correction pass 1, 2, or 3 with the exact findings shown;
- completed with an honest narrower result or null-result bundle.

The existence of this skill does not guarantee that every proposed theorem is true. Its purpose is to
make failed proof attempts recoverable, visible, bounded, and mathematically rechecked.
