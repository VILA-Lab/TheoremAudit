# User Guide

[Back to the README](../README.md)

This guide covers the user-facing workflow from a research request to inspection and revision.
A fresh checkout contains the plugin; research histories must be generated or supplied separately.

## Contents

- [Start or Select a Run](#start-or-select-a-run)
- [Inspect Research Progress](#inspect-research-progress)
- [Trace a Reviewed Claim](#trace-a-reviewed-claim)
- [Inspect the Manuscript](#inspect-the-manuscript)
- [Request a Revision](#request-a-revision)
- [Export Saved Work](#export-saved-work)

## Start or Select a Run

Install the plugin using the [Quick Start](../README.md#quick-start), then open the local web
interface for your research workspace. In **Research**, enter the research question and any
constraints that define the mathematical setting, evidence requirements, or intended output.

Choose **Start research** to launch a full research-to-paper run. Opening the interface alone does
not start research. To request a theory-only run, use Codex or the terminal's
`start --mode theory` option instead.

The interface initially shows **New research**, with no saved run selected. To inspect existing
work, select it from the run list or open `?run=RUN_ID` on the interface URL. Returning to
**New research** clears the previous paper and activity without clearing your entered question
or constraints. Keep the same workspace path across Codex, web, and terminal access.

## Inspect Research Progress

Use **Research** to monitor a web-launched Codex session and **Stages** to inspect research and
manuscript progress. Saved stages also reflect work launched outside this browser, even when
that work has no associated live console session here.

A stopped execution session and a completed research workflow are different outcomes. If execution
stops before completion, use **Resume run** when offered, or resume the exact identifier from the
terminal. A scientific blocker may require correction or additional evidence rather than another
execution attempt.

Use **Issues** to inspect mathematical objections, proof-related evidence problems, and manuscript
findings. **Inspect** opens the finding's details, suggested action, source, and available evidence
links; it does not start research or modify the run. If a finding led to a revision, inspect both
the finding and the subsequent correction or strengthening round.

This view omits contribution assessments, further-research suggestions, and literature-file
format diagnostics without claim links. These remain in the saved research files and API output;
their omission does not resolve them. A completed run with no mathematical blockers is not
therefore formally verified or cleared for submission. Inspect the contribution assessments
alongside the manuscript before interpreting its readiness.

## Trace a Reviewed Claim

1. Open **Evidence** and inspect the **Results overview** for the selected run.
2. Select **Advanced graph** and search for a theorem or assumption.
3. Select the object to inspect its status, supporting relationships, details, and source path.
4. Use **Core** for main claim relationships and **Stress test** for review-related evidence.
5. Follow supporting proofs and assumptions, then examine the associated review findings.

Earlier statements and proofs are preserved in the run's revision history. The graph displays
the evidence available for the selected run; it is not a visual diff of every historical version.
Use the linked sources and correction or strengthening history to compare earlier and revised work.

Two different changes are worth distinguishing:

| Change | What to inspect |
|---|---|
| **Proof correction** | The defect, the changed assumption or argument, affected dependencies, and renewed review. |
| **Contribution strengthening** | The limitation identified in review, the extended or additional result, its proof, and subsequent contribution assessment. |

Do not describe every revision as an error correction. A valid result may be strengthened because
it does not yet answer a sufficiently informative question.

## Inspect the Manuscript

Use **Paper trace** in the evidence graph to follow available links into manuscript sections.
Open **Paper** to inspect the compiled PDF and the indexed sections. When no compiled manuscript
is available, continue inspecting the research evidence rather than assuming it has been lost.

Compare the manuscript statement with its reviewed assumptions and scope. Then inspect novelty,
significance, and outstanding review findings separately. Mathematical acceptance does not imply
that a result is new, and PDF compilation does not imply submission readiness.

## Request a Revision

Object-specific actions include **Challenge**, **Plan revision**, **Trace evidence**, and
**Strengthen**. They prepare a request tied to the selected run and object. Review that request
before choosing **Run with Codex**; opening the request does not execute it.

For a presentation change, use **Request paper changes** in **Paper**, for example:

```text
Shorten the abstract and improve Figure 2's readability without changing
the theorem statements or their assumptions. Recompile and review the
revised manuscript.
```

For a mathematical change, state the intended change explicitly, for example:

```text
Investigate whether this conclusion still holds under a weaker assumption.
Preserve the earlier result, identify the affected proofs, and review the
revised mathematics before changing its manuscript presentation.
```

The revision workflow distinguishes paper-only edits from changes to completed mathematics.
Do not bypass it by editing accepted evidence files directly.

## Export Saved Work

From the cloned repository, export one selected run:

```bash
python3 ./plugins/theoremgate/scripts/dashboard.py \
  --workspace /absolute/path/to/research-workspace --run RUN_ID build
```

The export is saved under the workspace at `.theoremgate/dashboard/index.html`. It provides a
read-only evidence snapshot without execution controls. Inspect its contents before sharing:
the export does not remove private research or source paths automatically.
