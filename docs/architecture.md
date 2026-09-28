# Architecture and Reference

[Back to the README](../README.md)

This reference describes the research stages, packaged skills, executable tools, and evidence
storage used by TheoremAudit. For installation and user-facing commands, start with the
[Quick Start](../README.md#quick-start).

## Contents

- [Framework at a Glance](#framework-at-a-glance)
- [How It Works](#how-it-works)
- [Reasoning Skills](#reasoning-skills)
- [Executable Tools and Controllers](#executable-tools-and-controllers)
- [Governed Theory Workflow](#governed-theory-workflow)
- [Repair and Revision Semantics](#repair-and-revision-semantics)
- [Manuscript Workflow](#manuscript-workflow)
- [Run Directory](#run-directory)
- [Plugin Structure](#plugin-structure)

## Framework at a Glance

| Layer | Important components | Purpose |
|---|---|---|
| **Access interfaces** | Codex conversation; web interface; terminal interface | Let the researcher choose a conversational, visual, or scriptable entry point while using the same governed state |
| **Reasoning skills** | Direction, discovery, proof, audit, repair, literature, significance, contribution, experiments, manuscript, review, and venue skills | Produce role-specific research artifacts with the active Codex model |
| **Governance and control** | Workflow, proof validation, audit ledger, repair, revision routing, paper routing, and manuscript workflow | Validate artifacts and decide whether the run may advance |
| **Executable research tools** | Proof, literature, citation, experiment, figure, manuscript, and venue utilities | Record structured evidence and perform bounded operations |
| **Persistent evidence store** | `run.json`, `artifacts/`, `proofs/`, `literature/`, and `paper/` | Preserve provenance, dependencies, findings, decisions, and publication outputs |

The layers serve different purposes. Skills guide research reasoning; tools record or inspect
structured evidence; controllers enforce workflow rules; the run directory preserves the resulting
scientific record. The web interface adds run controls and revision actions to the evidence views,
while the terminal interface exposes the same governed operations for reproducible
execution.

## How It Works

The researcher chooses the objective and run intent. The governance layer chooses routine internal
stages, assigned actors, bounded repair routes, and evidence-supported publication routing.

### 1. Enter the governed workflow

TheoremAudit advances a run through three governed phases:

<p align="center">
  <img
    src="figures/Theormaudit.png"
    alt="TheoremAudit evidence-governed research workflow"
    width="72%"
  />
</p>

<p align="center">
  <em>
    Internal workflow from research formulation through mathematical validation, contribution
    assessment, and manuscript development.
  </em>
</p>

| Phase | Main stages | Evidence produced |
|---|---|---|
| **Research formulation** | Direction generation, direction selection, discovery, exploration | Candidate directions, selected direction, definitions, assumptions, theorem targets, proof obligations, and feasibility probes |
| **Proof and governance** | Proof development, local adversarial audit, governance review, theorem synthesis, final adversarial audit, arbitration | Proof records, dependency graph, audit findings, governance decisions, synthesized statements, and accepted or rejected mathematical status |
| **Contribution and publication** | Novelty audit, significance audit, contribution assessment, theory bundle, optional manuscript workflow | Literature evidence, novelty boundaries, significance assessment, contribution policy, paper route, and manuscript authorization |

At each stage, the active Codex model produces the required research output. TheoremAudit's tools
check its structure and supporting references before the run can advance. These software checks
are distinct from model-based assessment of mathematical arguments. If a claim fails validation or audit, TheoremAudit preserves the
failed attempt and routes the run to repair, narrowing, rejection, deferral, or an evidence report.

### 2. Complete each governed stage

A normal stage transition is:

1. The controller reads `run.json` and identifies the current stage, assigned actor, and required
   artifact.
2. Codex performs the stage-specific reasoning using the corresponding TheoremAudit skill.
3. The proposed artifact is written through a packaged tool with actor and provenance metadata.
4. The controller applies the stage's checks to the output and its evidence references.
5. If validation succeeds, the controller records the artifact hash and advances the run.
6. If validation or audit reveals a scientific defect, the controller routes repair, narrowing,
   rejection, or a null-result outcome without erasing the failed attempt.

The same process applies whether the action began in Codex conversation, the web interface, or the
terminal interface.

## Reasoning Skills

The 16 skills are task-specific instructions for the active Codex model, not 16 separate models.
Review roles are separated from proof-writing roles, but the actual execution and delegation depend
on the host Codex configuration. Skills do not authorize workflow transitions or replace tool checks.

### Pipeline coordination and inspection

| Skill | Responsibility |
|---|---|
| `theoremgate` | Starts or continues the complete governed theory-to-paper pipeline |
| `research-revision` | Classifies resume, retry, repair, re-audit, strengthening, literature, experiment, and manuscript revision requests |
| `dashboard` | Opens and interprets the web and embedded evidence views |

### Research formulation

| Skill | Responsibility |
|---|---|
| `research-direction` | Generates or compares feasible and falsifiable theoretical ML directions |
| `theory-discovery` | Defines the setting, assumptions, theorem targets, proof obligations, and dependency structure |

### Proof and mathematical governance

| Skill | Responsibility |
|---|---|
| `proof-development` | Designs proof strategies and produces auditable proof records |
| `adversarial-audit` | Uses a separate review role to search for proof gaps, counterexamples, assumption failures, and scope errors |
| `proof-repair` | Corrects a governed mathematical defect and rebuilds the affected proof closure for fresh audit |

### Evidence and contribution assessment

| Skill | Responsibility |
|---|---|
| `literature-audit` | Verifies primary literature, theorem provenance, closest work, novelty boundaries, and citation integrity |
| `significance-audit` | Assesses technical depth, operational assumptions, baselines, application evidence, and empirical needs |
| `contribution-development` | Converts accepted mathematics into an evidence-consistent paper contribution and claim policy |
| `contribution-strengthening` | Adds a bounded scientific extension when accepted theory does not meet the selected publication goal |
| `empirical-validation` | Designs reproducible support, stress, falsification, and contradiction experiments for accepted claims |

### Manuscript and publication

| Skill | Responsibility |
|---|---|
| `manuscript-writing` | Writes a complete manuscript from the governed theory bundle without exceeding proved evidence |
| `paper-review` | Reviews correctness, claim-evidence alignment, citations, exposition, experiments, and venue compliance |
| `venue-formatting` | Selects and stages a suitable venue package while preserving the governed manuscript content |

## Executable Tools and Controllers

The Python scripts are not merely convenience utilities. They implement the governance, integrity,
and evidence-recording mechanisms that constrain the model-facing skills.

### Pipeline and state control

| Script | Important mechanism |
|---|---|
| `direct_pipeline.py` | Starts full or theory-only runs and manages bounded automatic continuation |
| `codex_runner.py` | Launches controlled Codex jobs and normalizes execution events |
| `workflow.py` | Maintains the theory stage machine, assigned actors, artifact validators, and allowed transitions |
| `state_store.py` | Provides contained paths, atomic writes, locks, manifests, and completed-artifact hash verification |
| `research_artifacts.py` | Writes, validates, versions, and restores in-progress theory artifacts |

### Proof and governance evidence

| Script | Important mechanism |
|---|---|
| `proof_dag.py` | Models proof dependencies and computes ready, conditionally draftable, and blocked obligations |
| `proof_store.py` | Validates proof records, assumption use, status transitions, and evidence hashes |
| `proof_tools.py` | Scaffolds obligations and records proof blueprints, checks, drafts, and frontier state |
| `audit_findings.py` | Maintains evidence-linked findings, attack summaries, governance decisions, and hash-linked audit history |
| `audit_templates.py` | Provides controlled audit structures and attack families |
| `proof_repair.py` | Archives failed proof passes and returns the same run to discovery for bounded correction and fresh audit |

### Routing and research revision

| Script | Important mechanism |
|---|---|
| `paper_router.py` | Derives the strongest manuscript route and claim policy supported by accepted theory, novelty, and significance evidence |
| `revision_router.py` | Determines which evidence is preserved and which stages must be reopened for a requested revision |
| `contribution_strengthening.py` | Archives assessed packages and controls bounded strengthening passes |

### Literature and citations

| Script | Important mechanism |
|---|---|
| `literature_tools.py` | Searches, normalizes, deduplicates, validates, registers, and exports literature evidence |
| `scripts/literature/` | Contains source adapters and the canonical literature-record implementation |
| `citations.py` | Validates citation keys and evidence-linked citation use |

### Experiments and figures

| Script | Important mechanism |
|---|---|
| `experiment_tools.py` | Records strategy, script inspection, execution, outputs, evaluation, figures, and provenance |
| `experiment_schema.py` | Defines the controlled empirical-evidence schema |
| `experiment_resources.py` | Registers and acquires small pinned datasets/models, with byte budgets and provenance |
| `experiment_runtime.py` | Runs inspected CPU pilots and experiments with time, memory, and output monitoring |
| `figure_quality.py` | Audits figure structure and publication readiness |

Experiments are optional and are selected only when they test an accepted claim. The workflow
separates resource acquisition from execution, checks feasibility and provenance, and preserves
scripts, outputs, and evaluation evidence. Missing resources remain explicit limitations rather
than fabricated results. Detailed resource and execution rules are maintained in the installed
empirical-validation skill.

### Manuscript and venue control

| Script | Important mechanism |
|---|---|
| `manuscript_workflow.py` | Controls literature, venue, architecture, experiment, writing, compilation, review, revision, and packaging stages |
| `manuscript_tools.py` | Writes governed sections, assembles and compiles LaTeX, and records review and revision evidence |
| `venue_tools.py` | Audits, compares, stages, and verifies venue templates and rule snapshots |

### Interfaces

| Component | Important mechanism |
|---|---|
| `research_studio.py` | Serves the local web interface: run controls, revision actions, job progress, and integrated evidence views |
| `dashboard.py` | Exports the same persisted evidence model as self-contained read-only HTML or JSON |
| `mcp/dashboard_server.py` | Exposes the embedded evidence view through the plugin's MCP integration |

## Governed Theory Workflow

The theory governance controller is `scripts/workflow.py`.

```text
direction_generation
  -> direction_selection
  -> discovery
  -> exploration
  -> proof_development
  -> local_adversarial_audit
  -> governance_review
  -> theorem_synthesis
  -> final_adversarial_audit
  -> arbiter
  -> novelty_audit
  -> significance_audit
  -> contribution_assessment
  -> theory_bundle
```

| Stage | Assigned actor | Primary output |
|---|---|---|
| `direction_generation` | `direction_generator` | Candidate directions |
| `direction_selection` | `direction_selector` | Selected direction |
| `discovery` | `discoverer` | Definitions, assumptions, targets, proof DAG |
| `exploration` | `explorer` | Special-case probes and feasibility decision |
| `proof_development` | `proof_team` | Dependency-indexed proof records |
| `local_adversarial_audit` | `auditor` | Evidence-linked findings |
| `governance_review` | `governor` | Finding-level governance decisions |
| `theorem_synthesis` | `synthesizer` | Statements supported by the proof closure |
| `final_adversarial_audit` | `auditor` | Final statement-to-proof audit |
| `arbiter` | `governor` | Accepted, narrowed, conjectural, or rejected status |
| `novelty_audit` | `novelty_auditor` | Verified closest-work comparison |
| `significance_audit` | `significance_reviewer` | Depth and application-evidence assessment |
| `contribution_assessment` | `contribution_developer` | Contribution class and manuscript claims |
| `theory_bundle` | `controller` | Immutable accepted theory and paper route |

For advanced debugging, set the plugin path inside your checkout, then run the following commands
from the research workspace:

```bash
export THEOREMGATE_ROOT=/absolute/path/to/theoremgate/plugins/theoremgate
```

Inspect a specific run with:

```bash
python3 "$THEOREMGATE_ROOT/scripts/workflow.py" \
  --workspace . \
  status \
  --run RUN_ID
```

The stage loop is `status -> produce artifact -> validate -> complete -> status`. Completion checks
the declared actor against the role reported by `status`; this is not an access-control boundary:

```bash
python3 "$THEOREMGATE_ROOT/scripts/workflow.py" --workspace . validate --run RUN_ID

python3 "$THEOREMGATE_ROOT/scripts/workflow.py" \
  --workspace . \
  complete \
  --run RUN_ID \
  --actor ACTOR_FROM_STATUS
```

Proof development cannot complete while obligations remain `unstarted`, `planned`, or
`analysis_in_progress`. Documented partial, failed, or blocked attempts can proceed to review when
their required evidence and gaps are present. Completing this stage does not accept any theorem.

Do not edit completed artifacts directly or manually generate `theory_bundle.json`.

## Repair and Revision Semantics

TheoremAudit distinguishes correction from research revision:

- **Same-run proof correction:** Before theorem synthesis, a serious local mathematical finding may
  return the same run to discovery. The failed pass is archived under `corrections/round-XX/`, and a
  fresh review of the corrected arguments is required. At most three automatic correction rounds
  are allowed.
- **Same-run contribution strengthening:** Accepted mathematics that does not meet the selected
  publication goal may be extended through at most two bounded strengthening passes. Previous
  packages are archived under `strengthening/round-XX/`.
- **Linked research revision:** A post-bundle mathematical change, materially new contribution, or
  explicitly separate revision receives a child run linked through `parent_run_id`.
- **Paper-only revision:** Literature, experiments, manuscript content, or venue selection can be
  reopened without changing the immutable theory bundle.

Explicit requests such as retry, re-audit, repair, strengthen, rewrite, or revise literature are
routed by `scripts/revision_router.py`; they are not interpreted as silent new root runs.

## Manuscript Workflow

Full runs continue from the immutable theory bundle into `scripts/manuscript_workflow.py`:

```text
literature_audit
  -> exemplar_study
  -> venue_selection
  -> content_architecture
  -> empirical_validation
  -> section_writing
  -> compilation
  -> independent_review
  -> revision
  -> final_package
```

The paper is written only beneath the bound run's `paper/` directory. Manuscript claims must trace
to accepted theory-bundle statements. Mathematical content cannot be strengthened by editing the
paper; mathematical changes require governed theory evidence.

Accepted mathematics receives the strongest evidence-consistent full paper permitted by the route.
If no statement survives audit, the system produces an `evidence_report` containing the null result,
limitations, audited failure, and available future directions.

## Run Directory

Each run is isolated under:

```text
.theoremgate/runs/<run-id>/
  run.json                       # current stage, actor, status, and evidence hashes
  artifacts/                     # directions, discovery, audits, decisions, theory bundle
    _revisions/                  # versioned in-progress artifact history
  proofs/
    index.json                   # proof DAG and proof-record index
    PO-*/                        # obligation-specific records and evidence
  literature/
    registry.json                # canonical verified-literature registry
    raw/                         # retrieved source records
  corrections/                   # archived same-run proof-correction rounds, when used
  strengthening/                 # archived contribution-strengthening rounds, when used
  paper/                         # experiments, sections, review, compiled paper, final package
```

At the workspace level, `.theoremgate/latest.json` is a convenience pointer. It may be used for
read-only inspection, but mutations should always specify a concrete run ID.

## Plugin Structure

```text
theoremgate/
  .agents/plugins/marketplace.json       # public Codex marketplace manifest
  plugins/theoremgate/
    .codex-plugin/plugin.json            # plugin metadata and interface registration
    .mcp.json                            # embedded evidence-view server registration
    assets/
      research-studio/                   # local web-interface frontend
    mcp/
      dashboard_server.py                # MCP evidence-view server
      dashboard_widget.html              # embedded evidence-view resource
    scripts/
      theoremgate.py                     # unified terminal/web-interface launcher
      direct_pipeline.py                 # bounded continuation controller
      workflow.py                        # theory stage machine and validators
      manuscript_workflow.py             # post-theory paper stage machine
      revision_router.py                 # resume, repair, strengthening, and revision routing
      proof_dag.py                       # proof dependency model
      proof_store.py                     # proof-record integrity
      audit_findings.py                  # immutable findings and governance records
      state_store.py                     # run persistence, locking, and hashes
      paper_router.py                    # evidence-based manuscript route
      research_studio.py                 # local web-interface server
      dashboard.py                       # read-only evidence-view generator
    skills/                              # role-scoped Codex instructions
```
