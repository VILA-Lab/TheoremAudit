---
name: dashboard
description: Open and use TheoremAudit's interactive local web interface or embedded evidence view to start governed Codex research, inspect research runs, argument dependencies, compiler-style evidence diagnostics, stages, accepted results, paper traceability and blockers, or launch contextual revision actions. Use when the user asks to visualize progress, open the web interface or evidence view, start the pipeline visually, debug a research claim, inspect run status graphically, or compare TheoremAudit runs.
---

# TheoremAudit Web Interface

Read visualization state from persisted evidence; never infer or edit stage status. Prefer the local
web interface when the user requests a fully interactive browser experience. Resolve this skill
directory, resolve `../../scripts/research_studio.py`, and run:

```bash
python3 <plugin-root>/scripts/research_studio.py --workspace <absolute-workspace>
```

The server binds to `127.0.0.1:8765`, opens the system browser, reads run artifacts every five
seconds, and remains attached to the launching terminal until stopped with `Ctrl-C`. Use `--port N`
when that port is occupied and `--no-open` when the user wants to open the URL themselves. Report the
printed URL. Do not claim it is running when the process exited or browser launch failed.

The web interface provides focused Core, Stress-test, and Paper-trace graph lenses, an object inspector,
compiler-style diagnostics, theory and paper pipelines, a full compiled-PDF manuscript view,
independent-review findings, and contextual Challenge, Repair, Trace, Strengthen, and Revise actions.
Its Research view starts a new full original-research pipeline from only a research question and
optional constraints. It can resume an exact saved run, but it exposes no publication-route, venue,
model, or checkpoint chooser. Starting or resuming is the single authorization action; the web interface
does not interrupt an active run with confirmation or decision prompts.

The local execution boundary is deliberate:

- nothing launches merely because the web interface opens, refreshes, or renders a prompt;
- launching requires an explicit Start/Run button press and may consume the user's Codex quota;
- it uses the user's existing Codex CLI login, not an embedded TheoremAudit API key;
- model is optional and otherwise comes from the user's Codex configuration;
- stage transitions remain ordered; delegation follows the user's Codex configuration;
- only one mutating Codex job may run per workspace;
- job metadata and activity are persisted under `.theoremgate/studio/jobs/`;
- Stop terminates the local Codex process group but preserves completed artifacts;
- the server is loopback-only and mutation requests require its per-launch local token.

All execution remains subject to TheoremAudit actors, validation, evidence hashes, explicitly launched revisions, and
immutable completed artifacts. Never imply that the website itself bypasses those controls. When a
session is running, report its displayed state; do not claim success until it reaches `completed`.

When the user explicitly requests embedded UI, call `theoremgate_render_dashboard` first with the
absolute workspace and optional run ID so a compatible host can render the inline/fullscreen
component.

The embedded component lets users change runs, refresh read-only data, request fullscreen, continue through a
follow-up message, and ask a run-scoped question. Its controls send messages or call governed tools;
they never mutate completed artifacts directly.

A successful render-tool call proves that evidence data and the associated `ui://` resource are
available. It does not prove that the current host displayed the component. Claim that the evidence view
opened only when a component is visibly rendered. Codex CLI normally reports structured data rather
than displaying an iframe; say so plainly.

Use the offline snapshot only when a persistent local server is unsuitable. Resolve
`../../scripts/dashboard.py` and run:

```bash
python3 <plugin-root>/scripts/dashboard.py --workspace . build
```

The snapshot output is `.theoremgate/dashboard/index.html`. Report a clickable absolute file link.
Open it in the system browser only when the user asks and approval permits GUI launch.
Build or refresh the fallback file before opening it, verify that it exists, and treat browser-launch
failure as a failure. Inside interactive Codex CLI, shell commands require the `!` prefix; text such
as `open /path/file.html` without `!` is a model prompt, not a shell command. Never report success
after an in-app browser reports that no browser is available.

Use `--run RUN_ID` with the snapshot builder to select a run initially. Use `data` instead of `build` when the user wants the
normalized evidence JSON rather than HTML. The generated page is self-contained, offline, and
read-only; it has no network requests and does not execute workflow actions. Do not describe the
fallback browser file as embedded UI.

If no run exists, explain that the user must start one with `$theoremgate`. Preserve the governed
actor, validation, immutable-parent, and artifact-hash boundaries for every action initiated from a
visual surface.
