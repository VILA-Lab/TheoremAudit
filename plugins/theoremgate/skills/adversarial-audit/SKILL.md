---
name: adversarial-audit
description: Independently attack theoretical claims, proofs, assumptions, novelty, and scope; search for counterexamples; and issue severity-ranked findings without editing the target. Use for local or final TheoremAudit audits and skeptical mathematical review.
---

# Adversarial Audit

Read `assumption-attack.md` and `counterexample-search.md` under
`../theoremgate/references/source-skills/`.

Maintain role separation: inspect persisted artifacts and do not repair them while auditing. Test
quantifiers, conditioning, edge cases, degenerate parameters, hidden regularity, dependency closure,
citation entailment, novelty, and whether informal prose exceeds the formal statement.

Each finding needs a globally qualified stable ID (`LOCAL-*` or `FINAL-*`), target ID, controlled
kind, severity (`minor`, `major`, or `fatal`), attack method, reproducible evidence, hash-bound source
location, affected scope, and a concrete resolution condition. A failed attack is evidence of
scrutiny, not a proof. Use `RUN` only for a defect that genuinely affects every statement.

Use `../../scripts/audit_findings.py` to `add` immutable findings, append `amend` or `resolve`
verification events, verify a linked child repair when applicable, and persist Governance and
Arbiter decisions. `resolve` is only for a demonstrated false positive or evidence that already
existed when the audit began; it must never disguise a repair. A pre-synthesis repairable local
finding routes through `$proof-repair`, which archives the failed pass and requires a new audit.
Post-bundle or materially changed repairs require a linked child. Events form one SHA-256 chain and
never rewrite the base finding. Record whether verification used an `independent_subagent`,
`fresh_role_review`, or `external_check`; do not claim stronger independence than actually occurred.
Always pass the actor assigned by the current manifest
with `--actor` (`auditor` for adversarial-audit stages and `governor` for governance or Arbiter
stages). Use `invalidated`/`invalid` only for a false, contradicted, or fatally unsound statement
supported by a relevant unresolved fatal mathematical finding. Keep repairable or merely unproved
statements in their corresponding non-final statuses. Every `findings_addressed` ID must exist and
be relevant to that synthesized statement.
