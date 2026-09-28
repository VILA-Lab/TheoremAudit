#!/usr/bin/env python3
"""Validation and integrity helpers for run-scoped TheoremAudit proof records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from proof_dag import PROOF_STATUSES, ProofDAG, require_proof_id
from state_store import artifact_path, file_sha256, read_json


PROOF_INDEX_SCHEMA_VERSION = 2
GAP_SEVERITIES = {"minor", "major", "fatal"}
GAP_STATUSES = {"open", "resolved"}
BLUEPRINT_REQUIRED = PROOF_STATUSES - {"unstarted"}
DRAFT_REQUIRED = {"drafted", "partial", "conditional_draft", "accepted_by_arbiter"}
SCOPE_REQUIRED = DRAFT_REQUIRED
OPEN_GAP_REQUIRED = {
    "partial",
    "conditional_draft",
    "failed",
    "blocked",
    "blocked_by_dependency",
    "repair_requested",
    "rejected_by_arbiter",
}
GOVERNANCE_STATUSES = {"accepted_by_arbiter", "rejected_by_arbiter"}


def _require_list(value: Any, label: str) -> List[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _discovery_context(run_dir: Path) -> Dict[str, Any]:
    path = run_dir / "artifacts" / "discovery.json"
    if not path.is_file():
        return {"assumptions": set(), "obligations": {}}
    discovery = read_json(path)
    if not isinstance(discovery, dict):
        raise ValueError("discovery artifact must be an object")
    assumptions = {
        item.get("id") for item in discovery.get("assumptions", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    obligations = {
        item.get("id"): item for item in discovery.get("proof_obligations", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    return {"assumptions": assumptions, "obligations": obligations}


def _validate_bound_file(
    run_dir: Path,
    proof_id: str,
    relative_path: Any,
    expected_hash: Any,
    label: str,
    *,
    require_nonempty: bool = True,
) -> Path:
    relative = _require_text(relative_path, f"{proof_id}.{label}_path")
    path = artifact_path(run_dir, relative)
    if not path.is_file():
        raise ValueError(f"missing {label} for {proof_id}: {relative}")
    try:
        path.relative_to((run_dir / "proofs").resolve())
    except ValueError as exc:
        raise ValueError(f"{label} for {proof_id} must stay under proofs/") from exc
    if require_nonempty and path.stat().st_size == 0:
        raise ValueError(f"{label} for {proof_id} cannot be empty")
    actual_hash = file_sha256(path)
    if not isinstance(expected_hash, str) or actual_hash != expected_hash:
        raise ValueError(f"{label} hash mismatch for {proof_id}")
    return path


def _validate_gap(proof_id: str, gap: Any, seen: Set[str]) -> Dict[str, Any]:
    if not isinstance(gap, dict):
        raise ValueError(f"{proof_id}.gaps entries must be objects")
    gap_id = _require_text(gap.get("id"), f"{proof_id}.gap.id")
    if gap_id in seen:
        raise ValueError(f"duplicate gap ID for {proof_id}: {gap_id}")
    seen.add(gap_id)
    severity = gap.get("severity")
    if severity not in GAP_SEVERITIES:
        raise ValueError(f"invalid gap severity for {proof_id}/{gap_id}: {severity}")
    status = gap.get("status")
    if status not in GAP_STATUSES:
        raise ValueError(f"invalid gap status for {proof_id}/{gap_id}: {status}")
    _require_text(gap.get("description"), f"{proof_id}/{gap_id}.description")
    if status == "resolved":
        _require_text(gap.get("resolution"), f"{proof_id}/{gap_id}.resolution")
    elif gap.get("resolution") not in {None, ""}:
        raise ValueError(f"open gap {proof_id}/{gap_id} cannot claim a resolution")
    return gap


def _validate_history(proof_id: str, history: Any, status: str) -> List[Dict[str, Any]]:
    entries = _require_list(history, f"{proof_id}.status_history")
    if not entries:
        raise ValueError(f"{proof_id}.status_history cannot be empty")
    previous: Optional[str] = None
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{proof_id}.status_history[{position}] must be an object")
        next_status = entry.get("to")
        if next_status not in PROOF_STATUSES:
            raise ValueError(f"invalid history status for {proof_id}: {next_status}")
        if entry.get("from") != previous:
            raise ValueError(f"broken status history chain for {proof_id} at position {position}")
        _require_text(entry.get("actor"), f"{proof_id}.status_history[{position}].actor")
        _require_text(entry.get("reason"), f"{proof_id}.status_history[{position}].reason")
        _require_text(entry.get("recorded_at"), f"{proof_id}.status_history[{position}].recorded_at")
        previous = next_status
    if previous != status:
        raise ValueError(f"status history for {proof_id} ends at {previous}, not {status}")
    if status in GOVERNANCE_STATUSES and entries[-1]["actor"] != "governor":
        raise ValueError(f"{proof_id} status {status} requires a governor transition")
    return entries


def validate_blueprint(value: Any, proof_id: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("proof blueprint must be an object")
    declared = value.get("proof_id", proof_id)
    if declared != proof_id:
        raise ValueError(f"blueprint proof_id must be {proof_id}")
    _require_text(value.get("strategy"), f"{proof_id}.blueprint.strategy")
    for field in ("dependencies", "assumptions", "fragile_steps", "fallbacks"):
        _require_list(value.get(field, []), f"{proof_id}.blueprint.{field}")
    return value


def validate_status_transition(current: str, new: str, actor: str, reason: str) -> None:
    if current not in PROOF_STATUSES or new not in PROOF_STATUSES:
        raise ValueError(f"invalid proof status transition: {current} -> {new}")
    _require_text(reason, "status transition reason")
    if new in GOVERNANCE_STATUSES and actor != "governor":
        raise PermissionError(f"only governor may set proof status {new}")
    if current in GOVERNANCE_STATUSES and actor != "governor":
        raise PermissionError(f"only governor may change governed proof status {current}")
    if current in {"failed", "blocked", "blocked_by_dependency", "repair_requested"} and new not in {
        current, "planned", "analysis_in_progress", "partial", "conditional_draft", "drafted"
    }:
        raise ValueError(f"invalid repair transition: {current} -> {new}")


def validate_proof_index(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    index_path = artifact_path(run_dir, "proofs/index.json")
    index = read_json(index_path)
    if not isinstance(index, dict):
        raise ValueError("proof index must be an object")
    schema_version = index.get("schema_version")
    if schema_version not in {None, 1, PROOF_INDEX_SCHEMA_VERSION}:
        raise ValueError(f"unsupported proof index schema_version: {schema_version}")
    strict = schema_version == PROOF_INDEX_SCHEMA_VERSION
    records = _require_list(index.get("proofs"), "proofs")
    context = _discovery_context(run_dir)
    proof_map: Dict[str, Dict[str, Any]] = {}
    for position, value in enumerate(records):
        if not isinstance(value, dict):
            raise ValueError(f"proofs[{position}] must be an object")
        proof_id = require_proof_id(value.get("id"))
        if proof_id in proof_map:
            raise ValueError(f"duplicate proof obligation: {proof_id}")
        status = value.get("status")
        if status not in PROOF_STATUSES:
            raise ValueError(f"invalid proof status for {proof_id}: {status}")
        dependencies = _require_list(value.get("depends_on", []), f"{proof_id}.depends_on")
        for dependency in dependencies:
            require_proof_id(dependency)
        assumptions = _require_list(value.get("assumptions_used", []), f"{proof_id}.assumptions_used")
        if any(not isinstance(item, str) or not item for item in assumptions):
            raise ValueError(f"{proof_id}.assumptions_used must contain non-empty IDs")
        if len(assumptions) != len(set(assumptions)):
            raise ValueError(f"{proof_id}.assumptions_used contains duplicates")
        if context["assumptions"] and any(item not in context["assumptions"] for item in assumptions):
            raise ValueError(f"{proof_id} cites unknown assumptions")

        gaps = _require_list(value.get("gaps", []), f"{proof_id}.gaps")
        if strict:
            seen_gaps: Set[str] = set()
            validated_gaps = [_validate_gap(proof_id, gap, seen_gaps) for gap in gaps]
            open_gaps = [gap for gap in validated_gaps if gap["status"] == "open"]
            serious_open = [gap for gap in open_gaps if gap["severity"] in {"major", "fatal"}]
            if status in {"drafted", "accepted_by_arbiter"} and serious_open:
                raise ValueError(f"{proof_id} cannot be {status} with open major/fatal gaps")
            if status == "accepted_by_arbiter" and open_gaps:
                raise ValueError(f"{proof_id} cannot be accepted with any open gap")
            if status in OPEN_GAP_REQUIRED and not open_gaps:
                raise ValueError(f"{proof_id} status {status} requires an open structured gap")
            _validate_history(proof_id, value.get("status_history"), status)

            if status in BLUEPRINT_REQUIRED:
                blueprint = _validate_bound_file(
                    run_dir, proof_id, value.get("blueprint_path"), value.get("blueprint_sha256"), "blueprint"
                )
                validate_blueprint(read_json(blueprint), proof_id)
            if status in DRAFT_REQUIRED or value.get("draft_path") is not None:
                _validate_bound_file(
                    run_dir, proof_id, value.get("draft_path"), value.get("draft_sha256"), "draft"
                )
            if status in SCOPE_REQUIRED:
                _require_text(value.get("proved_scope"), f"{proof_id}.proved_scope")

            obligation = context["obligations"].get(proof_id, {})
            expected_assumptions = set(obligation.get("assumptions_expected", []))
            if status in {"drafted", "accepted_by_arbiter"} and not expected_assumptions <= set(assumptions):
                missing = sorted(expected_assumptions - set(assumptions))
                raise ValueError(f"{proof_id} omits expected assumptions: {missing}")
        else:
            # Legacy indexes remain readable but receive no retroactive integrity certification.
            value["_integrity_mode"] = "legacy_unverified"
            serious_gaps = [
                gap for gap in gaps
                if isinstance(gap, dict) and gap.get("severity") in {"major", "fatal"}
            ]
            if status in {"drafted", "accepted_by_arbiter"} and serious_gaps:
                raise ValueError(f"{proof_id} cannot be {status} with major/fatal gaps")
            if status in DRAFT_REQUIRED:
                draft_path = value.get("draft_path")
                if not isinstance(draft_path, str) or not draft_path:
                    raise ValueError(f"{proof_id} status {status} requires draft_path")
                draft = artifact_path(run_dir, draft_path)
                if not draft.is_file():
                    raise ValueError(f"missing proof draft for {proof_id}: {draft_path}")
        proof_map[proof_id] = value

    dag = ProofDAG(list(proof_map.values()))
    if strict:
        statuses = {proof_id: record["status"] for proof_id, record in proof_map.items()}
        for proof_id, record in proof_map.items():
            status = record["status"]
            allowed, reason, conditional = dag.can_attempt(proof_id, statuses)
            if status in {"drafted", "accepted_by_arbiter"} and (not allowed or conditional):
                raise ValueError(f"{proof_id} status {status} conflicts with dependencies: {reason}")
            if status == "conditional_draft" and (not allowed or not conditional):
                raise ValueError(f"{proof_id} conditional_draft lacks unresolved dependencies: {reason}")
            if status == "blocked_by_dependency" and allowed:
                raise ValueError(f"{proof_id} is blocked_by_dependency but dependencies permit drafting")
    return proof_map
