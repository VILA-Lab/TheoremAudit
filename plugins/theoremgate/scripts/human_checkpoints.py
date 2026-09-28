#!/usr/bin/env python3
"""Read and preserve legacy researcher-decision records without blocking execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from state_store import file_sha256, load_manifest, read_json, update_json, utc_now


CHECKPOINT_DECISIONS = {
    "direction_selection": {"approve", "request_alternatives", "edit_scope", "stop"},
    "governance_outcome": {
        "continue_with_salvage", "start_revision", "pivot_direction", "export", "stop"
    },
    "refinement": {
        "start_revision", "salvage_statements", "start_extension", "export", "stop"
    },
    "publication_route": {"write", "strengthen", "export", "stop"},
}
DECISION_ORIGINS = {"studio", "chat", "automatic_contract"}


def registry_path(run_dir: Path) -> Path:
    return run_dir / "artifacts" / "human_checkpoints.json"


def empty_registry() -> Dict[str, Any]:
    return {"schema_version": 1, "artifact": "human_checkpoint_registry", "decisions": []}


def load_registry(run_dir: Path) -> Dict[str, Any]:
    path = registry_path(run_dir)
    if not path.is_file():
        return empty_registry()
    value = read_json(path)
    if not isinstance(value, dict) or value.get("artifact") != "human_checkpoint_registry":
        raise ValueError("invalid human checkpoint registry")
    decisions = value.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("human checkpoint decisions must be a list")
    return value


def checkpoints_required(run_dir: Path) -> bool:
    # Checkpoint records remain readable as historical provenance, but execution
    # never waits for a new user response. Starting or resuming a run is the
    # authorization to make routine in-scope decisions autonomously.
    return False


def context_path(run_dir: Path, checkpoint: str) -> Path:
    if checkpoint == "direction_selection":
        return run_dir / "artifacts" / "selected_direction.json"
    if checkpoint in {"refinement", "publication_route"}:
        return run_dir / "artifacts" / "theory_bundle.json"
    if checkpoint == "governance_outcome":
        return run_dir / "artifacts" / "governance_review.json"
    raise ValueError(f"unknown human checkpoint: {checkpoint}")


def context_record(run_dir: Path, checkpoint: str) -> Dict[str, str]:
    path = context_path(run_dir, checkpoint)
    if not path.is_file():
        raise ValueError(f"checkpoint context is not ready: {path.relative_to(run_dir)}")
    return {"path": str(path.relative_to(run_dir)), "sha256": file_sha256(path)}


def latest_decision(run_dir: Path, checkpoint: str, *, current_only: bool = True) -> Optional[Dict[str, Any]]:
    if checkpoint not in CHECKPOINT_DECISIONS:
        raise ValueError(f"unknown human checkpoint: {checkpoint}")
    expected = context_record(run_dir, checkpoint)["sha256"] if current_only else None
    for item in reversed(load_registry(run_dir)["decisions"]):
        if item.get("checkpoint") != checkpoint:
            continue
        if expected is not None and item.get("context", {}).get("sha256") != expected:
            continue
        return item
    return None


def record_decision(
    run_dir: Path,
    checkpoint: str,
    decision: str,
    note: str = "",
    *,
    origin: str,
    researcher_message: str = "",
) -> Dict[str, Any]:
    if checkpoint not in CHECKPOINT_DECISIONS:
        raise ValueError(f"unknown human checkpoint: {checkpoint}")
    if decision not in CHECKPOINT_DECISIONS[checkpoint]:
        raise ValueError(f"invalid decision for {checkpoint}: {decision}")
    if not isinstance(note, str) or len(note) > 4_000:
        raise ValueError("checkpoint note must be text of at most 4000 characters")
    if origin not in DECISION_ORIGINS:
        raise ValueError(f"invalid checkpoint decision origin: {origin}")
    if origin == "automatic_contract" and checkpoint not in {"governance_outcome", "refinement"}:
        raise PermissionError(
            "automatic authorization cannot approve a research direction or publication route"
        )
    if origin == "chat" and (not isinstance(researcher_message, str) or not researcher_message.strip()):
        raise ValueError("chat checkpoint decisions require the researcher's exact approval message")
    if not isinstance(researcher_message, str) or len(researcher_message) > 4_000:
        raise ValueError("researcher_message must be text of at most 4000 characters")
    context = context_record(run_dir, checkpoint)

    def append(value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict) or value.get("artifact") != "human_checkpoint_registry":
            raise ValueError("invalid human checkpoint registry")
        items = value.get("decisions")
        if not isinstance(items, list):
            raise ValueError("human checkpoint decisions must be a list")
        sequence = len(items) + 1
        record = {
            "id": f"HD-{sequence:04d}",
            "checkpoint": checkpoint,
            "decision": decision,
            "note": note.strip(),
            "origin": origin,
            "researcher_message": researcher_message.strip(),
            "context": context,
            "recorded_at": utc_now(),
            "actor": "controller" if origin == "automatic_contract" else "researcher",
        }
        items.append(record)
        return value

    updated = update_json(registry_path(run_dir), append, empty_registry())
    return updated["decisions"][-1]


def public_status(run_dir: Path, checkpoint: str) -> Dict[str, Any]:
    path = context_path(run_dir, checkpoint)
    if not path.is_file():
        return {"checkpoint": checkpoint, "ready": False, "required": checkpoints_required(run_dir)}
    latest = latest_decision(run_dir, checkpoint)
    return {
        "checkpoint": checkpoint,
        "ready": True,
        "required": checkpoints_required(run_dir),
        "decision": latest,
        "context": context_record(run_dir, checkpoint),
    }
