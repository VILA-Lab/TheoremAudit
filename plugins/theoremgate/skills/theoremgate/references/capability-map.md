# Capability map

This export preserves the complete research capability while replacing legacy API execution with the
active Codex model. Original files are copied as read-only source references; they are not imported or
executed. No path to the original repository is required after the plugin is installed.

## Skills

| Original capability | Codex-native skill |
|---|---|
| direction generation and selection | `$research-direction` |
| discovery, exploration, mathematical probes | `$theory-discovery` |
| proof strategy and proof writing | `$proof-development` |
| bounded correction of audited assumptions, statements, and proofs | `$proof-repair` |
| bounded strengthening toward the researcher-selected publication goal | `$contribution-strengthening` |
| assumption attack and counterexample search | `$adversarial-audit` |
| theorem synthesis and governance | `$theoremgate` |
| resume, retry, governed repair, re-audit, strengthening, and paper revision | `$research-revision` |
| literature, related-work search, and independent novelty audit | `$literature-audit` |
| independent significance, assumption-operationalization, and application-evidence audit | `$significance-audit` |
| contribution development and evidence-based paper routing | `$contribution-development`, `$theoremgate` |
| empirical experiments | `$empirical-validation` |
| venue-independent title, narrative, section architecture, compiler, and all nine section skills | `$manuscript-writing` |
| post-architecture venue choice, compliance, and templates | `$venue-formatting` |
| independent paper review and revision | `$paper-review` |
| visual run creation, live Codex activity, stage, theorem, blocker, experiment, and paper-status evidence view | `$dashboard` |

The full original skill texts are under `source-skills/`, including abstract, introduction, setting,
main results, empirical, related work, discussion, conclusion, and proof appendix.

## Roles and agents

The historical role prompts are preserved under `source-roles/` for traceability. They are not a
runtime team and do not call external model APIs. Codex executes the governed roles using its own
delegation configuration. Stage transitions remain ordered, and audits review persisted evidence
separately from the proof-writing pass.

## Tools

All 37 non-empty original tool implementations are preserved under `source-tools/` for behavior and
schema traceability. Seven safe executable tool groups provide their Codex-native operations; see
`executable-tools.md`:

- governed artifact reads/writes, stage completion, decisions, blocking, weakening, repair, and commit
  are replaced by `workflow.py`, `manuscript_workflow.py`, and run-scoped atomic storage;
- proof drafts, blueprints, checks, dependencies, and statuses are handled by `proof_tools.py`,
  `proof_store.py`, and `proof_dag.py`;
- literature search is available through `literature_tools.py`, packaged source adapters, and Codex
  web access;
- citation deduplication is provided by `citations.py`;
- experiments are designed by `$empirical-validation` and executed only after code inspection within
  the user's authorized workspace; the legacy arbitrary-command runner is not enabled;
- experiment proposal, inspection, evaluation, and figure registration use `experiment_tools.py`;
- resource acquisition uses `experiment_resources.py`; new programs use version-2 feasibility
  records and `experiment_tools.py run-inspected` for bounded CPU pilots and experiments;
- manuscript section writing, assembly, fixed-command compilation, and review use
  `manuscript_tools.py` plus the paper controller;
- venue auditing and staging use `venue_tools.py`; structural integrity is hash-checked locally,
  while current official rules and redistribution authorization remain separate required checks.

The preserved legacy tool files themselves remain non-executable references. The old arbitrary-code
runner, direct model calls, unconstrained web wrappers, and global mutable-state helpers are not
enabled.

## Web interface, evidence view, and MCP boundary

The local MCP server exposes a read-only data tool, an MCP Apps render tool, and an offline-build
fallback. Compatible hosts receive `ui://theoremgate/dashboard-v1.html` as a
`text/html;profile=mcp-app` resource. The widget can refresh data and send follow-up prompts, but it
cannot bypass actors, validation, hashes, or immutable completed artifacts. The standalone
`scripts/dashboard.py` path remains available without a server, account, or API key.

The loopback-only web interface in `scripts/research_studio.py` can also launch governed work
through the user's logged-in Codex CLI. It does not embed a model API credential or arbitrary shell
endpoint. A visible user action creates a separate `codex exec --json` session; model selection is
optional, delegation follows Codex configuration, activity is persisted, and only one top-level
mutating session runs per workspace. This execution surface delegates research mutations back to the same skills and
controllers rather than implementing a second pipeline.

## Excluded runtime machinery

`runtime/client.py`, `runtime/loop.py`, `runtime/tools.py`, and `runtime/skills.py` are not shipped.
They exist to implement the old model/API loop, which Codex replaces. Caches, runs, outputs, logs,
credentials, and user state are also excluded.
