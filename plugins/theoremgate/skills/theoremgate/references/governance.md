# Governance

## Authority

- Reasoning roles may propose artifacts only for their assigned stage.
- `auditor` records findings and never edits proofs.
- `governor` decides findings and statements but never writes proof content.
- `synthesizer` derives statements from complete proof records and never upgrades a proof status.
- `novelty_auditor` compares accepted statements with primary sources and does not develop framing.
- `significance_reviewer` audits relevance and evidence independently and does not develop framing.
- `contribution_developer` evaluates paper value but cannot override novelty or significance findings.
- `controller` performs deterministic export only.

The controller enforces the stage actor on completion. Treat actor mismatch as an authority error.

## Proof honesty

- `drafted` means the proof is complete for its recorded scope and has no major/fatal gaps.
- `partial` and `conditional_draft` are not complete proofs.
- A statement may cite only `drafted` or `accepted_by_arbiter` proof records.
- Preserve exact assumptions, proved scope, dependencies, caveats, and known gaps.

## Audit honesty

- Use `minor`, `major`, or `fatal` severity.
- Record an attack method, reproducible evidence, an exact hash-bound source location, affected
  scope, and a resolution condition for every strict finding.
- Keep the base finding unresolved and immutable. Derive effective resolution only from a valid
  hash-chained verification event with persisted evidence.
- Amend severity or wording through hash-chained events; never silently rewrite a finding.
- Use same-run resolution only for a verified false positive or preexisting evidence. Perform a
  genuine proof repair in a linked revision cycle and bind it to the preceding finding with
  `verify-repair`.
- Do not treat a narrowed new statement as retroactively repairing the original audited artifact.
- Every major/fatal local finding requires a Governor decision.
- An unresolved major/fatal finding blocks any statement whose transitive proof or assumption
  closure depends on its target. `based_on` is research provenance and never propagates a blocker
  by itself.

## Arbiter actions

- `theorem_ready`: complete theorem-level result.
- `proposition_ready`: complete narrower or supporting result.
- `repair_requested`: a correctable obligation remains.
- `conjecture_only`: plausible but not proved.
- `rejected`: legacy non-final disposition for unsupported, redundant, or out-of-scope work; retain
  it as unresolved/deferred rather than an established result.
- `invalid`: false, contradicted, or fatally unsound, with an explicitly addressed relevant
  unresolved fatal mathematical finding; exclude it from the scientific portfolio.

Accept an empty theory bundle when no statement clears the gates. Never force a result to justify
writing. Contribution assessment may say `needs_development` or `defer` even when a small theorem is
mathematically sound.

## Autonomous fallback

If Governance classifies at least one serious local mathematical finding as `repair_requested`, the
controller automatically starts a bounded same-run correction before synthesis. Explicitly deferred,
excluded, or invalidated sibling closures keep those dispositions and are removed from the repaired
package rather than suppressing repair of an independent closure. It archives the failed pass,
returns to discovery, and requires a fresh audit. After three failed correction passes—or
when Governance invalidates/defers a claim or the repair would materially change the direction—do
not ask for a decision. Preserve the affected evidence and automatically synthesize only salvageable
proof closures, or persist a null outcome when none remain.

## Writing boundary

`writing_eligible` permits an evidence-bounded document; it does not imply submission readiness. The
deterministic `paper_route` uses `full_paper` whenever a result is accepted and `evidence_report`
otherwise. Downstream writing must consume that route and the strict theory bundle, not raw discovery
targets. Submission framing is enabled only when `submission_readiness` is `ready`.
