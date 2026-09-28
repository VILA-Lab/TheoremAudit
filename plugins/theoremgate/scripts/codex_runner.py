#!/usr/bin/env python3
"""Controlled local Codex process runner for the TheoremAudit web interface."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from state_store import path_lock, write_json


MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}$")
MODES = {"theory", "full", "resume", "repair"}
TERMINAL_STATES = {"completed", "failed", "cancelled", "interrupted"}
JOB_ID_PATTERN = re.compile(r"^[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$")
METADATA_FIELDS = {
    "mode", "question", "run_id", "node_id", "parent_run_id", "parent_job_id",
    "allow_subagents", "auto_repair", "max_auto_repair_rounds",
    "interaction_policy", "continuation_round",
}
MAX_AUTOMATIC_CONTINUATIONS = 3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_model(model: Optional[str]) -> Optional[str]:
    if model is None or not model.strip():
        return None
    value = model.strip()
    if not MODEL_PATTERN.fullmatch(value):
        raise ValueError("model must contain only letters, digits, dots, colons, slashes, underscores, or hyphens")
    return value


def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def build_pipeline_prompt(
    *,
    mode: str,
    question: str,
    run_id: str,
    parent_run_id: Optional[str] = None,
    constraints: str = "",
    allow_subagents: Optional[bool] = None,
    publication_goal: str = "original_research",
    auto_repair: bool = False,
    max_auto_repair_rounds: int = 3,
    interaction_policy: str = "autonomous",
) -> str:
    # Legacy allow_subagents arguments are ignored; delegation is managed by Codex.
    if mode not in MODES:
        raise ValueError("mode must be theory, full, resume, or repair")
    question = question.strip()
    run_id = run_id.strip()
    if not question:
        raise ValueError("research question is required")
    if not run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("an exact governed run ID is required")
    if len(question) > 20_000 or len(constraints) > 20_000:
        raise ValueError("research question and constraints must each be at most 20000 characters")
    if mode == "repair" and not parent_run_id:
        raise ValueError("repair mode requires a parent run")
    goal_labels = {
        "original_research": "original conference research",
        "workshop_or_short_paper": "workshop or short paper",
        "technical_note": "technical note",
        "expository_paper": "expository paper",
        "reproducibility_paper": "reproducibility paper",
        "no_preference": "no fixed publication route",
    }
    if publication_goal not in goal_labels:
        raise ValueError("invalid publication goal")
    if not isinstance(auto_repair, bool):
        raise ValueError("auto_repair must be true or false")
    if (
        not isinstance(max_auto_repair_rounds, int)
        or isinstance(max_auto_repair_rounds, bool)
        or not 0 <= max_auto_repair_rounds <= 3
    ):
        raise ValueError("max_auto_repair_rounds must be between 0 and 3")
    if interaction_policy not in {"checkpointed", "autonomous", "confirm_once", "controller_default"}:
        raise ValueError("invalid interaction policy")

    repair_policy = (
        "When Governance classifies at least one serious local mathematical finding as repair_requested, follow the "
        "controller into $proof-repair for at most three same-run correction passes and fresh audits. Preserve explicit "
        "deferred or invalidated dispositions for other closures. Do not ask for "
        "routine correction approval. If the candidate theory bundle "
        "does not satisfy the original-research acceptance goal, follow the controller into "
        "$contribution-strengthening for at most two same-run passes. "
    )
    theorem_strength_policy = (
        "For full runs, discovery must define a publication-strength "
        "theorem package: a nonvacuous primary result with a concrete technical obstacle, an explicit novelty delta "
        "and closest-work boundary, a complete proof route, and either a distinct proved companion result or an "
        "exceptional-depth justification. Do not satisfy this gate with a renamed standard theorem, a direct "
        "specialization, an assumption that encodes the conclusion, or decorative mathematics. "
    )
    interaction_instructions = (
        "The researcher's explicit start or resume action authorizes autonomous execution. Never ask for a separate "
        "confirmation or a mid-run decision. Do not pause for direction, routine repair, salvage, strengthening, "
        "publication-route, venue, or writing choices. Target an acceptance-ready original research paper, select the strongest feasible direction within the stated "
        "research question; preserve bounded repairs and audits; and, when the requested goal remains unsupported, "
        "finalize the strongest honest narrower result. For a full run, always write the strongest evidence-consistent "
        "document. If no statement survives audit, write an evidence report that explains the failed claims "
        "and preserved evidence without inventing a theorem. Never change the central "
        "research question, invent evidence, or promote claims beyond the audits. The evidence-report route "
        "is always writable and must finish without asking the researcher to choose another topic."
    )
    checkpoint_instructions = (
        "Human checkpoints are disabled. Do not wait for or synthesize direction, governance, refinement, "
        "publication-route, venue, or writing decisions. Follow controller routing and give every accepted-result "
        "paper a full-length manuscript plus a named venue selected by the venue-formatting agent after a comparative "
        "assessment of the run evidence and packaged candidates. Never use a fixed venue ranking or numeric venue score. Treat venue-rule verification and final "
        "submission readiness as separate gates; use Research-Draft only for null-result or non-research expository outputs. "
        "For a submission-eligible route, require the selected locally staged template's official rules to be verified and fresh. Finish the strongest supported "
        "in-scope outcome without a venue or route prompt."
    )
    completion_instruction = (
        "Never leave a recoverable stage silently in progress. If external failure prevents safe persistence, report "
        "the exact failed operation and preserved state."
    )
    if mode == "theory":
        objective = (
            f"The new governed run {run_id} is already initialized. Continue that exact run one validated stage at a time through the immutable "
            "theory bundle. Stop after theory routing; do not start manuscript writing."
        )
    elif mode == "full":
        objective = (
            f"The new governed run {run_id} is already initialized. Continue that exact run one validated stage at a time through the immutable "
            "theory bundle. Continue through the "
            "separate paper workflow, compilation, independent review, revision, and final package."
        )
    elif mode == "resume":
        objective = (
            f"Resume exactly the existing governed run {run_id} from its persisted current stage. Continue only "
            "the unfinished governed theory or paper workflow associated with that run."
        )
    else:
        objective = (
            f"The governed research revision {run_id} is already initialized from evidence cycle {parent_run_id}. "
            "Work only in that revision cycle. Read the parent proof graph, audit findings, synthesis, Arbiter "
            "decisions, and persisted revision provenance before acting. Treat based_on targets as research "
            "provenance, not logical proof dependencies. Reuse unaffected, hash-verified proof evidence; revisit "
            "only the transitive proof closure touched by the repair objective. If the objective requests salvage, "
            "independently audit and govern each proof-supported narrower statement rather than inheriting failure "
            "from its original target. Perform a fresh independent verification pass after the revision. "
            "Continue through a new immutable theory bundle and rebuild the strongest evidence-consistent paper."
        )
    extra = f"\nResearcher constraints:\n{constraints.strip()}" if constraints.strip() else ""
    return (
        "Use $theoremgate for this workspace. "
        f"{objective}\n\nResearch question:\n{question}{extra}\n\n"
        f"Researcher publication goal: {goal_labels[publication_goal]} ({publication_goal}). "
        "Use this goal when comparing directions, theorem breadth, novelty evidence, experiments, "
        "and manuscript readiness, but never weaken correctness gates or overstate the supported route. "
        "If the goal is not reached, preserve and use the strongest honest alternative allowed by the run's "
        "interaction policy.\n"
        f"{repair_policy} {theorem_strength_policy} {interaction_instructions}\n"
        f"RUN CONTRACT: operate only on run {run_id} until an authorized router transition. The controller has already selected and, when needed, "
        "initialized it. A full run always uses the original-research acceptance goal; do not ask the researcher to choose a paper tier. Do not run workflow init directly, do not create an unrelated run, and do not switch to the latest "
        f"run. Pass --run {run_id} to every workflow.py and manuscript_workflow.py status, validate, init, and "
        "complete command until an explicitly authorized revision_router.py operation returns a linked child ID; "
        "after that, bind every mutation to that returned child.\n"
        f"{checkpoint_instructions} After governance, a same_run_proof_correction action returns the exact run to "
        "discovery and must be "
        "continued with $proof-repair. When bounded correction is unavailable, continue_with_salvage permits synthesis "
        "only from unaffected proof closures; start_revision or pivot_direction requires a linked revision cycle. "
        "At theory routing, a same_run_contribution_strengthening action must be continued with "
        "$contribution-strengthening from its reported resume stage; preserve accepted results and rerun every affected "
        "proof, novelty, significance, and contribution gate.\n"
        "Use only the plugin's governed controllers and packaged tools. Never run the legacy main.py, never overwrite "
        "a completed artifact, never invent citations or experimental results, and never broaden claims to justify a paper. "
        "Do not create a paper, draft manuscript, paper-like Markdown file, LaTeX manuscript, or `papers/` output with "
        "apply_patch, shell redirection, or an ordinary file-writing tool. Manuscript prose is authorized only after "
        "manuscript_workflow.py init succeeds for the exact run, and must be written beneath that run's `paper/` directory "
        "through manuscript_tools.py. Before reporting a paper path, verify the governed paper workflow exists. "
        "Validate and complete every stage with its required actor. Broad literature retrieval must be registered as "
        "discovery_candidate evidence; promote only a deliberate theorem-level shortlist to closest_work or "
        "novelty_neighbor. If earlier retrieval was overclassified, use literature_tools.py curate-novelty or "
        "reclassify-use and preserve the reclassification history. Validator minima are integrity floors, not "
        "literature-search targets. Never add one convenient paper merely to make a schema pass, never mark an abstract "
        "or landing page as theorem verification, and never justify a bibliography shortfall. Every paper must cite at least 15 relevant audited sources, and mature-area or original-research papers must cite at least 20. When a literature validator fails, return to the hybrid search protocol, inspect primary "
        "theorem text for the closest candidates, and record the executed structured and web queries. If that evidence "
        "cannot be obtained, use an unverified novelty verdict, continue the full paper with calibrated claims, and keep submission readiness false. Insufficient novelty "
        "evidence is not a reason to "
        "strand the run: complete an honest unverified novelty audit, continue through significance, contribution, and "
        "theory-bundle routing, and return the strongest supported document. Every accepted selected statement in every "
        "paper type must have a complete, labeled appendix proof with exact main-to-appendix cross-references. A run with "
        "no accepted statements must instead include a complete evidence appendix; never fabricate a proof. "
        "On the first manuscript and every full rewrite, select the best-fit venue before creating the schema-v3 "
        "content architecture. Bind the architecture and page budget to that venue's snapshot, allocate pages to every "
        "section, choose clear scholarly headings in conventional, technical, or combined forms according to the "
        "paper and section hierarchy, and satisfy the "
        "venue's enforced component constraints. For a no-limit journal, require at least 10 main-text pages excluding "
        "references and appendices, use matched-exemplar length only as a nonbinding allocation target, and do not invent a "
        "minimum total length. Place references before an explicitly labeled Appendix and choose a clear proof-section title "
        "that fits the manuscript hierarchy. For every selected claim, require a proof-detail plan and a genuinely detailed "
        "appendix derivation with explicit assumption use, auxiliary lemmas, at least three justified critical steps, "
        "constant/event bookkeeping, boundary checks, and an exact concluding inference; never accept sketches or omitted "
        "calculations as complete proofs. A request "
        "for a new manuscript must use revision_router.py action rewrite_manuscript and must not reuse unchanged section hashes. "
        f"{completion_instruction}"
    )


def normalize_event(raw: Dict[str, Any], seq: int) -> Dict[str, Any]:
    event_type = str(raw.get("type", "event"))
    title = event_type.replace("_", " ").replace(".", " · ").title()
    message = ""
    item = raw.get("item") if isinstance(raw.get("item"), dict) else {}
    if event_type == "thread.started":
        message = f"Codex session {raw.get('thread_id', '')} started."
    elif event_type in {"turn.started", "turn.completed", "turn.failed"}:
        usage = raw.get("usage")
        message = json.dumps(usage, ensure_ascii=False) if usage else str(raw.get("message", ""))
    elif event_type in {"item.started", "item.completed"}:
        item_type = str(item.get("type", "item"))
        title = item_type.replace("_", " ").title()
        message = str(
            item.get("text")
            or item.get("aggregated_output")
            or item.get("command")
            or item.get("name")
            or item.get("status")
            or ""
        )
    elif event_type == "error":
        title = "Codex error"
        message = str(raw.get("message") or raw.get("error") or "Unknown Codex error")
    else:
        message = str(raw.get("message") or raw.get("text") or "")
    if len(message) > 8_000:
        message = message[:7_999] + "…"
    return {
        "seq": seq,
        "timestamp": utc_now(),
        "type": event_type,
        "title": title,
        "message": message,
        "item_type": item.get("type") if item else None,
    }


class CodexJobRunner:
    """Run at most one mutating Codex job at a time in a workspace."""

    def __init__(
        self,
        workspace: Path,
        *,
        codex_binary: str = "codex",
        command_builder: Optional[Callable[[Dict[str, Any], Path], List[str]]] = None,
    ) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.codex_binary = codex_binary
        self.command_builder = command_builder
        self.root = self.workspace / ".theoremgate" / "studio" / "jobs"
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._processes: Dict[str, subprocess.Popen[bytes]] = {}
        self._events: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.RLock()
        self._load_jobs()

    @property
    def available(self) -> bool:
        return self.command_builder is not None or shutil.which(self.codex_binary) is not None

    def _load_jobs(self) -> None:
        if not self.root.is_dir():
            return
        for path in sorted(self.root.iterdir(), reverse=True):
            metadata_path = path / "job.json"
            if not metadata_path.is_file():
                continue
            try:
                value = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if (
                not isinstance(value, dict)
                or value.get("job_id") != path.name
                or not JOB_ID_PATTERN.fullmatch(path.name)
            ):
                continue
            if value.get("status") in {"starting", "running", "cancelling"} and not pid_alive(value.get("pid")):
                value["status"] = "interrupted"
                value["completed_at"] = utc_now()
                value["error"] = "TheoremAudit web interface restarted while this Codex job was active."
                self._write_metadata(path, value)
            self._jobs[value["job_id"]] = value
            events_path = path / "events.jsonl"
            events: deque[Dict[str, Any]] = deque(maxlen=2_000)
            if events_path.is_file():
                for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict):
                        events.append(event)
            self._events[value["job_id"]] = list(events)

    def _write_metadata(self, job_dir: Path, value: Dict[str, Any]) -> None:
        job_dir.mkdir(parents=True, exist_ok=True)
        write_json(job_dir / "job.json", value)

    def _disk_active_job(self) -> Optional[str]:
        if not self.root.is_dir():
            return None
        for job_dir in self.root.iterdir():
            path = job_dir / "job.json"
            if not path.is_file():
                continue
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if value.get("status") in {"starting", "running", "cancelling"} and pid_alive(value.get("pid")):
                return value.get("job_id") or job_dir.name
        return None

    def _public(self, job: Dict[str, Any]) -> Dict[str, Any]:
        keys = (
            "job_id", "kind", "status", "label", "mode", "model", "question", "run_id", "node_id",
            "parent_run_id", "parent_job_id", "thread_id", "started_at", "completed_at", "exit_code",
            "error", "event_count", "allow_subagents",
            "continuation_round", "automatic_continuation_job_id",
            "automatic_continuation_error", "last_event_at", "outcome",
        )
        result = {key: job.get(key) for key in keys if job.get(key) is not None}
        result["last_message_available"] = (self.root / job["job_id"] / "last_message.txt").is_file()
        return result

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.get("started_at", ""), reverse=True)
            active = next((item["job_id"] for item in jobs if item.get("status") not in TERMINAL_STATES), None)
            return {
                "available": self.available,
                "active_job_id": active,
                "jobs": [self._public(item) for item in jobs[:30]],
            }

    def events(self, job_id: str, after: int = 0) -> Dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise ValueError("Codex job was not found")
            items = [item for item in self._events.get(job_id, []) if int(item.get("seq", 0)) > after]
            return {"job": self._public(self._jobs[job_id]), "events": items}

    def _command(self, job: Dict[str, Any], job_dir: Path) -> List[str]:
        if self.command_builder is not None:
            return self.command_builder(job, job_dir)
        command = [
            self.codex_binary,
            "exec",
            "--json",
            "--color",
            "never",
            "--skip-git-repo-check",
            "--approve-for-me",
            "-C",
            str(self.workspace),
            "--output-last-message",
            str(job_dir / "last_message.txt"),
        ]
        if job.get("model"):
            command.extend(["--model", job["model"]])
        command.append(job["prompt"])
        return command

    def start(
        self,
        *,
        prompt: str,
        kind: str,
        label: str,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.available:
            raise ValueError("Codex CLI is not available on PATH")
        prompt = prompt.strip()
        if not prompt or len(prompt) > 60_000:
            raise ValueError("Codex prompt must contain between 1 and 60000 characters")
        model = validate_model(model)
        if not isinstance(kind, str) or not kind.strip() or len(kind) > 40:
            raise ValueError("job kind must contain between 1 and 40 characters")
        if not isinstance(label, str) or not label.strip() or len(label) > 240:
            raise ValueError("job label must contain between 1 and 240 characters")
        if metadata and any(key not in METADATA_FIELDS for key in metadata):
            unknown = sorted(set(metadata) - METADATA_FIELDS)
            raise ValueError(f"unsupported job metadata fields: {unknown}")
        with path_lock(self.root / "runner"):
            with self._lock:
                active = next(
                    (item.get("job_id") for item in self._jobs.values()
                     if item.get("status") not in TERMINAL_STATES and pid_alive(item.get("pid"))),
                    None,
                ) or self._disk_active_job()
                if active:
                    raise ValueError(f"another Codex job is already active in this workspace ({active})")
                return self._start_locked(
                    prompt=prompt, kind=kind, label=label, model=model, metadata=metadata,
                )

    def _start_locked(
        self,
        *,
        prompt: str,
        kind: str,
        label: str,
        model: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        with self._lock:
            job_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
            job_dir = self.root / job_id
            job: Dict[str, Any] = {
                "schema_version": 1,
                "job_id": job_id,
                "kind": kind.strip(),
                "label": label.strip(),
                "status": "starting",
                "model": model,
                "prompt": prompt,
                "started_at": utc_now(),
                "completed_at": None,
                "thread_id": None,
                "exit_code": None,
                "error": None,
                "event_count": 0,
            }
            if metadata:
                job.update(metadata)
            job_dir.mkdir(parents=True, exist_ok=False)
            self._jobs[job_id] = job
            self._events[job_id] = []
            self._write_metadata(job_dir, job)
            stderr_handle = None
            try:
                stderr_handle = open(job_dir / "stderr.log", "ab", buffering=0)
                command = self._command(job, job_dir)
                if not isinstance(command, list) or not command or any(
                    not isinstance(part, str) or "\x00" in part for part in command
                ):
                    raise ValueError("Codex command builder returned an invalid command")
                process = subprocess.Popen(
                    command,
                    cwd=str(self.workspace),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=stderr_handle,
                    start_new_session=True,
                    bufsize=0,
                )
            except Exception as exc:
                job["status"] = "failed"
                job["completed_at"] = utc_now()
                job["error"] = str(exc)
                self._write_metadata(job_dir, job)
                if stderr_handle is not None:
                    try:
                        stderr_handle.close()
                    except Exception:
                        pass
                raise ValueError(f"could not start Codex: {exc}") from exc
            job["status"] = "running"
            job["pid"] = process.pid
            self._processes[job_id] = process
            self._write_metadata(job_dir, job)
            threading.Thread(
                target=self._read_process,
                args=(job_id, process, stderr_handle),
                daemon=True,
                name=f"theoremgate-codex-{job_id}",
            ).start()
            return self._public(job)

    def _append_event(self, job_id: str, value: Dict[str, Any]) -> None:
        job_dir = self.root / job_id
        with self._lock:
            events = self._events.setdefault(job_id, [])
            events.append(value)
            if len(events) > 2_000:
                del events[:-2_000]
            job = self._jobs[job_id]
            job["event_count"] = int(job.get("event_count", 0)) + 1
            job["last_event_at"] = value.get("timestamp") or utc_now()
            if value.get("type") == "thread.started" and value.get("thread_id"):
                job["thread_id"] = value["thread_id"]
            with open(job_dir / "events.jsonl", "a", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False) + "\n")
                handle.flush()
            self._write_metadata(job_dir, job)

    def _governed_state(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Return the exact theory/paper completion state for one pipeline job."""
        run_id = job.get("run_id")
        manifest: Dict[str, Any] = {}
        if isinstance(run_id, str) and run_id:
            manifest_path = self.workspace / ".theoremgate" / "runs" / run_id / "run.json"
            try:
                decoded = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(decoded, dict):
                    manifest = decoded
            except (OSError, json.JSONDecodeError):
                manifest = {}
        theory_stage = manifest.get("current_stage") or "unknown"
        if manifest.get("status") != "completed" and theory_stage != "complete":
            return {"complete": False, "stage": theory_stage, "manifest": manifest}
        contract = manifest.get("execution_contract", {}) if isinstance(manifest, dict) else {}
        requested_mode = contract.get("requested_mode") or job.get("mode")
        if requested_mode == "theory":
            return {"complete": True, "stage": "complete", "manifest": manifest}
        if not isinstance(run_id, str) or not run_id:
            return {"complete": True, "stage": "complete", "manifest": manifest}
        paper_path = self.workspace / ".theoremgate" / "runs" / run_id / "paper" / "paper_run.json"
        try:
            paper = json.loads(paper_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"complete": False, "stage": "paper_initialization", "manifest": manifest}
        if not isinstance(paper, dict):
            return {"complete": False, "stage": "paper_initialization", "manifest": manifest}
        paper_stage = paper.get("current_stage") or "paper_complete"
        return {
            "complete": paper.get("status") == "completed",
            "stage": paper_stage,
            "manifest": manifest,
        }

    def _execution_outcome(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the persisted outcome without asking the researcher to route it."""
        if job.get("kind") != "pipeline":
            outcome = {
                "schema_version": 1,
                "state": "execution_complete" if job.get("status") == "completed" else "execution_stopped",
                "run_id": job.get("run_id"),
                "current_stage": None,
                "summary": "The Codex action finished and its persisted evidence is available.",
                "options": [],
                "recorded_at": utc_now(),
            }
            write_json(self.root / job["job_id"] / "outcome.json", outcome)
            return outcome
        governed = self._governed_state(job)
        run_id = job.get("run_id")
        stage = governed["stage"]
        run_complete = governed["complete"]
        job_status = job.get("status")
        if run_complete:
            state = "completed_result"
            summary = "The governed research-to-paper run reached its final persisted result."
        elif job_status in {"cancelled", "interrupted"}:
            state = "interrupted"
            summary = f"Execution stopped while the governed run remained at {stage}. Completed evidence was preserved."
        else:
            round_number = int(job.get("continuation_round", 0) or 0)
            if round_number < MAX_AUTOMATIC_CONTINUATIONS:
                state = "automatic_continuation"
                summary = (
                    f"The governed run remains at {stage}; automatic continuation "
                    f"{round_number + 1} of {MAX_AUTOMATIC_CONTINUATIONS} is starting."
                )
            else:
                state = "continuation_budget_exhausted"
                summary = (
                    f"The governed run remains at {stage} after {MAX_AUTOMATIC_CONTINUATIONS} "
                    "automatic continuation attempts. Completed evidence was preserved."
                )
        outcome = {
            "schema_version": 1,
            "state": state,
            "run_id": run_id,
            "current_stage": stage,
            "summary": summary,
            "options": [],
            "recorded_at": utc_now(),
        }
        job_dir = self.root / job["job_id"]
        write_json(job_dir / "outcome.json", outcome)
        return outcome

    def _maybe_start_automatic_continuation(self, job_id: str) -> None:
        with self._lock:
            job = dict(self._jobs[job_id])
        if job.get("kind") != "pipeline" or job.get("status") in {"cancelled", "interrupted"}:
            return
        governed = self._governed_state(job)
        round_number = int(job.get("continuation_round", 0) or 0)
        if governed["complete"] or round_number >= MAX_AUTOMATIC_CONTINUATIONS:
            return
        manifest = governed.get("manifest", {})
        question = str(job.get("question") or manifest.get("research_question") or "").strip()
        run_id = str(job.get("run_id") or "").strip()
        if not question or not run_id:
            return
        contract = manifest.get("execution_contract", {}) if isinstance(manifest, dict) else {}
        publication_goal = contract.get("publication_goal", "original_research")
        try:
            prompt = build_pipeline_prompt(
                mode="resume",
                question=question,
                run_id=run_id,
                parent_run_id=manifest.get("parent_run_id"),
                constraints="",
                publication_goal=publication_goal,
                auto_repair=False,
                max_auto_repair_rounds=0,
                interaction_policy="autonomous",
            )
            child = self.start(
                prompt=prompt,
                kind="pipeline",
                label=f"Automatic continuation {round_number + 1}/{MAX_AUTOMATIC_CONTINUATIONS}",
                model=job.get("model"),
                metadata={
                    "mode": "resume",
                    "question": question,
                    "run_id": run_id,
                    "parent_run_id": manifest.get("parent_run_id"),
                    "parent_job_id": job_id,
                    "auto_repair": False,
                    "max_auto_repair_rounds": 0,
                    "interaction_policy": "autonomous",
                    "continuation_round": round_number + 1,
                },
            )
        except ValueError as exc:
            with self._lock:
                current = self._jobs[job_id]
                current["automatic_continuation_error"] = str(exc)
                self._write_metadata(self.root / job_id, current)
            return
        with self._lock:
            current = self._jobs[job_id]
            current["automatic_continuation_job_id"] = child["job_id"]
            self._write_metadata(self.root / job_id, current)

    def _read_process(
        self,
        job_id: str,
        process: subprocess.Popen[bytes],
        stderr_handle: Any,
    ) -> None:
        try:
            if process.stdout is not None:
                for raw_line in iter(process.stdout.readline, b""):
                    text = raw_line.decode("utf-8", errors="replace").strip()
                    if not text:
                        continue
                    with self._lock:
                        seq = int(self._jobs[job_id].get("event_count", 0)) + 1
                    try:
                        raw = json.loads(text)
                    except json.JSONDecodeError:
                        event = {
                            "seq": seq,
                            "timestamp": utc_now(),
                            "type": "stdout",
                            "title": "Codex output",
                            "message": text[:8_000],
                            "item_type": None,
                        }
                    else:
                        event = normalize_event(raw, seq) if isinstance(raw, dict) else normalize_event({}, seq)
                        if isinstance(raw, dict) and raw.get("thread_id"):
                            event["thread_id"] = raw["thread_id"]
                    self._append_event(job_id, event)
            exit_code = process.wait()
        except Exception as exc:
            exit_code = process.poll()
            with self._lock:
                self._jobs[job_id]["error"] = str(exc)
        finally:
            if process.stdout is not None:
                try:
                    process.stdout.close()
                except Exception:
                    pass
            try:
                stderr_handle.close()
            except Exception:
                pass
        with self._lock:
            job = self._jobs[job_id]
            job["exit_code"] = exit_code
            job["completed_at"] = utc_now()
            if job.get("status") == "cancelling":
                job["status"] = "cancelled"
            elif exit_code == 0:
                job["status"] = "completed"
            else:
                job["status"] = "failed"
                if not job.get("error"):
                    job["error"] = f"Codex exited with status {exit_code}. See stderr.log for details."
            job["outcome"] = self._execution_outcome(job)
            self._processes.pop(job_id, None)
            self._write_metadata(self.root / job_id, job)
        self._maybe_start_automatic_continuation(job_id)

    def cancel(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            process = self._processes.get(job_id)
            if job is None:
                raise ValueError("Codex job was not found")
            if job.get("status") in TERMINAL_STATES:
                return self._public(job)
            if process is None:
                raise ValueError("active Codex process was not found")
            job["status"] = "cancelling"
            self._write_metadata(self.root / job_id, job)
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

        def force_stop() -> None:
            time.sleep(5)
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        threading.Thread(target=force_stop, daemon=True).start()
        return self._public(job)

    def wait(self, job_id: str, timeout: float = 10.0) -> Dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    raise ValueError("Codex job was not found")
                if job.get("status") in TERMINAL_STATES:
                    return self._public(job)
            time.sleep(0.02)
        raise TimeoutError(f"Codex job {job_id} did not finish in time")

    def run_continuation_chain(
        self,
        job_id: str,
        *,
        timeout: Optional[float] = None,
        on_job_finished: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Wait across the complete bounded automatic-continuation chain.

        A direct caller must not treat one child Codex turn ending as the end of a
        governed pipeline.  This method follows the child IDs created by
        ``_maybe_start_automatic_continuation`` until the governed theory/paper
        workflow is complete or the three-continuation budget is exhausted.
        """
        started = time.monotonic()
        current_job_id = job_id
        completed_jobs: List[Dict[str, Any]] = []
        while True:
            while True:
                if timeout is not None and time.monotonic() - started >= timeout:
                    raise TimeoutError(
                        f"Codex pipeline continuation for {job_id} did not finish in time"
                    )
                try:
                    completed = self.wait(current_job_id, timeout=0.5)
                    break
                except TimeoutError:
                    continue
            completed_jobs.append(completed)
            if on_job_finished is not None:
                on_job_finished(completed)
            with self._lock:
                governed = self._governed_state(dict(self._jobs[current_job_id]))
            outcome = completed.get("outcome", {})
            outcome_state = outcome.get("state") if isinstance(outcome, dict) else None
            if outcome_state == "completed_result":
                return {
                    "schema_version": 1,
                    "complete": True,
                    "run_id": completed.get("run_id"),
                    "current_stage": governed["stage"],
                    "continuations_used": int(completed.get("continuation_round", 0) or 0),
                    "jobs": completed_jobs,
                }

            if outcome_state != "automatic_continuation":
                return {
                    "schema_version": 1,
                    "complete": False,
                    "run_id": completed.get("run_id"),
                    "current_stage": governed["stage"],
                    "continuations_used": int(completed.get("continuation_round", 0) or 0),
                    "reason": outcome_state or "execution_stopped",
                    "error": completed.get("error"),
                    "jobs": completed_jobs,
                }

            # The process reader records terminal state before it starts and links
            # the continuation child, so wait briefly for that atomic hand-off.
            while True:
                if timeout is not None and time.monotonic() - started >= timeout:
                    raise TimeoutError(
                        f"Codex pipeline continuation for {job_id} did not finish in time"
                    )
                with self._lock:
                    current = self._public(self._jobs[current_job_id])
                child_id = current.get("automatic_continuation_job_id")
                if child_id:
                    current_job_id = str(child_id)
                    break
                continuation_error = current.get("automatic_continuation_error")
                round_number = int(current.get("continuation_round", 0) or 0)
                if continuation_error or round_number >= MAX_AUTOMATIC_CONTINUATIONS:
                    return {
                        "schema_version": 1,
                        "complete": False,
                        "run_id": completed.get("run_id"),
                        "current_stage": governed["stage"],
                        "continuations_used": round_number,
                        "reason": (
                            "automatic_continuation_error"
                            if continuation_error
                            else "continuation_budget_exhausted"
                        ),
                        "error": continuation_error,
                        "jobs": completed_jobs,
                    }
                time.sleep(0.02)

    def close(self, timeout: float = 5.0) -> None:
        """Stop active child processes before the web-interface process exits."""
        with self._lock:
            active = list(self._processes.items())
            for job_id, process in active:
                job = self._jobs[job_id]
                job["status"] = "cancelling"
                self._write_metadata(self.root / job_id, job)
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + max(0.0, timeout)
        for _, process in active:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
