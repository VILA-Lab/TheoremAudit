---
name: contribution-development
description: Assess and strengthen the paper-level contribution of audited theoretical results without changing what was proved. Use after theorem governance to decide framing, differentiation, missing evidence, and writing readiness.
---

# Contribution Development

Read `../theoremgate/references/source-skills/contribution-development.md` and the preserved
`contribution_developer-prompts.py` role reference. Work only from accepted theorem records,
supporting proofs, audits, and verified literature.

Use those preserved files for research judgment and their unified submission-evidence terminology;
do not introduce alternate manuscript categories.

First read `artifacts/novelty_audit.json` and `artifacts/significance_audit.json`; do not override
their classifications, blockers, or application-evidence assessment.
Identify significance, audience, strongest honest framing, missing comparisons, and required
empirical or expository support. Do not inflate an attributed specialization into a novel theorem.
Do not repair mathematics in this role.

Never classify accepted mathematics as `null_result`. When an accepted theorem, lower bound, or
counterexample has `unclear` originality, use `provisional_result`; it still receives a `full_paper`
with calibrated novelty language while submission readiness remains incomplete. Reserve
`null_result` for an empty accepted scope.

For every full run, use the controller's `original_research` acceptance goal without asking the user
to choose a tier. Build one coherent scientific argument and assign
every accepted statement a result role, dependency list, and placement: main, supporting, appendix,
separate paper, or deferred. Positive theorems, lower bounds, counterexamples, and negative boundary
results may share one paper when they answer the same central question. Do not force unrelated valid
results into one manuscript, and do not discard them; route them to a separate paper or defer them.

Return the schema in `../theoremgate/references/artifacts.md`: publication goal, coherent paper argument,
result roles and placements, contribution type, significance, primary statement IDs, paper value,
claim policy, development obligations, and empirical requirements. Do not choose a manuscript
category; `paper_router.py` assigns `full_paper` to accepted results and independently derives
submission readiness from the evidence.

The publication goal is a user constraint, not evidence. Preserve it exactly. The router reports
whether that goal is satisfied and exposes the novelty, significance, application, parameter,
baseline, theoretical-depth, and blocker gates separately. If the user requests original research
but the audits support only attributed positioning, retain the valid results in the full paper and
report the unmet submission goal;
never manufacture novelty or silently change the user's goal.

When the selected goal is unmet, make each blocking development obligation executable: name the
missing theorem, assumption relaxation, lower bound, method, comparison, or evidence and explain
which routing gate it could change. The controller may route these obligations through
`$contribution-strengthening`; this role proposes the scientific need but does not alter proofs.
