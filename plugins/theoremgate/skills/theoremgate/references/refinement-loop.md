# Bounded proof correction

TheoremAudit does not run a hidden Method-Team/Attack-Team agent loop. Codex executes the governed
stages in order, using persisted artifacts between roles and its own configuration for delegation.

When local audit finds a repairable mathematical defect:

1. the auditor records the finding without editing the proof;
2. Governance records `repair_requested`;
3. the controller archives the failed pass beneath `corrections/round-XX/`;
4. the same run returns to discovery and `$proof-repair` makes the smallest valid correction;
5. exploration, proof development, local audit, and Governance run again;
6. after three failed correction passes, correction stops and the controller automatically preserves
   the strongest independently supported narrower or null outcome.

Do not use this mechanism for novelty, significance, experiments, manuscript revision, a new topic,
or post-bundle strengthening. Those use ordinary stage completion or a linked revision explicitly
requested before it begins; the active run never pauses to solicit that request.
