#!/usr/bin/env python3
"""Start a bounded, evidence-preserving contribution strengthening pass."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable

from state_store import (
    load_manifest,
    path_lock,
    read_json,
    resolve_run,
    save_manifest,
    utc_now,
    verify_completed_artifacts,
    write_json,
)


MAX_STRENGTHENING_ROUNDS = 2
STRENGTHENABLE_GOALS = {"original_research", "workshop_or_short_paper"}
STRENGTHENING_LOCK = "artifact-operation"


def strengthening_round(manifest: Dict[str, Any], run_dir: Path | None = None) -> int:
    """Return the strengthening rounds consumed anywhere in this run lineage."""
    rounds = 0
    current = manifest
    visited = set()
    while True:
        state = current.get("strengthening_state", {})
        value = state.get("round", 0) if isinstance(state, dict) else 0
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            rounds = max(rounds, value)
        parent_id = current.get("parent_run_id")
        if run_dir is None or not isinstance(parent_id, str) or not parent_id or parent_id in visited:
            break
        visited.add(parent_id)
        parent_path = run_dir.parent / parent_id
        if not parent_path.is_dir():
            break
        current = load_manifest(parent_path)
    return rounds


def strengthening_available(
    manifest: Dict[str, Any], theory_bundle: Dict[str, Any], run_dir: Path | None = None
) -> bool:
    if manifest.get("current_stage") != "theory_bundle":
        return False
    route = theory_bundle.get("paper_route", {})
    goal = route.get("publication_goal")
    if goal not in STRENGTHENABLE_GOALS or route.get("publication_goal_satisfied") is not False:
        return False
    accepted = theory_bundle.get("accepted_statements", [])
    if not isinstance(accepted, list) or not accepted:
        return False
    return strengthening_round(manifest, run_dir) < MAX_STRENGTHENING_ROUNDS


def choose_resume_stage(theory_bundle: Dict[str, Any]) -> str:
    """Retry literature only when novelty is the sole failed acceptance-evidence gate."""
    route = theory_bundle.get("paper_route", {})
    gates = route.get("routing_gates", {})
    other_gates = [
        "acceptance_strength_sufficient",
        "application_evidence_ready",
        "parameter_sensitivity_ready",
        "baseline_evidence_ready",
        "theoretical_depth_ready",
        "no_major_or_fatal_significance_blocker",
    ]
    legacy_strength = gates.get("significance_sufficient_for_conference")
    if "acceptance_strength_sufficient" not in gates and legacy_strength is not None:
        gates = dict(gates)
        gates["acceptance_strength_sufficient"] = legacy_strength
    if gates.get("novelty_supported") is False and all(gates.get(key) is True for key in other_gates):
        return "novelty_audit"
    return "discovery"


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


def _reset_stage_artifacts(
    run_dir: Path,
    manifest: Dict[str, Any],
    stages: Iterable[str],
) -> None:
    for stage_name in stages:
        _remove_path(run_dir / manifest["stages"][stage_name]["artifact"])
    if "local_adversarial_audit" in stages:
        _remove_path(run_dir / "artifacts" / "audit_operation_ledger.json")
        for pattern in ("local_audit_evidence_*", "final_audit_evidence_*"):
            for path in (run_dir / "artifacts").glob(pattern):
                _remove_path(path)


def start_strengthening_unlocked(
    run_dir: Path,
    manifest: Dict[str, Any],
    stages: Dict[str, Dict[str, str]],
    theory_bundle: Dict[str, Any],
    *,
    reason: str,
) -> Dict[str, Any]:
    """Archive the assessed package and reopen only the stages needed to strengthen it."""
    reason = reason.strip()
    if not reason:
        raise ValueError("contribution strengthening reason cannot be empty")
    verify_completed_artifacts(run_dir, manifest)
    if not strengthening_available(manifest, theory_bundle, run_dir):
        raise ValueError("this theory route is not eligible for automatic contribution strengthening")

    next_round = strengthening_round(manifest, run_dir) + 1
    resume_stage = choose_resume_stage(theory_bundle)
    stage_names = list(stages)
    reset_names = stage_names[stage_names.index(resume_stage):]
    archive = run_dir / "strengthening" / f"round-{next_round:02d}"
    if archive.exists():
        raise ValueError(f"contribution strengthening archive already exists: {archive.name}")

    archive.mkdir(parents=True)
    write_json(archive / "run.before.json", manifest)
    _copy_if_present(run_dir / "artifacts", archive / "artifacts")
    _copy_if_present(run_dir / "proofs", archive / "proofs")
    _copy_if_present(run_dir / "literature", archive / "literature")

    route = theory_bundle["paper_route"]
    accepted_ids = [
        item.get("effective_statement", {}).get("id")
        for item in theory_bundle.get("accepted_statements", [])
        if isinstance(item, dict)
    ]
    record = {
        "round": next_round,
        "status": "in_progress",
        "reason": reason,
        "publication_goal": route.get("publication_goal"),
        "previous_submission_readiness": route.get("submission_readiness"),
        "resume_stage": resume_stage,
        "accepted_statement_ids": [item for item in accepted_ids if item],
        "routing_gates": route.get("routing_gates", {}),
        "remaining_blockers": route.get("review_blockers", []),
        "unmet_goal_reasons": route.get("unmet_publication_goal_reasons", []),
        "archive": str(archive.relative_to(run_dir)),
        "started_at": utc_now(),
    }

    _reset_stage_artifacts(run_dir, manifest, reset_names)
    if resume_stage == "discovery":
        _remove_path(run_dir / "proofs")
        (run_dir / "proofs").mkdir()

    for stage_name in reset_names:
        spec = manifest["stages"][stage_name]
        spec.clear()
        spec.update({
            "status": "pending",
            "actor": stages[stage_name]["actor"],
            "artifact": stages[stage_name]["artifact"],
        })
    manifest["stages"][resume_stage]["status"] = "in_progress"
    manifest["current_stage"] = resume_stage
    manifest["status"] = "active"
    manifest.pop("completed_at", None)
    manifest.pop("revision_state", None)

    previous = manifest.get("strengthening_state", {})
    history = list(previous.get("history", [])) if isinstance(previous, dict) else []
    history.append(record)
    manifest["strengthening_state"] = {
        "round": next_round,
        "maximum_rounds": MAX_STRENGTHENING_ROUNDS,
        "status": "in_progress",
        "publication_goal": record["publication_goal"],
        "previous_submission_readiness": record["previous_submission_readiness"],
        "resume_stage": resume_stage,
        "accepted_statement_ids": record["accepted_statement_ids"],
        "routing_gates": record["routing_gates"],
        "archive": record["archive"],
        "started_at": record["started_at"],
        "history": history,
    }
    save_manifest(run_dir, manifest)

    index_path = run_dir / "strengthening" / "index.json"
    index = read_json(index_path) if index_path.exists() else {
        "schema_version": 1,
        "artifact": "contribution_strengthening_history",
        "maximum_rounds": MAX_STRENGTHENING_ROUNDS,
        "rounds": [],
    }
    index["rounds"].append(record)
    write_json(index_path, index)
    return record


def command_status(args: argparse.Namespace) -> int:
    run_dir = resolve_run(Path(args.workspace), args.run)
    manifest = load_manifest(run_dir)
    bundle_path = run_dir / "artifacts" / "theory_bundle.json"
    bundle = read_json(bundle_path) if bundle_path.exists() else {}
    print(json.dumps({
        "run_id": manifest.get("run_id"),
        "current_stage": manifest.get("current_stage"),
        "eligible": strengthening_available(manifest, bundle, run_dir),
        "strengthening_state": manifest.get("strengthening_state"),
    }, indent=2))
    return 0


def command_start(args: argparse.Namespace) -> int:
    run_dir = resolve_run(Path(args.workspace), args.run)
    with path_lock(run_dir / STRENGTHENING_LOCK):
        manifest = load_manifest(run_dir)
        bundle = read_json(run_dir / "artifacts" / "theory_bundle.json")
        import workflow
        record = start_strengthening_unlocked(
            run_dir, manifest, workflow.STAGES, bundle, reason=args.reason,
        )
    print(json.dumps({
        "run_id": manifest["run_id"],
        "strengthening": record,
        "current_stage": manifest["current_stage"],
        "instruction": "Use $contribution-strengthening and continue this exact run.",
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
