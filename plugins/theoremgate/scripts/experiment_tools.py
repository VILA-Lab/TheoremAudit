#!/usr/bin/env python3
"""Govern experiments, bounded inspected CPU runs, and publication-quality figures."""

from __future__ import annotations

import argparse
import ast
import copy
import csv
import hashlib
import json
import re
from pathlib import Path

from experiment_schema import validate_experiment, validate_strategy
from figure_quality import SIZE_CLASSES, audit_figure
from state_store import file_sha256, read_json, utc_now
from tool_utils import contained, identifier, load_object_argument, locked_json_update, paper_dir


INDEX_SCHEMA_VERSION = 2
FORBIDDEN_IMPORTS = {
    "ctypes", "ftplib", "http", "importlib", "multiprocessing", "paramiko", "requests",
    "shutil", "socket", "subprocess", "urllib",
}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_ATTRIBUTES = {
    "popen", "remove", "rmdir", "spawnl", "spawnv", "system", "unlink",
}
FIGURE_LABEL = re.compile(r"^fig:[A-Za-z0-9][A-Za-z0-9:_.-]{0,79}$")
ONE_COLUMN_VENUE_FORMATS = {"iclr", "jmlr", "tmlr", "colt"}
VISUAL_SCORE_FIELDS = (
    "visual_hierarchy", "typography", "color_design", "layout_balance",
    "data_ink_efficiency", "statistical_communication", "caption_alignment",
    "cross_figure_consistency",
)
VISUAL_BOOLEAN_FIELDS = (
    "legible_at_paper_size", "labels_correct", "palette_accessible", "no_clipping",
    "notation_consistent", "effect_readable", "uncertainty_not_dominant",
    "single_scientific_question",
)
VISUAL_REJECTION_FIELDS = (
    "crowded_legends", "unbalanced_panels", "tiny_axes_or_text", "excessive_whitespace",
)


def professional_visual_pass(review: dict) -> bool:
    scores = review["design_scores"]
    overall = sum(float(scores[field]) for field in VISUAL_SCORE_FIELDS) / len(VISUAL_SCORE_FIELDS)
    return (
        all(review[field] for field in VISUAL_BOOLEAN_FIELDS)
        and not any(review[field] for field in VISUAL_REJECTION_FIELDS)
        and not review.get("blocking_tradeoffs")
        and min(float(scores[field]) for field in VISUAL_SCORE_FIELDS) >= 4.0
        and overall >= 4.25
    )


def _canonical_hash(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluation_hash(evaluation: dict) -> str:
    return _canonical_hash({key: value for key, value in evaluation.items() if key != "evaluation_sha256"})


def figure_review_hash(review: dict) -> str:
    return _canonical_hash({key: value for key, value in review.items() if key != "review_sha256"})


def _legacy_review_predecessor(review: dict, figure_id: str, history: list) -> dict:
    predecessors = [item["figure"] for item in history if item.get("figure", {}).get("figure_id") == figure_id]
    if not predecessors:
        raise ValueError("figure review hash repair requires an archived predecessor")
    previous = predecessors[-1]
    old_review = previous.get("visual_review", {})
    if previous.get("record_sha256") != _canonical_hash({
        key: value for key, value in previous.items() if key != "record_sha256"
    }) or old_review.get("review_sha256") != figure_review_hash(old_review):
        raise ValueError("preceding figure review has an unresolved integrity error")
    if review.get("review_sha256") == figure_review_hash(review) or review.get("review_sha256") != _canonical_hash({
        **review, "review_sha256": old_review["review_sha256"]
    }):
        raise ValueError("figure review hash mismatch does not match the known legacy defect; repair refused")
    return previous


def validate_figure_review_hash(figure: dict, history: list) -> None:
    review = figure.get("visual_review", {})
    if review.get("review_sha256") != figure_review_hash(review):
        raise ValueError(f"main figure visual review was modified: {figure.get('figure_id')}")
    if "review_hash_repair" not in figure:
        return
    receipt = figure["review_hash_repair"]
    if not isinstance(receipt, dict) or receipt.get("repair_sha256") != _canonical_hash({
        key: value for key, value in receipt.items() if key != "repair_sha256"
    }):
        raise ValueError("figure review hash repair receipt was modified")
    original = receipt.get("original_review")
    if (
        receipt.get("schema_version") != 1
        or receipt.get("method") != "legacy_previous_hash_in_payload"
        or receipt.get("figure_id") != figure.get("figure_id")
        or not isinstance(original, dict)
        or any(not isinstance(receipt.get(field), str) or not receipt[field].strip()
               for field in ("actor", "reason", "repaired_at"))
    ):
        raise ValueError("invalid figure review hash repair receipt")
    previous = _legacy_review_predecessor(original, figure["figure_id"], history)
    if (
        receipt.get("previous_figure_sha256") != previous["record_sha256"]
        or receipt.get("corrected_sha256") != figure_review_hash(original)
        or review != {**original, "review_sha256": figure_review_hash(original)}
    ):
        raise ValueError("figure review hash repair changed the reviewed content")


def validate_evaluation_hashes(experiment: dict) -> None:
    evaluations = [*experiment.get("evaluation_history", []), experiment.get("evaluation")]
    for evaluation in evaluations:
        if evaluation is None:
            continue
        if not isinstance(evaluation, dict) or evaluation.get("evaluation_sha256") != evaluation_hash(evaluation):
            raise ValueError(f"experiment evaluation record was modified: {experiment.get('id')}")
    repairs = experiment.get("evaluation_hash_repairs", [])
    if not isinstance(repairs, list):
        raise ValueError("evaluation hash repairs must be a list")
    repaired_revisions = set()
    for repair in repairs:
        if not isinstance(repair, dict) or repair.get("repair_sha256") != _canonical_hash({
            key: value for key, value in repair.items() if key != "repair_sha256"
        }):
            raise ValueError("evaluation hash repair receipt was modified")
        revision = repair.get("evaluation_revision")
        if (
            repair.get("schema_version") != 1
            or repair.get("method") != "legacy_previous_hash_in_payload"
            or repair.get("experiment_id") != experiment.get("id")
            or not isinstance(revision, int) or isinstance(revision, bool) or revision < 2
            or revision in repaired_revisions
            or any(not isinstance(repair.get(field), str) or not repair[field].strip()
                   for field in ("actor", "reason", "repaired_at"))
        ):
            raise ValueError("invalid evaluation hash repair receipt")
        repaired_revisions.add(revision)
        matching = [item for item in evaluations if item and item.get("evaluation_revision") == revision]
        preceding = [item for item in evaluations if item and item.get("evaluation_revision") == revision - 1]
        original = repair.get("original_evaluation")
        if len(matching) != 1 or len(preceding) != 1 or not isinstance(original, dict):
            raise ValueError("evaluation hash repair lacks its original record or revision chain")
        corrected = {**original, "evaluation_sha256": evaluation_hash(original)}
        previous_hash = preceding[0]["evaluation_sha256"]
        legacy_hash = _canonical_hash({**original, "evaluation_sha256": previous_hash})
        if (
            matching[0] != corrected
            or repair.get("corrected_sha256") != corrected["evaluation_sha256"]
            or repair.get("previous_evaluation_sha256") != previous_hash
            or repair.get("original_record_sha256") != _canonical_hash(original)
            or original.get("evaluation_sha256") != legacy_hash
            or original.get("evaluation_sha256") == corrected["evaluation_sha256"]
        ):
            raise ValueError("evaluation hash repair does not reproduce the known legacy defect")


def _actor(args) -> str:
    return identifier(getattr(args, "actor", "experimenter"), "actor")


def _require_stage(root: Path, actor: str) -> None:
    manifest_path = root / "paper_run.json"
    if not manifest_path.is_file():
        return  # Compatibility for isolated tool use and pre-controller runs.
    manifest = read_json(manifest_path)
    if manifest.get("status") != "active" or manifest.get("current_stage") != "empirical_validation":
        raise ValueError("experiment evidence can change only during the empirical_validation stage")
    expected = manifest.get("stages", {}).get("empirical_validation", {}).get("actor")
    if expected and actor != expected:
        raise PermissionError(f"empirical_validation requires actor {expected}")


def inspect_code(path: Path) -> list[str]:
    """Return conservative findings; this is a guardrail, not a security proof."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings, forbidden_names = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    findings.append(f"forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module in FORBIDDEN_IMPORTS:
                findings.append(f"forbidden import: {node.module}")
            if module == "os":
                forbidden_names.update(
                    alias.asname or alias.name for alias in node.names if alias.name in FORBIDDEN_ATTRIBUTES
                )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS | forbidden_names:
                findings.append(f"forbidden dynamic/process call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRIBUTES:
                findings.append(f"forbidden process/destructive call: {node.func.attr}")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    findings.append("forbidden shell=True execution")
                if keyword.arg == "download" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    findings.append("forbidden runtime download=True")
    return sorted(set(findings))


def index_path(root: Path) -> Path:
    return root / "experiments" / "index.json"


def _empty_index() -> dict:
    now = utc_now()
    return {
        "schema_version": INDEX_SCHEMA_VERSION, "artifact": "experiment_evidence_registry",
        "created_at": now, "updated_at": now, "revision": 0, "strategy": None,
        "strategy_history": [], "experiments": [], "inspections": [], "executions": [],
        "figures": [], "figure_history": [], "events": [],
    }


def _upgrade_index(value: dict) -> dict:
    if value.get("schema_version") == INDEX_SCHEMA_VERSION:
        return value
    upgraded = _empty_index()
    if isinstance(value, dict):
        upgraded["strategy"] = value.get("strategy")
        upgraded["experiments"] = list(value.get("experiments") or [])
        upgraded["figures"] = list(value.get("figures") or [])
    return upgraded


def load_index(root: Path) -> dict:
    path = index_path(root)
    return _upgrade_index(read_json(path)) if path.exists() else _empty_index()


def _event(value: dict, kind: str, actor: str, details: dict) -> None:
    payload = {"kind": kind, "actor": actor, "recorded_at": utc_now(), "details": details}
    payload["event_id"] = f"EVT-{len(value['events']) + 1:05d}"
    payload["event_sha256"] = _canonical_hash(payload)
    value["events"].append(payload)
    value["revision"] = int(value.get("revision", 0)) + 1
    value["updated_at"] = utc_now()


def _update(root: Path, transform):
    def apply(value):
        value = _upgrade_index(value)
        return transform(value)
    return locked_json_update(index_path(root), apply, _empty_index())


def accepted_statement_ids(root: Path) -> set[str]:
    bundle = read_json(root.parent / "artifacts" / "theory_bundle.json")
    selected = bundle.get("paper_route", {}).get("selected_statement_ids")
    if selected:
        return set(selected)
    return {
        item["effective_statement"]["id"] for item in bundle.get("accepted_statements", [])
        if isinstance(item, dict) and isinstance(item.get("effective_statement"), dict)
    }


def accepted_assumption_ids(root: Path) -> set[str]:
    bundle = read_json(root.parent / "artifacts" / "theory_bundle.json")
    return {
        assumption
        for item in bundle.get("accepted_statements", []) if isinstance(item, dict)
        for assumption in item.get("effective_statement", {}).get("assumptions_used", [])
        if isinstance(assumption, str)
    }


def _experiment(value: dict, experiment_id: str) -> dict:
    matches = [item for item in value["experiments"] if item.get("id") == experiment_id]
    if len(matches) != 1:
        raise ValueError("experiment ID must identify exactly one proposal")
    return matches[0]


def command_inspect(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    path = contained(root, args.script)
    if not path.is_file() or path.suffix != ".py":
        raise ValueError("experiment script must be an existing .py file inside the paper directory")
    current = load_index(root)
    experiment_id = getattr(args, "id", None)
    if not experiment_id and len(current["experiments"]) == 1:
        experiment_id = current["experiments"][0]["id"]
    experiment_id = identifier(experiment_id or "", "experiment ID")
    _experiment(current, experiment_id)
    findings = inspect_code(path)
    managed = current.get("strategy", {}).get("schema_version") == 2
    if managed:
        from experiment_runtime import cpu_findings
        findings += cpu_findings(path)
    dependency_hashes = {}
    for relative in getattr(args, "dependency", None) or []:
        dependency = contained(root, relative)
        if not dependency.is_file():
            raise ValueError(f"inspection dependency is missing: {relative}")
        dependency_hashes[relative] = file_sha256(dependency)
        if dependency.suffix == ".py":
            findings += inspect_code(dependency)
            if managed:
                findings += cpu_findings(dependency)
    report = {
        "inspection_id": f"INS-{len(current['inspections']) + 1:05d}",
        "experiment_id": experiment_id, "script_path": args.script,
        "script_sha256": file_sha256(path), "inspected_at": utc_now(), "actor": actor,
        "dependency_sha256": dependency_hashes,
        "safe_for_manual_execution": not findings, "findings": findings,
        "notice": "Static inspection is a guardrail, not a sandbox or proof of safety.",
    }
    report["report_sha256"] = _canonical_hash(report)

    def transform(value):
        _experiment(value, experiment_id)
        if any(item.get("inspection_id") == report["inspection_id"] for item in value["inspections"]):
            raise ValueError("experiment registry changed concurrently; inspect again")
        value["inspections"].append(report)
        _event(value, "script_inspected", actor, {"inspection_id": report["inspection_id"]})
        return value
    _update(root, transform)
    print(json.dumps(report, indent=2))


def command_propose(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    record = load_object_argument(args.input, Path(args.workspace))
    experiment_id = identifier(record.get("id", ""), "experiment ID")
    record["status"] = "proposed"
    record.setdefault("evaluation_history", [])
    validate_experiment(record, accepted_statement_ids(root))
    known_assumptions = accepted_assumption_ids(root)
    if known_assumptions and any(item not in known_assumptions for item in record["assumptions_tested"]):
        raise ValueError("experiment assumptions_tested must come from accepted theorem assumptions")

    def transform(value):
        if not isinstance(value.get("strategy"), dict):
            raise ValueError("write the experiment strategy before proposing experiments")
        if experiment_id not in value["strategy"]["selected_experiment_ids"]:
            raise ValueError("only strategy-selected experiments may be proposed")
        if value["strategy"].get("schema_version") == 2:
            candidate = next(c for c in value["strategy"]["candidate_experiments"] if c["id"] == experiment_id)
            record["preflight"] = candidate["preflight"]
            if "real_system" in record["tags"] and record["preflight"]["evidence_kind"] != "real_data":
                raise ValueError("synthetic or semi-synthetic evidence cannot be tagged real_system")
        if any(item.get("id") == experiment_id for item in value["experiments"]):
            raise ValueError(f"duplicate experiment ID: {experiment_id}")
        value["experiments"].append(record)
        _event(value, "experiment_proposed", actor, {"experiment_id": experiment_id})
        return value
    _update(root, transform)
    print(json.dumps({"proposed": experiment_id}, indent=2))


def _validate_result_file(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"raw JSON results are invalid: {exc}") from exc
        if data in ({}, [], None):
            raise ValueError("raw JSON results cannot be empty")
        return {"format": "json", "top_level_type": type(data).__name__}
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"raw CSV results are invalid: {exc}") from exc
    if len(rows) < 2 or not rows[0] or any(not cell.strip() for cell in rows[0]):
        raise ValueError("raw CSV results require a non-empty header and at least one data row")
    if any(len(row) != len(rows[0]) for row in rows[1:]):
        raise ValueError("raw CSV results have inconsistent row widths")
    return {"format": "csv", "columns": rows[0], "rows": len(rows) - 1}


def command_record_execution(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    evidence = load_object_argument(args.input, Path(args.workspace))
    experiment_id = identifier(args.id, "experiment ID")
    current = load_index(root)
    _experiment(current, experiment_id)
    inspections = [item for item in current["inspections"] if item["experiment_id"] == experiment_id]
    if not inspections or not inspections[-1]["safe_for_manual_execution"]:
        raise ValueError("execution requires a latest safe script inspection")
    inspection = inspections[-1]
    managed = None
    if current.get("strategy", {}).get("schema_version") == 2:
        from experiment_runtime import verify_receipt
        managed = verify_receipt(root, evidence, inspection)
    script = contained(root, inspection["script_path"])
    if file_sha256(script) != inspection["script_sha256"]:
        raise ValueError("experiment script changed after inspection; inspect it again")
    for relative, digest in inspection.get("dependency_sha256", {}).items():
        dependency = contained(root, relative)
        if not dependency.is_file() or file_sha256(dependency) != digest:
            raise ValueError(f"experiment dependency changed after inspection: {relative}")
    command = evidence.get("command")
    if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
        raise ValueError("execution command must be a non-empty JSON list of strings")
    exit_code = evidence.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise ValueError("execution exit_code must be an integer")
    environment = evidence.get("environment")
    if not isinstance(environment, dict) or not environment:
        raise ValueError("execution environment must be a non-empty object")
    output_paths = evidence.get("output_paths")
    if not isinstance(output_paths, list) or not output_paths:
        raise ValueError("execution output_paths must be a non-empty list")
    artifact_hashes = {}
    for relative in output_paths:
        path = contained(root, relative)
        if not path.is_file():
            raise ValueError(f"execution output is missing: {relative}")
        artifact_hashes[relative] = file_sha256(path)
    log_hashes = {}
    for field in ("stdout_path", "stderr_path"):
        relative = evidence.get(field)
        if not isinstance(relative, str) or not relative:
            raise ValueError(f"execution requires {field}")
        path = contained(root, relative)
        if not path.is_file():
            raise ValueError(f"execution log is missing: {relative}")
        log_hashes[relative] = file_sha256(path)
    for field in ("started_at", "finished_at"):
        if not isinstance(evidence.get(field), str) or not evidence[field].strip():
            raise ValueError(f"execution requires {field}")
    execution = {
        "execution_id": f"RUN-{experiment_id}-{len([item for item in current['executions'] if item['experiment_id'] == experiment_id]) + 1:03d}",
        "experiment_id": experiment_id, "inspection_id": inspection["inspection_id"],
        "script_path": inspection["script_path"], "script_sha256": inspection["script_sha256"],
        "command": command, "started_at": evidence["started_at"], "finished_at": evidence["finished_at"],
        "exit_code": exit_code, "status": "completed" if exit_code == 0 else "failed",
        "environment": environment, "output_paths": output_paths, "artifact_sha256": artifact_hashes,
        "stdout_path": evidence["stdout_path"], "stderr_path": evidence["stderr_path"],
        "log_sha256": log_hashes, "recorded_at": utc_now(), "actor": actor,
    }
    if managed is not None:
        execution.update({"managed_receipt_path": evidence["managed_receipt_path"],
                          "managed_receipt_sha256": evidence["managed_receipt_sha256"],
                          "pilot": managed["pilot"], "resource_sha256": managed["resource_sha256"]})
    execution["record_sha256"] = _canonical_hash(execution)

    def transform(value):
        _experiment(value, experiment_id)
        if any(item.get("execution_id") == execution["execution_id"] for item in value["executions"]):
            raise ValueError("experiment registry changed concurrently; record execution again")
        value["executions"].append(execution)
        _event(value, "execution_recorded", actor, {"execution_id": execution["execution_id"]})
        return value
    _update(root, transform)
    print(json.dumps(execution, indent=2))


def command_mark_blocked(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    blockage = load_object_argument(args.input, Path(args.workspace))
    for field in ("reason", "attempted", "required_resource", "claim_assessment"):
        if not isinstance(blockage.get(field), str) or not blockage[field].strip():
            raise ValueError(f"blocked experiment requires {field}")
    blockage.update({"recorded_at": utc_now(), "actor": actor})
    blockage["record_sha256"] = _canonical_hash(blockage)

    def transform(value):
        experiment = _experiment(value, args.id)
        if experiment.get("status") not in {"proposed", "planned", "running"}:
            raise ValueError("only an unfinished experiment can be marked blocked")
        experiment["status"] = "blocked"
        experiment["blockage"] = blockage
        _event(value, "experiment_blocked", actor, {"experiment_id": args.id})
        return value
    _update(root, transform)
    print(json.dumps({"experiment_id": args.id, "status": "blocked"}, indent=2))


def command_evaluate(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    value = load_index(root)
    experiment = _experiment(value, args.id)
    executions = [item for item in value["executions"] if item["experiment_id"] == args.id]
    if not executions:
        raise ValueError("evaluation requires a recorded execution")
    execution = executions[-1]
    if execution.get("pilot"):
        raise ValueError("a feasibility pilot cannot be used as the full experiment's scientific evaluation")
    evaluation = load_object_argument(args.input, Path(args.workspace))
    if evaluation.get("verdict") not in {"supports", "contradicts", "inconclusive", "failed"}:
        raise ValueError("verdict must be supports, contradicts, inconclusive, or failed")
    for field in ("summary", "uncertainty", "raw_results_path", "configuration", "limitations", "claim_assessment"):
        if field not in evaluation:
            raise ValueError(f"evaluation is missing {field}")
    results = contained(root, evaluation["raw_results_path"])
    if not results.is_file() or results.suffix.lower() not in {".json", ".csv"}:
        raise ValueError("raw_results_path must identify JSON or CSV inside the paper directory")
    if evaluation["raw_results_path"] not in execution["artifact_sha256"]:
        raise ValueError("raw results were not declared by the recorded execution")
    if file_sha256(results) != execution["artifact_sha256"][evaluation["raw_results_path"]]:
        raise ValueError("raw results changed after execution was recorded")
    evaluation["raw_results_validation"] = _validate_result_file(results)
    evaluation["raw_results_sha256"] = file_sha256(results)
    configuration = evaluation["configuration"]
    if not isinstance(configuration, dict):
        raise ValueError("evaluation.configuration must be an object")
    if configuration.get("seeds") != experiment["design"]["seeds"]:
        raise ValueError("evaluation configuration seeds must match the proposed design")
    if execution["status"] == "failed" and evaluation["verdict"] != "failed":
        raise ValueError("a failed execution cannot support, contradict, or resolve a claim")
    existing = experiment.get("evaluation")
    replace = getattr(args, "replace", False)
    reason = getattr(args, "reason", "")
    if existing and not replace:
        raise ValueError("experiment already has an evaluation; pass --replace with a reason")
    if existing and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("replacing an evaluation requires --reason")
    next_revision = (existing.get("evaluation_revision", 1) + 1) if existing else 1
    expected_existing_hash = existing.get("evaluation_sha256") if existing else None
    evaluation.update({
        "evaluation_revision": next_revision,
        "execution_id": execution["execution_id"], "evaluated_at": utc_now(), "actor": actor,
        "replacement_reason": reason.strip() if existing else "",
    })
    evaluation["evaluation_sha256"] = evaluation_hash(evaluation)
    status = {"supports": "evaluated", "contradicts": "contradictory", "inconclusive": "inconclusive", "failed": "failed"}[evaluation["verdict"]]

    def transform(index):
        target = _experiment(index, args.id)
        current_hash = target.get("evaluation", {}).get("evaluation_sha256")
        if current_hash != expected_existing_hash:
            raise ValueError("experiment evaluation changed concurrently; reload before evaluating")
        if target.get("evaluation"):
            target.setdefault("evaluation_history", []).append(target["evaluation"])
        target.update({"status": status, "evaluation": evaluation})
        if existing:
            for figure in index["figures"]:
                if figure.get("experiment_id") == args.id:
                    figure["status"] = "stale_after_reevaluation"
                    figure["record_sha256"] = _canonical_hash({
                        key: item for key, item in figure.items() if key != "record_sha256"
                    })
        validate_experiment(target, accepted_statement_ids(root), root, require_final=True)
        validate_evaluation_hashes(target)
        _event(index, "experiment_evaluated", actor, {"experiment_id": args.id, "verdict": evaluation["verdict"]})
        return index
    _update(root, transform)
    print(json.dumps({"evaluated": args.id, "verdict": evaluation["verdict"],
                      "revision": evaluation["evaluation_revision"]}, indent=2))


def command_repair_evaluation_hash(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    revision, reason = args.revision, args.reason.strip()
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 2 or not reason:
        raise ValueError("hash repair requires revision >= 2 and a non-empty reason")
    if not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
        raise ValueError("hash repair requires the expected stored SHA-256")
    result = {}

    def transform(index):
        _require_stage(root, actor)
        target = _experiment(index, args.id)
        evaluations = [*target.get("evaluation_history", []), target.get("evaluation")]
        matching = [item for item in evaluations if item and item.get("evaluation_revision") == revision]
        preceding = [item for item in evaluations if item and item.get("evaluation_revision") == revision - 1]
        if len(matching) != 1 or len(preceding) != 1:
            raise ValueError("hash repair requires a unique revision and its immediate predecessor")
        evaluation, previous = matching[0], preceding[0]
        prior_repairs = target.get("evaluation_hash_repairs", [])
        if any(item.get("evaluation_revision") == revision and
               item.get("original_evaluation", {}).get("evaluation_sha256") == args.expected_sha256
               for item in prior_repairs):
            validate_evaluation_hashes(target)
            result.update({"repaired": False, "already_repaired": True})
            return index
        if evaluation.get("evaluation_sha256") != args.expected_sha256:
            raise ValueError("evaluation changed; reload its stored hash before repairing")
        if previous.get("evaluation_sha256") != evaluation_hash(previous):
            raise ValueError("preceding evaluation has an unresolved integrity error")
        corrected_hash = evaluation_hash(evaluation)
        if corrected_hash == args.expected_sha256:
            raise ValueError("evaluation hash is already valid; no repair is needed")
        legacy_hash = _canonical_hash({**evaluation, "evaluation_sha256": previous["evaluation_sha256"]})
        if legacy_hash != args.expected_sha256:
            raise ValueError("hash mismatch does not match the known legacy defect; repair refused")
        executions = [item for item in index["executions"]
                      if item.get("execution_id") == evaluation.get("execution_id")]
        if len(executions) != 1 or executions[0].get("experiment_id") != args.id:
            raise ValueError("evaluation repair requires its registered experiment execution")
        execution = executions[0]
        if execution.get("record_sha256") != _canonical_hash({
            key: value for key, value in execution.items() if key != "record_sha256"
        }) or execution.get("artifact_sha256", {}).get(evaluation.get("raw_results_path")) != evaluation.get("raw_results_sha256"):
            raise ValueError("evaluation repair execution evidence is inconsistent")
        # Preserve the exact malformed record in the same atomic registry transaction.
        original = copy.deepcopy(evaluation)
        receipt = {
            "schema_version": 1, "method": "legacy_previous_hash_in_payload",
            "experiment_id": args.id, "evaluation_revision": revision,
            "actor": actor, "reason": reason, "repaired_at": utc_now(),
            "original_evaluation": original, "original_record_sha256": _canonical_hash(original),
            "previous_evaluation_sha256": previous["evaluation_sha256"],
            "corrected_sha256": corrected_hash,
        }
        receipt["repair_sha256"] = _canonical_hash(receipt)
        evaluation["evaluation_sha256"] = corrected_hash
        target.setdefault("evaluation_hash_repairs", []).append(receipt)
        validate_experiment(target, accepted_statement_ids(root), root, require_final=True)
        validate_evaluation_hashes(target)
        _event(index, "experiment_evaluation_hash_repaired", actor, {
            "experiment_id": args.id, "evaluation_revision": revision,
            "repair_sha256": receipt["repair_sha256"],
        })
        result.update({"repaired": True, "repair_sha256": receipt["repair_sha256"],
                       "corrected_sha256": corrected_hash})
        return index

    _update(root, transform)
    print(json.dumps({"experiment_id": args.id, "revision": revision, **result}, indent=2))


def command_audit_figure(args):
    root = paper_dir(args.workspace, args.run)
    path = contained(root, args.path)
    if not path.is_file():
        raise ValueError("figure does not exist")
    report = audit_figure(path, args.size_class, panels=args.panels, role=args.role)
    report["path"] = args.path
    print(json.dumps(report, indent=2))


def command_repair_figure_review_hash(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    if not args.reason.strip() or not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
        raise ValueError("figure review hash repair requires a reason and expected stored SHA-256")
    result = {}

    def transform(index):
        _require_stage(root, actor)
        figures = [item for item in index["figures"] if item.get("figure_id") == args.figure_id]
        if len(figures) != 1:
            raise ValueError("figure ID must identify exactly one registered figure")
        figure = figures[0]
        if figure.get("record_sha256") != _canonical_hash({
            key: value for key, value in figure.items() if key != "record_sha256"
        }):
            raise ValueError("figure record was modified; hash repair refused")
        history = index.get("figure_history", [])
        existing = figure.get("review_hash_repair", {})
        if existing.get("original_review", {}).get("review_sha256") == args.expected_sha256:
            validate_figure_review_hash(figure, history)
            result.update({"repaired": False, "already_repaired": True})
            return index
        review = figure.get("visual_review", {})
        if review.get("review_sha256") != args.expected_sha256:
            raise ValueError("figure review changed; reload its stored hash before repairing")
        previous = _legacy_review_predecessor(review, args.figure_id, history)
        for path_field, hash_field in (("path", "figure_sha256"), ("results_path", "results_sha256")):
            path = contained(root, figure[path_field])
            if not path.is_file() or file_sha256(path) != figure[hash_field]:
                raise ValueError("figure review repair requires unchanged figure and result files")
        receipt = {
            "schema_version": 1, "method": "legacy_previous_hash_in_payload",
            "figure_id": args.figure_id, "original_review": copy.deepcopy(review),
            "previous_figure_sha256": previous["record_sha256"],
            "corrected_sha256": figure_review_hash(review),
            "actor": actor, "reason": args.reason.strip(), "repaired_at": utc_now(),
        }
        receipt["repair_sha256"] = _canonical_hash(receipt)
        review["review_sha256"] = receipt["corrected_sha256"]
        figure["review_hash_repair"] = receipt
        figure["record_sha256"] = _canonical_hash({key: value for key, value in figure.items() if key != "record_sha256"})
        validate_figure_review_hash(figure, history)
        _event(index, "figure_review_hash_repaired", actor, {
            "figure_id": args.figure_id, "repair_sha256": receipt["repair_sha256"],
        })
        result.update({"repaired": True, "repair_sha256": receipt["repair_sha256"]})
        return index

    _update(root, transform)
    print(json.dumps({"figure_id": args.figure_id, **result}, indent=2))


def command_figure(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    value = load_index(root)
    experiment = _experiment(value, args.id)
    evaluation = experiment.get("evaluation")
    if not isinstance(evaluation, dict) or evaluation.get("verdict") == "failed":
        raise ValueError("figure registration requires a non-failed evaluated experiment")
    path = contained(root, args.path)
    if not path.is_file():
        raise ValueError("figure must exist inside the paper directory")
    if not FIGURE_LABEL.fullmatch(args.label):
        raise ValueError("figure label must use the form fig:descriptive-name")
    if not isinstance(args.caption, str) or len(args.caption.strip()) < 80:
        raise ValueError("figure caption must be publication-ready and at least 80 characters")
    if re.search(r"\b(?:prove[sd]?|proof of)\b", args.caption, re.IGNORECASE):
        raise ValueError("empirical figure captions cannot claim to prove a theorem")
    if not isinstance(args.alt_text, str) or len(args.alt_text.strip()) < 20:
        raise ValueError("figure alt text must describe the visual content")
    multi_panel_justification = getattr(args, "multi_panel_justification", "")
    if args.role == "main" and args.panels > 2:
        raise ValueError(
            "main-paper figures may contain at most two panels; split larger empirical "
            "programs into separate publication-ready figures"
        )
    if args.panels > 1:
        justification = multi_panel_justification.strip() if isinstance(multi_panel_justification, str) else ""
        if len(justification) < 120:
            raise ValueError(
                "multi-panel figures require a substantive --multi-panel-justification "
                "explaining why a single joint view is necessary; use separate single-panel "
                "figures by default"
            )
        if not re.search(
            r"\b(?:same axis|shared axis|paired comparison|direct comparison|side-by-side|joint view|same scale)\b",
            justification,
            re.IGNORECASE,
        ):
            raise ValueError(
                "multi-panel justification must explain the shared scale or direct "
                "comparison that would be lost in separate figures"
            )
    report = audit_figure(path, args.size_class, panels=args.panels, role=args.role)
    if not report["structurally_valid"]:
        raise ValueError(f"figure failed structural audit: {report['errors']}")
    report["path"] = args.path
    results_path = args.results_path or evaluation["raw_results_path"]
    results = contained(root, results_path)
    if not results.is_file() or file_sha256(results) != evaluation["raw_results_sha256"]:
        raise ValueError("figure results must match the evaluated raw evidence")
    conflicts = [item for item in value["figures"] if item.get("label") == args.label or item.get("path") == args.path]
    replace, reason = getattr(args, "replace", False), getattr(args, "reason", "")
    if conflicts and (len(conflicts) != 1 or not replace):
        raise ValueError("figure path and label must be unique; pass --replace for one existing figure")
    if conflicts and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("replacing a figure requires --reason")
    figure_id = conflicts[0]["figure_id"] if conflicts else f"FIG-{len(value['figures']) + 1:04d}"
    record = {
        "figure_id": figure_id, "experiment_id": args.id,
        "path": args.path, "figure_sha256": file_sha256(path), "label": args.label,
        "caption": args.caption.strip(), "alt_text": args.alt_text.strip(),
        "size_class": args.size_class, "role": args.role, "placement": args.placement,
        "panels": args.panels, "results_path": results_path,
        "multi_panel_justification": (
            multi_panel_justification.strip() if args.panels > 1 else ""
        ),
        "results_sha256": evaluation["raw_results_sha256"], "quality_report": report,
        "status": "needs_visual_review", "registered_at": utc_now(), "actor": actor,
        "replacement_reason": reason.strip() if conflicts else "",
    }
    record["record_sha256"] = _canonical_hash(record)

    def transform(index):
        current_conflicts = [
            item for item in index["figures"]
            if item.get("label") == record["label"] or item.get("path") == record["path"]
        ]
        if conflicts:
            if len(current_conflicts) != 1 or current_conflicts[0].get("record_sha256") != conflicts[0].get("record_sha256"):
                raise ValueError("experiment registry changed concurrently; register the figure again")
            position = index["figures"].index(current_conflicts[0])
            index.setdefault("figure_history", []).append({
                "figure": current_conflicts[0], "replaced_at": utc_now(), "actor": actor,
                "reason": reason.strip(),
            })
            index["figures"][position] = record
        else:
            if current_conflicts or any(item.get("figure_id") == record["figure_id"] for item in index["figures"]):
                raise ValueError("experiment registry changed concurrently; register the figure again")
            index["figures"].append(record)
        _event(index, "figure_registered", actor, {"figure_id": record["figure_id"]})
        return index
    _update(root, transform)
    print(json.dumps({"registered": record, "next": "run review-figure after rendering the paper-scale figure"}, indent=2))


def command_review_figure(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    review = load_object_argument(args.input, Path(args.workspace))
    current = load_index(root)
    registered = [
        item for item in current["figures"] if item.get("figure_id") == args.figure_id
    ]
    if len(registered) != 1:
        raise ValueError("figure ID must identify exactly one registered figure")
    registered_figure = registered[0]
    if review.get("schema_version") != 2:
        raise ValueError("professional visual review requires schema_version 2")
    for field in VISUAL_BOOLEAN_FIELDS:
        if not isinstance(review.get(field), bool):
            raise ValueError(f"visual review requires boolean {field}")
    for field in VISUAL_REJECTION_FIELDS:
        if not isinstance(review.get(field), bool):
            raise ValueError(f"visual review requires boolean rejection check {field}")
    scores = review.get("design_scores")
    if not isinstance(scores, dict) or set(scores) != set(VISUAL_SCORE_FIELDS):
        raise ValueError(f"design_scores must contain exactly {list(VISUAL_SCORE_FIELDS)}")
    for field, score in scores.items():
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValueError(f"design score {field} must be between 1 and 5")
    overall = sum(float(scores[field]) for field in VISUAL_SCORE_FIELDS) / len(VISUAL_SCORE_FIELDS)
    declared_overall = review.get("overall_score")
    if not isinstance(declared_overall, (int, float)) or abs(float(declared_overall) - overall) > 0.01:
        raise ValueError("overall_score must equal the mean of design_scores")
    if review.get("independence_mode") not in {"fresh_role_review", "independent_subagent", "external_check"}:
        raise ValueError("visual review requires an independent or fresh-role review mode")
    if not isinstance(review.get("reviewer_identity"), str) or not review["reviewer_identity"].strip():
        raise ValueError("visual review requires reviewer_identity")
    if not isinstance(review.get("notes"), str) or len(review["notes"].strip()) < 40:
        raise ValueError("visual review requires substantive notes")
    for field in ("strengths", "remaining_tradeoffs", "exemplar_principles_applied"):
        values = review.get(field)
        if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
            raise ValueError(f"visual review requires a list of non-empty {field}")
    blocking_tradeoffs = review.get("blocking_tradeoffs")
    if not isinstance(blocking_tradeoffs, list) or any(
        not isinstance(item, str) or not item.strip() for item in blocking_tradeoffs
    ):
        raise ValueError("visual review requires blocking_tradeoffs as a list")
    if len(review["strengths"]) < 2:
        raise ValueError("visual review requires at least two concrete strengths")
    if len(review["exemplar_principles_applied"]) < 2:
        raise ValueError("visual review must apply at least two cross-paper visual principles")
    candidates = review.get("design_candidates")
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise ValueError("visual review requires at least two rendered design candidates")
    candidate_paths = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"design_candidates[{index}] must be an object")
        relative = candidate.get("path")
        if not isinstance(relative, str) or not relative.strip() or relative in candidate_paths:
            raise ValueError("design candidate paths must be distinct non-empty strings")
        candidate_paths.add(relative)
        candidate_path = contained(root, relative)
        if not candidate_path.is_file() or candidate_path.suffix.lower() not in {".pdf", ".svg"}:
            raise ValueError(f"design candidate is missing or unsupported: {relative}")
        if candidate.get("sha256") != file_sha256(candidate_path):
            raise ValueError(f"design candidate hash mismatch: {relative}")
        if not isinstance(candidate.get("design_rationale"), str) or not candidate["design_rationale"].strip():
            raise ValueError("each design candidate requires a rationale")
        preview_relative = candidate.get("rendered_preview_path")
        if not isinstance(preview_relative, str) or not preview_relative.strip():
            raise ValueError("each design candidate requires a paper-size rendered_preview_path")
        preview_path = contained(root, preview_relative)
        if not preview_path.is_file() or preview_path.suffix.lower() != ".png":
            raise ValueError(f"paper-size rendered preview is missing or not PNG: {preview_relative}")
        if candidate.get("rendered_preview_sha256") != file_sha256(preview_path):
            raise ValueError(f"rendered preview hash mismatch: {preview_relative}")
        if candidate.get("render_source_sha256") != candidate.get("sha256"):
            raise ValueError("rendered preview must bind to its vector candidate hash")
        if candidate.get("rendered_size_class") != registered_figure["size_class"]:
            raise ValueError("rendered preview must use the registered paper size class")
        preview_report = audit_figure(
            preview_path,
            registered_figure["size_class"],
            panels=registered_figure["panels"],
            role=registered_figure["role"],
        )
        if not preview_report["structurally_valid"]:
            raise ValueError(
                f"paper-size rendered preview failed structural audit: {preview_report['errors']}"
            )
        candidate["paper_size_render_report"] = preview_report
        if not isinstance(candidate.get("paper_size_inspection"), str) or len(
            candidate["paper_size_inspection"].strip()
        ) < 40:
            raise ValueError("each design candidate requires substantive paper_size_inspection")
    selected = review.get("selected_candidate_path")
    if selected not in candidate_paths:
        raise ValueError("selected_candidate_path must identify one rendered design candidate")
    if not isinstance(review.get("selection_reason"), str) or len(review["selection_reason"].strip()) < 30:
        raise ValueError("visual review requires a substantive candidate selection reason")
    review.update({"reviewed_at": utc_now(), "actor": actor})

    def transform(value):
        matches = [item for item in value["figures"] if item.get("figure_id") == args.figure_id]
        if len(matches) != 1:
            raise ValueError("figure ID must identify exactly one registered figure")
        figure = matches[0]
        experiment = _experiment(value, figure["experiment_id"])
        if figure.get("status") != "needs_visual_review" or figure.get("results_sha256") != experiment.get("evaluation", {}).get("raw_results_sha256"):
            raise ValueError("figure is stale or not awaiting review; register the current artifact first")
        path = contained(root, figure["path"])
        if file_sha256(path) != figure["figure_sha256"]:
            raise ValueError("figure changed after registration; register the new artifact")
        if selected != figure["path"]:
            raise ValueError("selected design candidate must be the registered figure")
        exemplar_path = root / "writing_exemplars.json"
        if exemplar_path.is_file():
            if review.get("writing_exemplars_sha256") != file_sha256(exemplar_path):
                raise ValueError("visual review must bind to the current writing exemplar study")
        passed = professional_visual_pass(review)
        review["computed_overall_score"] = round(overall, 3)
        review["professional_quality_passed"] = passed
        review["review_sha256"] = figure_review_hash(review)
        figure["visual_review"] = review
        figure["status"] = "publication_ready" if passed and figure["quality_report"]["publication_master_eligible"] else "needs_revision"
        figure["record_sha256"] = _canonical_hash({key: item for key, item in figure.items() if key != "record_sha256"})
        _event(value, "figure_reviewed", actor, {"figure_id": args.figure_id, "status": figure["status"]})
        return value
    updated = _update(root, transform)
    figure = next(item for item in updated["figures"] if item["figure_id"] == args.figure_id)
    print(json.dumps({"figure_id": args.figure_id, "status": figure["status"]}, indent=2))


def command_emit_figure_tex(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    value = load_index(root)
    matches = [item for item in value["figures"] if item.get("figure_id") == args.figure_id]
    if len(matches) != 1 or matches[0].get("status") != "publication_ready":
        raise ValueError("LaTeX emission requires one publication-ready figure")
    figure = matches[0]
    environment = "figure*" if figure["size_class"] in {"double_column", "full_page"} else "figure"
    placement = {"here": "htbp", "top": "t", "page": "p"}[figure["placement"]]
    venue_snapshot = root / "venue" / "venue_snapshot.json"
    venue_format = ""
    if venue_snapshot.is_file():
        snapshot = read_json(venue_snapshot)
        metadata = snapshot.get("source_metadata", {}) if isinstance(snapshot, dict) else {}
        if isinstance(metadata, dict):
            venue_format = str(metadata.get("format") or "").casefold()
    if environment == "figure*":
        width = r"\textwidth"
    elif venue_format in ONE_COLUMN_VENUE_FORMATS:
        width = r"0.62\textwidth"
    else:
        width = r"\columnwidth"
    lines = [
        f"\\begin{{{environment}}}[{placement}]", r"\centering",
        f"\\includegraphics[width={width}]{{{figure['path']}}}",
        f"\\caption{{{figure['caption']}}}", f"\\label{{{figure['label']}}}",
        f"\\end{{{environment}}}", "",
    ]
    destination = contained(root, f"figures/{figure['figure_id'].lower()}.tex")
    if destination.exists() and not getattr(args, "replace", False):
        raise ValueError("figure LaTeX snippet already exists; pass --replace to regenerate it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
    relative = str(destination.relative_to(root))
    digest = file_sha256(destination)

    def transform(index):
        target = next(item for item in index["figures"] if item["figure_id"] == args.figure_id)
        target["latex_snippet_path"] = relative
        target["latex_snippet_sha256"] = digest
        target["record_sha256"] = _canonical_hash({key: item for key, item in target.items() if key != "record_sha256"})
        _event(index, "figure_latex_emitted", actor, {"figure_id": args.figure_id, "path": relative})
        return index
    _update(root, transform)
    print(json.dumps({"figure_id": args.figure_id, "written": str(destination),
                      "environment": environment, "width": width}, indent=2))


def command_strategy(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    strategy = load_object_argument(args.input, Path(args.workspace))
    if load_index(root).get("strategy") is None and strategy.get("schema_version") != 2:
        raise ValueError("new experiment programs require strategy schema_version 2 with resource preflight")
    validate_strategy(strategy, accepted_statement_ids(root))
    if strategy.get("schema_version") == 2:
        from experiment_resources import activity, check_feasibility
        activity(root, "checking_resources", "Checking selected experiments' resources and required fields.")
        try:
            for candidate in strategy["candidate_experiments"]:
                if candidate["selected"]:
                    check_feasibility(root, candidate)
        except (ValueError, PermissionError) as exc:
            activity(root, "awaiting_approval" if isinstance(exc, PermissionError) else "blocked", str(exc))
            raise
    replace, reason = getattr(args, "replace", False), getattr(args, "reason", "")

    def transform(value):
        existing = value.get("strategy")
        if existing and existing.get("schema_version") == 2 and strategy.get("schema_version") != 2:
            raise ValueError("cannot downgrade a resource-governed experiment strategy")
        if existing and existing.get("schema_version") != 2 and strategy.get("schema_version") == 2 and value["executions"]:
            raise ValueError("preserve legacy executions; use the experiment-revision workflow before switching to strategy v2")
        if existing and not replace:
            raise ValueError("strategy already exists; pass --replace with a reason")
        if existing and (not isinstance(reason, str) or not reason.strip()):
            raise ValueError("replacing the strategy requires --reason")
        proposed = {item.get("id") for item in value["experiments"]}
        if proposed and not proposed <= set(strategy["selected_experiment_ids"]):
            raise ValueError("a replacement strategy cannot silently discard existing proposals")
        if existing:
            value["strategy_history"].append({
                "strategy": existing, "replaced_at": utc_now(), "actor": actor,
                "reason": reason.strip(), "strategy_sha256": _canonical_hash(existing),
            })
        value["strategy"] = strategy
        _event(value, "strategy_written", actor, {"selected": strategy["selected_experiment_ids"]})
        return value
    _update(root, transform)
    if strategy.get("schema_version") == 2:
        checks = [c["preflight"] for c in strategy["candidate_experiments"] if c["selected"]]
        state = "blocked" if any(c["status"] == "blocked" for c in checks) else "awaiting_approval" if any(c["status"] == "awaiting_approval" for c in checks) else "ready"
        activity(root, state, "Experiment strategy recorded; inspect feasibility records for resource requirements.")
    print(json.dumps({"strategy_saved": True, "selected": strategy["selected_experiment_ids"]}, indent=2))


def command_finalize(args):
    root, actor = paper_dir(args.workspace, args.run), _actor(args)
    _require_stage(root, actor)
    summary = load_object_argument(args.input, Path(args.workspace))
    value = load_index(root)
    if not isinstance(value.get("strategy"), dict):
        raise ValueError("write an experiment strategy before finalizing empirical validation")
    incomplete_figures = [item["figure_id"] for item in value["figures"] if item["role"] == "main" and item["status"] != "publication_ready"]
    if summary.get("status") in {"completed", "contradictory", "blocked"} and incomplete_figures:
        raise ValueError(f"main figures require publication-ready visual review: {incomplete_figures}")
    artifact = {
        "schema_version": 2, "artifact": "empirical_validation",
        "status": summary.get("status"), "reason": summary.get("reason"),
        "strategy": value["strategy"], "experiments": value["experiments"],
        "coverage_tags": summary.get("coverage_tags"), "limitations": summary.get("limitations"),
        "figures": value.get("figures", []), "inspections": value.get("inspections", []),
        "executions": value.get("executions", []), "evidence_registry_sha256": file_sha256(index_path(root)),
    }
    if value["strategy"].get("schema_version") == 2:
        from experiment_resources import load_store, store_path
        artifact["resource_evidence"] = load_store(root)
        artifact["resource_registry_sha256"] = file_sha256(store_path(root)) if store_path(root).exists() else None
    from manuscript_workflow import validate_empirical
    validate_empirical(root.parent, artifact)
    from state_store import write_json
    write_json(root / "empirical_validation.json", artifact)
    print(json.dumps({"finalized": True, "status": artifact["status"],
                      "experiments": len(artifact["experiments"]), "figures": len(artifact["figures"])}, indent=2))


def command_run_inspected(args):
    from experiment_runtime import execute
    root = paper_dir(args.workspace, args.run)
    receipt = execute(root, identifier(args.id), load_object_argument(args.input, Path(args.workspace)),
                      workspace=args.workspace, run_id=args.run)
    if receipt["exit_code"] != 0:
        raise ValueError(f"CPU execution failed; receipt and logs preserved: {receipt['failure'] or receipt['exit_code']}")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default="."); result.add_argument("--run"); result.add_argument("--actor", default="experimenter")
    commands = result.add_subparsers(dest="command", required=True)
    strategy = commands.add_parser("write-strategy"); strategy.add_argument("--input", required=True); strategy.add_argument("--replace", action="store_true"); strategy.add_argument("--reason", default=""); strategy.set_defaults(function=command_strategy)
    inspect = commands.add_parser("inspect-script"); inspect.add_argument("--id"); inspect.add_argument("--script", required=True); inspect.add_argument("--dependency", action="append", default=[]); inspect.set_defaults(function=command_inspect)
    propose = commands.add_parser("propose"); propose.add_argument("--input", required=True); propose.set_defaults(function=command_propose)
    execution = commands.add_parser("record-execution"); execution.add_argument("--id", required=True); execution.add_argument("--input", required=True); execution.set_defaults(function=command_record_execution)
    bounded = commands.add_parser("run-inspected"); bounded.add_argument("--id", required=True); bounded.add_argument("--input", required=True); bounded.set_defaults(function=command_run_inspected)
    blocked = commands.add_parser("mark-blocked"); blocked.add_argument("--id", required=True); blocked.add_argument("--input", required=True); blocked.set_defaults(function=command_mark_blocked)
    evaluate = commands.add_parser("evaluate"); evaluate.add_argument("--id", required=True); evaluate.add_argument("--input", required=True); evaluate.add_argument("--replace", action="store_true"); evaluate.add_argument("--reason", default=""); evaluate.set_defaults(function=command_evaluate)
    repair = commands.add_parser("repair-evaluation-hash", help="Repair only the recognized legacy previous-hash defect, preserving the original record")
    repair.add_argument("--id", required=True); repair.add_argument("--revision", type=int, required=True)
    repair.add_argument("--expected-sha256", required=True); repair.add_argument("--reason", required=True)
    repair.set_defaults(function=command_repair_evaluation_hash)
    repair_figure = commands.add_parser("repair-figure-review-hash", help="Repair the recognized legacy reused-review hash defect")
    repair_figure.add_argument("--figure-id", required=True); repair_figure.add_argument("--expected-sha256", required=True)
    repair_figure.add_argument("--reason", required=True); repair_figure.set_defaults(function=command_repair_figure_review_hash)
    figure_audit = commands.add_parser("audit-figure"); figure_audit.add_argument("--path", required=True); figure_audit.add_argument("--size-class", choices=sorted(SIZE_CLASSES), required=True); figure_audit.add_argument("--panels", type=int, default=1); figure_audit.add_argument("--role", choices=("main", "appendix", "diagnostic"), default="main"); figure_audit.set_defaults(function=command_audit_figure)
    figure = commands.add_parser("register-figure"); figure.add_argument("--id", required=True); figure.add_argument("--path", required=True); figure.add_argument("--label", required=True); figure.add_argument("--caption", required=True); figure.add_argument("--alt-text", required=True); figure.add_argument("--size-class", choices=sorted(SIZE_CLASSES), required=True); figure.add_argument("--panels", type=int, default=1); figure.add_argument("--multi-panel-justification", default=""); figure.add_argument("--role", choices=("main", "appendix", "diagnostic"), default="main"); figure.add_argument("--placement", choices=("here", "top", "page"), default="top"); figure.add_argument("--results-path"); figure.add_argument("--replace", action="store_true"); figure.add_argument("--reason", default=""); figure.set_defaults(function=command_figure)
    review = commands.add_parser("review-figure"); review.add_argument("--figure-id", required=True); review.add_argument("--input", required=True); review.set_defaults(function=command_review_figure)
    figure_tex = commands.add_parser("emit-figure-tex"); figure_tex.add_argument("--figure-id", required=True); figure_tex.add_argument("--replace", action="store_true"); figure_tex.set_defaults(function=command_emit_figure_tex)
    finalize = commands.add_parser("finalize"); finalize.add_argument("--input", required=True); finalize.set_defaults(function=command_finalize)
    return result


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, OSError, PermissionError, SyntaxError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
