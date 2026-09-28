#!/usr/bin/env python3
"""Deterministic controller for the Codex-native TheoremAudit governed workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from proof_dag import ProofDAG
from proof_store import validate_proof_index
from proof_repair import correction_available, start_correction_unlocked
from contribution_strengthening import (
    strengthening_available,
    strengthening_round,
    start_strengthening_unlocked,
)
from paper_router import (
    PUBLICATION_GOALS,
    derive_route,
    validate_contribution,
    validate_novelty_audit,
    validate_significance_audit,
)
from state_store import (
    artifact_path,
    create_run,
    file_sha256,
    load_manifest,
    path_lock,
    read_json,
    resolve_run,
    save_manifest,
    utc_now,
    validate_run_id,
    verify_completed_artifacts,
    write_json,
)


STAGES: Dict[str, Dict[str, str]] = {
    "direction_generation": {
        "actor": "direction_generator",
        "artifact": "artifacts/directions.json",
    },
    "direction_selection": {
        "actor": "direction_selector",
        "artifact": "artifacts/selected_direction.json",
    },
    "discovery": {
        "actor": "discoverer",
        "artifact": "artifacts/discovery.json",
    },
    "exploration": {
        "actor": "explorer",
        "artifact": "artifacts/exploration.json",
    },
    "proof_development": {
        "actor": "proof_team",
        "artifact": "proofs/index.json",
    },
    "local_adversarial_audit": {
        "actor": "auditor",
        "artifact": "artifacts/local_audit.json",
    },
    "governance_review": {
        "actor": "governor",
        "artifact": "artifacts/governance_review.json",
    },
    "theorem_synthesis": {
        "actor": "synthesizer",
        "artifact": "artifacts/synthesized_theorems.json",
    },
    "final_adversarial_audit": {
        "actor": "auditor",
        "artifact": "artifacts/final_audit.json",
    },
    "arbiter": {
        "actor": "governor",
        "artifact": "artifacts/arbiter.json",
    },
    "novelty_audit": {
        "actor": "novelty_auditor",
        "artifact": "artifacts/novelty_audit.json",
    },
    "significance_audit": {
        "actor": "significance_reviewer",
        "artifact": "artifacts/significance_audit.json",
    },
    "contribution_assessment": {
        "actor": "contribution_developer",
        "artifact": "artifacts/contribution_assessment.json",
    },
    "theory_bundle": {
        "actor": "controller",
        "artifact": "artifacts/theory_bundle.json",
    },
}

SEVERITIES = {"minor", "major", "fatal"}
AUDIT_SCHEMA_VERSION = 4
LEGACY_APPEND_ONLY_AUDIT_SCHEMA_VERSION = 3
GOVERNANCE_SCHEMA_VERSION = 3
ARBITER_SCHEMA_VERSION = 4
FINDING_KINDS = {
    "proof_gap", "counterexample", "assumption_failure", "boundary_case",
    "definition_error", "dependency_error", "citation_mismatch", "novelty_issue",
    "scope_overclaim", "numerical_contradiction", "reproducibility_issue", "other",
}
MATHEMATICAL_FATAL_KINDS = {
    "proof_gap", "counterexample", "assumption_failure", "boundary_case",
    "definition_error", "dependency_error", "numerical_contradiction",
}
PROOF_READY = {"drafted", "accepted_by_arbiter"}
ACCEPTED_DECISIONS = {"theorem_ready", "proposition_ready"}
DECISION_STATUSES = ACCEPTED_DECISIONS | {
    "repair_requested",
    "conjecture_only",
    "rejected",
    "invalid",
}


def require_dict(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> List[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def require_fields(value: Dict[str, Any], fields: Iterable[str], label: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise ValueError(f"{label} is missing required fields: {missing}")


def canonical_sha256(value: Dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def verify_record_provenance(value: Dict[str, Any], label: str) -> None:
    provenance = require_dict(value.get("_provenance"), f"{label}._provenance")
    for field in ("actor", "operation", "recorded_at", "record_sha256"):
        require_text(provenance.get(field), f"{label}._provenance.{field}")
    payload = {
        key: item for key, item in value.items()
        if key not in {"_provenance", "_integrity_mode"}
    }
    if canonical_sha256(payload) != provenance["record_sha256"]:
        raise ValueError(f"{label} provenance hash does not match its immutable record")


def verify_workspace_evidence(run_dir: Path, value: Any, label: str) -> None:
    evidence = require_dict(value, label)
    relative = require_text(evidence.get("path"), f"{label}.path")
    expected = require_text(evidence.get("sha256"), f"{label}.sha256")
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise ValueError(f"{label}.sha256 must be a lowercase SHA-256 digest")
    workspace = run_dir.parents[2].resolve()
    unresolved = Path(relative)
    if unresolved.is_absolute() or ".." in unresolved.parts:
        raise ValueError(f"{label}.path must be workspace-relative and contained")
    path = (workspace / unresolved).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ValueError(f"{label}.path escapes the workspace") from exc
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label}.path must identify a regular file")
    if file_sha256(path) != expected:
        raise ValueError(f"{label} hash no longer matches the persisted evidence")


def ancestor_run(run_dir: Path, origin_run_id: Any) -> Path:
    origin_id = validate_run_id(origin_run_id)
    parent = load_manifest(run_dir).get("parent_run_id")
    visited = set()
    while parent:
        parent = validate_run_id(parent)
        if parent in visited:
            raise ValueError("run ancestry contains a cycle")
        visited.add(parent)
        candidate = (run_dir.parent / parent).resolve()
        try:
            candidate.relative_to(run_dir.parent.resolve())
        except ValueError as exc:
            raise ValueError("ancestor run escapes the run store") from exc
        manifest = load_manifest(candidate)
        verify_completed_artifacts(candidate, manifest)
        if parent == origin_id:
            return candidate
        parent = manifest.get("parent_run_id")
    raise ValueError(f"origin run is not an ancestor: {origin_id}")


def raw_origin_finding(origin: Path, finding_id: Any) -> Dict[str, Any]:
    target = require_text(finding_id, "origin_finding_id")
    manifest = load_manifest(origin)
    matches = []
    for stage in ("local_adversarial_audit", "final_adversarial_audit"):
        state = manifest.get("stages", {}).get(stage, {})
        if state.get("status") != "completed":
            continue
        artifact = require_dict(read_json(artifact_path(origin, state["artifact"])), stage)
        matches.extend({
            "finding": item, "audit_stage": stage, "audit_sha256": state["evidence_sha256"]
        } for item in artifact.get("findings", [])
          if isinstance(item, dict) and item.get("id") == target)
    if len(matches) != 1:
        raise ValueError("origin finding does not uniquely identify completed ancestor evidence")
    return matches[0]


def unique_records(
    values: Any,
    label: str,
    fields: Iterable[str] = ("id",),
) -> Dict[str, Dict[str, Any]]:
    records = require_list(values, label)
    result: Dict[str, Dict[str, Any]] = {}
    for position, item in enumerate(records):
        item = require_dict(item, f"{label}[{position}]")
        require_fields(item, fields, f"{label}[{position}]")
        record_id = require_text(item["id"], f"{label}[{position}].id")
        if record_id in result:
            raise ValueError(f"duplicate {label} ID: {record_id}")
        result[record_id] = item
    return result


def completed_artifact(run_dir: Path, stage: str) -> Dict[str, Any]:
    return require_dict(read_json(artifact_path(run_dir, STAGES[stage]["artifact"])), stage)


def discovery_maps(run_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    discovery = completed_artifact(run_dir, "discovery")
    return {
        "assumptions": unique_records(discovery.get("assumptions"), "assumptions"),
        "targets": unique_records(discovery.get("theorem_targets"), "theorem_targets"),
        "obligations": unique_records(
            discovery.get("proof_obligations"), "proof_obligations"
        ),
    }


def validate_directions(run_dir: Path) -> None:
    artifact = completed_artifact(run_dir, "direction_generation")
    candidates = unique_records(artifact.get("candidates"), "candidates")
    if len(candidates) < 1:
        raise ValueError("direction generation requires at least one candidate")
    for candidate_id, candidate in candidates.items():
        require_text(candidate.get("title"), f"{candidate_id}.title")
        require_text(candidate.get("question"), f"{candidate_id}.question")


def validate_selection(run_dir: Path) -> None:
    artifact = completed_artifact(run_dir, "direction_selection")
    candidates = unique_records(
        completed_artifact(run_dir, "direction_generation").get("candidates"),
        "candidates",
    )
    selected_id = require_text(artifact.get("selected_id"), "selected_id")
    if selected_id not in candidates:
        raise ValueError(f"selected direction does not exist: {selected_id}")
    require_text(artifact.get("rationale"), "selection rationale")
    require_list(artifact.get("novelty_evidence", []), "novelty_evidence")


def validate_discovery(run_dir: Path) -> None:
    artifact = completed_artifact(run_dir, "discovery")
    require_dict(artifact.get("setting"), "setting")
    contract = load_manifest(run_dir).get("execution_contract", {})
    publication_strength_required = (
        contract.get("requested_mode") == "full"
        and contract.get("publication_goal") in {
            "original_research", "workshop_or_short_paper"
        }
    )
    maps = discovery_maps(run_dir)
    if not maps["assumptions"]:
        raise ValueError("discovery requires at least one assumption")
    if not maps["targets"]:
        raise ValueError("discovery requires at least one theorem target")
    if not maps["obligations"]:
        raise ValueError("discovery requires at least one proof obligation")
    primary = require_text(artifact.get("primary_target_id"), "primary_target_id")
    if primary not in maps["targets"]:
        raise ValueError(f"primary target does not exist: {primary}")
    for assumption_id, assumption in maps["assumptions"].items():
        require_text(assumption.get("statement"), f"{assumption_id}.statement")
    strong_result_types = {
        "upper-bound", "lower-bound", "tight-bound", "separation", "equivalence",
        "impossibility", "existence", "necessity", "stability", "adaptation",
        "characterization", "construction", "exact-formula",
    }
    for target_id, target in maps["targets"].items():
        require_text(target.get("statement"), f"{target_id}.statement")
        if publication_strength_required:
            result_type = require_text(target.get("result_type"), f"{target_id}.result_type")
            if result_type not in strong_result_types:
                raise ValueError(f"invalid publication theorem result type: {result_type}")
    supported_targets = set()
    for proof_id, obligation in maps["obligations"].items():
        require_text(obligation.get("description"), f"{proof_id}.description")
        supports = obligation.get("supports")
        support_ids = supports if isinstance(supports, list) else [supports]
        if not support_ids or any(item not in maps["targets"] for item in support_ids):
            raise ValueError(f"{proof_id} supports unknown theorem targets: {support_ids}")
        supported_targets.update(support_ids)
        dependencies = require_list(obligation.get("depends_on", []), f"{proof_id}.depends_on")
        obligation["depends_on"] = dependencies
    ProofDAG(list(maps["obligations"].values()))
    if publication_strength_required:
        strength = require_dict(artifact.get("publication_strength"), "publication_strength")
        for field in (
            "technical_obstacle", "novelty_delta", "closest_work_boundary",
            "nonvacuity_check", "complete_proof_route",
        ):
            require_text(strength.get(field), f"publication_strength.{field}")
        companion_value = strength.get("companion_result_id")
        companion = companion_value.strip() if isinstance(companion_value, str) else ""
        exceptional_value = strength.get("exceptional_depth_justification")
        exceptional = exceptional_value.strip() if isinstance(exceptional_value, str) else ""
        if bool(companion) == bool(exceptional):
            raise ValueError(
                "publication_strength requires exactly one of companion_result_id or "
                "exceptional_depth_justification"
            )
        if primary not in supported_targets:
            raise ValueError("the publication primary target requires a proof obligation")
        if companion:
            if companion == primary or companion not in maps["targets"]:
                raise ValueError("publication companion result must be a distinct theorem target")
            if companion not in supported_targets:
                raise ValueError("publication companion result requires a proof obligation")


def validate_exploration(run_dir: Path) -> None:
    artifact = completed_artifact(run_dir, "exploration")
    recommendation = artifact.get("recommendation")
    if recommendation not in {"continue", "narrow", "reshape", "blocked"}:
        raise ValueError(f"invalid exploration recommendation: {recommendation}")
    require_list(artifact.get("probes", []), "probes")
    require_text(artifact.get("rationale"), "exploration rationale")


def validate_proofs(run_dir: Path) -> None:
    proof_map = validate_proof_index(run_dir)
    obligations = discovery_maps(run_dir)["obligations"]
    expected = set(obligations)
    actual = set(proof_map)
    if actual != expected:
        raise ValueError(
            f"proof index must cover every discovery obligation; missing={sorted(expected-actual)}, "
            f"unknown={sorted(actual-expected)}"
        )
    # A valid working index is not yet a completed proof-development attempt.
    unfinished = [
        f"{proof_id} ({record['status']})"
        for proof_id, record in sorted(proof_map.items())
        if record["status"] in {"unstarted", "planned", "analysis_in_progress"}
    ]
    if unfinished:
        raise ValueError(
            "proof_development cannot complete with unfinished obligations: "
            + ", ".join(unfinished)
            + "; register the proof drafts or document partial, failed, or blocked "
            "attempts with their required gap evidence before requesting review"
        )
    for proof_id, record in proof_map.items():
        expected_dependencies = set(obligations[proof_id].get("depends_on", []))
        actual_dependencies = set(record.get("depends_on", []))
        if actual_dependencies != expected_dependencies:
            raise ValueError(
                f"{proof_id} dependencies differ from discovery; "
                f"expected={sorted(expected_dependencies)}, actual={sorted(actual_dependencies)}"
            )


def audit_findings(run_dir: Path, stage: str) -> List[Dict[str, Any]]:
    artifact = completed_artifact(run_dir, stage)
    schema = artifact.get("schema_version")
    strict_v2 = schema == 2
    append_only = schema in {LEGACY_APPEND_ONLY_AUDIT_SCHEMA_VERSION, AUDIT_SCHEMA_VERSION}
    externally_anchored = schema == AUDIT_SCHEMA_VERSION
    strict = strict_v2 or append_only
    if schema not in {
        None, 1, 2, LEGACY_APPEND_ONLY_AUDIT_SCHEMA_VERSION, AUDIT_SCHEMA_VERSION,
    }:
        raise ValueError(f"unsupported {stage} schema_version: {schema}")
    if strict:
        if artifact.get("artifact") != "adversarial_audit" or artifact.get("stage") != stage:
            raise ValueError(f"invalid strict {stage} artifact identity")
    findings = require_list(artifact.get("findings"), "findings")
    if append_only:
        summary = require_dict(artifact.get("attack_summary"), "attack_summary")
        required_methods = {
            "assumption_stress", "boundary_case", "dependency_check",
            "counterexample_search", "scope_alignment",
        }
        methods = set(require_list(summary.get("attack_methods"), "attack_summary.attack_methods"))
        if not required_methods <= methods:
            raise ValueError(
                "schema-v3 audit must record assumption, boundary, dependency, "
                "counterexample, and scope attacks"
            )
        targets = set(require_list(summary.get("targets_reviewed"), "attack_summary.targets_reviewed"))
        if stage == "local_adversarial_audit":
            required_targets = set(validate_proof_index(run_dir))
        else:
            required_targets = set(synthesized_statements(run_dir))
            if "claim_proof_alignment" not in methods:
                raise ValueError("final audit must record a claim-proof-alignment attack")
        if not required_targets <= targets:
            raise ValueError(
                f"attack summary does not cover required targets: {sorted(required_targets - targets)}"
            )
        evidence_files = require_list(summary.get("evidence_files"), "attack_summary.evidence_files")
        if not evidence_files:
            raise ValueError("attack summary requires persisted evidence")
        for position, evidence in enumerate(evidence_files):
            verify_workspace_evidence(run_dir, evidence, f"attack_summary.evidence_files[{position}]")
        conclusion = summary.get("conclusion")
        expected_conclusion = "findings_recorded" if findings else "no_findings_after_attack"
        if conclusion != expected_conclusion:
            raise ValueError("attack-summary conclusion does not match the recorded findings")
        require_text(summary.get("rationale"), "attack_summary.rationale")
        require_text(summary.get("actor"), "attack_summary.actor")
        require_text(summary.get("recorded_at"), "attack_summary.recorded_at")
        stored_summary_hash = require_text(summary.get("summary_sha256"), "attack_summary.summary_sha256")
        summary_payload = {key: value for key, value in summary.items() if key != "summary_sha256"}
        if canonical_sha256(summary_payload) != stored_summary_hash:
            raise ValueError("attack summary hash is invalid")
        if externally_anchored:
            ledger_path = run_dir / "artifacts" / "audit_operation_ledger.json"
            if not ledger_path.is_file():
                raise ValueError("schema-v4 attack summary is missing its external operation ledger")
            ledger = require_dict(read_json(ledger_path), "audit operation ledger")
            if (
                ledger.get("schema_version") != 1
                or ledger.get("artifact") != "audit_operation_ledger"
            ):
                raise ValueError("invalid audit operation ledger identity")
            records = [
                item for item in require_list(ledger.get("records"), "audit operation records")
                if isinstance(item, dict) and item.get("stage") == stage
            ]
            if not records:
                raise ValueError("schema-v4 attack summary has no external operation record")
            previous_summary = None
            for position, record in enumerate(records):
                label = f"audit operation records[{position}]"
                require_fields(
                    record,
                    (
                        "id", "stage", "operation", "previous_summary_sha256",
                        "summary_sha256", "reason", "_provenance",
                    ),
                    label,
                )
                verify_record_provenance(record, label)
                if record["stage"] != stage:
                    raise ValueError(f"{label} targets the wrong audit stage")
                operation = record["operation"]
                if operation not in {"record", "revise"}:
                    raise ValueError(f"{label} has an unsupported operation")
                if position == 0 and operation != "record":
                    raise ValueError("the first attack-summary operation must record the summary")
                if position > 0 and operation != "revise":
                    raise ValueError("later attack-summary operations must be revisions")
                if record["previous_summary_sha256"] != previous_summary:
                    raise ValueError("attack-summary operation chain is broken")
                require_text(record["summary_sha256"], f"{label}.summary_sha256")
                require_text(record["reason"], f"{label}.reason")
                provenance = require_dict(record["_provenance"], f"{label}._provenance")
                if provenance.get("actor") != STAGES[stage]["actor"]:
                    raise ValueError("attack-summary operation was not recorded by the assigned auditor")
                previous_summary = record["summary_sha256"]
            if previous_summary != stored_summary_hash:
                raise ValueError(
                    "attack summary differs from the latest externally recorded operation; "
                    "use revise-attack-summary instead of editing JSON"
                )
    seen: Set[str] = set()
    result: List[Dict[str, Any]] = []
    maps = discovery_maps(run_dir)
    valid_targets = {"RUN"} | set(maps["assumptions"]) | set(maps["targets"]) | set(maps["obligations"])
    discovery = completed_artifact(run_dir, "discovery")
    for item in discovery.get("definitions", []):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            valid_targets.add(item["id"])
    exploration = completed_artifact(run_dir, "exploration")
    for item in exploration.get("probes", []):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            valid_targets.add(item["id"])
    if stage == "final_adversarial_audit":
        valid_targets |= set(synthesized_statements(run_dir))
    for position, raw in enumerate(findings):
        finding = require_dict(raw, f"findings[{position}]")
        require_fields(
            finding,
            ("id", "target_id", "kind", "severity", "description", "resolved"),
            f"findings[{position}]",
        )
        finding_id = require_text(finding["id"], f"findings[{position}].id")
        if finding_id in seen:
            raise ValueError(f"duplicate finding: {finding_id}")
        seen.add(finding_id)
        if finding["target_id"] not in valid_targets:
            raise ValueError(f"finding targets unknown artifact: {finding['target_id']}")
        if finding["severity"] not in SEVERITIES:
            raise ValueError(f"invalid finding severity: {finding['severity']}")
        require_text(finding["kind"], f"{finding_id}.kind")
        require_text(finding["description"], f"{finding_id}.description")
        if not isinstance(finding["resolved"], bool):
            raise ValueError(f"{finding_id}.resolved must be boolean")
        if finding["resolved"]:
            require_text(finding.get("resolution"), f"{finding_id}.resolution")
        finding = dict(finding)
        finding["_integrity_mode"] = (
            "append_only_v3" if append_only else "strict_v2" if strict_v2 else "legacy_unverified"
        )
        if strict:
            expected_prefix = "LOCAL-" if stage == "local_adversarial_audit" else "FINAL-"
            if not finding_id.startswith(expected_prefix):
                raise ValueError(f"{finding_id} must start with {expected_prefix}")
            if finding["kind"] not in FINDING_KINDS:
                raise ValueError(f"unsupported finding kind: {finding['kind']}")
            if finding["kind"] == "other":
                require_text(finding.get("subtype"), f"{finding_id}.subtype")
            fields = ["attack_method", "evidence", "source", "resolution_condition",
                      "scope_affected", "_provenance"]
            if strict_v2:
                fields.append("amendment_history")
            require_fields(finding, fields, finding_id)
            require_text(finding["attack_method"], f"{finding_id}.attack_method")
            require_text(finding["resolution_condition"], f"{finding_id}.resolution_condition")
            evidence = require_dict(finding["evidence"], f"{finding_id}.evidence")
            require_text(evidence.get("summary"), f"{finding_id}.evidence.summary")
            source = require_dict(finding["source"], f"{finding_id}.source")
            for field in ("path", "location", "sha256"):
                require_text(source.get(field), f"{finding_id}.source.{field}")
            require_list(finding["scope_affected"], f"{finding_id}.scope_affected")
            if append_only:
                unknown_scope = [item for item in finding["scope_affected"] if item not in valid_targets]
                if unknown_scope:
                    raise ValueError(f"{finding_id} has unknown affected scope IDs: {unknown_scope}")
            provenance = require_dict(finding["_provenance"], f"{finding_id}._provenance")
            for field in ("actor", "recorded_at", "record_sha256"):
                require_text(provenance.get(field), f"{finding_id}._provenance.{field}")
            if finding["resolved"]:
                resolution_evidence = require_dict(
                    finding.get("resolution_evidence"), f"{finding_id}.resolution_evidence"
                )
                require_text(
                    resolution_evidence.get("verification"),
                    f"{finding_id}.resolution_evidence.verification",
                )
            if append_only:
                if finding["resolved"]:
                    raise ValueError(f"{finding_id} base record is immutable and must start unresolved")
                verify_record_provenance(finding, finding_id)
                if finding["_provenance"]["actor"] != STAGES[stage]["actor"]:
                    raise ValueError(f"{finding_id} was not recorded by the assigned auditor")
                verify_workspace_evidence(run_dir, finding["source"], f"{finding_id}.source")
                if "path" in evidence:
                    verify_workspace_evidence(run_dir, evidence, f"{finding_id}.evidence")
        result.append(finding)

    if append_only:
        by_id = {item["id"]: item for item in result}
        events = require_list(artifact.get("events"), "events")
        previous = None
        seen_events = set()
        for position, raw in enumerate(events):
            event = require_dict(raw, f"events[{position}]")
            require_fields(
                event,
                ("id", "event_type", "actor", "recorded_at", "previous_event_sha256", "event_sha256"),
                f"events[{position}]",
            )
            event_id = require_text(event["id"], f"events[{position}].id")
            if event_id in seen_events:
                raise ValueError(f"duplicate audit event: {event_id}")
            seen_events.add(event_id)
            if event["previous_event_sha256"] != previous:
                raise ValueError(f"audit event chain is broken at {event_id}")
            stored_hash = require_text(event["event_sha256"], f"{event_id}.event_sha256")
            payload = {key: value for key, value in event.items() if key != "event_sha256"}
            if canonical_sha256(payload) != stored_hash:
                raise ValueError(f"audit event hash is invalid: {event_id}")
            require_text(event["actor"], f"{event_id}.actor")
            require_text(event["recorded_at"], f"{event_id}.recorded_at")
            if event["actor"] != STAGES[stage]["actor"]:
                raise ValueError(f"{event_id} was not recorded by the assigned auditor")
            previous = stored_hash
            event_type = event["event_type"]
            if event_type in {"amendment", "resolution_verification"}:
                expected_prefix = "AMEND-" if event_type == "amendment" else "VERIFY-"
                if not event_id.startswith(expected_prefix):
                    raise ValueError(f"{event_id} does not match event type {event_type}")
                finding_id = event.get("finding_id")
                if finding_id not in by_id:
                    raise ValueError(f"audit event targets unknown current finding: {finding_id}")
                finding = by_id[finding_id]
                if finding["resolved"]:
                    raise ValueError(f"event follows resolution of {finding_id}")
                if event_type == "amendment":
                    require_text(event.get("reason"), f"{event_id}.reason")
                    changes = require_dict(event.get("changes"), f"{event_id}.changes")
                    if not changes or any(
                        field not in {"severity", "description", "resolution_condition"}
                        for field in changes
                    ):
                        raise ValueError(f"{event_id} contains unsupported amendment fields")
                    history_changes = {}
                    for field, raw_change in changes.items():
                        change = require_dict(raw_change, f"{event_id}.changes.{field}")
                        if change.get("from") != finding.get(field):
                            raise ValueError(f"{event_id} amendment base does not match {field}")
                        updated = require_text(change.get("to"), f"{event_id}.changes.{field}.to")
                        if field == "severity" and updated not in SEVERITIES:
                            raise ValueError(f"{event_id} has invalid amended severity")
                        history_changes[field] = {"from": finding.get(field), "to": updated}
                        finding[field] = updated
                    finding.setdefault("amendment_history", []).append({
                        "id": event_id, "actor": event["actor"], "recorded_at": event["recorded_at"],
                        "reason": event["reason"], "changes": history_changes,
                    })
                else:
                    if event.get("outcome") != "resolved":
                        raise ValueError(f"{event_id} has invalid resolution outcome")
                    if event.get("resolution_type") not in {"false_positive", "preexisting_evidence"}:
                        raise ValueError(f"{event_id} has invalid resolution type")
                    require_text(event.get("resolution"), f"{event_id}.resolution")
                    require_text(event.get("verification"), f"{event_id}.verification")
                    if event.get("verification_mode") not in {
                        "independent_subagent", "fresh_role_review", "external_check"
                    }:
                        raise ValueError(f"{event_id} has invalid verification mode")
                    verify_workspace_evidence(run_dir, event.get("evidence"), f"{event_id}.evidence")
                    finding["resolved"] = True
                    finding["resolution"] = event["resolution"]
                    finding["resolution_evidence"] = {
                        "verification": event["verification"], "event_id": event_id,
                        "evidence": event["evidence"],
                    }
            elif event_type == "cross_run_repair_verification":
                if not event_id.startswith("REPAIR-"):
                    raise ValueError(f"{event_id} does not match cross-run repair verification")
                for field in (
                    "origin_run_id", "origin_finding_id", "origin_target_id", "origin_audit_stage",
                    "origin_audit_sha256", "origin_finding_sha256", "repair_run_id",
                    "outcome", "verification", "verification_mode", "repaired_artifact",
                ):
                    if field not in event:
                        raise ValueError(f"{event_id} is missing {field}")
                if event["repair_run_id"] != load_manifest(run_dir)["run_id"]:
                    raise ValueError(f"{event_id} repair_run_id does not match the current run")
                if event["outcome"] not in {"resolved", "unresolved"}:
                    raise ValueError(f"{event_id} has invalid repair outcome")
                require_text(event["verification"], f"{event_id}.verification")
                if event["verification_mode"] not in {
                    "independent_subagent", "fresh_role_review", "external_check"
                }:
                    raise ValueError(f"{event_id} has invalid verification mode")
                verify_workspace_evidence(
                    run_dir, event["repaired_artifact"], f"{event_id}.repaired_artifact"
                )
                repaired_path = (run_dir.parents[2] / event["repaired_artifact"]["path"]).resolve()
                try:
                    repaired_path.relative_to(run_dir.resolve())
                except ValueError as exc:
                    raise ValueError(f"{event_id} repaired artifact is outside the child run") from exc
                origin = ancestor_run(run_dir, event["origin_run_id"])
                origin_record = raw_origin_finding(origin, event["origin_finding_id"])
                original = origin_record["finding"]
                if original.get("target_id") != event["origin_target_id"]:
                    raise ValueError(f"{event_id} origin target does not match ancestor evidence")
                if (
                    origin_record["audit_stage"] != event["origin_audit_stage"]
                    or origin_record["audit_sha256"] != event["origin_audit_sha256"]
                    or original.get("_provenance", {}).get("record_sha256")
                    != event["origin_finding_sha256"]
                ):
                    raise ValueError(f"{event_id} origin hashes do not match ancestor evidence")
                imported_id = f"LOCAL-{event['origin_finding_id']}"
                if event["outcome"] == "resolved" and imported_id in by_id:
                    imported = by_id[imported_id]
                    if imported["resolved"]:
                        raise ValueError(f"{event_id} follows resolution of {imported_id}")
                    imported["resolved"] = True
                    imported["resolution"] = (
                        "The hash-bound ancestor finding was resolved in this linked repair."
                    )
                    imported["resolution_evidence"] = {
                        "verification": event["verification"],
                        "event_id": event_id,
                        "evidence": event["repaired_artifact"],
                    }
            else:
                raise ValueError(f"unsupported audit event type: {event_type}")
        if externally_anchored and stage == "local_adversarial_audit":
            manifest = load_manifest(run_dir)
            contract = manifest.get("execution_contract", {})
            authorization = contract.get("repair_authorization")
            if (
                contract.get("intent") == "repair"
                and isinstance(authorization, dict)
                and authorization.get("action") == "repair_mathematics"
            ):
                parent_id = require_text(manifest.get("parent_run_id"), "repair parent_run_id")
                parent = (run_dir.parent / validate_run_id(parent_id)).resolve()
                try:
                    parent.relative_to(run_dir.parent.resolve())
                except ValueError as exc:
                    raise ValueError("repair parent escapes the run registry") from exc
                parent_manifest = load_manifest(parent)
                verify_completed_artifacts(parent, parent_manifest)
                governance_state = parent_manifest.get("stages", {}).get("governance_review", {})
                if governance_state.get("status") != "completed":
                    raise ValueError("repair parent has no completed governance decision")
                governance = read_json(
                    artifact_path(parent, governance_state["artifact"])
                )
                expected_repairs = {
                    item.get("finding_id") for item in governance.get("decisions", [])
                    if isinstance(item, dict) and item.get("action") == "repair_requested"
                }
                arbiter_state = parent_manifest.get("stages", {}).get("arbiter", {})
                if arbiter_state.get("status") == "completed":
                    arbiter = read_json(artifact_path(parent, arbiter_state["artifact"]))
                    expected_repairs.update(
                        finding_id
                        for item in arbiter.get("decisions", [])
                        if isinstance(item, dict) and item.get("status") == "repair_requested"
                        for finding_id in item.get("findings_addressed", [])
                        if isinstance(finding_id, str) and finding_id
                    )
                requested_target = authorization.get("target")
                if isinstance(requested_target, str) and requested_target.startswith(("LOCAL-", "FINAL-")):
                    expected_repairs &= {requested_target}
                if not expected_repairs:
                    raise ValueError("repair authorization does not identify a governed repair finding")
                verified = {
                    event.get("origin_finding_id") for event in events
                    if event.get("event_type") == "cross_run_repair_verification"
                    and event.get("origin_run_id") == parent_id
                    and event.get("outcome") == "resolved"
                }
                missing_repairs = expected_repairs - verified
                if missing_repairs:
                    raise ValueError(
                        "repair child is missing hash-bound ancestor verification for: "
                        f"{sorted(missing_repairs)}"
                    )
    return result


def validate_governance_review(run_dir: Path) -> None:
    artifact = completed_artifact(run_dir, "governance_review")
    schema = artifact.get("schema_version")
    strict = schema in {2, GOVERNANCE_SCHEMA_VERSION}
    append_only = schema == GOVERNANCE_SCHEMA_VERSION
    if schema not in {None, 1, 2, GOVERNANCE_SCHEMA_VERSION}:
        raise ValueError(f"unsupported governance schema_version: {schema}")
    if strict and (
        artifact.get("artifact") != "governance_review"
        or artifact.get("stage") != "governance_review"
    ):
        raise ValueError("invalid strict governance artifact identity")
    decisions = require_list(artifact.get("decisions"), "decisions")
    findings = {item["id"]: item for item in audit_findings(run_dir, "local_adversarial_audit")}
    seen = set()
    for position, raw in enumerate(decisions):
        decision = require_dict(raw, f"decisions[{position}]")
        require_fields(decision, ("finding_id", "action", "reason"), f"decisions[{position}]")
        finding_id = decision["finding_id"]
        if finding_id not in findings:
            raise ValueError(f"governance decision targets unknown finding: {finding_id}")
        if finding_id in seen:
            raise ValueError(f"duplicate governance decision: {finding_id}")
        seen.add(finding_id)
        allowed_actions = (
            {"cleared", "repair_requested", "invalidated", "deferred"}
            if strict else {"cleared", "repair_requested", "excluded"}
        )
        if decision["action"] not in allowed_actions:
            raise ValueError(f"invalid governance action: {decision['action']}")
        if decision["action"] == "cleared" and not findings[finding_id]["resolved"]:
            raise ValueError(f"unresolved finding cannot be cleared: {finding_id}")
        require_text(decision["reason"], f"{finding_id}.reason")
        if strict:
            provenance = require_dict(decision.get("_provenance"), f"{finding_id}._provenance")
            require_text(provenance.get("actor"), f"{finding_id}._provenance.actor")
            if append_only:
                verify_record_provenance(decision, finding_id)
                if decision["_provenance"]["actor"] != STAGES["governance_review"]["actor"]:
                    raise ValueError(f"{finding_id} decision was not recorded by the Governor")
            if decision["action"] == "invalidated":
                finding = findings[finding_id]
                if (
                    finding["resolved"]
                    or finding["severity"] != "fatal"
                    or finding["kind"] not in MATHEMATICAL_FATAL_KINDS
                ):
                    raise ValueError(
                        f"{finding_id} can be invalidated only by unresolved fatal mathematical evidence"
                    )
    required = {
        item["id"]
        for item in findings.values()
        if item["severity"] in {"major", "fatal"}
    }
    missing = required - seen
    if missing:
        raise ValueError(f"governor must decide every major/fatal local finding: {sorted(missing)}")


def synthesized_statements(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    artifact = completed_artifact(run_dir, "theorem_synthesis")
    statements = unique_records(artifact.get("statements"), "statements")
    proofs = validate_proof_index(run_dir)
    maps = discovery_maps(run_dir)
    for statement_id, statement in statements.items():
        require_text(statement.get("formal"), f"{statement_id}.formal")
        require_text(statement.get("proven_scope"), f"{statement_id}.proven_scope")
        sources = require_list(statement.get("synthesized_from"), f"{statement_id}.synthesized_from")
        if not sources:
            raise ValueError(f"{statement_id} must cite supporting proof obligations")
        if len(sources) != len(set(sources)):
            raise ValueError(f"{statement_id}.synthesized_from contains duplicates")
        unknown = [source for source in sources if source not in proofs]
        if unknown:
            raise ValueError(f"{statement_id} cites unknown proofs: {unknown}")
        incomplete = [source for source in sources if proofs[source]["status"] not in PROOF_READY]
        if incomplete:
            raise ValueError(f"{statement_id} cites incomplete proofs: {incomplete}")
        based_on = require_list(statement.get("based_on"), f"{statement_id}.based_on")
        if len(based_on) != len(set(based_on)):
            raise ValueError(f"{statement_id}.based_on contains duplicates")
        if any(target not in maps["targets"] for target in based_on):
            raise ValueError(f"{statement_id} cites unknown theorem targets")
        assumptions = require_list(
            statement.get("assumptions_used", []), f"{statement_id}.assumptions_used"
        )
        if len(assumptions) != len(set(assumptions)):
            raise ValueError(f"{statement_id}.assumptions_used contains duplicates")
        if any(item not in maps["assumptions"] for item in assumptions):
            raise ValueError(f"{statement_id} cites unknown assumptions")
        statement_assumption_closure(run_dir, statement, proofs=proofs, maps=maps)
    return statements


def statement_assumption_closure(
    run_dir: Path,
    statement: Dict[str, Any],
    *,
    proofs: Dict[str, Dict[str, Any]] | None = None,
    maps: Dict[str, Dict[str, Dict[str, Any]]] | None = None,
) -> List[Dict[str, Any]]:
    """Return the complete, text-bearing assumption closure for a synthesized statement.

    A statement depends on its cited proof obligations and every transitive proof dependency.
    Merely retaining assumption IDs is insufficient for downstream writing: the complete discovery
    text is carried into the theory bundle so a condition cannot disappear during synthesis.
    """
    proofs = proofs or validate_proof_index(run_dir)
    maps = maps or discovery_maps(run_dir)
    pending = list(statement.get("synthesized_from", []))
    proof_ids: Set[str] = set()
    while pending:
        proof_id = pending.pop()
        if proof_id in proof_ids:
            continue
        if proof_id not in proofs:
            raise ValueError(f"{statement['id']} cites unknown proof: {proof_id}")
        proof_ids.add(proof_id)
        pending.extend(proofs[proof_id].get("depends_on", []))

    required_by: Dict[str, Set[str]] = {}
    for proof_id in proof_ids:
        for assumption_id in proofs[proof_id].get("assumptions_used", []):
            required_by.setdefault(assumption_id, set()).add(proof_id)

    declared = set(statement.get("assumptions_used", []))
    missing = set(required_by) - declared
    if missing:
        raise ValueError(
            f"{statement['id']} omits assumptions required by its proof closure: {sorted(missing)}"
        )

    closure = []
    for assumption_id in sorted(declared):
        assumption = dict(maps["assumptions"][assumption_id])
        closure.append({
            "id": assumption_id,
            "statement": require_text(
                assumption.get("statement"), f"{assumption_id}.statement"
            ),
            "required_by_proofs": sorted(required_by.get(assumption_id, set())),
        })
    return closure


def statement_proof_closure(
    statement: Dict[str, Any], proofs: Dict[str, Dict[str, Any]]
) -> Set[str]:
    """Return the transitive proof obligations that establish a statement."""
    pending = list(statement.get("synthesized_from", []))
    closure: Set[str] = set()
    while pending:
        proof_id = pending.pop()
        if proof_id in closure:
            continue
        if proof_id not in proofs:
            raise ValueError(f"{statement['id']} cites unknown proof: {proof_id}")
        closure.add(proof_id)
        pending.extend(proofs[proof_id].get("depends_on", []))
    return closure


def statement_dependency_targets(
    statement: Dict[str, Any], proofs: Dict[str, Dict[str, Any]]
) -> Set[str]:
    """Targets whose correctness can block the synthesized statement.

    ``based_on`` records research provenance, not a logical dependency. A finding on an
    original target therefore blocks a synthesized statement only when it also reaches
    the statement through its transitive proof or assumption closure.
    """
    proof_ids = statement_proof_closure(statement, proofs)
    assumptions = set(statement.get("assumptions_used", []))
    for proof_id in proof_ids:
        assumptions.update(proofs[proof_id].get("assumptions_used", []))
    return {"RUN", statement["id"], *proof_ids, *assumptions}


def statement_targets(
    statement: Dict[str, Any],
    proofs: Dict[str, Dict[str, Any]] | None = None,
    *,
    include_provenance: bool = True,
) -> Set[str]:
    """Return statement relevance targets.

    ``include_provenance=True`` preserves the schema-3 interpretation for immutable old
    Arbiter records. New correctness decisions must pass a proof index and set it false.
    """
    if proofs is not None and not include_provenance:
        return statement_dependency_targets(statement, proofs)
    return {
        "RUN",
        statement["id"],
        *statement.get("synthesized_from", []),
        *statement.get("based_on", []),
        *statement.get("assumptions_used", []),
    }


def all_findings(run_dir: Path) -> List[Dict[str, Any]]:
    local = audit_findings(run_dir, "local_adversarial_audit")
    final = audit_findings(run_dir, "final_adversarial_audit")
    local_ids = {item["id"] for item in local}
    collisions = local_ids & {item["id"] for item in final}
    if collisions and any(
        item.get("_integrity_mode") == "strict" for item in local + final
        if item["id"] in collisions
    ):
        raise ValueError(f"audit finding IDs collide across stages: {sorted(collisions)}")
    return local + final


def repair_verification_events(run_dir: Path) -> List[Dict[str, Any]]:
    records = []
    for stage in ("local_adversarial_audit", "final_adversarial_audit"):
        audit_findings(run_dir, stage)
        artifact = completed_artifact(run_dir, stage)
        for event in artifact.get("events", []):
            if event.get("event_type") == "cross_run_repair_verification":
                record = dict(event)
                record["audit_stage"] = stage
                records.append(record)
    return records


def statement_blockers(
    statement: Dict[str, Any],
    findings: List[Dict[str, Any]],
    proofs: Dict[str, Dict[str, Any]] | None = None,
    *,
    include_provenance: bool = False,
) -> List[Dict[str, Any]]:
    if proofs is None and not include_provenance:
        raise ValueError("correct blocker analysis requires the proof index")
    targets = statement_targets(
        statement, proofs, include_provenance=include_provenance
    )
    return [
        item
        for item in findings
        if (item["target_id"] in targets or bool(targets & set(item.get("scope_affected", []))))
        and item["severity"] in {"major", "fatal"}
        and not item["resolved"]
    ]


def nonfinal_disposition(decision: Dict[str, Any], blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep unfinished work visible; reserve exclusion for invalid or fatally refuted claims."""
    status = decision["status"]
    if status == "invalid":
        return {
            "excluded": True,
            "disposition": "invalid_excluded",
            "reason": "arbiter determined the statement is mathematically invalid",
        }
    if any(
        blocker.get("severity") == "fatal"
        and blocker.get("kind") in MATHEMATICAL_FATAL_KINDS
        for blocker in blockers
    ):
        return {
            "excluded": True,
            "disposition": "invalid_excluded",
            "reason": "an unresolved fatal mathematical audit finding targets this statement",
        }
    return {
        "excluded": False,
        "disposition": {
            "repair_requested": "repair_candidate",
            "conjecture_only": "conjecture",
            "rejected": "deferred_or_unresolved",
        }.get(status, "deferred_or_unresolved"),
        "reason": decision["reason"],
    }


def arbiter_decisions(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    artifact = completed_artifact(run_dir, "arbiter")
    schema = artifact.get("schema_version")
    strict = schema in {2, 3, ARBITER_SCHEMA_VERSION}
    append_only = schema in {3, ARBITER_SCHEMA_VERSION}
    if schema not in {None, 1, 2, 3, ARBITER_SCHEMA_VERSION}:
        raise ValueError(f"unsupported arbiter schema_version: {schema}")
    if strict and (
        artifact.get("artifact") != "arbiter_decisions" or artifact.get("stage") != "arbiter"
    ):
        raise ValueError("invalid strict arbiter artifact identity")
    decisions = require_list(artifact.get("decisions"), "decisions")
    statements = synthesized_statements(run_dir)
    proofs = validate_proof_index(run_dir)
    include_provenance = schema != ARBITER_SCHEMA_VERSION
    findings = all_findings(run_dir)
    findings_by_id = {item["id"]: item for item in findings}
    result: Dict[str, Dict[str, Any]] = {}
    for position, raw in enumerate(decisions):
        decision = require_dict(raw, f"decisions[{position}]")
        require_fields(decision, ("statement_id", "status", "reason"), f"decisions[{position}]")
        statement_id = decision["statement_id"]
        if statement_id not in statements:
            raise ValueError(f"arbiter decision targets unknown statement: {statement_id}")
        if statement_id in result:
            raise ValueError(f"duplicate arbiter decision: {statement_id}")
        if decision["status"] not in DECISION_STATUSES:
            raise ValueError(f"invalid arbiter status: {decision['status']}")
        require_text(decision["reason"], f"{statement_id}.reason")
        if strict:
            addressed = require_list(
                decision.get("findings_addressed"), f"{statement_id}.findings_addressed"
            )
            if len(addressed) != len(set(addressed)):
                raise ValueError(f"{statement_id}.findings_addressed contains duplicates")
            unknown = [item for item in addressed if item not in findings_by_id]
            if unknown:
                raise ValueError(f"{statement_id} addresses unknown findings: {unknown}")
            targets = statement_targets(
                statements[statement_id], proofs,
                include_provenance=include_provenance,
            )
            unrelated = [item for item in addressed if (
                findings_by_id[item]["target_id"] not in targets
                and not bool(targets & set(findings_by_id[item].get("scope_affected", [])))
            )]
            if unrelated:
                raise ValueError(f"{statement_id} addresses unrelated findings: {unrelated}")
            provenance = require_dict(
                decision.get("_provenance"), f"{statement_id}._provenance"
            )
            require_text(provenance.get("actor"), f"{statement_id}._provenance.actor")
            if append_only:
                verify_record_provenance(decision, statement_id)
                if decision["_provenance"]["actor"] != STAGES["arbiter"]["actor"]:
                    raise ValueError(f"{statement_id} decision was not recorded by the Governor")
        if decision.get("weakened_form") is not None:
            require_text(decision["weakened_form"], f"{statement_id}.weakened_form")
            if decision["status"] not in ACCEPTED_DECISIONS:
                raise ValueError(
                    f"{statement_id}.weakened_form requires an accepted decision status"
                )
        blockers = statement_blockers(
            statements[statement_id], findings, proofs,
            include_provenance=include_provenance,
        )
        if decision["status"] in ACCEPTED_DECISIONS and blockers:
            raise ValueError(
                f"accepted statement {statement_id} has open blockers: "
                f"{[item['id'] for item in blockers]}"
            )
        if strict and decision["status"] == "invalid":
            fatal_evidence = [
                item for item in blockers
                if item["severity"] == "fatal"
                and item["kind"] in MATHEMATICAL_FATAL_KINDS
                and item["id"] in decision["findings_addressed"]
            ]
            if not fatal_evidence:
                raise ValueError(
                    f"invalid decision for {statement_id} requires an addressed, relevant, "
                    "unresolved fatal mathematical finding"
                )
        if strict and decision["status"] == "repair_requested" and not blockers:
            raise ValueError(f"repair_requested decision for {statement_id} requires an open blocker")
        result[statement_id] = decision
    missing = set(statements) - set(result)
    if missing:
        raise ValueError(f"arbiter must decide every synthesized statement: {sorted(missing)}")
    return result


def validate_contribution_assessment(run_dir: Path) -> None:
    artifact = completed_artifact(run_dir, "contribution_assessment")
    accepted_ids = {
        statement_id
        for statement_id, decision in arbiter_decisions(run_dir).items()
        if decision["status"] in ACCEPTED_DECISIONS
    }
    validate_contribution(artifact, accepted_ids)
    contracted_goal = load_manifest(run_dir).get("execution_contract", {}).get(
        "publication_goal", "no_preference"
    )
    if contracted_goal not in PUBLICATION_GOALS:
        raise ValueError("run contract contains an invalid publication goal")
    if contracted_goal != "no_preference" and artifact.get("publication_goal") != contracted_goal:
        raise ValueError(
            "contribution assessment changed the researcher publication goal: "
            f"expected {contracted_goal}, received {artifact.get('publication_goal')}"
        )
    novelty = completed_artifact(run_dir, "novelty_audit")
    validate_novelty_audit(novelty, accepted_ids)
    significance = completed_artifact(run_dir, "significance_audit")
    validate_significance_audit(significance, accepted_ids)
    derive_route(accepted_ids, novelty, significance, artifact)


def build_theory_bundle(run_dir: Path) -> Dict[str, Any]:
    statements = synthesized_statements(run_dir)
    decisions = arbiter_decisions(run_dir)
    proofs = validate_proof_index(run_dir)
    arbiter_schema = completed_artifact(run_dir, "arbiter").get("schema_version")
    include_provenance = arbiter_schema != ARBITER_SCHEMA_VERSION
    findings = all_findings(run_dir)
    novelty = completed_artifact(run_dir, "novelty_audit")
    significance = completed_artifact(run_dir, "significance_audit")
    contribution = completed_artifact(run_dir, "contribution_assessment")
    accepted = []
    retained = []
    excluded = []
    for statement_id, statement in sorted(statements.items()):
        decision = decisions[statement_id]
        blockers = statement_blockers(
            statement, findings, proofs,
            include_provenance=include_provenance,
        )
        effective_statement = dict(statement)
        effective_statement["assumption_closure"] = statement_assumption_closure(
            run_dir, statement, proofs=proofs
        )
        weakened_form = decision.get("weakened_form")
        if weakened_form:
            effective_statement["formal"] = weakened_form
        if effective_statement["assumption_closure"]:
            assumption_text = " ".join(
                f"[{item['id']}] {item['statement']}"
                for item in effective_statement["assumption_closure"]
            )
            effective_statement["standalone_formal"] = (
                f"Assume {assumption_text} Then {effective_statement['formal']}"
            )
        else:
            effective_statement["standalone_formal"] = effective_statement["formal"]
        record = {
            "effective_statement": effective_statement,
            "decision": decision,
            "supporting_proofs": [proofs[source] for source in statement["synthesized_from"]],
            "open_blockers": blockers,
        }
        if weakened_form:
            record["original_synthesized_statement"] = statement
        if decision["status"] in ACCEPTED_DECISIONS and not blockers:
            accepted.append(record)
        else:
            disposition = nonfinal_disposition(decision, blockers)
            record["disposition"] = disposition["disposition"]
            if disposition["excluded"]:
                record["exclusion_reasons"] = [disposition["reason"]]
                excluded.append(record)
            else:
                record["retention_reason"] = disposition["reason"]
                record["not_established_as_result"] = True
                retained.append(record)
    route = derive_route(
        [record["effective_statement"]["id"] for record in accepted],
        novelty,
        significance,
        contribution,
    )
    writing_eligible = bool(route["writing_allowed"])
    unresolved_repairs = [
        decision for decision in decisions.values()
        if decision["status"] == "repair_requested"
    ]
    lineage_depth = 0
    parent_id = load_manifest(run_dir).get("parent_run_id")
    visited: Set[str] = set()
    while parent_id:
        parent_id = validate_run_id(parent_id)
        if parent_id in visited:
            raise ValueError("run ancestry contains a cycle")
        visited.add(parent_id)
        lineage_depth += 1
        parent_manifest = load_manifest((run_dir.parent / parent_id).resolve())
        parent_id = parent_manifest.get("parent_run_id")
    blocking_extensions = [
        item for item in contribution.get("development_obligations", [])
        if item.get("priority") == "blocking"
    ]
    manifest = load_manifest(run_dir)
    completed_strengthening_rounds = strengthening_round(manifest)
    if unresolved_repairs:
        next_action = "child_mathematical_repair"
    elif (
        blocking_extensions
        and completed_strengthening_rounds < 2
        and not (
            route.get("submission_readiness") == "ready"
            or (
                "submission_readiness" not in route
                and route.get("publication_tier") in {
                    "conference_candidate", "short_paper_candidate"
                }
            )
        )
    ):
        next_action = "child_contribution_extension"
    else:
        next_action = "paper_pipeline"
    return {
        "schema_version": 5,
        "artifact": "theory_bundle",
        "generated_at": utc_now(),
        "run_id": load_manifest(run_dir)["run_id"],
        "research_question": load_manifest(run_dir)["research_question"],
        "theory_ready": bool(accepted),
        "writing_eligible": writing_eligible,
        "writing_included": False,
        "accepted_statements": accepted,
        "retained_nonfinal_statements": retained,
        "excluded_statements": excluded,
        "repair_verification_lineage": repair_verification_events(run_dir),
        "novelty_audit": novelty,
        "significance_audit": significance,
        "contribution_assessment": contribution,
        "paper_route": route,
        "refinement": {
            "protocol": "bounded_same_run_strengthening_then_guided_revision",
            "lineage_depth": lineage_depth,
            "default_max_repair_rounds": 3,
            "progress_vector": {
                "accepted_statements": len(accepted),
                "retained_nonfinal_statements": len(retained),
                "unresolved_major_or_fatal_findings": sum(
                    1 for item in findings
                    if item["severity"] in {"major", "fatal"} and not item["resolved"]
                ),
                "drafted_or_accepted_proofs": sum(
                    1 for item in proofs.values() if item["status"] in PROOF_READY
                ),
                "blocking_development_obligations": len(blocking_extensions),
            },
            "next_action": next_action,
            "stopping_rule": (
                "Stop automatic strengthening when the publication goal is reached, two passes "
                "are completed, or the next action would materially change the research direction."
            ),
        },
        "unresolved_repairs": unresolved_repairs,
    }


def validate_stage(run_dir: Path, stage: str) -> Path:
    if stage not in STAGES:
        raise ValueError(f"unknown workflow stage: {stage}")
    path = artifact_path(run_dir, STAGES[stage]["artifact"])
    if not path.is_file():
        raise ValueError(f"stage artifact is missing: {path}")
    if stage == "direction_generation":
        validate_directions(run_dir)
    elif stage == "direction_selection":
        validate_selection(run_dir)
    elif stage == "discovery":
        validate_discovery(run_dir)
    elif stage == "exploration":
        validate_exploration(run_dir)
    elif stage == "proof_development":
        validate_proofs(run_dir)
    elif stage in {"local_adversarial_audit", "final_adversarial_audit"}:
        audit_findings(run_dir, stage)
    elif stage == "governance_review":
        validate_governance_review(run_dir)
    elif stage == "theorem_synthesis":
        synthesized_statements(run_dir)
    elif stage == "arbiter":
        arbiter_decisions(run_dir)
    elif stage == "novelty_audit":
        accepted_ids = {
            statement_id
            for statement_id, decision in arbiter_decisions(run_dir).items()
            if decision["status"] in ACCEPTED_DECISIONS
        }
        validate_novelty_audit(completed_artifact(run_dir, stage), accepted_ids)
    elif stage == "significance_audit":
        accepted_ids = {
            statement_id
            for statement_id, decision in arbiter_decisions(run_dir).items()
            if decision["status"] in ACCEPTED_DECISIONS
        }
        validate_significance_audit(completed_artifact(run_dir, stage), accepted_ids)
    elif stage == "contribution_assessment":
        validate_contribution_assessment(run_dir)
    elif stage == "theory_bundle":
        bundle = require_dict(read_json(path), "theory_bundle")
        if bundle.get("artifact") != "theory_bundle" or bundle.get("schema_version") != 5:
            raise ValueError("invalid deterministic theory bundle")
    return path


def command_init(args: argparse.Namespace) -> int:
    requested_mode = getattr(args, "requested_mode", None)
    intent = getattr(args, "intent", None) or (
        "repair" if args.parent_run else "new_full" if requested_mode == "full" else "new_theory"
    )
    auto_repair_enabled = getattr(args, "auto_repair_enabled", False)
    requested_repair_rounds = getattr(args, "max_auto_repair_rounds", None)
    max_auto_repair_rounds = (
        3 if auto_repair_enabled else 0
    ) if requested_repair_rounds is None else requested_repair_rounds
    requested_publication_goal = getattr(args, "publication_goal", None)
    publication_goal = (
        "original_research"
        if requested_mode == "full" or intent == "new_full"
        else requested_publication_goal or "no_preference"
    )
    run_dir = create_run(
        workspace=Path(args.workspace),
        question=args.question,
        stages=STAGES,
        run_id=args.run_id,
        parent_run_id=args.parent_run,
        execution_contract={
            "intent": intent,
            "initiated_from": getattr(args, "initiated_from", "cli"),
            "requested_mode": requested_mode or (
                "repair" if intent == "repair" else intent.removeprefix("new_")
            ),
            "subagents_permitted": getattr(args, "subagents_permitted", None),
            "human_checkpoints_required": False,
            "interaction_policy": "autonomous",
            "publication_goal": publication_goal,
            "auto_repair_enabled": auto_repair_enabled,
            "max_auto_repair_rounds": max_auto_repair_rounds,
            "repair_round": getattr(args, "repair_round", 0),
        },
    )
    print(
        json.dumps(
            {"run_dir": str(run_dir), "current_stage": next(iter(STAGES))}, indent=2
        )
    )
    return 0


def command_status(args: argparse.Namespace) -> int:
    run_dir = resolve_run(Path(args.workspace), args.run)
    manifest = load_manifest(run_dir)
    verify_completed_artifacts(run_dir, manifest)
    print(json.dumps(manifest, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    run_dir = resolve_run(Path(args.workspace), args.run)
    with path_lock(run_dir / "artifact-operation"):
        manifest = load_manifest(run_dir)
        verify_completed_artifacts(run_dir, manifest)
        revision_state = manifest.get("revision_state", {})
        if revision_state.get("status") in {
            "linked_revision_required", "linked_revision_started",
        }:
            child = revision_state.get("child_run_id")
            suffix = f" {child}" if child else ""
            raise ValueError(
                "this run is frozen while its governed linked repair continues in child run"
                f"{suffix}; do not synthesize the unrepaired parent"
            )
        stage = manifest["current_stage"]
        if stage == "complete":
            raise ValueError("run is already complete")
        path = validate_stage(run_dir, stage)
    print(json.dumps({"stage": stage, "valid": True, "artifact": str(path)}, indent=2))
    return 0


def command_complete(args: argparse.Namespace) -> int:
    run_dir = resolve_run(Path(args.workspace), args.run)
    with path_lock(run_dir / "artifact-operation"):
        manifest = load_manifest(run_dir)
        verify_completed_artifacts(run_dir, manifest)
        revision_state = manifest.get("revision_state", {})
        if revision_state.get("status") in {
            "linked_revision_required", "linked_revision_started",
        }:
            child = revision_state.get("child_run_id")
            suffix = f" {child}" if child else ""
            raise ValueError(
                "this run is frozen while its governed linked repair continues in child run"
                f"{suffix}; do not synthesize the unrepaired parent"
            )
        stage = manifest["current_stage"]
        if stage == "complete":
            raise ValueError("run is already complete")
        expected_actor = STAGES[stage]["actor"]
        if args.actor != expected_actor:
            raise PermissionError(
                f"stage {stage} requires actor {expected_actor}; received {args.actor}"
            )
        path = artifact_path(run_dir, STAGES[stage]["artifact"])
        if stage == "theory_bundle":
            write_json(path, build_theory_bundle(run_dir))
        validate_stage(run_dir, stage)
        if stage == "theory_bundle":
            candidate_bundle = read_json(path)
            if strengthening_available(manifest, candidate_bundle, run_dir):
                record = start_strengthening_unlocked(
                    run_dir,
                    manifest,
                    STAGES,
                    candidate_bundle,
                    reason=(
                        "The audited result is valid but does not meet the researcher-selected "
                        "publication goal. Preserve it and develop the highest-leverage coherent "
                        "addition before finalizing incomplete submission evidence."
                    ),
                )
                print(json.dumps({
                    "strengthened_from": "theory_bundle",
                    "current_stage": manifest["current_stage"],
                    "next_action": {
                        "type": "same_run_contribution_strengthening",
                        "round": record["round"],
                        "maximum_rounds": manifest["strengthening_state"]["maximum_rounds"],
                        "publication_goal": record["publication_goal"],
                        "previous_submission_readiness": record.get(
                            "previous_submission_readiness", record.get("previous_tier")
                        ),
                        "resume_stage": record["resume_stage"],
                        "archive": record["archive"],
                        "instruction": (
                            "Use $contribution-strengthening and continue this exact run. Preserve "
                            "accepted results, strengthen the scientific package, and rerun every "
                            "affected proof, novelty, and significance gate."
                        ),
                    },
                }, indent=2))
                return 0
        serious_governance = False
        if stage == "governance_review":
            serious_governance = any(
                isinstance(item, dict)
                and item.get("action") in {"repair_requested", "invalidated", "deferred", "excluded"}
                for item in read_json(path).get("decisions", [])
            )
        if stage == "governance_review" and correction_available(run_dir, manifest):
            record = start_correction_unlocked(
                run_dir,
                manifest,
                STAGES,
                reason=(
                    "Governance identified a repairable mathematical defect. Preserve the failed "
                    "pass, correct the smallest affected assumption or proof closure, and re-audit."
                ),
            )
            print(json.dumps({
                "corrected_from": "governance_review",
                "current_stage": manifest["current_stage"],
                "next_action": {
                    "type": "same_run_proof_correction",
                    "round": record["round"],
                    "maximum_rounds": manifest["correction_state"]["maximum_rounds"],
                    "finding_ids": record["finding_ids"],
                    "nonrepair_dispositions": record.get("nonrepair_dispositions", []),
                    "archive": record["archive"],
                    "instruction": (
                        "Use $proof-repair and continue this exact run from discovery. "
                        "Repair every repair-requested closure, preserve the recorded disposition "
                        "of deferred or invalidated closures, and do not synthesize failed proofs."
                    ),
                },
            }, indent=2))
            return 0
        stage_state = manifest["stages"][stage]
        stage_state.update(
            {
                "status": "completed",
                "completed_at": utc_now(),
                "evidence_sha256": file_sha256(path),
            }
        )
        names = list(STAGES)
        next_index = names.index(stage) + 1
        if next_index == len(names):
            manifest["current_stage"] = "complete"
            manifest["status"] = "completed"
            manifest["completed_at"] = utc_now()
        else:
            next_stage = names[next_index]
            manifest["current_stage"] = next_stage
            manifest["stages"][next_stage]["status"] = "in_progress"
        if stage == "governance_review":
            correction_state = manifest.get("correction_state")
            if isinstance(correction_state, dict) and correction_state.get("status") == "in_progress":
                completed_at = utc_now()
                outcome = "ended_with_salvage" if serious_governance else "passed_reaudit"
                correction_state["status"] = outcome
                correction_state["completed_at"] = completed_at
                history = correction_state.get("history", [])
                if isinstance(history, list) and history and isinstance(history[-1], dict):
                    history[-1]["status"] = outcome
                    history[-1]["completed_at"] = completed_at
        if stage == "theory_bundle":
            strengthening_state = manifest.get("strengthening_state")
            if isinstance(strengthening_state, dict) and strengthening_state.get("status") == "in_progress":
                route = read_json(path).get("paper_route", {})
                completed_at = utc_now()
                outcome = (
                    "publication_goal_met"
                    if route.get("publication_goal_satisfied") is True
                    else "goal_unmet_after_budget"
                )
                strengthening_state["status"] = outcome
                strengthening_state["completed_at"] = completed_at
                strengthening_state["final_manuscript_kind"] = route.get("manuscript_kind")
                strengthening_state["final_submission_readiness"] = route.get("submission_readiness")
                history = strengthening_state.get("history", [])
                if isinstance(history, list) and history and isinstance(history[-1], dict):
                    history[-1]["status"] = outcome
                    history[-1]["completed_at"] = completed_at
                    history[-1]["final_manuscript_kind"] = route.get("manuscript_kind")
                    history[-1]["final_submission_readiness"] = route.get("submission_readiness")
        save_manifest(run_dir, manifest)
    result = {"completed": stage, "current_stage": manifest["current_stage"]}
    print(json.dumps(result, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--workspace", default=".", help="User workspace for run data")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Create a new immutable-evidence run")
    init.add_argument("--question", required=True)
    init.add_argument("--run-id")
    init.add_argument("--parent-run")
    init.add_argument("--intent", choices=("new_theory", "new_full", "repair"))
    init.add_argument("--initiated-from", choices=("controller", "cli", "studio"), default="cli")
    init.add_argument(
        "--requested-mode", choices=("theory", "full", "repair"), required=True,
        help="Declare whether this run stops at theory, continues through a paper, or repairs a parent run",
    )
    init.add_argument(
        "--subagents-permitted",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    init.add_argument(
        "--publication-goal",
        choices=sorted(PUBLICATION_GOALS),
        default=None,
        help="Publication target; full runs default to original_research.",
    )
    init.add_argument(
        "--auto-repair-enabled",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    init.add_argument("--max-auto-repair-rounds", type=int)
    init.add_argument("--repair-round", type=int, default=0)
    init.set_defaults(handler=command_init)

    for name, handler in (
        ("status", command_status),
        ("validate", command_validate),
    ):
        command = commands.add_parser(name)
        command.add_argument("--run")
        command.set_defaults(handler=handler)

    complete = commands.add_parser("complete")
    complete.add_argument("--run")
    complete.add_argument("--actor", required=True)
    complete.set_defaults(handler=command_complete)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except (ValueError, PermissionError) as exc:
        raise SystemExit(f"error: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
