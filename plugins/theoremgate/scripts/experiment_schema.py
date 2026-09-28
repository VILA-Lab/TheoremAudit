#!/usr/bin/env python3
"""Adaptive experiment-strategy and claim-linked evidence validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Optional

from state_store import file_sha256


FINAL_STATUSES = {"evaluated", "contradictory", "inconclusive", "failed"}
VERDICTS = {"supports", "contradicts", "inconclusive", "failed"}


def _dict(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _identifier(value: Any, label: str) -> str:
    text = _text(value, label)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,79}", text):
        raise ValueError(f"{label} has an invalid identifier")
    return text


def validate_strategy(value: dict, accepted_ids: Iterable[str]) -> dict:
    value = _dict(value, "experiment strategy")
    if value.get("schema_version", 1) not in {1, 2}:
        raise ValueError("unsupported experiment strategy version")
    accepted = set(accepted_ids)
    _text(value.get("objective"), "strategy.objective")
    criteria = _list(value.get("selection_criteria"), "strategy.selection_criteria")
    if not criteria or any(not isinstance(item, str) or not item.strip() for item in criteria):
        raise ValueError("strategy.selection_criteria must contain non-empty criteria")
    _list(value.get("reviewer_risks"), "strategy.reviewer_risks")
    candidates = _list(value.get("candidate_experiments"), "strategy.candidate_experiments")
    candidate_ids = set()
    selected = set()
    for index, candidate in enumerate(candidates):
        candidate = _dict(candidate, f"strategy.candidate_experiments[{index}]")
        candidate_id = _identifier(candidate.get("id"), f"candidate[{index}].id")
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate experiment candidate: {candidate_id}")
        candidate_ids.add(candidate_id)
        claims = _list(candidate.get("claim_ids"), f"{candidate_id}.claim_ids")
        if not claims or any(claim not in accepted for claim in claims):
            raise ValueError(f"{candidate_id}.claim_ids must be a non-empty subset of accepted claims")
        for field in ("purpose", "expected_information", "feasibility", "decision_reason"):
            _text(candidate.get(field), f"{candidate_id}.{field}")
        if not isinstance(candidate.get("selected"), bool):
            raise ValueError(f"{candidate_id}.selected must be boolean")
        if value.get("schema_version") == 2:
            from experiment_resources import validate_preflight
            validate_preflight(candidate.get("preflight"))
        if candidate["selected"]:
            selected.add(candidate_id)
    selected_ids = _list(value.get("selected_experiment_ids"), "strategy.selected_experiment_ids")
    if len(selected_ids) != len(set(selected_ids)) or set(selected_ids) != selected:
        raise ValueError("strategy.selected_experiment_ids must exactly match selected candidates")
    coverage = _list(value.get("claim_coverage"), "strategy.claim_coverage")
    covered = set()
    for index, item in enumerate(coverage):
        item = _dict(item, f"strategy.claim_coverage[{index}]")
        claim_id = _text(item.get("claim_id"), f"claim_coverage[{index}].claim_id")
        if claim_id not in accepted or claim_id in covered:
            raise ValueError(f"claim_coverage has unknown or duplicate claim: {claim_id}")
        covered.add(claim_id)
        status = item.get("status")
        if status not in {"selected", "not_empirically_testable", "deferred"}:
            raise ValueError(f"{claim_id}.status is invalid")
        experiment_ids = _list(item.get("experiment_ids"), f"{claim_id}.experiment_ids")
        if any(experiment_id not in selected for experiment_id in experiment_ids):
            raise ValueError(f"{claim_id} references a non-selected experiment")
        if status == "selected" and not experiment_ids:
            raise ValueError(f"{claim_id} selected coverage requires an experiment")
        if status != "selected" and experiment_ids:
            raise ValueError(f"{claim_id} non-selected coverage cannot reference experiments")
        _text(item.get("rationale"), f"{claim_id}.rationale")
    if accepted != covered:
        raise ValueError("strategy.claim_coverage must account for every accepted claim")
    return value


def validate_experiment(value: dict, accepted_ids: Iterable[str], paper_root: Optional[Path] = None,
                        require_final: bool = False) -> dict:
    value = _dict(value, "experiment")
    experiment_id = _identifier(value.get("id"), "experiment.id")
    accepted = set(accepted_ids)
    claims = _list(value.get("claim_ids"), f"{experiment_id}.claim_ids")
    if not claims or len(claims) != len(set(claims)) or any(claim not in accepted for claim in claims):
        raise ValueError(f"{experiment_id}.claim_ids must be unique accepted claims")
    for field in ("purpose", "theoretical_prediction", "selection_rationale"):
        _text(value.get(field), f"{experiment_id}.{field}")
    _list(value.get("assumptions_tested"), f"{experiment_id}.assumptions_tested")
    tags = _list(value.get("tags"), f"{experiment_id}.tags")
    if any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise ValueError(f"{experiment_id}.tags must contain non-empty text")
    design = _dict(value.get("design"), f"{experiment_id}.design")
    _text(design.get("substrate"), f"{experiment_id}.design.substrate")
    for field in ("independent_variables", "dependent_metrics", "baselines", "controls",
                  "falsification_criteria"):
        items = _list(design.get(field), f"{experiment_id}.design.{field}")
        if field in {"dependent_metrics", "falsification_criteria"} and not items:
            raise ValueError(f"{experiment_id}.design.{field} cannot be empty")
    seeds = design.get("seeds")
    if not isinstance(seeds, int) or isinstance(seeds, bool) or seeds < 1:
        raise ValueError(f"{experiment_id}.design.seeds must be a positive integer")
    _text(design.get("uncertainty_method"), f"{experiment_id}.design.uncertainty_method")
    status = value.get("status", "proposed")
    if status not in {"proposed", "planned", "running", "evaluated", "contradictory",
                      "inconclusive", "failed", "blocked"}:
        raise ValueError(f"{experiment_id}.status is invalid")
    if require_final and status not in FINAL_STATUSES:
        raise ValueError(f"{experiment_id} requires a final evaluation")
    if status == "blocked":
        blockage = _dict(value.get("blockage"), f"{experiment_id}.blockage")
        for field in ("reason", "attempted", "required_resource", "claim_assessment"):
            _text(blockage.get(field), f"{experiment_id}.blockage.{field}")
    if status in FINAL_STATUSES:
        evaluation = _dict(value.get("evaluation"), f"{experiment_id}.evaluation")
        verdict = evaluation.get("verdict")
        if verdict not in VERDICTS:
            raise ValueError(f"{experiment_id}.evaluation.verdict is invalid")
        if status == "contradictory" and verdict != "contradicts":
            raise ValueError(f"{experiment_id} contradictory status requires contradicts verdict")
        for field in ("summary", "uncertainty", "raw_results_path", "raw_results_sha256",
                      "claim_assessment"):
            _text(evaluation.get(field), f"{experiment_id}.evaluation.{field}")
        _dict(evaluation.get("configuration"), f"{experiment_id}.evaluation.configuration")
        _list(evaluation.get("limitations"), f"{experiment_id}.evaluation.limitations")
        digest = evaluation["raw_results_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{experiment_id}.evaluation.raw_results_sha256 is invalid")
        if paper_root is not None:
            result_path = (paper_root / evaluation["raw_results_path"]).resolve()
            try:
                result_path.relative_to(paper_root.resolve())
            except ValueError as exc:
                raise ValueError(f"{experiment_id} raw results escape the paper directory") from exc
            if not result_path.is_file() or result_path.suffix.lower() not in {".json", ".csv"}:
                raise ValueError(f"{experiment_id} raw results are missing")
            if file_sha256(result_path) != digest:
                raise ValueError(f"{experiment_id} raw results were modified")
    return value
