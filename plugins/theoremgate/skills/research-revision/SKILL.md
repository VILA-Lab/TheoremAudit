---
name: research-revision
description: Route and execute requests to resume, retry, repair, re-audit, strengthen, revise literature, rerun experiments, revise a manuscript, respond to reviewer findings or researcher paper-edit instructions, pivot, or start a new TheoremAudit research run while preserving completed evidence. Use when the researcher says rerun, continue, retry, fix the proof, audit again, strengthen for a venue, expand citations or Related Work, redo experiments, rewrite the paper, address review comments, change a paper section, salvage results, or try another topic.
---

# Research Revision

Resolve the installed plugin root and use `../../scripts/revision_router.py`. Bind every operation to
the exact run ID selected by the researcher; never infer a mutable target from “latest.”

## Classify the request

Map the researcher's intent to exactly one action:

| Intent | Action |
|---|---|
| continue unfinished work | `resume` |
| retry the current unfinished stage | `retry_stage` |
| independently inspect an audit again | `independent_reaudit` |
| correct assumptions, theorem, or proof | `repair_mathematics` |
| retain independently proved narrower results | `salvage_results` |
| improve novelty, depth, or publication route | `strengthen_contribution` |
| rerun empirical evidence | `rerun_experiments` |
| expand, replace, or re-audit sources, citations, bibliography, or Related Work coverage | `revise_literature` |
| revise prose or organization using the existing audited source set | `revise_manuscript` |
| select the paper/venue again and write a genuinely new manuscript from the accepted theory | `rewrite_manuscript` |
| change to a materially different direction | `pivot_direction` |
| start unrelated research | `new_run` |

If the wording is ambiguous between operations that change mathematical scope, inspect the run and
choose the least-mutating interpretation that preserves the current question and completed evidence.
Do not ask for a choice and do not interpret “rerun” as “start over.”

## Route paper edits by type

Treat a free-form paper action submitted through the web interface as a governed revision request,
not permission to edit completed files directly. Infer the edit type, scope, target, and earliest
invalidated stage from the researcher's exact text; do not require the researcher to classify the
request.

| Paper edit | Route |
|---|---|
| persisted reviewer findings | Classify every finding by its required action, then choose the earliest affected stage |
| clarity, scholarly writing, section content, or organization | `revise_manuscript` |
| citations, bibliography, source coverage, or Related Work | `revise_literature` |
| figure or table presentation using existing evidence | `revise_manuscript` |
| a figure, table, or empirical claim requiring new evidence | `rerun_experiments` |
| venue/template change or full manuscript rewrite | `rewrite_manuscript` |
| theorem statement, assumption, constant, proof, or mathematical scope | `repair_mathematics` |

For a custom paper-only researcher instruction, persist the request exactly once before editing:

```bash
python3 <plugin-root>/scripts/manuscript_tools.py --workspace . --run RUN_ID \
  add-user-comment --edit-type EDIT_TYPE --scope SCOPE --target TARGET \
  --priority required --text "the researcher's instruction"
```

For `mathematical_claim`, bind the exact instruction to the `revision_router.py plan` and `start`
reason for the linked mathematical revision. Do not reopen the completed parent manuscript merely to
store that request as a paper comment.

A persisted reviewer finding is already revision evidence. Do not copy it into `user_comments.json`
or wait for the researcher to select findings. When independent review reports actionable findings,
handle every open finding automatically in one revision cycle, group compatible edits, and retain one
explicit response per finding ID. Choose the earliest invalidation point needed by any finding,
rebuild all downstream evidence once, compile once, and perform one fresh independent review. Present
the PDF as current only after that cycle closes or after an initially clean review.

## Plan before mutation

Run:

```bash
python3 <plugin-root>/scripts/revision_router.py --workspace . --run RUN_ID plan \
  --action ACTION --target TARGET --reason "researcher request"
```

Honor the returned execution mode:

- `same_run`: retry only the persisted current stage.
- `read_only_reaudit`: write no changes to the evidence being audited.
- `linked_revision`: preserve the parent and create a new evidence cycle.
- `paper_revision`: preserve the theory bundle and revise only downstream paper evidence.
- `new_root`: initialize unrelated research only when the researcher asked for it.

Theory completion is not paper completion. For a `same_run` plan containing
`paper_resume_stage`, continue that exact stage with the manuscript tools. Preserve
the completed theory bundle and paper stages; do not initialize a new theory run.

For `paper_revision`, run the matching `start` command after planning. The controller archives the
affected paper stages and resumes the same run at `paper_resume_stage`. `revise_literature` must
resume at `literature_audit`; never substitute `revise_manuscript`, edit a completed literature
artifact directly, or manipulate `paper_run.json`. After the literature audit, rebuild every
downstream paper stage through independent review and final packaging.

Use `rewrite_manuscript` when the researcher asks for a new manuscript, renewed paper/venue
selection, or a full rewrite. It resumes at `venue_selection`, selects the venue before requiring a
new venue-bound schema-v3 page plan, and rejects unchanged section hashes. Do not route a full rewrite to
`revise_manuscript`, which is only for bounded prose and organization edits.

```bash
python3 <plugin-root>/scripts/revision_router.py --workspace . --run RUN_ID start \
  --action revise_literature --target related_work \
  --reason "expand and re-audit Related Work coverage"
```

## Execute a researcher-approved mathematical revision

For a mathematical repair explicitly requested by the researcher, run `start` with
`--researcher-authorized`. Never start or repeat a revision automatically.

```bash
python3 <plugin-root>/scripts/revision_router.py --workspace . --run RUN_ID start \
  --action repair_mathematics --target PO-4 --reason "repair the filtration gap" \
  --researcher-authorized
```

In the revision, make the smallest defensible correction and then perform a fresh independent audit
before governance. Reuse only hash-verified unaffected evidence. If the same blocker remains,
automatically retain the strongest supported salvage, narrower, negative, or null result within the
approved question; do not ask for another decision.

## Finish with an outcome

Scientific failure changes the result or route; it does not justify a silent dead end. Tooling and
classification errors are repaired automatically. Novelty uncertainty becomes an `unverified`
route. A false theorem becomes a repaired, weakened, salvaged, negative, or invalid result. A human
checkpoint is never opened. Never overwrite completed evidence and never leave a recoverable stage
silently `in_progress`.
