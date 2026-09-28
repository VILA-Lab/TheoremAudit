#!/usr/bin/env python3
"""Safely write and inspect the current governed TheoremAudit artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import workflow
from state_store import (
    artifact_path,
    file_sha256,
    load_manifest,
    path_lock,
    read_json,
    utc_now,
    verify_completed_artifacts,
    write_json,
)
from tool_utils import run_dir


OPERATION_LOCK = "artifact-operation"


def operation_lock_path(root: Path) -> Path:
    return root / OPERATION_LOCK


def load_candidate(value: str, workspace: str) -> Dict[str, Any]:
    stripped = value.lstrip()
    if stripped.startswith("{"):
        try:
            result = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("expected a JSON object or workspace-contained JSON file") from exc
    else:
        workspace_root = Path(workspace).resolve()
        supplied = Path(value)
        candidate = supplied.resolve() if supplied.is_absolute() else (workspace_root / supplied).resolve()
        try:
            candidate.relative_to(workspace_root)
        except ValueError as exc:
            raise ValueError("input JSON file must stay inside the workspace") from exc
        if not candidate.is_file():
            raise ValueError("expected a JSON object or workspace-contained JSON file")
        result = read_json(candidate)
    if not isinstance(result, dict):
        raise ValueError("input must be a JSON object")
    return result


def revision_index_path(root: Path, stage_name: str) -> Path:
    return root / "artifacts" / "_revisions" / stage_name / "index.json"


def revision_summary(root: Path, stage_name: str) -> Dict[str, Any]:
    path = revision_index_path(root, stage_name)
    if not path.exists():
        return {"count": 0, "latest": None}
    index = read_json(path)
    revisions = index.get("revisions", []) if isinstance(index, dict) else []
    if not isinstance(revisions, list):
        raise ValueError(f"invalid artifact revision index for stage {stage_name}")
    return {"count": len(revisions), "latest": revisions[-1] if revisions else None}


def record_revision(
    root: Path,
    stage_name: str,
    actor: str,
    reason: str,
    value: Dict[str, Any],
    value_sha256: str,
    previous_sha256: Optional[str],
    manifest_revision: int,
) -> None:
    index_path = revision_index_path(root, stage_name)
    if index_path.exists():
        index = read_json(index_path)
        if not isinstance(index, dict) or not isinstance(index.get("revisions"), list):
            raise ValueError(f"invalid artifact revision index for stage {stage_name}")
    else:
        index = {
            "schema_version": 1,
            "artifact": "artifact_revision_index",
            "stage": stage_name,
            "revisions": [],
        }
    revision = len(index["revisions"]) + 1
    snapshot_path = index_path.parent / f"{revision:04d}.json"
    if snapshot_path.exists():
        raise ValueError(f"artifact revision snapshot already exists: {snapshot_path.name}")
    entry = {
        "revision": revision,
        "stage": stage_name,
        "actor": actor,
        "reason": reason,
        "written_at": utc_now(),
        "manifest_revision": manifest_revision,
        "previous_sha256": previous_sha256,
        "value_sha256": value_sha256,
        "snapshot": str(snapshot_path.relative_to(root)),
    }
    try:
        write_json(snapshot_path, {**entry, "value": value})
        index["revisions"].append(entry)
        write_json(index_path, index)
    except Exception:
        snapshot_path.unlink(missing_ok=True)
        raise


def current(workspace: str, run_id: Optional[str]) -> Tuple[Path, Dict[str, Any], str, Dict[str, Any]]:
    root = run_dir(workspace, run_id)
    manifest = load_manifest(root)
    verify_completed_artifacts(root, manifest)
    if manifest.get("status") == "completed":
        raise ValueError("theory workflow is already completed")
    stage_name = manifest.get("current_stage")
    stages = manifest.get("stages")
    if not isinstance(stage_name, str) or not isinstance(stages, dict) or stage_name not in stages:
        raise ValueError("run manifest has an inconsistent current stage")
    stage = stages[stage_name]
    if not isinstance(stage, dict) or stage.get("status") != "in_progress":
        raise ValueError(f"current stage {stage_name} is not marked in_progress")
    return root, manifest, stage_name, stage


def command_show(args):
    root, _, stage_name, stage = current(args.workspace, args.run)
    path = artifact_path(root, stage["artifact"])
    print(json.dumps({"stage": stage_name, "actor": stage["actor"], "artifact": str(path),
                      "exists": path.exists(), "value": read_json(path) if path.exists() else None,
                      "revision_history": revision_summary(root, stage_name)}, indent=2))


def command_write(args):
    root = run_dir(args.workspace, args.run)
    with path_lock(operation_lock_path(root)):
        root, manifest, stage_name, stage = current(args.workspace, args.run)
        if stage_name == "theory_bundle":
            raise ValueError("theory_bundle is generated by the controller and cannot be written manually")
        if args.actor != stage.get("actor"):
            raise PermissionError(
                f"stage {stage_name} requires actor {stage.get('actor')}; received {args.actor}"
            )
        reason = args.reason.strip()
        if not reason:
            raise ValueError("artifact write reason cannot be empty")
        value = load_candidate(args.input, args.workspace)
        path = artifact_path(root, stage["artifact"])
        existed = path.exists()
        if existed and not args.replace:
            raise ValueError("current artifact already exists; pass --replace only before stage completion")
        previous_value = read_json(path) if existed else None
        previous_sha256 = file_sha256(path) if existed else None
        write_json(path, value)
        value_sha256 = file_sha256(path)
        if previous_sha256 == value_sha256:
            raise ValueError("replacement is identical to the current artifact")
        try:
            workflow.validate_stage(root, stage_name)
            record_revision(
                root,
                stage_name,
                args.actor,
                reason,
                value,
                value_sha256,
                previous_sha256,
                manifest.get("state_revision", 0),
            )
        except Exception as exc:
            if existed:
                write_json(path, previous_value)
            else:
                path.unlink(missing_ok=True)
            raise ValueError(f"candidate artifact was rejected and the previous version was restored: {exc}") from exc
        print(json.dumps({
            "written": str(path),
            "stage": stage_name,
            "actor": args.actor,
            "value_sha256": value_sha256,
            "revision_history": revision_summary(root, stage_name),
        }, indent=2))


def command_validate(args):
    root = run_dir(args.workspace, args.run)
    with path_lock(operation_lock_path(root)):
        root, _, stage_name, _ = current(args.workspace, args.run)
        workflow.validate_stage(root, stage_name)
    print(json.dumps({"valid": True, "stage": stage_name}, indent=2))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("show").set_defaults(function=command_show)
    write = commands.add_parser("write-current")
    write.add_argument("--input", required=True)
    write.add_argument("--actor", required=True)
    write.add_argument("--reason", required=True)
    write.add_argument("--replace", action="store_true")
    write.set_defaults(function=command_write)
    commands.add_parser("validate").set_defaults(function=command_validate)
    return result


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, PermissionError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
