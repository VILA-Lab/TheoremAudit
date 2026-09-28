---
name: theoremgate
description: "Run the complete governed theoretical machine-learning pipeline with the active Codex model: directions, discovery, proofs, adversarial audits, theorem governance, literature, contribution development, experiments, manuscript writing, review, revision, and venue packaging. Use to start, inspect, or continue a resumable TheoremAudit run under `.theoremgate/runs`. Do not use for an isolated ordinary math question that does not need this workflow."
---

# TheoremAudit

TheoremAudit is the current product name; TheoremGate is its former name. Handle
requests using either name with this skill. Keep the installed `theoremgate`
skill identifier, script paths, and `.theoremgate/` run storage unchanged.

Use the active Codex model. Do not call a separate model API, choose a model inside the skill, or
launch the repository's legacy `main.py`.

## Locate the controller

Resolve this installed skill directory, then resolve `../../scripts/workflow.py` to an absolute
path. Pass the user's current working directory through `--workspace`.

Read `references/executable-tools.md` before using packaged tool commands.

When the user asks for a visual status view, route to `$dashboard`; it renders persisted artifacts
without changing workflow state.

Classify the requested deliverable before initialization, because this determines which controller
mode is allowed:

- Use a **full** run when the user asks for a paper-facing outcome, including requests to write,
  generate, prepare, submit, revise, or package a paper, manuscript, workshop paper, conference
  paper, technical report, arXiv draft, or complete research-to-paper result.
- Use a **theory-only** run only when the user explicitly asks to stop after theorem development,
  proof evidence, audit, governance, or a governed theory bundle.
- If the user asks to "do the research," "make the strongest result," "turn this into a paper," or
  gives a publication goal, treat the request as **full**.
- If the wording is ambiguous, preserve the user's stated scope: start **full** only when the
  requested output is paper-facing; otherwise start **theory-only** when the request is limited to
  theorem/proof development.

## Direct launches must use the Pipeline Continuation Controller

When this skill is invoked directly from chat or the CLI for a new run, do not call
`workflow.py init` yourself. Launch the long-lived Pipeline Continuation Controller instead:

```bash
python3 <plugin-root>/scripts/direct_pipeline.py --workspace . start \
  --question "the research question" \
  --constraints "optional researcher constraints"
```

The default is a full original-research attempt. Only when the researcher explicitly requests a
theory-only run, add `--mode theory`.

For a direct request to continue an exact existing run, use:

```bash
python3 <plugin-root>/scripts/direct_pipeline.py --workspace . resume --run RUN_ID
```

Keep polling the yielded process until it emits one terminal event: `pipeline_completed`,
`continuation_budget_exhausted`, or `continuation_failed`. The Pipeline Continuation Controller owns
the initial Codex turn plus at most three automatic continuation turns within the same run. A
continuation turn ending with a progress summary such as “proof development in progress” is not a
terminal execution outcome and must never be returned to the researcher as completion. These
continuation turns are not child runs. When the continuation budget is exhausted, report the exact
preserved stage and reason without implying that researcher intervention is needed.

Web-interface run contracts already use the web-interface job runner. Do not launch a second
Pipeline Continuation Controller for them; continue the exact supplied run normally.

Controller-only fallback for initializing a full research-to-paper run:

```bash
python3 <plugin-root>/scripts/workflow.py --workspace . init \
  --question "the research question" \
  --intent new_full --requested-mode full --publication-goal original_research
```

Initialize an explicitly theory-only run:

```bash
python3 <plugin-root>/scripts/workflow.py --workspace . init \
  --question "the research question" \
  --intent new_theory --requested-mode theory
```

Capture the `run_dir` returned by `init`, take its final path component as `RUN_ID`, and bind the
entire task to that exact run. Pass `--run RUN_ID` to every subsequent theory and manuscript
controller command. Never rely on the implicit latest-run pointer for a mutating operation.

Honor the user's run intent literally:

- **New run:** call `init` once, then work only on the returned run ID. Never substitute an older run.
- **Resume:** do not call `init`; resolve the explicitly selected run and continue its current stage.
- **Repair after completed or materially changed theory:** call
  `init --parent-run PARENT_ID --intent repair`, then work only in the returned linked child run.
  The parent run remains preserved and the child run records `parent_run_id`.

For requests such as rerun, retry, audit again, repair, salvage, strengthen, redo experiments, or
rewrite the manuscript, route through `$research-revision` and `scripts/revision_router.py` before
mutating state. Do not interpret “rerun” as a new root run.

A request to select the paper or venue again and write a new manuscript is
`rewrite_manuscript`, not a template-only venue change and not a bounded prose revision. Reopen the
same paper at `venue_selection`, select the best-fit venue, then create a venue-bound page-aware architecture,
rewrite every section, compile within the enforced venue and component constraints, and repeat review
and packaging. This same venue-first page-aware sequence is mandatory during the first paper run.

A request for more citations, a comprehensive Related Work section, bibliography expansion, or new
closest-work verification is `revise_literature`, not an ordinary prose revision. Start the routed
paper revision at `literature_audit`; do not edit the completed audit or paper manifest directly.

When the web interface supplies a run contract, the run is already initialized or selected. Do not call
`init`, create another run, or change to the latest run.

## Run autonomously without confirmation prompts

An explicit request to start, resume, repair, or write is the authorization to execute. Start
immediately; never ask the researcher to reply “confirmed,” approve a direction, choose among routine
repair/salvage options, accept a lower publication route, select a venue template, or authorize paper
writing. Select the strongest feasible direction within scope, execute bounded proof repair and
contribution strengthening, choose the strongest honest route, and—for a full run—always write the
strongest evidence-consistent document.

Autonomy never authorizes changing the central research question, inventing evidence, weakening the
correctness standard, or using unsupported submission claims. It may narrow a theorem when that is
the strongest valid result, but every accepted result still receives a `full_paper`. If no statement
survives audit, write an `evidence_report` with a complete evidence appendix. Never fabricate a
theorem or proof.

Inspect the bound run:

```bash
python3 <plugin-root>/scripts/workflow.py --workspace . status --run RUN_ID
```

Never silently overwrite completed evidence. Before theorem synthesis, a governed local-audit repair
may use `$proof-repair`: the controller archives the failed pass under `corrections/` and returns the
same run to discovery for a bounded correction and fresh audit. Use a linked child run only after a
frozen theory bundle, for a topic/contribution change, or when the researcher explicitly requests a
separate revision.

## Execute the governed theory stage

1. Read `references/workflow.md` and identify the current stage, actor, artifact, and routed role.
2. Read only the matching section in `references/artifacts.md`.
3. Read `references/governance.md` for audits, governance, synthesis, Arbiter, contribution, or
   theory-bundle stages.
4. Read `references/paper-routing.md` for novelty audit, significance audit, contribution assessment, or theory-bundle
   stages. Route to the matching specialist skill listed in `references/capability-map.md`. Perform the
   reasoning with the active Codex model. For an independent audit or review, begin a fresh pass and
   inspect only persisted artifacts; do not reuse proof-authoring reasoning as audit evidence.
5. Write the required artifact into the run directory.
   For either adversarial-audit stage, use `audit_findings.py record-attack-summary` after the
   attack pass. If a late finding changes that summary, use `revise-attack-summary --reason ...`;
   never edit the audit JSON or recompute its hashes manually. Schema-v4 summaries are bound to a
   separate operation ledger and direct edits must fail validation. A finding-free audit still
   requires persisted targets, methods, and evidence; never manufacture an empty audit object and
   call it independent review.
6. Validate it:

   ```bash
   python3 <plugin-root>/scripts/workflow.py --workspace . validate --run RUN_ID
   ```

7. Complete it with the exact actor listed by `status`:

   ```bash
   python3 <plugin-root>/scripts/workflow.py --workspace . complete --run RUN_ID --actor <actor>
   ```

8. Re-run `status` and continue only when the user's request covers the next stage.

If completing Governance returns `next_action.type == "same_run_proof_correction"`, immediately route
to `$proof-repair` and continue the exact run ID from discovery. Do not synthesize the failed proof,
create a child run, or ask for routine correction approval.

If completing the theory-bundle stage returns
`next_action.type == "same_run_contribution_strengthening"`, route to
`$contribution-strengthening` and continue the exact run from its reported resume stage. Preserve the
accepted result and target the routing gates that prevent the researcher-selected publication goal.
After the two-pass strengthening budget, finalize and use the strongest honest route without asking
for another choice.

For full runs targeting original research or a workshop paper, discovery must pass the
publication-strength theorem gate. Require a nonvacuous primary theorem with a concrete technical
obstacle, an explicit theorem-level novelty delta and closest-work boundary, and a complete proof
route. Also require a distinct proof-obligated companion result unless the primary theorem has a
recorded exceptional-depth justification. A renamed standard result, direct specialization,
assumption-shaped conclusion, vacuous companion, or ornamental mathematics does not satisfy this
gate.

## Preserve role separation

- Do not let proof authors perform their own adversarial audit.
- Do not edit a proof while acting as auditor; persist a finding.
- Do not let the synthesizer repair a proof or invent support.
- Do not let the Governor or Arbiter hide unresolved findings.
- Do not let contribution framing override the independent novelty or significance audits.
- Treat deterministic validation failure as a requirement to repair the in-progress artifact or its
  recoverable evidence classification. Do not bypass validation. If the scientific evidence remains
  insufficient after repair, complete the stage with the schema's conservative evidence outcome
  (`unclear`, `unverified`, or narrow significance) instead of leaving it in progress.

## Always produce an execution outcome

A theorem or novelty claim may fail; the execution must still finish
with a useful persisted outcome. For recoverable tool or registry problems, repair them and continue.
For insufficient novelty, significance, or empirical evidence, complete the remaining audits and
write the strongest honest full paper supported by the accepted mathematics. Before finalizing
incomplete submission evidence,
automatically attempt at most two `$contribution-strengthening` passes. Each pass must add scientific
evidence—not framing—and repeat every affected correctness, novelty, and significance gate. When no
accepted mathematical result exists, preserve the null-result theory bundle and write an
`evidence_report` with its evidence, limitations, audited failure, and available future directions.

Automatically attempt at most three same-run proof corrections when Governance classifies at least one
serious local mathematical finding as `repair_requested`. A deferred, excluded, or invalidated
sibling closure must not suppress repair of an independent primary closure; preserve that sibling's
disposition and omit it from the repaired package. This is correction of the approved direction, not
a new research revision. Preserve each failed pass and require a fresh independent audit. Do not
automatically revise novelty, significance, contribution framing, experiments, or a completed theory
bundle. When the correction budget is exhausted, preserve only supported proof closures and complete
an honest salvage or null outcome. Do not materially change the approved research direction.

Automatically attempt at most two same-run contribution-strengthening passes when accepted
mathematics exists but the deterministic route does not satisfy the publication goal. Preserve the
accepted theorem package, select one coherent missing contribution, and rerun the affected stages.
Do not automatically change the central question or stack unrelated theorems. After the budget,
complete the strongest honest route. In a full run, always write it automatically.

For every full run with at least one accepted statement, write a full-length venue-oriented paper
with labeled main results and complete appendix proofs. Partial or unverified novelty changes the
allowed originality wording and `submission_ready` status; it must not shorten the paper, suppress
the technical contribution, or force neutral formatting. Assign a best-fit provisional named venue
automatically and preserve any official-rule or redistribution warnings. Use neutral
`Research-Draft` formatting only for `evidence_report` outputs.

Do not pause for user input. If an external system failure prevents safe persistence, record the exact
failure and preserved state. Never end an execution with only “blocked,” never leave a recoverable
stage silently `in_progress`, and never start a different run outside the research scope.

## Continue into the paper pipeline

After `artifacts/theory_bundle.json` is completed, read `references/paper-workflow.md`. For a full
run, start the separate controller; completed full-run bundles always provide a writable route:

```bash
python3 <plugin-root>/scripts/manuscript_workflow.py --workspace . --run RUN_ID init
```

For a full run, the start request authorizes writing the strongest deterministic route whose bundle
permits writing, including an evidence-complete research draft below the
aspirational goal. Do not request a separate `write` decision.

For its current stage, write the requested artifact beneath the run's `paper/` directory, validate,
and complete with the exact actor reported by status:

```bash
python3 <plugin-root>/scripts/manuscript_workflow.py --workspace . --run RUN_ID status
python3 <plugin-root>/scripts/manuscript_workflow.py --workspace . --run RUN_ID validate
python3 <plugin-root>/scripts/manuscript_workflow.py --workspace . --run RUN_ID complete --actor <actor>
```

Never alter completed theory artifacts to improve the paper. A post-bundle mathematical change
requires a linked child run with `parent_run_id`, so the original accepted evidence remains
preserved. Venue template files are development snapshots; verify official current requirements and
redistribution rights before submission or public release.

Never draft a substitute manuscript before this handoff. Do not create `papers/*.md`, a standalone
paper-like Markdown file, `paper.tex`, or manuscript prose with `apply_patch`, shell redirection, or
an ordinary file-writing tool. The only authorized manuscript root is the exact run's `paper/`
directory after `manuscript_workflow.py init` succeeds. Write sections with `manuscript_tools.py`,
and verify the paper workflow before reporting any manuscript path. Automatically continue a
recoverable incomplete execution up to three times; after that bounded limit, report the exact
preserved stage without presenting a choice form.
