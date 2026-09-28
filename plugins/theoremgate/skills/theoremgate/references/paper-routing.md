# Paper routing

Every full run has one manuscript outcome: `full_paper` when at least one mathematical statement is
accepted. Do not assign alternate category or tier labels to accepted-result manuscripts; those
labels conflate the document with the evidence available at one point in the run.

If no statement survives mathematical audit, use `evidence_report`. This is the only alternative to
`full_paper`; it records the attempted claims, proof evidence, counterexamples, audit findings, and
supported future direction without presenting an unproved theorem.

## Separate manuscript generation from submission readiness

For `full_paper`:

- set `writing_allowed: true` and `full_length_allowed: true`;
- include every selected formal result and its complete proof or complete proof appendix;
- record the evidence needed for venue selection without naming or ranking a venue;
- let the venue-formatting agent compare compatible packaged venues and choose the best scholarly fit;
- write, compile, review, revise, and package the complete manuscript;
- use `submission_readiness` to record whether the package is ready for a submission check.

`submission_readiness` is `ready` only when the required novelty, significance, operational,
empirical, review, and venue-rule evidence passes. Otherwise it is `evidence_incomplete`. This status
must not change the manuscript into a different paper category or stop writing.

For `evidence_report`, set `submission_readiness: not_applicable`, use neutral formatting, and include
a complete evidence appendix.

## Claim calibration

Novelty evidence controls wording, not paper generation:

- `verified_novelty`: verified novelty claims are allowed within the audited comparison scope.
- `plausible_incremental_novelty`: describe a plausible incremental contribution and its remaining
  overlap.
- `uncertain_overlap`: foreground the proved technical contribution, disclose unresolved closest-work
  separation, and avoid first, unique, or unprecedented claims.
- `attributed_existing_result`: use proper attribution and present the value as synthesis,
  clarification, derivation, or reproducibility.

Never invent a numeric novelty probability or convert incomplete source verification into a verified
priority claim.

## Automatic continuation

The controller never asks the researcher to choose a paper category, length, route, or venue during a
full run. Run bounded proof repair and contribution strengthening when eligible, then generate the
`full_paper` from every accepted result. Remaining weaknesses become explicit limitations and
submission-readiness conditions. They do not become alternate manuscript types and do not terminate
the paper pipeline.

The route must preserve selected statement IDs, result roles, proof placement, the coherent scientific
argument, originality classifications, significance findings, claim policy, empirical requirements,
and development obligations. Framing never overrides mathematical audits.
