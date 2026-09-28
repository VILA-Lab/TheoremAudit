#!/usr/bin/env python3
"""Route resume, retry, repair, strengthening, and rerun requests safely."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import manuscript_workflow
from state_store import create_run, load_manifest, resolve_run, save_manifest, update_json, utc_now
from workflow import STAGES


ACTIONS = {
    "resume",
    "retry_stage",
    "independent_reaudit",
    "repair_mathematics",
    "salvage_results",
    "strengthen_contribution",
    "rerun_experiments",
    "revise_literature",
    "revise_manuscript",
    "rewrite_manuscript",
    "pivot_direction",
    "new_run",
}
LINKED_ACTIONS = {
    "repair_mathematics",
    "salvage_results",
    "strengthen_contribution",
    "pivot_direction",
}
AUTO_REPAIR_ACTIONS = {"repair_mathematics", "salvage_results"}
PAPER_ACTIONS = {
    "rerun_experiments", "revise_literature", "revise_manuscript", "rewrite_manuscript",
}
PAPER_RESUME_STAGES = {
    "rerun_experiments": "empirical_validation",
    "revise_literature": "literature_audit",
    "revise_manuscript": "section_writing",
    "rewrite_manuscript": "venue_selection",
}
AUDIT_STAGES = {
    "local_adversarial_audit", "final_adversarial_audit", "novelty_audit",
    "significance_audit", "independent_review",
}
REPAIR_STRATEGIES = {
    "repair_mathematics": "repair_full_theorem",
    "salvage_results": "salvage_independent_statements",
    "strengthen_contribution": "contribution_extension",
    "pivot_direction": "pivot_direction",
}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _plan_id(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "RR-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:12].upper()


def _prompt(action: str, run_id: str, target: str, reason: str) -> str:
    instructions = {
        "resume": f"Resume the exact run from its persisted {target} stage.",
        "retry_stage": f"Retry only the unfinished {target} stage and reuse all completed evidence.",
        "independent_reaudit": f"Independently re-audit {target} without editing the evidence under review.",
        "repair_mathematics": "Repair the smallest proof and assumption closure affected by the governed finding, then use a fresh Attack role and Governor decision.",
        "salvage_results": "Salvage independently supported statements, re-audit their transitive proof closures, and do not inherit failure solely from research provenance.",
        "strengthen_contribution": "Preserve accepted mathematics and develop the smallest falsifiable extension that addresses the recorded publication-route blocker.",
        "rerun_experiments": "Preserve accepted theory and rerun only the selected empirical evidence with new execution records and figure review.",
        "revise_literature": "Preserve the theory bundle, reopen the paper at literature audit, rebuild every affected downstream paper artifact, and finish with a fresh independent review.",
        "revise_manuscript": "Preserve the theory bundle and create a manuscript revision followed by compilation and independent review.",
        "rewrite_manuscript": (
            "Preserve the theory bundle, select the best-fit venue first, design a new venue-bound "
            "page-aware content architecture with scholarly section titles, rewrite every manuscript "
            "section, and rebuild compilation, review, and packaging."
        ),
        "pivot_direction": "Use the failed evidence as a boundary condition and select a materially different research direction.",
        "new_run": "Create a new root research run and do not inherit scientific claims from the selected run.",
    }
    return (
        f"Use $research-revision for TheoremAudit run {run_id}. {instructions[action]} "
        f"Researcher objective: {reason}"
    )


def route_request(run_dir: Path, *, action: str, target: str = "", reason: str) -> Dict[str, Any]:
    if action not in ACTIONS:
        raise ValueError(f"unsupported revision action: {action}")
    reason = _text(reason, "reason")
    manifest = load_manifest(run_dir)
    current = manifest.get("current_stage", "unknown")
    selected_target = target.strip() or current
    theory_stages = list(STAGES)
    paper_stages = [
        "literature_audit", "exemplar_study", "venue_selection", "content_architecture",
        "empirical_validation", "section_writing", "compilation", "independent_review",
        "revision", "final_package",
    ]

    if action in {"resume", "retry_stage"}:
        paper = None
        if current == "complete" or manifest.get("status") == "completed":
            paper_path = manuscript_workflow.paper_manifest_path(run_dir)
            if not paper_path.is_file():
                raise ValueError("theory is complete and no paper workflow exists; initialize the paper workflow or choose a revision")
            paper = manuscript_workflow.load_paper_manifest(run_dir)
            if paper.get("status") == "completed":
                raise ValueError("a completed run cannot be resumed; choose a repair, strengthening, paper revision, or new run")
            if paper.get("status") != "active":
                raise ValueError("paper workflow is blocked; resolve its recorded blocker through the appropriate revision")
            current = paper.get("current_stage")
            if current not in manuscript_workflow.STAGES or paper.get("stages", {}).get(current, {}).get("status") != "in_progress":
                raise ValueError("paper workflow has no unfinished current stage to resume")
            selected_target = target.strip().removeprefix("paper/") or current
        if selected_target != current:
            raise ValueError("same-run retry must target the persisted current stage")
        mode = "same_run"
        invalidated = []
        preserves = [name for name in theory_stages if manifest["stages"][name]["status"] == "completed"]
        if paper is not None:
            preserves += [f"paper/{name}" for name, stage in paper["stages"].items() if stage["status"] == "completed"]
    elif action == "independent_reaudit":
        if selected_target not in AUDIT_STAGES:
            raise ValueError("independent re-audit requires an audit or review stage target")
        mode = "read_only_reaudit"
        invalidated = []
        preserves = theory_stages
    elif action in LINKED_ACTIONS:
        mode = "linked_revision"
        invalidated = theory_stages
        preserves = ["parent_evidence", "unaffected_hash_verified_proofs", "audit_history"]
    elif action in PAPER_ACTIONS:
        mode = "paper_revision"
        resume_stage = PAPER_RESUME_STAGES[action]
        start = paper_stages.index(resume_stage)
        invalidated = paper_stages[start:]
        preserves = ["theory_bundle", *paper_stages[:start]]
    else:
        mode = "new_root"
        invalidated = []
        preserves = ["source_run_as_optional_context_only"]

    contract = manifest.get("execution_contract", {})
    repair_round = int(contract.get("repair_round", 0) or 0)
    max_rounds = int(contract.get("max_auto_repair_rounds", 0) or 0)
    auto_authorized = (
        action in AUTO_REPAIR_ACTIONS
        and contract.get("auto_repair_enabled") is True
        and repair_round < max_rounds
    )
    payload = {
        "schema_version": 1,
        "artifact": "research_revision_plan",
        "source_run_id": manifest["run_id"],
        "action": action,
        "target": selected_target,
        "reason": reason,
        "execution_mode": mode,
        "preserve": preserves,
        "recompute_or_invalidate": invalidated,
        "automatic_execution_authorized": auto_authorized,
        "repair_budget": {
            "current_round": repair_round,
            "maximum_rounds": max_rounds,
            "remaining_rounds": max(0, max_rounds - repair_round),
        },
        "recommended_prompt": _prompt(action, manifest["run_id"], selected_target, reason),
        "created_at": utc_now(),
    }
    if action in PAPER_ACTIONS:
        payload["paper_resume_stage"] = PAPER_RESUME_STAGES[action]
    elif action in {"resume", "retry_stage"} and paper is not None:
        payload["paper_resume_stage"] = current
        payload["recommended_prompt"] = _prompt(action, manifest["run_id"], f"paper/{current}", reason)
    payload["plan_id"] = _plan_id({key: value for key, value in payload.items() if key != "created_at"})
    return payload


def request_registry_path(run_dir: Path) -> Path:
    return run_dir / "artifacts" / "revision_requests.json"


def record_request(run_dir: Path, plan: Dict[str, Any], child_run_id: str | None = None) -> Dict[str, Any]:
    def append(value):
        if not isinstance(value, dict) or value.get("artifact") != "research_revision_requests":
            raise ValueError("invalid research revision registry")
        records = value.get("requests")
        if not isinstance(records, list):
            raise ValueError("research revision registry requests must be a list")
        record = dict(plan)
        record["recorded_at"] = utc_now()
        record["child_run_id"] = child_run_id
        records.append(record)
        return value

    return update_json(
        request_registry_path(run_dir),
        append,
        {"schema_version": 1, "artifact": "research_revision_requests", "requests": []},
    )


def start_linked_revision(
    workspace: Path,
    run_dir: Path,
    plan: Dict[str, Any],
    *,
    researcher_authorized: bool,
) -> Path:
    if plan["execution_mode"] != "linked_revision":
        raise ValueError("only linked-revision plans create a child theory run")
    if not researcher_authorized and not plan["automatic_execution_authorized"]:
        raise PermissionError("linked revision requires explicit researcher authorization or an available automatic-repair budget")
    parent = load_manifest(run_dir)
    contract = parent.get("execution_contract", {})
    repair_round = int(contract.get("repair_round", 0) or 0) + (0 if researcher_authorized else 1)
    max_rounds = int(contract.get("max_auto_repair_rounds", 0) or 0)
    if plan["action"] in AUTO_REPAIR_ACTIONS and repair_round > max_rounds and not researcher_authorized:
        raise ValueError("automatic repair budget is exhausted; retain the strongest supported governed outcome")
    child = create_run(
        workspace=workspace,
        question=f"{plan['action'].replace('_', ' ').title()}: {plan['reason']}",
        stages=STAGES,
        parent_run_id=run_dir.name,
        execution_contract={
            "intent": "repair",
            "initiated_from": "controller",
            "requested_mode": "repair",
            "human_checkpoints_required": False,
            "interaction_policy": "autonomous",
            "repair_strategy": REPAIR_STRATEGIES[plan["action"]],
            "researcher_decision_id": plan["plan_id"] if researcher_authorized else None,
            "publication_goal": contract.get("publication_goal", "no_preference"),
            "auto_repair_enabled": contract.get("auto_repair_enabled", False),
            "max_auto_repair_rounds": max_rounds,
            "repair_round": repair_round,
            "repair_authorization": {
                "plan_id": plan["plan_id"],
                "source_run_id": parent["run_id"],
                "action": plan["action"],
                "target": plan["target"],
                "origin": "direct_researcher" if researcher_authorized else "automatic_contract",
            },
        },
    )
    record_request(run_dir, plan, child.name)
    refreshed_parent = load_manifest(run_dir)
    refreshed_parent["status"] = "superseded_by_linked_revision"
    refreshed_parent["revision_state"] = {
        "status": "linked_revision_started",
        "child_run_id": child.name,
        "plan_id": plan["plan_id"],
        "action": plan["action"],
        "started_at": utc_now(),
        "continuation_policy": (
            "Continue only in the child run. The parent cannot enter theorem synthesis "
            "from unrepaired evidence."
        ),
    }
    save_manifest(run_dir, refreshed_parent)
    return child


def start_paper_revision(run_dir: Path, plan: Dict[str, Any]) -> dict:
    """Start an evidence-preserving same-run paper revision at its routed stage."""
    if plan.get("execution_mode") != "paper_revision":
        raise ValueError("only paper-revision plans can reopen the paper workflow")
    resume_stage = plan.get("paper_resume_stage")
    if resume_stage not in manuscript_workflow.STAGES:
        raise ValueError("paper revision plan has an invalid resume stage")
    manifest = manuscript_workflow.start_paper_revision(
        run_dir,
        start_stage=resume_stage,
        reason=plan["reason"],
        plan_id=plan["plan_id"],
        revision_action=plan["action"],
    )
    record_request(run_dir, plan)
    return manifest


def command_plan(args) -> None:
    run_dir = resolve_run(Path(args.workspace), args.run)
    print(json.dumps(route_request(run_dir, action=args.action, target=args.target, reason=args.reason), indent=2))


def command_start(args) -> None:
    workspace = Path(args.workspace).resolve()
    run_dir = resolve_run(workspace, args.run)
    plan = route_request(run_dir, action=args.action, target=args.target, reason=args.reason)
    if plan["execution_mode"] == "linked_revision":
        child = start_linked_revision(
            workspace, run_dir, plan, researcher_authorized=args.researcher_authorized
        )
        result = {"plan": plan, "child_run_id": child.name, "run_dir": str(child)}
    elif plan["execution_mode"] == "paper_revision":
        manifest = start_paper_revision(run_dir, plan)
        result = {
            "plan": plan,
            "run_id": run_dir.name,
            "paper_stage": manifest["current_stage"],
            "paper_status": manifest["status"],
        }
    else:
        raise ValueError("start is available only for linked or paper revisions")
    print(json.dumps(result, indent=2))


def command_status(args) -> None:
    run_dir = resolve_run(Path(args.workspace), args.run)
    path = request_registry_path(run_dir)
    value = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "schema_version": 1, "artifact": "research_revision_requests", "requests": []
    }
    print(json.dumps(value, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--workspace", default=".")
    root.add_argument("--run", required=True)
    commands = root.add_subparsers(dest="command", required=True)
    for name, handler in (("plan", command_plan), ("start", command_start)):
        command = commands.add_parser(name)
        command.add_argument("--action", required=True, choices=sorted(ACTIONS))
        command.add_argument("--target", default="")
        command.add_argument("--reason", required=True)
        if name == "start":
            command.add_argument("--researcher-authorized", action="store_true")
        command.set_defaults(function=handler)
    status = commands.add_parser("status")
    status.set_defaults(function=command_status)
    return root


def main() -> None:
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, PermissionError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
