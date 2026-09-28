"""Shared containment and JSON helpers for packaged TheoremAudit tools."""

from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from state_store import file_sha256, read_json, resolve_run, update_json, utc_now


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DEFAULT_MAX_JSON_BYTES = 8 * 1024 * 1024


def identifier(value: str, label: str = "identifier") -> str:
    if (
        not isinstance(value, str)
        or not SAFE_ID.fullmatch(value)
        or value.endswith(".")
        or ".." in value
    ):
        raise ValueError(f"{label} must use letters, digits, '.', '_', or '-'")
    return value


def contained(root: Path, relative: str) -> Path:
    if root.is_symlink():
        raise ValueError("allowed root cannot be a symbolic link")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be relative and contained")
    resolved_root = root.resolve()
    result = (resolved_root / path).resolve()
    try:
        result.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("path escapes its allowed root") from exc
    return result


def workspace_path(root: Path, supplied: str) -> Path:
    resolved_root = root.resolve()
    candidate = Path(supplied)
    result = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
    try:
        result.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("input JSON file must stay inside the allowed workspace") from exc
    return result


def load_object_argument(
    value: str,
    allowed_root: Path,
    max_bytes: int = DEFAULT_MAX_JSON_BYTES,
) -> dict:
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    stripped = value.lstrip()
    if stripped.startswith("{"):
        if len(value.encode("utf-8")) > max_bytes:
            raise ValueError(f"inline JSON exceeds the {max_bytes}-byte safety limit")
        try:
            result = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("expected a JSON object or workspace-contained JSON file") from exc
    else:
        candidate = workspace_path(allowed_root, value)
        if not candidate.is_file():
            raise ValueError("expected a JSON object or workspace-contained JSON file")
        if candidate.stat().st_size > max_bytes:
            raise ValueError(f"input JSON exceeds the {max_bytes}-byte safety limit")
        result = read_json(candidate)
    if not isinstance(result, dict):
        raise ValueError("input must be a JSON object")
    return result


def run_dir(workspace: str, run_id: Optional[str]) -> Path:
    return resolve_run(Path(workspace), run_id)


def paper_dir(workspace: str, run_id: Optional[str]) -> Path:
    run_root = run_dir(workspace, run_id).resolve()
    unresolved = run_root / "paper"
    if unresolved.is_symlink():
        raise ValueError("paper directory cannot be a symbolic link")
    root = unresolved.resolve()
    try:
        root.relative_to(run_root)
    except ValueError as exc:
        raise ValueError("paper directory escapes the selected run") from exc
    if not root.is_dir():
        raise ValueError("paper workflow has not been initialized")
    manifest_path = root / "paper_run.json"
    authorization_path = root / "manuscript_authorization.json"
    if not manifest_path.is_file() or not authorization_path.is_file():
        raise ValueError("governed manuscript authorization is missing")
    manifest = read_json(manifest_path)
    authorization = read_json(authorization_path)
    if (
        not isinstance(manifest, dict)
        or not isinstance(authorization, dict)
        or authorization.get("artifact") != "manuscript_authorization"
        or authorization.get("run_id") != run_root.name
        or authorization.get("authorized_output_root") != "paper"
        or manifest.get("manuscript_authorization_sha256") != file_sha256(authorization_path)
    ):
        raise ValueError("invalid governed manuscript authorization")
    bundle_path = run_root / "artifacts" / "theory_bundle.json"
    if (
        not bundle_path.is_file()
        or authorization.get("theory_bundle_sha256") != file_sha256(bundle_path)
    ):
        raise ValueError("manuscript authorization does not match the current theory bundle")
    return root


def locked_json_update(path: Path, updater: Callable[[Dict[str, Any]], Dict[str, Any]], default: dict) -> dict:
    def transform(value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} must contain a JSON object")
        updated = updater(value)
        if not isinstance(updated, dict):
            raise ValueError("JSON updater must return an object")
        return updated

    return update_json(path, transform, default)


def append_json_record(
    path: Path,
    key: str,
    record: dict,
    *,
    actor: str,
    id_key: str = "id",
    operation: str = "append",
) -> dict:
    if not isinstance(record, dict):
        raise ValueError("record must be a JSON object")
    record_id = record.get(id_key)
    if not isinstance(record_id, str) or not record_id:
        raise ValueError(f"record requires a non-empty {id_key}")
    actor = identifier(actor, "actor")
    payload = dict(record)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload["_provenance"] = {
        "actor": actor,
        "operation": operation,
        "recorded_at": utc_now(),
        "record_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }

    def append(value: Dict[str, Any]) -> Dict[str, Any]:
        records = value.setdefault(key, [])
        if not isinstance(records, list):
            raise ValueError(f"{key} must be a list")
        if any(item.get(id_key) == record_id for item in records if isinstance(item, dict)):
            raise ValueError(f"duplicate {id_key}: {record_id}")
        records.append(payload)
        return value

    return locked_json_update(path, append, {key: []})
