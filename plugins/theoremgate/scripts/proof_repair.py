#!/usr/bin/env python3
"""Start a bounded, evidence-preserving proof correction inside one active run."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List

from state_store import (
    file_sha256,
    load_manifest,
    path_lock,
    read_json,
    resolve_run,
    save_manifest,
    utc_now,
    verify_completed_artifacts,
    write_json,
)


MAX_CORRECTION_ROUNDS = 3
RESET_FROM_STAGE = "discovery"
CORRECTION_LOCK = "artifact-operation"
MATHEMATICAL_FINDING_KINDS = {
    "proof_gap", "counterexample", "assumption_failure", "boundary_case",
    "definition_error", "dependency_error", "numerical_contradiction",
}


def _serious_repair_findings(run_dir: Path) -> List[Dict[str, Any]]:
    audit = read_json(run_dir / "artifacts" / "local_audit.json")
    governance = read_json(run_dir / "artifacts" / "governance_review.json")
    findings = {
        item.get("id"): item
        for item in audit.get("findings", [])
        if isinstance(item, dict)
    }
    result = []
    for decision in governance.get("decisions", []):
        if not isinstance(decision, dict) or decision.get("action") != "repair_requested":
            continue
        finding = findings.get(decision.get("finding_id"))
        if isinstance(finding, dict) and finding.get("severity") in {"major", "fatal"}:
            result.append(finding)
    return result


def _serious_governance_records(run_dir: Path) -> List[Dict[str, Any]]:
    audit = read_json(run_dir / "artifacts" / "local_audit.json")
    governance = read_json(run_dir / "artifacts" / "governance_review.json")
    findings = {
        item.get("id"): item
        for item in audit.get("findings", [])
        if isinstance(item, dict)
    }
    records = []
    for decision in governance.get("decisions", []):
        if not isinstance(decision, dict):
            continue
        finding = findings.get(decision.get("finding_id"))
        if not isinstance(finding, dict) or finding.get("severity") not in {"major", "fatal"}:
            continue
        records.append({
            "finding_id": finding.get("id"),
            "kind": finding.get("kind"),
            "action": decision.get("action"),
        })
    return records


def correction_round(manifest: Dict[str, Any]) -> int:
    state = manifest.get("correction_state", {})
    value = state.get("round", 0) if isinstance(state, dict) else 0
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def correction_available(run_dir: Path, manifest: Dict[str, Any]) -> bool:
    """Return true when at least one serious mathematical closure needs in-scope repair.

    Other serious findings may be deferred, excluded, invalidated, or cleared. Those
    dispositions must not suppress repair of an independent repair-requested closure.
    """
    if manifest.get("current_stage") != "governance_review":
        return False
    if correction_round(manifest) >= MAX_CORRECTION_ROUNDS:
        return False
    findings = _serious_repair_findings(run_dir)
    if not findings:
        return False
    serious_records = _serious_governance_records(run_dir)
    repair_records = [
        item for item in serious_records if item["action"] == "repair_requested"
    ]
    return bool(repair_records) and all(
        item["kind"] in MATHEMATICAL_FINDING_KINDS for item in repair_records
    ) and all(
        item["action"] in {
            "repair_requested", "deferred", "excluded", "invalidated", "cleared"
        }
        for item in serious_records
    )


def _copy_if_present(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _reset_artifact_paths(run_dir: Path, manifest: Dict[str, Any], stages: Iterable[str]) -> None:
    for stage_name in stages:
        relative = manifest["stages"][stage_name]["artifact"]
        _remove_path(run_dir / relative)
    _remove_path(run_dir / "artifacts" / "audit_operation_ledger.json")
    for path in (run_dir / "artifacts").glob("local_audit_evidence_*"):
        _remove_path(path)


def start_correction_unlocked(
    run_dir: Path,
    manifest: Dict[str, Any],
    stages: Dict[str, Dict[str, str]],
    *,
    reason: str,
) -> Dict[str, Any]:
    """Archive the failed pass and return the same run to discovery.

    The caller must hold the run's artifact-operation lock.
    """
    reason = reason.strip()
    if not reason:
        raise ValueError("proof correction reason cannot be empty")
    verify_completed_artifacts(run_dir, manifest)
    if not correction_available(run_dir, manifest):
        raise ValueError("this governance outcome is not eligible for same-run proof correction")

    names = list(stages)
    reset_index = names.index(RESET_FROM_STAGE)
    reset_stages = names[reset_index:]
    next_round = correction_round(manifest) + 1
    archive = run_dir / "corrections" / f"round-{next_round:02d}"
    if archive.exists():
        raise ValueError(f"proof correction archive already exists: {archive.name}")

    archive.mkdir(parents=True)
    write_json(archive / "run.before.json", manifest)
    _copy_if_present(run_dir / "artifacts", archive / "artifacts")
    _copy_if_present(run_dir / "proofs", archive / "proofs")

    findings = _serious_repair_findings(run_dir)
    finding_ids = [item["id"] for item in findings]
    nonrepair_dispositions = [
        {"finding_id": item["finding_id"], "action": item["action"]}
        for item in _serious_governance_records(run_dir)
        if item["action"] != "repair_requested"
    ]
    source_hashes = {
        "local_audit": file_sha256(run_dir / "artifacts" / "local_audit.json"),
        "governance_review": file_sha256(run_dir / "artifacts" / "governance_review.json"),
    }

    _reset_artifact_paths(run_dir, manifest, reset_stages)
    _remove_path(run_dir / "proofs")
    (run_dir / "proofs").mkdir()

    for stage_name in reset_stages:
        spec = manifest["stages"][stage_name]
        spec.clear()
        spec.update({
            "status": "pending",
            "actor": stages[stage_name]["actor"],
            "artifact": stages[stage_name]["artifact"],
        })
    manifest["stages"][RESET_FROM_STAGE]["status"] = "in_progress"
    manifest["current_stage"] = RESET_FROM_STAGE
    manifest["status"] = "active"
    manifest.pop("completed_at", None)
    manifest.pop("revision_state", None)

    old_state = manifest.get("correction_state", {})
    history = list(old_state.get("history", [])) if isinstance(old_state, dict) else []
    record = {
        "round": next_round,
        "status": "in_progress",
        "reason": reason,
        "finding_ids": finding_ids,
        "nonrepair_dispositions": nonrepair_dispositions,
        "archive": str(archive.relative_to(run_dir)),
        "source_hashes": source_hashes,
        "started_at": utc_now(),
        "resume_stage": RESET_FROM_STAGE,
    }
    history.append(record)
    manifest["correction_state"] = {
        "round": next_round,
        "maximum_rounds": MAX_CORRECTION_ROUNDS,
        "status": "in_progress",
        "finding_ids": finding_ids,
        "nonrepair_dispositions": nonrepair_dispositions,
        "archive": record["archive"],
        "started_at": record["started_at"],
        "history": history,
    }
    save_manifest(run_dir, manifest)

    index_path = run_dir / "corrections" / "index.json"
    index = read_json(index_path) if index_path.exists() else {
        "schema_version": 1,
        "artifact": "proof_correction_history",
        "maximum_rounds": MAX_CORRECTION_ROUNDS,
        "rounds": [],
    }
    index["rounds"].append(record)
    write_json(index_path, index)
    return record


def command_status(args: argparse.Namespace) -> int:
    run_dir = resolve_run(Path(args.workspace), args.run)
    manifest = load_manifest(run_dir)
    print(json.dumps({
        "run_id": manifest.get("run_id"),
        "current_stage": manifest.get("current_stage"),
        "eligible": correction_available(run_dir, manifest),
        "correction_state": manifest.get("correction_state"),
    }, indent=2))
    return 0


def command_start(args: argparse.Namespace) -> int:
    run_dir = resolve_run(Path(args.workspace), args.run)
    with path_lock(run_dir / CORRECTION_LOCK):
        manifest = load_manifest(run_dir)
        import workflow
        record = start_correction_unlocked(
            run_dir, manifest, workflow.STAGES, reason=args.reason,
        )
    print(json.dumps({
        "run_id": manifest["run_id"],
        "correction": record,
        "current_stage": manifest["current_stage"],
        "instruction": "Use $proof-repair and continue this same run from discovery.",
    }, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--workspace", default=".")
    root.add_argument("--run")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("status").set_defaults(handler=command_status)
    start = commands.add_parser("start")
    start.add_argument("--reason", required=True)
    start.set_defaults(handler=command_start)
    return root


def main() -> None:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (ValueError, PermissionError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
