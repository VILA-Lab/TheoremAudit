# Executable tool groups

Resolve the plugin root from the active skill and invoke scripts with `python3`. Always pass the
user's workspace via `--workspace`; optionally pass `--run` to avoid relying on the latest pointer.
Inline JSON and JSON-file arguments are size-bounded, and file inputs used by packaged tools must
resolve inside that workspace.

## Pipeline Continuation Controller

`scripts/direct_pipeline.py start` is the required entry point for new runs launched directly from
chat or the CLI; `resume --run RUN_ID` continues an exact run. The Pipeline Continuation Controller
keeps a host process alive across the initial Codex turn and at most three automatic continuation
turns, so a child turn ending at an unfinished stage is treated as progress rather than completion.
It emits `pipeline_completed`, `continuation_budget_exhausted`, or `continuation_failed`; never use a
generic finished event for both complete and incomplete outcomes. Full starts default to an
`original_research` publication goal; explicit `--mode theory` starts stop after the theory bundle.
Web-interface contracts already have an equivalent continuation controller and must not be double-wrapped.

## Governed research artifacts

`scripts/research_artifacts.py` shows, writes, and validates the current theory-stage artifact. Its
`write-current` command accepts an inline JSON object or a JSON-file path contained in the workspace.
Every write requires the stage's assigned `--actor` and a non-empty `--reason`. It validates a
candidate before retaining it, restores the previous version after failure, and records successful
versions with hashes and provenance under `artifacts/_revisions/<stage>/`. It refuses to write
generated theory bundles and refuses replacement unless `--replace` is explicit before stage
completion. Complete stages with `scripts/workflow.py complete --actor <actor>`.

## Audits and decisions

`scripts/audit_findings.py` supports `add`, `amend`, `resolve`, `verify-repair`, `decide`, and
`arbiter-decision`. `record-attack-summary` seals the attack pass; if a late finding changes that
summary, use `revise-attack-summary --reason ...`. Both operations are hash-linked through a
separate audit-operation ledger, so editing the audit JSON and recomputing its local hash is invalid.
Operations are accepted only in their matching current stage and require the assigned `--actor`.
New findings require a controlled kind, attack method, evidence summary, workspace-contained source
path and exact location, resolution condition, and optional affected scope/evidence file. Findings
and decisions have atomic append, stage-qualified IDs, duplicate-ID protection, timestamps, actors,
and record hashes. Schema-v3 findings are immutable; amendments and resolutions are reconstructed
from a SHA-256 event chain. `resolve` is restricted to false positives or preexisting evidence and
requires a hash-bound evidence file. A pre-synthesis repairable local finding routes through
`proof_repair.py`, which archives the failed pass and returns the same run to discovery. A completed
or materially changed research result uses a linked child, where `verify-repair` binds ancestor
evidence to the child artifact. Governance and Arbiter commands reject known semantic violations. The
arbiter may mark a statement `invalid` only when a relevant unresolved fatal mathematical finding
is explicitly addressed; repairable and conjectural statements retain their non-final statuses.
The workflow controller performs final cross-artifact validation.

## Proofs

`scripts/proof_tools.py` supports `scaffold`, `migrate-index`, `write-blueprint`, `add-check`, and `write-draft` during
`proof_development`, plus `frontier` for dependency-aware parallel scheduling. The frontier separates
unconditionally ready, conditionally draftable, and transitively blocked obligations. Draft metadata
must contain the assumptions used, proved scope, and structured gaps. Writes require `--actor
proof_team`; blueprint and draft status changes also require a reason. Strict indexes hash-bind both
blueprints and drafts, validate assumptions against discovery, and prevent proof-team assignment of
Arbiter statuses. Migration creates an explicitly labeled present-day integrity baseline rather than
claiming historical verification. The proof index and dependency DAG are validated after updates.

## Literature

`scripts/literature_tools.py normalize` upgrades legacy inputs to `literature_record.v1`; `dedupe`
performs transitive cross-source merging and reports aliases, decisions, and conflicts; `validate`
checks the canonical schema. `search-and-save` invokes one allow-listed adapter, persists its exact
JSON output and hash, merges records into the run-level registry, and defaults broad retrieval to
the non-blocking `discovery_candidate` purpose. `ingest`
adds independently fetched records, while `register-use` links papers to stages, claims, sections,
artifacts, and evidence locators. `reclassify-use` changes an active evidence purpose while preserving
the earlier link as audit history; `curate-novelty` keeps a deliberate theorem-level shortlist and
demotes the remaining leads to discovery candidates. `registry`, `validate-registry`, `coverage`, and `export-bib`
inspect and publish the canonical state. `seed-theory` initializes the registry from an existing
theory bundle when its manuscript workflow predates registry support. `run` remains a non-persistent inspection command. All file
inputs are workspace-contained and adapter arguments are bounded. Network availability is
environment-dependent, and retrieved metadata is not equivalent to theorem verification. See
`literature-record.md`.

## Research revision routing

`scripts/proof_repair.py status|start` controls bounded same-run correction of audited mathematical
defects. `workflow.py complete` starts it automatically when at least one serious mathematical
finding is `repair_requested` and fewer than three correction passes have been attempted. Deferred,
excluded, or invalidated sibling closures retain their dispositions and do not suppress repair of an
independent closure. Each pass is preserved under `corrections/round-XX/`; discovery, exploration,
proofs, local audit, and governance must be rebuilt and revalidated.

`scripts/contribution_strengthening.py status|start` controls bounded same-run strengthening when
the candidate theory bundle is mathematically accepted but below the selected publication goal. It
archives each assessed package, chooses either `novelty_audit` or `discovery` as the minimal resume
stage, and permits at most two passes before honest route finalization.

`scripts/revision_router.py plan` maps an explicit rerun request to same-run continuation,
read-only re-audit, linked mathematical/contribution revision, paper revision, or a new root run.
Use `revise_literature` when citations, bibliography, closest-work evidence, or Related Work coverage
must change; it resumes the same paper at `literature_audit`. Use `rewrite_manuscript` for a new
paper/venue selection and genuinely new manuscript; it resumes at `venue_selection`, selects the
venue before deriving a new page plan, and rejects unchanged section hashes. `start` creates evidence-preserving
linked theory revisions or same-run paper revisions. Linked theory revisions require explicit
researcher authorization; paper revisions preserve the immutable theory bundle and archive every
paper stage at or after the routed resume stage.
`status` shows the append-only revision-request ledger. Once a repair child is started, its parent is
frozen and marked as superseded; theorem synthesis continues only in the child lineage.

## Experiments

`scripts/experiment_tools.py` supports `write-strategy`, `propose`,
`inspect-script`, `run-inspected`, `record-execution`, `mark-blocked`, `evaluate`, `audit-figure`, `register-figure`, `review-figure`,
`emit-figure-tex`, `repair-evaluation-hash`, `repair-figure-review-hash`, and `finalize`.
Its schema-v2 atomic evidence registry retains strategy/evaluation replacement
history, script inspections, commands, environments, logs, outputs, hashes, figures, and provenance
events. Static inspection rejects network/process/dynamic-code primitives but is explicitly not a
sandbox. New strategy-v2 programs use `run-inspected` for a bounded CPU pilot and full execution
with verified local assets. `record-execution` alone is retained for legacy programs.
`scripts/experiment_resources.py` supports `status`, `register`, `acquire`, and approved `configure`.
See [experiment-resources.md](experiment-resources.md) for resource and feasibility contracts.
Evaluation validates non-empty JSON/CSV and binds it to that execution.
Replacement evaluations may reuse an earlier record; the hash field itself is excluded from hashing.
If a legacy evaluation fails integrity validation because its previous hash was included in the
payload, use `repair-evaluation-hash --id EXP_ID --revision N --expected-sha256 STORED_HASH
--reason "documented repair reason"` at `empirical_validation`. The command recognizes only that
specific defect, checks the predecessor and execution evidence, and atomically preserves the complete
original record in `evaluation_hash_repairs` with a validated repair receipt. It does not change
scientific content or waive other validation failures. Re-run `finalize` and stage validation afterward.
Never edit the registry or recalculate arbitrary mismatched hashes by hand.
The same legacy defect in a reused visual review can be repaired with
`repair-figure-review-hash --figure-id FIG_ID --expected-sha256 STORED_HASH --reason "reason"`.
It requires a valid archived predecessor and unchanged figure/results files, preserves the complete
original review in a validated receipt, and leaves scores, conclusions, and review timestamps intact.
Figure registration enforces vector publication masters, paper-aware size classes, result linkage,
captions, alt text, structural audits, and rendered visual review before a main figure is considered
publication-ready.

## Manuscripts

`scripts/manuscript_tools.py` supports `write-section`, `assemble`, `compile`, `write-review`,
`add-user-comment`, and `write-revision`.
`add-user-comment` records a researcher-authored paper-only edit type, scope, target, priority, and
exact text; persist each custom paper request once. A mathematical-change instruction instead belongs
in the linked revision-router ledger and must not reopen the completed parent paper. Reviewer findings
are already persisted in `review.json` and must
be answered by finding ID rather than duplicated as user comments. A combined review revision may
address all findings automatically in one cycle while retaining a separate response for each finding
ID.
Section writing rejects internal workflow vocabulary and requires its real LaTeX citation keys to
match the declared canonical record IDs. Replacement requires a reason and retains the prior
hash-bound record. Assembly consumes the governed section index, uses staged venue style and
bibliography metadata when available, and regenerates `references.bib` deterministically from cited
registry records. It places references before an explicitly labeled appendix. Compilation uses
bounded fixed `pdflatex` and `bibtex` invocations and records source/PDF/log hashes, rendered page
count, page-budget status, and warnings in `compile_report.json`. Reviews bind to the exact compile; a
revision must answer every review finding and open user comment with a disposition and changed-file
hashes, then return through section validation, assembly, compilation, and independent re-review.
For schema-v3 component-aware manuscripts, completing an imperfect compilation archives the source,
PDF, section files, and findings, then returns to `section_writing`. The controller permits two
automatic presentation-repair rounds. If the following compile still has nonfatal presentation
findings, it restores the best archived attempt and advances to review; the reviewer uses
`package_with_warnings`, and final packaging preserves those finding IDs as warnings. This mechanism
cannot absorb mathematical-correctness or unsupported-claim defects.

## Venues

`scripts/venue_tools.py list` emits a schema-v2 integrity audit with controlled findings, declared
asset roles, SHA-256 hashes, provenance/freshness state, and separate local-staging, submission, and
redistribution decisions. `candidates --run RUN_ID` emits a hash-bound, alphabetically displayed
candidate set and the persisted research context without ranking or selecting a venue. The
venue-formatting agent compares at least three candidates on contribution, theorem/proof, empirical,
length/appendix, and rule-status axes, then records one reasoned selection. Submission-eligible routes
require a selected snapshot whose official rules are verified, fresh, and submission-ready; other
full-paper routes retain accurate readiness warnings. Evidence reports use `Research-Draft`.
`recommend` is a compatibility alias for `candidates` and makes no recommendation. `stage --venue <name>` refuses templates with structural `error`/`fatal`
findings, copies only declared stageable assets transactionally, and writes a hash-bound schema-v3
`venue_snapshot.json`. Replacements require a reason and archive the previous package. `verify`
detects snapshot, file-set, or asset mutation. Package integrity never implies current official
compliance or redistribution authorization.

## Evidence View

`scripts/dashboard.py build` creates `.theoremgate/dashboard/index.html` from run manifests and
available theory/paper artifacts. `data` emits the same normalized read-only model as JSON. The page
is self-contained, performs no network requests, and cannot advance or mutate a workflow.

`scripts/research_studio.py` serves the live loopback web interface. In addition to the read-only
evidence views, its explicit Run controls invoke `scripts/codex_runner.py`, which starts one governed
local Codex CLI session at a time and persists normalized JSON events in
`.theoremgate/studio/jobs/`. It accepts research questions and reviewed prompts, never arbitrary
commands. Opening or refreshing the workspace never starts a model run.
