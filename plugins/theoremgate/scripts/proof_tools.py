#!/usr/bin/env python3
"""Create and update run-scoped proof artifacts without escaping the proof stage."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from proof_dag import ProofDAG
from proof_store import (
    BLUEPRINT_REQUIRED,
    DRAFT_REQUIRED,
    GOVERNANCE_STATUSES,
    OPEN_GAP_REQUIRED,
    PROOF_INDEX_SCHEMA_VERSION,
    PROOF_STATUSES,
    require_proof_id,
    validate_blueprint,
    validate_proof_index,
    validate_status_transition,
)
from state_store import artifact_path, file_sha256, load_manifest, read_json, utc_now, verify_completed_artifacts, write_json
from tool_utils import contained, load_object_argument, run_dir


def proof_root(args):
    root = run_dir(args.workspace, args.run)
    manifest = load_manifest(root)
    verify_completed_artifacts(root, manifest)
    if manifest.get("current_stage") != "proof_development":
        raise ValueError("proof tools are writable only during proof_development")
    stage = manifest.get("stages", {}).get("proof_development", {})
    if stage.get("status") != "in_progress":
        raise ValueError("proof_development is not marked in_progress")
    if args.actor != stage.get("actor"):
        raise PermissionError(
            f"proof_development requires actor {stage.get('actor')}; received {args.actor}"
        )
    return root


def obligations(root):
    discovery = read_json(root / "artifacts" / "discovery.json")
    return {item["id"]: item for item in discovery.get("proof_obligations", [])}


def load_index(root):
    path = root / "proofs" / "index.json"
    return read_json(path) if path.exists() else {"proofs": []}


def record_for(index, po_id):
    matches = [record for record in index.get("proofs", []) if record.get("id") == po_id]
    if len(matches) != 1:
        raise ValueError(f"proof index must contain exactly one record for {po_id}")
    return matches[0]


def command_scaffold(args):
    root = proof_root(args)
    path = root / "proofs" / "index.json"
    if path.exists():
        raise ValueError("proof index already exists")
    records = []
    for po_id, obligation in obligations(root).items():
        require_proof_id(po_id)
        records.append({
            "id": po_id,
            "status": "unstarted",
            "blueprint_path": None,
            "blueprint_sha256": None,
            "draft_path": None,
            "draft_sha256": None,
            "depends_on": obligation.get("depends_on", []),
            "assumptions_used": [],
            "proved_scope": "",
            "gaps": [],
            "status_history": [{
                "from": None,
                "to": "unstarted",
                "actor": args.actor,
                "reason": "Proof obligation scaffolded from discovery.",
                "recorded_at": utc_now(),
            }],
        })
    write_json(path, {"schema_version": PROOF_INDEX_SCHEMA_VERSION, "proofs": records})
    validate_proof_index(root)
    print(json.dumps({"created": str(path), "proofs": len(records)}, indent=2))


def command_migrate(args):
    root = proof_root(args)
    path = root / "proofs" / "index.json"
    index = read_json(path)
    if index.get("schema_version") == PROOF_INDEX_SCHEMA_VERSION:
        print(json.dumps({"migrated": False, "reason": "already current"}, indent=2))
        return
    if not isinstance(index, dict) or not isinstance(index.get("proofs"), list):
        raise ValueError("legacy proof index must contain a proofs list")
    old_schema_version = index.get("schema_version")
    reason = args.reason.strip()
    if not reason:
        raise ValueError("migration reason cannot be empty")
    migrated_at = utc_now()
    for record in index["proofs"]:
        if not isinstance(record, dict):
            raise ValueError("legacy proof records must be objects")
        proof_id = require_proof_id(record.get("id"))
        status = record.get("status")
        if status in GOVERNANCE_STATUSES:
            raise ValueError(
                f"legacy governed status for {proof_id} requires explicit governor migration"
            )
        record.setdefault("assumptions_used", [])
        record.setdefault("proved_scope", "")
        record.setdefault("depends_on", [])
        raw_gaps = record.get("gaps", [])
        if not isinstance(raw_gaps, list):
            raise ValueError(f"legacy gaps for {proof_id} must be a list")
        normalized_gaps = []
        for position, gap in enumerate(raw_gaps, start=1):
            if isinstance(gap, dict):
                description = gap.get("description") or gap.get("reason") or f"Legacy gap {position}."
                resolved = bool(gap.get("resolved")) or bool(gap.get("resolution"))
                normalized_gaps.append({
                    "id": gap.get("id") or f"G-MIG-{position}",
                    "severity": gap.get("severity") if gap.get("severity") in {"minor", "major", "fatal"} else "major",
                    "description": description,
                    "status": "resolved" if resolved else "open",
                    "resolution": gap.get("resolution") if resolved else None,
                })
            else:
                normalized_gaps.append({
                    "id": f"G-MIG-{position}",
                    "severity": "major",
                    "description": str(gap),
                    "status": "open",
                    "resolution": None,
                })
        if status in OPEN_GAP_REQUIRED and not any(gap["status"] == "open" for gap in normalized_gaps):
            normalized_gaps.append({
                "id": "G-MIG-STATUS",
                "severity": "major",
                "description": f"Legacy {status} status requires explicit review after migration.",
                "status": "open",
                "resolution": None,
            })
        record["gaps"] = normalized_gaps

        if status in BLUEPRINT_REQUIRED:
            blueprint_path = root / "proofs" / proof_id / "blueprint.json"
            if not blueprint_path.is_file():
                write_json(blueprint_path, {
                    "proof_id": proof_id,
                    "strategy": "Legacy integrity baseline; the original blueprint was not persisted.",
                    "dependencies": record["depends_on"],
                    "assumptions": record["assumptions_used"],
                    "fragile_steps": [],
                    "fallbacks": [],
                    "migration_note": reason,
                })
            record["blueprint_path"] = str(blueprint_path.relative_to(root))
            record["blueprint_sha256"] = file_sha256(blueprint_path)
        else:
            record["blueprint_path"] = None
            record["blueprint_sha256"] = None

        draft_path = record.get("draft_path")
        if draft_path:
            draft = artifact_path(root, draft_path)
            try:
                draft.relative_to((root / "proofs").resolve())
            except ValueError as exc:
                raise ValueError(f"legacy draft for {proof_id} must stay under proofs/") from exc
            if not draft.is_file() or draft.stat().st_size == 0:
                raise ValueError(f"legacy draft for {proof_id} is missing or empty")
            record["draft_sha256"] = file_sha256(draft)
        else:
            record["draft_sha256"] = None
        if status in DRAFT_REQUIRED and not record.get("proved_scope", "").strip():
            raise ValueError(f"legacy {proof_id} requires proved_scope before migration")
        record["status_history"] = [{
            "from": None,
            "to": status,
            "actor": args.actor,
            "reason": f"Legacy integrity baseline: {reason}",
            "recorded_at": migrated_at,
        }]
    index["schema_version"] = PROOF_INDEX_SCHEMA_VERSION
    index["migration"] = {
        "from_schema_version": old_schema_version,
        "migrated_at": migrated_at,
        "actor": args.actor,
        "reason": reason,
        "integrity_notice": "Hashes certify the migration baseline, not earlier file history.",
    }
    write_json(path, index)
    validate_proof_index(root)
    print(json.dumps({"migrated": True, "proofs": len(index["proofs"])}, indent=2))


def command_frontier(args):
    root = proof_root(args)
    proof_map = validate_proof_index(root)
    dag = ProofDAG(list(proof_map.values()))
    statuses = {proof_id: record["status"] for proof_id, record in proof_map.items()}
    print(json.dumps({
        "topological_order": dag.topological_order(),
        "frontier": dag.drafting_frontier(statuses),
    }, indent=2))


def command_blueprint(args):
    root = proof_root(args)
    po_id = require_proof_id(args.po)
    if po_id not in obligations(root):
        raise ValueError(f"unknown proof obligation: {po_id}")
    value = load_object_argument(args.input, Path(args.workspace))
    value.setdefault("proof_id", po_id)
    validate_blueprint(value, po_id)
    path = contained(root / "proofs", f"{po_id}/blueprint.json")
    if path.exists() and not args.replace:
        raise ValueError("blueprint already exists")
    index = load_index(root)
    if index.get("schema_version") != PROOF_INDEX_SCHEMA_VERSION:
        raise ValueError("legacy proof index must be migrated before governed updates")
    original_index = copy.deepcopy(index)
    previous_blueprint = read_json(path) if path.exists() else None
    record = record_for(index, po_id)
    reason = args.reason.strip()
    validate_status_transition(record["status"], "planned", args.actor, reason)
    write_json(path, value)
    record.update({
        "status": "planned",
        "blueprint_path": str(path.relative_to(root)),
        "blueprint_sha256": file_sha256(path),
    })
    record["status_history"].append({
        "from": record["status_history"][-1]["to"],
        "to": "planned",
        "actor": args.actor,
        "reason": reason,
        "recorded_at": utc_now(),
    })
    index_path = root / "proofs" / "index.json"
    try:
        write_json(index_path, index)
        validate_proof_index(root)
    except Exception:
        write_json(index_path, original_index)
        if previous_blueprint is None:
            path.unlink(missing_ok=True)
        else:
            write_json(path, previous_blueprint)
        raise
    print(json.dumps({"written": str(path)}, indent=2))


def command_check(args):
    root = proof_root(args)
    po_id = require_proof_id(args.po)
    if po_id not in obligations(root):
        raise ValueError(f"unknown proof obligation: {po_id}")
    value = load_object_argument(args.input, Path(args.workspace))
    checks_path = contained(root / "proofs", f"{po_id}/tool_checks.json")
    current = read_json(checks_path) if checks_path.exists() else {"checks": []}
    checks = current.setdefault("checks", [])
    if not isinstance(checks, list):
        raise ValueError("checks must be a list")
    checks.append(value)
    write_json(checks_path, current)
    print(json.dumps({"written": str(checks_path), "count": len(checks)}, indent=2))


def command_draft(args):
    root = proof_root(args)
    po_id = require_proof_id(args.po)
    if args.status not in PROOF_STATUSES:
        raise ValueError(f"invalid proof status: {args.status}")
    if args.status in GOVERNANCE_STATUSES:
        raise PermissionError("proof-team draft tools cannot assign Arbiter proof statuses")
    index = load_index(root)
    if index.get("schema_version") != PROOF_INDEX_SCHEMA_VERSION:
        raise ValueError("legacy proof index must be migrated before governed updates")
    record = record_for(index, po_id)
    if record["status"] == "unstarted":
        raise ValueError("write and validate a proof blueprint before drafting")
    reason = args.reason.strip()
    validate_status_transition(record["status"], args.status, args.actor, reason)
    content_path = contained(root / "proofs", args.input)
    if not content_path.is_file():
        raise ValueError(
            f"draft input file does not exist: {content_path}; --input must be relative "
            f"to the run proofs directory (for example, inputs/{po_id}.md), "
            "or an absolute path inside that directory"
        )
    suffix = content_path.suffix if content_path.suffix in {".md", ".tex"} else ".md"
    draft_path = contained(root / "proofs", f"{po_id}{suffix}")
    if draft_path.exists() and not args.replace:
        raise ValueError("proof draft already exists")
    previous_draft = draft_path.read_bytes() if draft_path.exists() else None
    original_index = copy.deepcopy(index)
    draft_path.write_text(content_path.read_text(encoding="utf-8"), encoding="utf-8")
    metadata = load_object_argument(args.metadata, Path(args.workspace))
    previous_status = record["status"]
    record.update({
        "status": args.status,
        "draft_path": str(draft_path.relative_to(root)),
        "draft_sha256": file_sha256(draft_path),
        "assumptions_used": metadata.get("assumptions_used", []),
        "proved_scope": metadata.get("proved_scope", ""),
        "gaps": metadata.get("gaps", []),
    })
    record["status_history"].append({
        "from": previous_status,
        "to": args.status,
        "actor": args.actor,
        "reason": reason,
        "recorded_at": utc_now(),
    })
    index_path = root / "proofs" / "index.json"
    try:
        write_json(index_path, index)
        validate_proof_index(root)
    except Exception:
        write_json(index_path, original_index)
        if previous_draft is None:
            draft_path.unlink(missing_ok=True)
        else:
            draft_path.write_bytes(previous_draft)
        raise
    print(json.dumps({"written": str(draft_path), "status": args.status}, indent=2))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    result.add_argument("--actor", required=True)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("scaffold").set_defaults(function=command_scaffold)
    migrate = commands.add_parser("migrate-index")
    migrate.add_argument("--reason", required=True)
    migrate.set_defaults(function=command_migrate)
    commands.add_parser("frontier").set_defaults(function=command_frontier)
    blueprint = commands.add_parser("write-blueprint")
    blueprint.add_argument("--po", required=True)
    blueprint.add_argument("--input", required=True)
    blueprint.add_argument("--reason", required=True)
    blueprint.add_argument("--replace", action="store_true")
    blueprint.set_defaults(function=command_blueprint)
    check = commands.add_parser("add-check")
    check.add_argument("--po", required=True)
    check.add_argument("--input", required=True)
    check.set_defaults(function=command_check)
    draft = commands.add_parser("write-draft")
    draft.add_argument("--po", required=True)
    draft.add_argument("--input", required=True, help="Path relative to the run proofs directory")
    draft.add_argument("--metadata", required=True)
    draft.add_argument("--status", required=True)
    draft.add_argument("--reason", required=True)
    draft.add_argument("--replace", action="store_true")
    draft.set_defaults(function=command_draft)
    return result


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, PermissionError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
