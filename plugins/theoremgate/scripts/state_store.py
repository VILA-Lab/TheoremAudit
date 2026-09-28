#!/usr/bin/env python3
"""Run-scoped, integrity-checked state primitives for TheoremAudit."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional


RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
STAGE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LOCK_TIMEOUT_SECONDS = 10.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing JSON artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def _lock_file(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _try_lock(handle: Any) -> bool:
    if os.name == "nt":
        import msvcrt

        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def _unlock(handle: Any) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def path_lock(path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    """Hold a cross-process advisory lock for one state path."""
    lock_path = _lock_file(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    with lock_path.open("a+b") as handle:
        while not _try_lock(handle):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for state lock: {path}")
            time.sleep(0.05)
        try:
            yield
        finally:
            _unlock(handle)


def _write_json_unlocked(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
        temporary = None
        if os.name != "nt":
            try:
                directory = os.open(str(path.parent), os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            except OSError:
                # Some network and virtual filesystems do not support directory fsync.
                pass
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_json(path: Path, value: Any) -> None:
    with path_lock(path):
        _write_json_unlocked(path, value)


def update_json(path: Path, updater: Callable[[Any], Any], default: Any) -> Any:
    """Atomically read, transform, and replace one JSON value under a single lock."""
    with path_lock(path):
        current = read_json(path) if path.exists() else deepcopy(default)
        updated = updater(current)
        _write_json_unlocked(path, updated)
        return updated


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_run_id(value: Any) -> str:
    if not isinstance(value, str) or not RUN_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "run ID must be 1-128 characters using letters, digits, '.', '_', or '-'"
        )
    return value


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:48] or "research"


def data_root(workspace: Path) -> Path:
    return workspace.resolve() / ".theoremgate"


def runs_root(workspace: Path) -> Path:
    return data_root(workspace) / "runs"


def safe_run_path(workspace: Path, run_id: str) -> Path:
    root = runs_root(workspace).resolve()
    candidate = (root / validate_run_id(run_id)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("run path escapes the workspace run root") from exc
    return candidate


def manifest_path(run_dir: Path) -> Path:
    return run_dir / "run.json"


def load_manifest(run_dir: Path) -> Dict[str, Any]:
    value = read_json(manifest_path(run_dir))
    if not isinstance(value, dict):
        raise ValueError("run manifest must be a JSON object")
    return value


def save_manifest(run_dir: Path, value: Dict[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ValueError("run manifest must be a JSON object")
    path = manifest_path(run_dir)
    with path_lock(path):
        current_revision = 0
        if path.exists():
            current = read_json(path)
            if not isinstance(current, dict):
                raise ValueError("run manifest must be a JSON object")
            current_revision = current.get("state_revision", 0)
            if not isinstance(current_revision, int) or current_revision < 0:
                raise ValueError("run manifest has an invalid state_revision")
        expected_revision = value.get("state_revision", 0)
        if expected_revision != current_revision:
            raise ValueError(
                "run manifest changed concurrently; reload the run before updating it"
            )
        updated = dict(value)
        updated["state_revision"] = current_revision + 1
        _write_json_unlocked(path, updated)
        value.clear()
        value.update(updated)


def validate_stages(stages: Any) -> Dict[str, Dict[str, str]]:
    if not isinstance(stages, dict) or not stages:
        raise ValueError("stages must be a non-empty object")
    for name, spec in stages.items():
        if not isinstance(name, str) or not STAGE_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"invalid stage name: {name!r}")
        if not isinstance(spec, dict):
            raise ValueError(f"stage {name} specification must be an object")
        for field in ("actor", "artifact"):
            if not isinstance(spec.get(field), str) or not spec[field].strip():
                raise ValueError(f"stage {name} requires a non-empty {field}")
        artifact = Path(spec["artifact"])
        if artifact.is_absolute() or ".." in artifact.parts:
            raise ValueError(f"stage {name} artifact must stay inside the run")
    return stages


def resolve_run(workspace: Path, run_id: Optional[str] = None) -> Path:
    if run_id:
        candidate = safe_run_path(workspace, run_id)
    else:
        latest = read_json(data_root(workspace) / "latest.json")
        if not isinstance(latest, dict) or not latest.get("run_id"):
            raise ValueError("latest run pointer is missing or invalid")
        candidate = safe_run_path(workspace, latest["run_id"])
    if not candidate.is_dir():
        raise ValueError(f"run not found: {candidate.name}")
    return candidate


def create_run(
    workspace: Path,
    question: str,
    stages: Dict[str, Dict[str, str]],
    run_id: Optional[str] = None,
    parent_run_id: Optional[str] = None,
    execution_contract: Optional[Dict[str, Any]] = None,
) -> Path:
    question = question.strip()
    if not question:
        raise ValueError("research question cannot be empty")
    stages = validate_stages(stages)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    selected_id = validate_run_id(run_id or f"{stamp}-{slug(question)}")
    run_dir = safe_run_path(workspace, selected_id)
    if run_dir.exists():
        raise ValueError(f"run already exists: {run_dir}")
    if parent_run_id:
        parent = safe_run_path(workspace, parent_run_id)
        if not parent.is_dir():
            raise ValueError(f"parent run not found: {parent_run_id}")

    contract = dict(execution_contract or {})
    allowed_contract_fields = {
        "intent", "initiated_from", "requested_mode", "subagents_permitted",
        "human_checkpoints_required", "repair_strategy", "researcher_decision_id",
        "publication_goal", "auto_repair_enabled", "max_auto_repair_rounds",
        "repair_round", "repair_authorization", "interaction_policy", "run_confirmed_at",
    }
    unknown_contract_fields = sorted(set(contract) - allowed_contract_fields)
    if unknown_contract_fields:
        raise ValueError(
            f"unsupported execution contract fields: {unknown_contract_fields}"
        )
    intent = contract.get("intent", "repair" if parent_run_id else "new_theory")
    if intent not in {"new_theory", "new_full", "repair"}:
        raise ValueError("execution contract intent must be new_theory, new_full, or repair")
    if intent == "repair" and not parent_run_id:
        raise ValueError("repair execution contracts require a parent run")
    if intent != "repair" and parent_run_id:
        raise ValueError("only repair execution contracts may have a parent run")
    initiated_from = contract.get("initiated_from", "controller")
    if initiated_from not in {"controller", "cli", "studio"}:
        raise ValueError("execution contract initiated_from must be controller, cli, or studio")
    requested_mode = contract.get("requested_mode", intent.removeprefix("new_"))
    if requested_mode not in {"theory", "full", "repair"}:
        raise ValueError("execution contract requested_mode must be theory, full, or repair")
    expected_mode = {
        "new_theory": "theory",
        "new_full": "full",
        "repair": "repair",
    }[intent]
    if requested_mode != expected_mode:
        raise ValueError(
            f"execution contract intent {intent} requires requested_mode={expected_mode}"
        )
    subagents_permitted = contract.get("subagents_permitted")
    if subagents_permitted is not None and not isinstance(subagents_permitted, bool):
        raise ValueError("execution contract subagents_permitted must be true or false")
    human_checkpoints_required = contract.get("human_checkpoints_required", False)
    if not isinstance(human_checkpoints_required, bool):
        raise ValueError("execution contract human_checkpoints_required must be true or false")
    interaction_policy = contract.get(
        "interaction_policy", "checkpointed" if human_checkpoints_required else "controller_default"
    )
    if interaction_policy not in {"checkpointed", "autonomous", "confirm_once", "controller_default"}:
        raise ValueError("invalid execution contract interaction_policy")
    run_confirmed_at = contract.get("run_confirmed_at")
    if run_confirmed_at is not None and (
        not isinstance(run_confirmed_at, str) or not run_confirmed_at.strip()
    ):
        raise ValueError("execution contract run_confirmed_at must be non-empty text")
    if interaction_policy == "confirm_once":
        if human_checkpoints_required:
            raise ValueError("confirm_once interaction policy cannot require human checkpoints")
        if run_confirmed_at is None:
            raise ValueError("confirm_once interaction policy requires run_confirmed_at")
    if interaction_policy == "autonomous" and human_checkpoints_required:
        raise ValueError("autonomous interaction policy cannot require human checkpoints")
    repair_strategy = contract.get("repair_strategy")
    if repair_strategy is not None and repair_strategy not in {
        "repair_full_theorem", "salvage_independent_statements", "pivot_direction",
        "contribution_extension"
    }:
        raise ValueError("invalid execution contract repair_strategy")
    if repair_strategy is not None and intent != "repair":
        raise ValueError("repair_strategy is available only for repair contracts")
    researcher_decision_id = contract.get("researcher_decision_id")
    if researcher_decision_id is not None and (
        not isinstance(researcher_decision_id, str) or not researcher_decision_id.strip()
    ):
        raise ValueError("execution contract researcher_decision_id must be non-empty text")
    repair_authorization = contract.get("repair_authorization")
    if repair_authorization is not None:
        if intent != "repair" or not isinstance(repair_authorization, dict):
            raise ValueError("repair_authorization is available only for repair contracts")
        required_authorization = {"plan_id", "source_run_id", "action", "target", "origin"}
        if set(repair_authorization) != required_authorization:
            raise ValueError("repair_authorization has invalid fields")
        if repair_authorization["source_run_id"] != parent_run_id:
            raise ValueError("repair_authorization source_run_id must match the parent run")
        for field in required_authorization:
            if not isinstance(repair_authorization[field], str) or not repair_authorization[field].strip():
                raise ValueError(f"repair_authorization.{field} must be non-empty text")
        if repair_authorization["origin"] not in {"automatic_contract", "direct_researcher"}:
            raise ValueError("repair_authorization.origin is invalid")
    publication_goal = contract.get("publication_goal", "no_preference")
    if publication_goal not in {
        "original_research", "workshop_or_short_paper", "technical_note",
        "expository_paper", "reproducibility_paper", "no_preference",
    }:
        raise ValueError("invalid execution contract publication_goal")
    auto_repair_enabled = contract.get("auto_repair_enabled", False)
    if not isinstance(auto_repair_enabled, bool):
        raise ValueError("execution contract auto_repair_enabled must be true or false")
    max_auto_repair_rounds = contract.get("max_auto_repair_rounds", 3 if auto_repair_enabled else 0)
    if (
        not isinstance(max_auto_repair_rounds, int)
        or isinstance(max_auto_repair_rounds, bool)
        or not 0 <= max_auto_repair_rounds <= 3
    ):
        raise ValueError("execution contract max_auto_repair_rounds must be between 0 and 3")
    if not auto_repair_enabled and max_auto_repair_rounds != 0:
        raise ValueError("disabled automatic repair requires max_auto_repair_rounds=0")
    repair_round = contract.get("repair_round", 0)
    if (
        not isinstance(repair_round, int)
        or isinstance(repair_round, bool)
        or not 0 <= repair_round <= max_auto_repair_rounds
    ):
        raise ValueError("execution contract repair_round exceeds the automatic repair budget")
    normalized_contract = {
        "intent": intent,
        "initiated_from": initiated_from,
        "requested_mode": requested_mode,
        "subagents_permitted": subagents_permitted,
        "human_checkpoints_required": human_checkpoints_required,
        "interaction_policy": interaction_policy,
        "repair_strategy": repair_strategy,
        "researcher_decision_id": researcher_decision_id,
        "publication_goal": publication_goal,
        "auto_repair_enabled": auto_repair_enabled,
        "max_auto_repair_rounds": max_auto_repair_rounds,
        "repair_round": repair_round,
        "repair_authorization": repair_authorization,
    }
    if run_confirmed_at is not None:
        normalized_contract["run_confirmed_at"] = run_confirmed_at

    try:
        run_dir.mkdir(parents=True)
    except FileExistsError as exc:
        raise ValueError(f"run already exists: {run_dir}") from exc
    (run_dir / "artifacts").mkdir()
    (run_dir / "proofs").mkdir()
    stage_names = list(stages)
    manifest = {
        "schema_version": 2,
        "artifact": "run_manifest",
        "run_id": selected_id,
        "research_question": question,
        "created_at": utc_now(),
        "parent_run_id": parent_run_id,
        "execution_contract": normalized_contract,
        "status": "active",
        "current_stage": stage_names[0],
        "stages": {
            name: {
                "status": "pending",
                "actor": spec["actor"],
                "artifact": spec["artifact"],
            }
            for name, spec in stages.items()
        },
    }
    manifest["stages"][stage_names[0]]["status"] = "in_progress"
    save_manifest(run_dir, manifest)
    write_json(data_root(workspace) / "latest.json", {"run_id": selected_id})
    return run_dir


def artifact_path(run_dir: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"artifact path must stay inside the run: {relative_path}")
    candidate = (run_dir / relative).resolve()
    try:
        candidate.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"artifact path escapes the run: {relative_path}") from exc
    return candidate


def verify_completed_artifacts(run_dir: Path, manifest: Dict[str, Any]) -> None:
    for name, stage in manifest.get("stages", {}).items():
        if stage.get("status") != "completed":
            continue
        path = artifact_path(run_dir, stage["artifact"])
        expected = stage.get("evidence_sha256")
        if not path.is_file() or not expected:
            raise ValueError(f"completed stage {name} has missing evidence")
        actual = file_sha256(path)
        if actual != expected:
            raise ValueError(f"completed artifact for {name} was modified")
