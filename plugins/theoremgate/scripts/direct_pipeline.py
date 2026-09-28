#!/usr/bin/env python3
"""Run direct TheoremAudit launches through a bounded continuation controller."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from codex_runner import CodexJobRunner, build_pipeline_prompt
from state_store import create_run, load_manifest, resolve_run
from workflow import STAGES


def initialize_run(workspace: Path, question: str, mode: str) -> Path:
    """Create the autonomous contract used by direct skill launches."""
    if mode not in {"full", "theory"}:
        raise ValueError("direct start mode must be full or theory")
    return create_run(
        workspace=workspace,
        question=question,
        stages=STAGES,
        execution_contract={
            "intent": "new_full" if mode == "full" else "new_theory",
            "initiated_from": "cli",
            "requested_mode": mode,
            "human_checkpoints_required": False,
            "interaction_policy": "autonomous",
            "publication_goal": "original_research" if mode == "full" else "no_preference",
            "auto_repair_enabled": False,
            "max_auto_repair_rounds": 0,
            "repair_round": 0,
        },
    )


def initialize_full_run(workspace: Path, question: str) -> Path:
    """Compatibility helper for the default full research-to-paper launch."""
    return initialize_run(workspace, question, "full")


def terminal_event(result: Dict[str, Any]) -> str:
    """Name the controller's terminal event without conflating stop and success."""
    if result.get("complete") is True:
        return "pipeline_completed"
    if result.get("reason") == "continuation_budget_exhausted":
        return "continuation_budget_exhausted"
    return "continuation_failed"


def run_continuation_controller(
    *,
    workspace: Path,
    run_dir: Path,
    mode: str,
    constraints: str = "",
    model: Optional[str] = None,
    runner: Optional[CodexJobRunner] = None,
) -> Dict[str, Any]:
    """Start one Codex turn and continue the same run until a terminal outcome."""
    manifest = load_manifest(run_dir)
    contract = manifest.get("execution_contract", {})
    question = str(manifest.get("research_question") or "").strip()
    publication_goal = str(contract.get("publication_goal") or "original_research")
    active_runner = runner or CodexJobRunner(workspace)
    prompt = build_pipeline_prompt(
        mode=mode,
        question=question,
        run_id=run_dir.name,
        parent_run_id=manifest.get("parent_run_id"),
        constraints=constraints,
        publication_goal=publication_goal,
        auto_repair=False,
        max_auto_repair_rounds=0,
        interaction_policy="autonomous",
    )
    job = active_runner.start(
        prompt=prompt,
        kind="pipeline",
        label="Direct governed pipeline" if mode == "full" else "Resume governed pipeline",
        model=model,
        metadata={
            "mode": mode,
            "question": question,
            "run_id": run_dir.name,
            "parent_run_id": manifest.get("parent_run_id"),
            "auto_repair": False,
            "max_auto_repair_rounds": 0,
            "interaction_policy": "autonomous",
            "continuation_round": 0,
        },
    )
    print(json.dumps({"event": "launched", "run_id": run_dir.name, "job": job}), flush=True)

    def report(completed: Dict[str, Any]) -> None:
        print(
            json.dumps(
                {
                    "event": "codex_turn_finished",
                    "job_id": completed.get("job_id"),
                    "continuation_round": completed.get("continuation_round", 0),
                    "outcome": completed.get("outcome"),
                }
            ),
            flush=True,
        )

    try:
        return active_runner.run_continuation_chain(job["job_id"], on_job_finished=report)
    except KeyboardInterrupt:
        active_runner.close()
        raise


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--workspace", default=".")
    commands = root.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="Create and continue an autonomous governed run")
    start.add_argument("--question", required=True)
    start.add_argument("--mode", choices=("full", "theory"), default="full")
    start.add_argument("--constraints", default="")
    start.add_argument("--model")

    resume = commands.add_parser("resume", help="Continue an exact existing run")
    resume.add_argument("--run", required=True)
    resume.add_argument("--constraints", default="")
    resume.add_argument("--model")
    return root


def main() -> int:
    args = parser().parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    if args.command == "start":
        mode = args.mode
        run_dir = initialize_run(workspace, args.question, mode)
    else:
        run_dir = resolve_run(workspace, args.run)
        mode = "resume"
    try:
        result = run_continuation_controller(
            workspace=workspace,
            run_dir=run_dir,
            mode=mode,
            constraints=args.constraints,
            model=args.model,
        )
    except KeyboardInterrupt:
        print(json.dumps({"event": "interrupted", "run_id": run_dir.name}), flush=True)
        return 130
    print(json.dumps({"event": terminal_event(result), **result}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
