#!/usr/bin/env python3
"""Persist immutable, evidence-linked audit and governance records."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from state_store import (
    artifact_path,
    file_sha256,
    load_manifest,
    path_lock,
    read_json,
    safe_run_path,
    utc_now,
    verify_completed_artifacts,
)
from tool_utils import (
    append_json_record,
    identifier,
    locked_json_update,
    run_dir,
    workspace_path,
)


AUDIT_SCHEMA_VERSION = 4
GOVERNANCE_SCHEMA_VERSION = 3
ARBITER_SCHEMA_VERSION = 4
AUDIT_STAGES = {"local_adversarial_audit", "final_adversarial_audit"}
FINDING_KINDS = {
    "proof_gap", "counterexample", "assumption_failure", "boundary_case",
    "definition_error", "dependency_error", "citation_mismatch", "novelty_issue",
    "scope_overclaim", "numerical_contradiction", "reproducibility_issue", "other",
}
MATHEMATICAL_FATAL_KINDS = {
    "proof_gap", "counterexample", "assumption_failure", "boundary_case",
    "definition_error", "dependency_error", "numerical_contradiction",
}
GOVERNANCE_ACTIONS = {"cleared", "repair_requested", "invalidated", "deferred"}
RESOLUTION_TYPES = {"false_positive", "preexisting_evidence"}
VERIFICATION_MODES = {"independent_subagent", "fresh_role_review", "external_check"}


def canonical_sha256(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} cannot be empty")
    return value.strip()


def finding_id(value: str, stage: str) -> str:
    raw = identifier(value, "finding ID")
    prefix = "LOCAL-" if stage == "local_adversarial_audit" else "FINAL-"
    return raw if raw.startswith(prefix) else f"{prefix}{raw}"


def workspace_evidence_file(
    workspace: str, supplied: str, label: str, contained_in: Optional[Path] = None
) -> dict:
    root = Path(workspace).resolve()
    path = workspace_path(root, supplied)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must identify a regular workspace file")
    if contained_in is not None:
        try:
            path.relative_to(contained_in.resolve())
        except ValueError as exc:
            raise ValueError(f"{label} must belong to the selected run") from exc
    return {"path": str(path.relative_to(root)), "sha256": file_sha256(path)}


def evidence_source(workspace: str, supplied: str, location: str, selected_run: Path) -> dict:
    result = workspace_evidence_file(workspace, supplied, "source path", selected_run)
    result["location"] = required_text(location, "source location")
    return result


def initialize_artifact(path: Path, stage: str) -> None:
    specifications = {
        "local_adversarial_audit": (AUDIT_SCHEMA_VERSION, "adversarial_audit", "findings"),
        "final_adversarial_audit": (AUDIT_SCHEMA_VERSION, "adversarial_audit", "findings"),
        "governance_review": (GOVERNANCE_SCHEMA_VERSION, "governance_review", "decisions"),
        "arbiter": (ARBITER_SCHEMA_VERSION, "arbiter_decisions", "decisions"),
    }
    schema, artifact, collection = specifications[stage]

    def initialize(value):
        if not value:
            result = {
                "schema_version": schema, "artifact": artifact, "stage": stage, collection: [],
            }
            if stage in AUDIT_STAGES:
                result["events"] = []
            return result
        if "schema_version" not in value and value.get(collection) == []:
            value.update({"schema_version": schema, "artifact": artifact, "stage": stage})
            if stage in AUDIT_STAGES:
                value["events"] = []
        elif value.get("schema_version") != schema:
            raise ValueError(
                f"cannot mutate {stage} schema {value.get('schema_version')!r} with schema-v{schema} tools; "
                "legacy evidence remains readable and immutable"
            )
        return value

    locked_json_update(path, initialize, {})


def attack_operation_ledger(root: Path) -> Path:
    return root / "artifacts" / "audit_operation_ledger.json"


def build_attack_summary(args, root: Path) -> dict:
    targets = [identifier(item, "attack target") for item in args.targets]
    methods = [identifier(item, "attack method") for item in args.attack_methods]
    if len(targets) != len(set(targets)) or not targets:
        raise ValueError("attack summary requires unique non-empty targets")
    if len(methods) != len(set(methods)) or not methods:
        raise ValueError("attack summary requires unique non-empty methods")
    evidence = [
        workspace_evidence_file(args.workspace, item, "attack evidence", root)
        for item in args.evidence_files
    ]
    if not evidence:
        raise ValueError("attack summary requires at least one persisted evidence file")
    summary = {
        "targets_reviewed": targets,
        "attack_methods": methods,
        "evidence_files": evidence,
        "conclusion": args.conclusion,
        "rationale": required_text(args.rationale, "attack-summary rationale"),
        "actor": identifier(args.actor, "actor"),
        "recorded_at": utc_now(),
    }
    summary["summary_sha256"] = canonical_sha256(summary)
    return summary


def append_attack_summary_anchor(
    root: Path, stage: str, summary: dict, actor: str, *, operation: str,
    previous_summary_sha256: Optional[str], reason: str,
) -> None:
    ledger_path = attack_operation_ledger(root)
    empty_ledger = {
        "schema_version": 1,
        "artifact": "audit_operation_ledger",
        "records": [],
    }
    def initialize_ledger(value):
        if not value:
            return dict(empty_ledger)
        if (
            value.get("schema_version") != 1
            or value.get("artifact") != "audit_operation_ledger"
            or not isinstance(value.get("records"), list)
        ):
            raise ValueError("invalid audit operation ledger")
        return value

    locked_json_update(ledger_path, initialize_ledger, empty_ledger)
    existing = read_json(ledger_path)
    records = existing.get("records", [])
    sequence = 1 + sum(
        1 for item in records
        if isinstance(item, dict) and item.get("stage") == stage
    )
    record = {
        "id": f"{stage.upper()}-SUMMARY-{sequence:04d}",
        "stage": stage,
        "operation": operation,
        "previous_summary_sha256": previous_summary_sha256,
        "summary_sha256": summary["summary_sha256"],
        "reason": required_text(reason, "attack-summary operation reason"),
    }
    append_json_record(ledger_path, "records", record, actor=actor)


def command_attack_summary(args):
    """Persist and externally anchor what was actually attacked."""
    with stage_path(args, AUDIT_STAGES) as (root, path, stage, _):
        summary = build_attack_summary(args, root)

        def write_once(value):
            if value.get("attack_summary") is not None:
                raise ValueError(
                    "attack summary already exists; use revise-attack-summary instead of editing JSON"
                )
            value["attack_summary"] = summary
            return value

        locked_json_update(path, write_once, {})
        append_attack_summary_anchor(
            root, stage, summary, args.actor, operation="record",
            previous_summary_sha256=None, reason="Initial attack summary seal.",
        )
    print(json.dumps({"stage": stage, "attack_summary": summary}, indent=2))


def command_revise_attack_summary(args):
    """Revise an in-progress summary through a hash-linked external operation record."""
    with stage_path(args, AUDIT_STAGES) as (root, path, stage, _):
        current = read_json(path).get("attack_summary")
        if not isinstance(current, dict):
            raise ValueError("no attack summary exists; use record-attack-summary")
        previous = required_text(current.get("summary_sha256"), "previous attack-summary hash")
        summary = build_attack_summary(args, root)
        reason = required_text(args.reason, "attack-summary revision reason")

        def replace(value):
            existing = value.get("attack_summary")
            if not isinstance(existing, dict) or existing.get("summary_sha256") != previous:
                raise ValueError("attack summary changed during revision")
            value["attack_summary"] = summary
            return value

        locked_json_update(path, replace, {})
        append_attack_summary_anchor(
            root, stage, summary, args.actor, operation="revise",
            previous_summary_sha256=previous, reason=reason,
        )
    print(json.dumps({"stage": stage, "attack_summary": summary}, indent=2))


@contextmanager
def stage_path(args, allowed):
    root = run_dir(args.workspace, args.run)
    with path_lock(root / "artifact-operation"):
        manifest = load_manifest(root)
        verify_completed_artifacts(root, manifest)
        stage = manifest["current_stage"]
        if stage not in allowed:
            raise ValueError(f"current stage {stage} does not accept this operation")
        stage_state = manifest["stages"].get(stage, {})
        if stage_state.get("status") != "in_progress":
            raise ValueError(f"current stage {stage} is not marked in_progress")
        expected_actor = stage_state.get("actor")
        if args.actor != expected_actor:
            raise PermissionError(f"stage {stage} requires actor {expected_actor}; received {args.actor}")
        path = artifact_path(root, stage_state["artifact"])
        initialize_artifact(path, stage)
        yield root, path, stage, manifest


def append_ledger_event(path: Path, event: dict, actor: str, prefix: str) -> dict:
    actor = identifier(actor, "actor")
    created: Dict[str, Any] = {}

    def append(value):
        events = value.setdefault("events", [])
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        previous = events[-1].get("event_sha256") if events else None
        sequence = len(events) + 1
        record = dict(event)
        record.update({
            "id": f"{prefix}-{sequence:04d}",
            "actor": actor,
            "recorded_at": utc_now(),
            "previous_event_sha256": previous,
        })
        record["event_sha256"] = canonical_sha256(record)
        events.append(record)
        created.update(record)
        return value

    locked_json_update(path, append, {})
    return created


def current_finding(path: Path, qualified: str) -> dict:
    artifact = read_json(path)
    matches = [item for item in artifact.get("findings", []) if item.get("id") == qualified]
    if len(matches) != 1:
        raise ValueError("finding ID must identify exactly one current finding")
    effective = dict(matches[0])
    effective["resolved"] = False
    for event in artifact.get("events", []):
        if event.get("finding_id") != qualified:
            continue
        if event.get("event_type") == "amendment":
            for field, change in event.get("changes", {}).items():
                effective[field] = change.get("to")
        elif event.get("event_type") == "resolution_verification":
            effective["resolved"] = event.get("outcome") == "resolved"
            effective["resolution"] = event.get("resolution")
    return effective


def command_finding(args):
    with stage_path(args, AUDIT_STAGES) as (root, path, stage, _):
        from workflow import completed_artifact, discovery_maps, synthesized_statements

        kind = required_text(args.kind, "kind")
        if kind not in FINDING_KINDS:
            raise ValueError(f"unsupported finding kind: {kind}")
        subtype = required_text(args.subtype, "other subtype") if kind == "other" else None
        scopes = [identifier(item, "scope ID") for item in args.scope]
        if len(scopes) != len(set(scopes)):
            raise ValueError("scope IDs must be unique")
        maps = discovery_maps(root)
        valid_targets = {"RUN"} | set(maps["assumptions"]) | set(maps["targets"]) | set(maps["obligations"])
        discovery = completed_artifact(root, "discovery")
        exploration = completed_artifact(root, "exploration")
        valid_targets.update(
            item["id"] for item in discovery.get("definitions", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
        valid_targets.update(
            item["id"] for item in exploration.get("probes", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
        if stage == "final_adversarial_audit":
            valid_targets.update(synthesized_statements(root))
        target = identifier(args.target, "target ID")
        if target not in valid_targets:
            raise ValueError(f"finding targets unknown run artifact: {target}")
        unknown_scope = [item for item in scopes if item not in valid_targets]
        if unknown_scope:
            raise ValueError(f"finding contains unknown affected scope IDs: {unknown_scope}")
        record = {
            "id": finding_id(args.id, stage),
            "target_id": target,
            "kind": kind,
            "subtype": subtype,
            "severity": args.severity,
            "description": required_text(args.description, "description"),
            "attack_method": required_text(args.attack_method, "attack method"),
            "evidence": {"summary": required_text(args.evidence, "evidence")},
            "source": evidence_source(args.workspace, args.source_path, args.source_location, root),
            "resolution_condition": required_text(args.resolution_condition, "resolution condition"),
            "scope_affected": sorted(scopes),
            "resolved": False,
        }
        if args.evidence_file:
            record["evidence"].update(
                workspace_evidence_file(args.workspace, args.evidence_file, "evidence file")
            )
        append_json_record(path, "findings", record, actor=args.actor)
    print(json.dumps({"stage": stage, "finding": record}, indent=2))


def command_amend(args):
    with stage_path(args, AUDIT_STAGES) as (_, path, stage, _):
        qualified = finding_id(args.id, stage)
        effective = current_finding(path, qualified)
        if effective.get("resolved"):
            raise ValueError("resolved findings cannot be amended")
        changes = {}
        for field in ("severity", "description", "resolution_condition"):
            supplied = getattr(args, field)
            if supplied is not None:
                updated = required_text(supplied, field.replace("_", " "))
                if updated != effective.get(field):
                    changes[field] = {"from": effective.get(field), "to": updated}
        if not changes:
            raise ValueError("amendment must change severity, description, or resolution condition")
        event = append_ledger_event(path, {
            "event_type": "amendment",
            "finding_id": qualified,
            "reason": required_text(args.reason, "amendment reason"),
            "changes": changes,
        }, args.actor, "AMEND")
    print(json.dumps({"stage": stage, "event": event}, indent=2))


def command_resolve(args):
    """Append verification that a finding was false or already answered; never record a repair."""
    with stage_path(args, AUDIT_STAGES) as (_, path, stage, _):
        qualified = finding_id(args.id, stage)
        effective = current_finding(path, qualified)
        if effective.get("resolved"):
            raise ValueError("finding is already resolved")
        evidence = workspace_evidence_file(args.workspace, args.evidence_file, "resolution evidence")
        event = append_ledger_event(path, {
            "event_type": "resolution_verification",
            "finding_id": qualified,
            "outcome": "resolved",
            "resolution_type": args.resolution_type,
            "resolution": required_text(args.resolution, "resolution"),
            "verification": required_text(args.verification, "verification"),
            "verification_mode": args.verification_mode,
            "evidence": evidence,
        }, args.actor, "VERIFY")
    print(json.dumps({"stage": stage, "event": event}, indent=2))


def ancestor_run(workspace: Path, current_manifest: dict, origin_run_id: str) -> Path:
    parent = current_manifest.get("parent_run_id")
    visited = set()
    while parent:
        parent = identifier(parent, "parent run ID")
        if parent in visited:
            raise ValueError("run ancestry contains a cycle")
        visited.add(parent)
        candidate = safe_run_path(workspace, parent)
        manifest = load_manifest(candidate)
        if parent == origin_run_id:
            return candidate
        parent = manifest.get("parent_run_id")
    raise ValueError("origin run must be an ancestor of the selected repair run")


def origin_finding(origin: Path, finding: str) -> dict:
    matches = []
    manifest = load_manifest(origin)
    verify_completed_artifacts(origin, manifest)
    for stage in sorted(AUDIT_STAGES):
        state = manifest.get("stages", {}).get(stage, {})
        if state.get("status") != "completed":
            continue
        artifact = read_json(artifact_path(origin, state["artifact"]))
        matches.extend({
            "finding": item,
            "audit_stage": stage,
            "audit_sha256": state["evidence_sha256"],
        } for item in artifact.get("findings", []) if item.get("id") == finding)
    if len(matches) != 1:
        raise ValueError("origin finding must identify exactly one completed ancestor finding")
    return matches[0]


def command_verify_repair(args):
    with stage_path(args, AUDIT_STAGES) as (root, path, stage, manifest):
        origin_id = identifier(args.origin_run, "origin run ID")
        origin = ancestor_run(Path(args.workspace).resolve(), manifest, origin_id)
        origin_record = origin_finding(origin, identifier(args.finding, "finding ID"))
        original = origin_record["finding"]
        repaired = workspace_evidence_file(args.workspace, args.repaired_path, "repaired artifact")
        repaired_path = workspace_path(Path(args.workspace).resolve(), repaired["path"])
        try:
            repaired_path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("repaired artifact must belong to the selected child run") from exc
        event = append_ledger_event(path, {
            "event_type": "cross_run_repair_verification",
            "origin_run_id": origin_id,
            "origin_finding_id": original["id"],
            "origin_target_id": original["target_id"],
            "origin_audit_stage": origin_record["audit_stage"],
            "origin_audit_sha256": origin_record["audit_sha256"],
            "origin_finding_sha256": original.get("_provenance", {}).get("record_sha256"),
            "repair_run_id": manifest["run_id"],
            "outcome": args.outcome,
            "verification": required_text(args.verification, "verification"),
            "verification_mode": args.verification_mode,
            "repaired_artifact": repaired,
        }, args.actor, "REPAIR")
    print(json.dumps({"stage": stage, "event": event}, indent=2))


def command_decision(args):
    with stage_path(args, {"governance_review"}) as (root, path, stage, _):
        from workflow import MATHEMATICAL_FATAL_KINDS, audit_findings

        finding_name = identifier(args.finding, "finding ID")
        findings = {item["id"]: item for item in audit_findings(root, "local_adversarial_audit")}
        if finding_name not in findings:
            raise ValueError(f"governance decision targets unknown finding: {finding_name}")
        target = findings[finding_name]
        if args.action == "cleared" and not target["resolved"]:
            raise ValueError("unresolved finding cannot be cleared")
        if args.action == "invalidated" and (
            target["resolved"] or target["severity"] != "fatal"
            or target["kind"] not in MATHEMATICAL_FATAL_KINDS
        ):
            raise ValueError("invalidation requires unresolved fatal mathematical evidence")
        record = {
            "finding_id": finding_name,
            "action": args.action,
            "reason": required_text(args.reason, "reason"),
        }
        append_json_record(path, "decisions", record, actor=args.actor, id_key="finding_id")
    print(json.dumps({"stage": stage, "decision": record}, indent=2))


def command_arbiter(args):
    with stage_path(args, {"arbiter"}) as (root, path, stage, _):
        from workflow import (
            ACCEPTED_DECISIONS, MATHEMATICAL_FATAL_KINDS, all_findings,
            statement_blockers, statement_targets, synthesized_statements,
        )
        from proof_store import validate_proof_index

        statement_id = identifier(args.statement, "statement ID")
        statements = synthesized_statements(root)
        if statement_id not in statements:
            raise ValueError(f"arbiter decision targets unknown statement: {statement_id}")
        findings = all_findings(root)
        by_id = {item["id"]: item for item in findings}
        addressed = [identifier(item, "finding ID") for item in args.findings]
        if len(addressed) != len(set(addressed)):
            raise ValueError("findings addressed must be unique")
        unknown = [item for item in addressed if item not in by_id]
        if unknown:
            raise ValueError(f"arbiter decision addresses unknown findings: {unknown}")
        proofs = validate_proof_index(root)
        targets = statement_targets(
            statements[statement_id], proofs, include_provenance=False
        )
        unrelated = [item for item in addressed if (
            by_id[item]["target_id"] not in targets
            and not bool(targets & set(by_id[item].get("scope_affected", [])))
        )]
        if unrelated:
            raise ValueError(f"arbiter decision addresses unrelated findings: {unrelated}")
        blockers = statement_blockers(
            statements[statement_id], findings, proofs, include_provenance=False
        )
        if args.status in ACCEPTED_DECISIONS and blockers:
            raise ValueError(f"accepted statement has open blockers: {[item['id'] for item in blockers]}")
        if args.status == "invalid" and not any(
            item["id"] in addressed and item["severity"] == "fatal"
            and item["kind"] in MATHEMATICAL_FATAL_KINDS for item in blockers
        ):
            raise ValueError("invalid status requires addressed unresolved fatal mathematical evidence")
        if args.status == "repair_requested" and not blockers:
            raise ValueError("repair_requested status requires an open blocker")
        if args.weakened_form and args.status not in ACCEPTED_DECISIONS:
            raise ValueError("weakened_form requires an accepted decision status")
        record = {
            "statement_id": statement_id,
            "status": args.status,
            "reason": required_text(args.reason, "reason"),
            "weakened_form": args.weakened_form or None,
            "findings_addressed": addressed,
        }
        append_json_record(path, "decisions", record, actor=args.actor, id_key="statement_id")
    print(json.dumps({"stage": stage, "decision": record}, indent=2))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    result.add_argument("--actor", required=True)
    commands = result.add_subparsers(dest="command", required=True)

    summary = commands.add_parser("record-attack-summary")
    summary.add_argument("--targets", nargs="+", required=True)
    summary.add_argument("--attack-methods", nargs="+", required=True)
    summary.add_argument("--evidence-files", nargs="+", required=True)
    summary.add_argument(
        "--conclusion", required=True,
        choices=("findings_recorded", "no_findings_after_attack"),
    )
    summary.add_argument("--rationale", required=True)
    summary.set_defaults(function=command_attack_summary)

    revise_summary = commands.add_parser("revise-attack-summary")
    revise_summary.add_argument("--targets", nargs="+", required=True)
    revise_summary.add_argument("--attack-methods", nargs="+", required=True)
    revise_summary.add_argument("--evidence-files", nargs="+", required=True)
    revise_summary.add_argument(
        "--conclusion", required=True,
        choices=("findings_recorded", "no_findings_after_attack"),
    )
    revise_summary.add_argument("--rationale", required=True)
    revise_summary.add_argument("--reason", required=True)
    revise_summary.set_defaults(function=command_revise_attack_summary)

    finding = commands.add_parser("add")
    finding.add_argument("--id", required=True)
    finding.add_argument("--target", required=True)
    finding.add_argument("--kind", required=True, choices=sorted(FINDING_KINDS))
    finding.add_argument("--subtype", default="")
    finding.add_argument("--severity", required=True, choices=("minor", "major", "fatal"))
    finding.add_argument("--description", required=True)
    finding.add_argument("--attack-method", required=True)
    finding.add_argument("--evidence", required=True)
    finding.add_argument("--evidence-file")
    finding.add_argument("--source-path", required=True)
    finding.add_argument("--source-location", required=True)
    finding.add_argument("--resolution-condition", required=True)
    finding.add_argument("--scope", nargs="*", default=[])
    finding.set_defaults(function=command_finding)

    amend = commands.add_parser("amend")
    amend.add_argument("--id", required=True)
    amend.add_argument("--reason", required=True)
    amend.add_argument("--severity", choices=("minor", "major", "fatal"))
    amend.add_argument("--description")
    amend.add_argument("--resolution-condition")
    amend.set_defaults(function=command_amend)

    resolve = commands.add_parser("resolve")
    resolve.add_argument("--id", required=True)
    resolve.add_argument("--resolution-type", required=True, choices=sorted(RESOLUTION_TYPES))
    resolve.add_argument("--resolution", required=True)
    resolve.add_argument("--verification", required=True)
    resolve.add_argument("--verification-mode", required=True, choices=sorted(VERIFICATION_MODES))
    resolve.add_argument("--evidence-file", required=True)
    resolve.set_defaults(function=command_resolve)

    repair = commands.add_parser("verify-repair")
    repair.add_argument("--origin-run", required=True)
    repair.add_argument("--finding", required=True)
    repair.add_argument("--repaired-path", required=True)
    repair.add_argument("--outcome", required=True, choices=("resolved", "unresolved"))
    repair.add_argument("--verification", required=True)
    repair.add_argument("--verification-mode", required=True, choices=sorted(VERIFICATION_MODES))
    repair.set_defaults(function=command_verify_repair)

    decision = commands.add_parser("decide")
    decision.add_argument("--finding", required=True)
    decision.add_argument("--action", required=True, choices=sorted(GOVERNANCE_ACTIONS))
    decision.add_argument("--reason", required=True)
    decision.set_defaults(function=command_decision)

    arbiter = commands.add_parser("arbiter-decision")
    arbiter.add_argument("--statement", required=True)
    arbiter.add_argument("--status", required=True, choices=(
        "theorem_ready", "proposition_ready", "repair_requested",
        "conjecture_only", "rejected", "invalid",
    ))
    arbiter.add_argument("--reason", required=True)
    arbiter.add_argument("--weakened-form", default="")
    arbiter.add_argument("--findings", nargs="*", default=[])
    arbiter.set_defaults(function=command_arbiter)
    return result


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, PermissionError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
