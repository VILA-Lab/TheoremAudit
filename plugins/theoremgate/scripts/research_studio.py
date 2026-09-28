#!/usr/bin/env python3
"""Serve the local interactive TheoremAudit web interface."""

from __future__ import annotations

import argparse
import json
import secrets
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from dashboard import dashboard_data, summarize_run
from codex_runner import CodexJobRunner, build_pipeline_prompt, validate_model
from state_store import create_run, load_manifest, resolve_run, save_manifest
from workflow import STAGES


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PLUGIN_ROOT / "assets" / "research-studio"
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/launch.html": ("launch.html", "text/html; charset=utf-8"),
    "/launch.js": ("launch.js", "text/javascript; charset=utf-8"),
    "/launch.css": ("launch.css", "text/css; charset=utf-8"),
    "/logo.svg": ("../logo.svg", "image/svg+xml"),
    "/icon.svg": ("../icon.svg", "image/svg+xml"),
}
ACTION_VERBS = {
    "challenge": "Challenge",
    "repair": "Revision",
    "trace": "Trace",
    "strengthen": "Strengthen",
    "revise": "Revise",
}


def content_security_policy(*, allow_same_origin_frame: bool = False) -> str:
    frame_ancestors = "'self'" if allow_same_origin_frame else "'none'"
    return (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; "
        f"frame-ancestors {frame_ancestors}"
    )


def prepare_pipeline_run(
    *,
    workspace: Path,
    mode: str,
    question: str,
    selected_run_id: Optional[str],
    parent_run_id: Optional[str],
    allow_subagents: Optional[bool] = None,
    publication_goal: str = "original_research",
    auto_repair: bool = False,
    max_auto_repair_rounds: int = 3,
) -> Dict[str, Any]:
    """Resolve one explicit run contract before any Codex process is launched."""
    workspace = workspace.expanduser().resolve()
    question = question.strip()
    # Legacy allow_subagents arguments are ignored; delegation is managed by Codex.
    # Keep the existing web policy for legacy automatic-repair parameters.
    auto_repair = False
    max_auto_repair_rounds = 0
    if not isinstance(auto_repair, bool):
        raise ValueError("auto_repair must be true or false")
    if (
        not isinstance(max_auto_repair_rounds, int)
        or isinstance(max_auto_repair_rounds, bool)
        or not 0 <= max_auto_repair_rounds <= 3
    ):
        raise ValueError("max_auto_repair_rounds must be between 0 and 3")
    effective_rounds = max_auto_repair_rounds if auto_repair else 0
    if mode in {"theory", "full"}:
        if not question:
            raise ValueError("research question is required for a new run")
        publication_goal = "original_research" if mode == "full" else "no_preference"
        run_dir = create_run(
            workspace=workspace,
            question=question,
            stages=STAGES,
            execution_contract={
                "intent": f"new_{mode}",
                "initiated_from": "studio",
                "requested_mode": mode,
                "human_checkpoints_required": False,
                "interaction_policy": "autonomous",
                "publication_goal": publication_goal,
                "auto_repair_enabled": auto_repair,
                "max_auto_repair_rounds": effective_rounds,
                "repair_round": 0,
            },
        )
    elif mode == "repair":
        if not question:
            raise ValueError("repair objective is required")
        if not parent_run_id:
            raise ValueError("repair mode requires an exact parent run")
        parent = resolve_run(workspace, parent_run_id)
        publication_goal = load_manifest(parent).get("execution_contract", {}).get(
            "publication_goal", "no_preference"
        )
        parent_contract = load_manifest(parent).get("execution_contract", {})
        strategy = "repair_full_theorem"
        run_dir = create_run(
            workspace=workspace,
            question=question,
            stages=STAGES,
            parent_run_id=parent.name,
            execution_contract={
                "intent": "repair",
                "initiated_from": "studio",
                "requested_mode": "repair",
                "human_checkpoints_required": False,
                "interaction_policy": "autonomous",
                "repair_strategy": strategy,
                "researcher_decision_id": None,
                "publication_goal": publication_goal,
                "auto_repair_enabled": auto_repair,
                "max_auto_repair_rounds": effective_rounds,
                "repair_round": int(parent_contract.get("repair_round", 0) or 0) if auto_repair else 0,
            },
        )
    elif mode == "resume":
        if not selected_run_id:
            raise ValueError("resume mode requires an exact selected run")
        run_dir = resolve_run(workspace, selected_run_id)
        manifest = load_manifest(run_dir)
        question = str(manifest.get("research_question", "")).strip()
        if not question:
            raise ValueError("selected run has no research question")
        parent_run_id = manifest.get("parent_run_id")
        publication_goal = manifest.get("execution_contract", {}).get(
            "publication_goal", "no_preference"
        )
        contract = manifest.setdefault("execution_contract", {})
        contract["human_checkpoints_required"] = False
        contract["interaction_policy"] = "autonomous"
        contract.pop("run_confirmed_at", None)
        if (
            contract.get("auto_repair_enabled") != auto_repair
            or contract.get("max_auto_repair_rounds", 0) != effective_rounds
        ):
            contract["auto_repair_enabled"] = auto_repair
            contract["max_auto_repair_rounds"] = effective_rounds
            contract.setdefault("repair_round", 0)
            save_manifest(run_dir, manifest)
    else:
        raise ValueError("mode must be theory, full, resume, or repair")
    return {
        "run_dir": run_dir,
        "run_id": run_dir.name,
        "question": question,
        "parent_run_id": parent_run_id,
        "mode": mode,
        "repair_strategy": (
            load_manifest(run_dir).get("execution_contract", {}).get("repair_strategy")
        ),
        "publication_goal": publication_goal,
        "auto_repair": auto_repair,
        "max_auto_repair_rounds": effective_rounds,
        "interaction_policy": "autonomous",
    }


def contextual_prompt(run: Dict[str, Any], action: str, node_id: Optional[str], note: str) -> str:
    graph_nodes = {node["id"]: node for node in run.get("graph", {}).get("nodes", [])}
    node = graph_nodes.get(node_id or "")
    context = "the overall research run"
    if node:
        context = f"{node['kind']} {node['id']} ({node['title']}): {node.get('summary', '')}"
    prefix = (
        f"For TheoremAudit run {run['run_id']}, operate only on that exact run. "
        f"Pass --run {run['run_id']} to every governed controller command and do not switch to the latest run."
    )
    if action == "challenge":
        instruction = (
            f"adversarially challenge {context}. Check scope, hidden assumptions, boundary cases, "
            "counterexamples, proof dependencies, and claim-evidence alignment. Persist findings only "
            "through the governed audit workflow and do not edit completed artifacts."
        )
    elif action == "repair":
        instruction = (
            f"use $research-revision to design a governed revision for {context}. Validate the finding first, identify the smallest "
            "sound change, and create a new evidence-preserving revision linked to this run if completed evidence must change. "
            "Preserve the original run as immutable evidence."
        )
    elif action == "trace":
        instruction = (
            f"trace {context} through assumptions, proof obligations, accepted statements, novelty evidence, "
            "paper sections, and reviewer findings. Report missing or inconsistent links without modifying files."
        )
    elif action == "strengthen":
        instruction = (
            f"evaluate how to strengthen {context}. Rank concrete next actions by which correctness, novelty, "
            "significance, empirical, or venue blocker each action would actually unlock. Do not promise a route "
            "upgrade without completed evidence."
        )
    elif action == "revise":
        instruction = (
            f"use $research-revision to classify and execute the free-form paper request for {context}. "
            "Infer its edit type, scope, target, and earliest invalidated stage, then route it as "
            "revise_manuscript, revise_literature, rerun_experiments, rewrite_manuscript, or "
            "repair_mathematics. For a researcher-authored "
            "paper-only request, persist it exactly once with manuscript_tools.py add-user-comment, including "
            "edit type, scope, target, and priority. Record a mathematical request in the linked revision-router "
            "ledger instead of reopening the completed parent paper. For an independent-review finding, bind the revision response to the "
            "existing finding ID and do not duplicate it as a user comment. When several review findings are "
            "selected, address them together in one revision cycle while retaining a separate response for each "
            "finding ID. Read the accepted theory bundle, "
            "claim policy, paper evidence, compilation report, and independent review before editing. Preserve "
            "the theorem scope unless repair_mathematics creates governed replacement evidence. Rebuild every "
            "invalidated downstream paper stage, compile the revised manuscript, and run a fresh independent review."
        )
    else:
        instruction = note.strip() or f"inspect {context} and recommend the next governed action."
        instruction = (
            "If this asks to continue, retry, rerun, re-audit, repair, strengthen, redo experiments, "
            "revise the manuscript, pivot, or start new research, use $research-revision to classify "
            "the request before changing evidence. " + instruction
        )
    if note.strip() and action in ACTION_VERBS:
        instruction += f" The researcher adds: {note.strip()}"
    return f"{prefix} {instruction}"


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "TheoremGateWeb/0.3"

    @property
    def workspace(self) -> Path:
        return self.server.workspace  # type: ignore[attr-defined]

    @property
    def runner(self) -> CodexJobRunner:
        return self.server.runner  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[studio] {self.address_string()} {format % args}")

    def _send_bytes(
        self,
        payload: bytes,
        content_type: str,
        status: int = HTTPStatus.OK,
        *,
        allow_same_origin_frame: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        self.send_header(
            "Content-Security-Policy",
            content_security_policy(allow_same_origin_frame=allow_same_origin_frame),
        )
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, value: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._send_bytes(payload, "application/json; charset=utf-8", status)

    def _error(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self._json({"error": message}, status)

    def _body(self) -> Optional[Dict[str, Any]]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._error("Content-Type must be application/json.", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return None
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._error("Invalid request length.")
            return None
        if length < 1 or length > 100_000:
            self._error("Request body must be between 1 and 100000 bytes.")
            return None
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._error("Request body must be valid JSON.")
            return None
        if not isinstance(payload, dict):
            self._error("Request body must be an object.")
            return None
        return payload

    def _authorized(self) -> bool:
        supplied = self.headers.get("X-TheoremGate-Token", "")
        expected = self.server.csrf_token  # type: ignore[attr-defined]
        if not supplied or not secrets.compare_digest(supplied, expected):
            self._error("Missing or invalid local workspace token.", HTTPStatus.FORBIDDEN)
            return False
        return True

    def _local_host(self) -> bool:
        host = self.headers.get("Host", "").rsplit(":", 1)[0].strip("[]").lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            self._error("TheoremAudit web interface accepts only loopback Host headers.", HTTPStatus.FORBIDDEN)
            return False
        return True

    def _research_run(self, run_id: str) -> Dict[str, Any]:
        run_dir = resolve_run(self.workspace, run_id)
        if not (run_dir / "run.json").is_file():
            raise ValueError("Run was not found.")
        return summarize_run(run_dir)

    def do_GET(self) -> None:  # noqa: N802
        if not self._local_host():
            return
        parsed = urlparse(self.path)
        if parsed.path in ASSETS:
            filename, content_type = ASSETS[parsed.path]
            path = (ASSET_ROOT / filename).resolve()
            plugin_root = PLUGIN_ROOT.resolve()
            if not path.is_relative_to(plugin_root) or not path.is_file() or path.is_symlink():
                self._error("TheoremAudit web-interface asset is missing.", HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_bytes(path.read_bytes(), content_type)
            return
        if parsed.path == "/api/health":
            self._json({"ok": True, "workspace": str(self.workspace)})
            return
        if parsed.path == "/api/state":
            try:
                selected = parse_qs(parsed.query).get("run", [None])[0]
                self._json(dashboard_data(self.workspace, selected, selected_only=True, auto_select=False))
            except ValueError as exc:
                self._error(str(exc), HTTPStatus.NOT_FOUND)
            return
        if parsed.path == "/api/runner":
            self._json({
                "csrf_token": self.server.csrf_token,  # type: ignore[attr-defined]
                **self.runner.snapshot(),
            })
            return
        if parsed.path == "/api/run/events":
            query = parse_qs(parsed.query)
            job_id = query.get("job", [""])[0]
            try:
                after = int(query.get("after", ["0"])[0])
                if not job_id or after < 0:
                    raise ValueError("job and a nonnegative after value are required")
                self._json(self.runner.events(job_id, after))
            except ValueError as exc:
                self._error(str(exc), HTTPStatus.NOT_FOUND)
            return
        if parsed.path == "/api/paper.pdf":
            try:
                run_id = parse_qs(parsed.query).get("run", [None])[0]
                run_dir = resolve_run(self.workspace, run_id)
                paper = run_dir / "paper" / "paper.pdf"
                if not paper.is_file():
                    self._error("This run does not have a compiled paper PDF.", HTTPStatus.NOT_FOUND)
                    return
                self._send_bytes(
                    paper.read_bytes(),
                    "application/pdf",
                    allow_same_origin_frame=True,
                )
            except ValueError as exc:
                self._error(str(exc), HTTPStatus.NOT_FOUND)
            return
        self._error("Not found.", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self._local_host():
            return
        parsed = urlparse(self.path)
        if parsed.path not in {
            "/api/prompt", "/api/run/start", "/api/run/action", "/api/run/cancel",
        }:
            self._error("Not found.", HTTPStatus.NOT_FOUND)
            return
        if not self._authorized():
            return
        payload = self._body()
        if payload is None:
            return

        if parsed.path == "/api/run/start":
            mode = payload.get("mode", "full")
            question = payload.get("question", "")
            constraints = payload.get("constraints", "")
            parent_run_id = payload.get("parent_run_id")
            selected_run_id = payload.get("run_id")
            model = payload.get("model")
            auto_repair = payload.get("auto_repair", False)
            max_auto_repair_rounds = payload.get("max_auto_repair_rounds", 3)
            publication_goal = "original_research" if mode == "full" else "no_preference"
            if not isinstance(mode, str) or not isinstance(question, str) or not isinstance(constraints, str):
                self._error("mode, question, and constraints must be text.")
                return
            if parent_run_id is not None and not isinstance(parent_run_id, str):
                self._error("parent_run_id must be text.")
                return
            if selected_run_id is not None and not isinstance(selected_run_id, str):
                self._error("run_id must be text.")
                return
            if model is not None and not isinstance(model, str):
                self._error("model must be text.")
                return
            if not isinstance(auto_repair, bool):
                self._error("auto_repair must be true or false.")
                return
            if (
                not isinstance(max_auto_repair_rounds, int)
                or isinstance(max_auto_repair_rounds, bool)
                or not 0 <= max_auto_repair_rounds <= 3
            ):
                self._error("max_auto_repair_rounds must be between 0 and 3.")
                return
            try:
                runner_state = self.runner.snapshot()
                if not runner_state.get("available"):
                    raise ValueError("Codex CLI is not available on PATH")
                if runner_state.get("active_job_id"):
                    raise ValueError(
                        f"another Codex job is already active in this workspace ({runner_state['active_job_id']})"
                    )
                contract = prepare_pipeline_run(
                    workspace=self.workspace,
                    mode=mode,
                    question=question,
                    selected_run_id=selected_run_id,
                    parent_run_id=parent_run_id,
                    publication_goal=publication_goal,
                    auto_repair=auto_repair,
                    max_auto_repair_rounds=max_auto_repair_rounds,
                )
                prompt = build_pipeline_prompt(
                    mode=mode,
                    question=contract["question"],
                    run_id=contract["run_id"],
                    parent_run_id=contract["parent_run_id"],
                    constraints=constraints,
                    publication_goal=contract["publication_goal"],
                    auto_repair=contract["auto_repair"],
                    max_auto_repair_rounds=contract["max_auto_repair_rounds"],
                    interaction_policy=contract["interaction_policy"],
                )
                labels = {
                    "theory": "New theory research run",
                    "full": "New research-to-paper run",
                    "resume": "Resume governed run",
                    "repair": "Verified research revision",
                }
                job = self.runner.start(
                    prompt=prompt,
                    kind="pipeline",
                    label=labels[mode],
                    model=validate_model(model),
                    metadata={
                        "mode": mode,
                        "question": contract["question"],
                        "run_id": contract["run_id"],
                        "parent_run_id": contract["parent_run_id"],
                        "auto_repair": contract["auto_repair"],
                        "max_auto_repair_rounds": contract["max_auto_repair_rounds"],
                        "interaction_policy": contract["interaction_policy"],
                    },
                )
                self._json(
                    {"job": job, "run_id": contract["run_id"]},
                    HTTPStatus.ACCEPTED,
                )
            except ValueError as exc:
                self._error(str(exc))
            return

        if parsed.path == "/api/run/cancel":
            job_id = payload.get("job_id")
            if not isinstance(job_id, str) or not job_id:
                self._error("job_id is required.")
                return
            try:
                self._json({"job": self.runner.cancel(job_id)}, HTTPStatus.ACCEPTED)
            except ValueError as exc:
                self._error(str(exc), HTTPStatus.NOT_FOUND)
            return

        run_id = payload.get("run_id")
        action = payload.get("action", "custom")
        node_id = payload.get("node_id")
        note = payload.get("note", "")
        if not isinstance(run_id, str) or not run_id:
            self._error("run_id is required.")
            return
        if action not in {*ACTION_VERBS, "custom"}:
            self._error("Unknown research action.")
            return
        if node_id is not None and not isinstance(node_id, str):
            self._error("node_id must be text.")
            return
        if not isinstance(note, str):
            self._error("note must be text.")
            return
        if len(note) > 20_000:
            self._error("note must be at most 20000 characters.")
            return
        try:
            run = self._research_run(run_id)
        except ValueError as exc:
            self._error(str(exc), HTTPStatus.NOT_FOUND)
            return
        if node_id and not any(node["id"] == node_id for node in run["graph"]["nodes"]):
            self._error("Selected research object was not found.", HTTPStatus.NOT_FOUND)
            return
        prompt = contextual_prompt(run, action, node_id, note)
        if parsed.path == "/api/prompt":
            self._json({
                "prompt": prompt,
                "action": action,
                "run_id": run_id,
                "node_id": node_id,
                "executes_automatically": False,
            })
            return

        model = payload.get("model")
        reviewed_prompt = payload.get("prompt")
        if model is not None and not isinstance(model, str):
            self._error("model must be text.")
            return
        if reviewed_prompt is not None:
            if not isinstance(reviewed_prompt, str) or not reviewed_prompt.strip() or len(reviewed_prompt) > 60_000:
                self._error("prompt must contain between 1 and 60000 characters.")
                return
            prompt = reviewed_prompt.strip()
        try:
            job = self.runner.start(
                prompt="Use $theoremgate. " + prompt,
                kind="action",
                label=f"{ACTION_VERBS.get(action, 'Research action')} · {node_id or run_id}",
                model=validate_model(model),
                metadata={
                    "run_id": run_id,
                    "node_id": node_id,
                },
            )
            self._json({"job": job}, HTTPStatus.ACCEPTED)
        except ValueError as exc:
            self._error(str(exc))


def serve(workspace: Path, host: str, port: int, open_browser: bool) -> None:
    workspace = workspace.expanduser().resolve()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("TheoremAudit web interface must bind to a loopback host")
    if not workspace.is_dir():
        raise ValueError("TheoremAudit workspace path does not exist or is not a directory")
    server = ThreadingHTTPServer((host, port), StudioHandler)
    server.workspace = workspace  # type: ignore[attr-defined]
    server.runner = CodexJobRunner(workspace)  # type: ignore[attr-defined]
    server.csrf_token = secrets.token_urlsafe(32)  # type: ignore[attr-defined]
    url = f"http://{host}:{server.server_port}/"
    print(json.dumps({"research_studio": url, "workspace": str(workspace)}, indent=2), flush=True)
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.runner.close()  # type: ignore[attr-defined]
        server.server_close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=8765)
    result.add_argument("--no-open", action="store_true")
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        serve(Path(args.workspace), args.host, args.port, not args.no_open)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
