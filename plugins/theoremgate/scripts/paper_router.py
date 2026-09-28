"""Evidence-based routing from accepted theory to an honest manuscript type."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from literature.record_schema import validate_record


ORIGINALITY_CLASSES = {
    "novel",
    "new_extension",
    "new_counterexample",
    "new_synthesis",
    "new_empirical_evidence",
    "attributed",
    "standard",
    "unclear",
}
AUDIT_VERDICTS = {"supported", "partial", "not_novel", "unverified"}
CONTRIBUTION_TYPES = {
    "novel_theorem",
    "incremental_extension",
    "synthesis",
    "counterexample_negative_result",
    "empirical_validation",
    "expository_result",
    "provisional_result",
    "null_result",
}
SIGNIFICANCE_LEVELS = {"high", "moderate", "narrow", "unclear", "insufficient"}
STRONG_ORIGINALITY = {"novel", "new_extension", "new_counterexample"}
NEW_RESEARCH_CLASSES = STRONG_ORIGINALITY | {"new_synthesis", "new_empirical_evidence"}
ATTRIBUTED_CLASSES = {"attributed", "standard"}
FRAMING_SCOPES = {"theory_only", "application_motivated", "application_validated"}
EVIDENCE_LEVELS = {"none", "synthetic_model", "semi_synthetic", "real_system"}
SPECIALIZATION_LEVELS = {
    "direct_specialization", "nontrivial_extension", "new_method", "new_lower_bound", "new_framework"
}
BOUND_PRACTICALITY = {"loose", "reasonable", "sharp", "unknown"}
PARAMETER_BURDEN = {"none", "moderate", "strong"}
BASELINE_STRENGTH = {"none", "weak", "reasonable", "strong"}
SIGNIFICANCE_RANK = {"insufficient": -1, "unclear": 0, "narrow": 1, "moderate": 2, "high": 3}
EMPIRICAL_RANK = {"not_required": 0, "recommended": 1, "required": 2}
PUBLICATION_GOALS = {
    "original_research", "workshop_or_short_paper", "technical_note",
    "expository_paper", "reproducibility_paper", "no_preference",
}
RESULT_ROLES = {
    "primary_result", "supporting_theorem", "supporting_proposition", "lemma", "corollary",
    "lower_bound", "counterexample", "boundary_result", "negative_result", "empirical_result",
}
PAPER_PLACEMENTS = {"main", "supporting", "appendix", "separate_paper", "deferred"}
OBLIGATION_PRIORITIES = {"low", "medium", "high", "blocking"}


def _require_list(value: Any, label: str) -> List[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def validate_novelty_audit(value: Dict[str, Any], accepted_ids: Iterable[str]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("novelty audit must be an object")
    accepted = set(accepted_ids)
    scope = _require_list(value.get("scope_statement_ids"), "scope_statement_ids")
    if len(scope) != len(set(scope)) or set(scope) != accepted:
        raise ValueError("novelty audit scope must cover every accepted statement exactly")
    comparisons = _require_list(value.get("closest_work_comparisons"), "closest_work_comparisons")
    comparison_ids = set()
    verified_comparison_ids = set()
    comparison_record_ids = set()
    for index, item in enumerate(comparisons):
        if not isinstance(item, dict):
            raise ValueError(f"closest_work_comparisons[{index}] must be an object")
        for field in ("id", "statement_id", "title", "source_url", "verified", "theorem_location",
                      "prior_result", "current_result", "delta", "overlap"):
            if field not in item:
                raise ValueError(f"closest_work_comparisons[{index}] is missing {field}")
        comparison_id = _require_text(item["id"], f"comparison[{index}].id")
        if comparison_id in comparison_ids:
            raise ValueError(f"duplicate closest-work comparison: {comparison_id}")
        comparison_ids.add(comparison_id)
        if item["statement_id"] not in accepted:
            raise ValueError(f"comparison targets non-accepted statement: {item['statement_id']}")
        if not isinstance(item["verified"], bool):
            raise ValueError(f"{comparison_id}.verified must be boolean")
        record = item.get("literature_record")
        if not isinstance(record, dict):
            raise ValueError(f"{comparison_id} requires literature_record.v1 provenance")
        try:
            validate_record(record)
        except ValueError as exc:
            raise ValueError(f"{comparison_id}.literature_record is invalid: {exc}") from exc
        record_id = record["record_id"]
        if record_id in comparison_record_ids:
            raise ValueError(f"duplicate closest-work literature record: {record_id}")
        comparison_record_ids.add(record_id)
        if record["bibliographic"]["title"].strip().casefold() != str(item["title"]).strip().casefold():
            raise ValueError(f"{comparison_id}.title does not match its literature record")
        record_urls = {
            url for url in (record["source"].get("landing_url"), record["source"].get("pdf_url"))
            if isinstance(url, str) and url
        }
        if item["source_url"] not in record_urls:
            raise ValueError(f"{comparison_id}.source_url is not bound to its literature record")
        if item["verified"]:
            if record["verification"]["status"] != "primary_source_verified":
                raise ValueError(
                    f"{comparison_id}.verified requires primary_source_verified evidence"
                )
            if not record["source"].get("is_primary"):
                raise ValueError(f"{comparison_id}.verified evidence must come from a primary source")
            supported = {
                claim_id
                for evidence in record["verification"].get("evidence", [])
                for claim_id in evidence.get("supports_claim_ids", [])
            }
            if item["statement_id"] not in supported:
                raise ValueError(
                    f"{comparison_id}.verified literature evidence does not support "
                    f"{item['statement_id']}"
                )
            evidence_locations = {
                location
                for evidence in record["verification"].get("evidence", [])
                for location in (evidence.get("theorem"), evidence.get("section"), evidence.get("pages"))
                if isinstance(location, str) and location.strip()
            }
            if item["theorem_location"] not in evidence_locations:
                raise ValueError(
                    f"{comparison_id}.theorem_location is not present in its verified evidence"
                )
            verified_comparison_ids.add(comparison_id)
        for field in ("title", "source_url", "theorem_location", "prior_result", "current_result", "delta", "overlap"):
            _require_text(item[field], f"{comparison_id}.{field}")
    findings = _require_list(value.get("findings"), "novelty findings")
    by_statement = {}
    finding_ids = set()
    for index, item in enumerate(findings):
        if not isinstance(item, dict):
            raise ValueError(f"findings[{index}] must be an object")
        for field in ("id", "statement_id", "classification", "reason", "evidence_ids"):
            if field not in item:
                raise ValueError(f"findings[{index}] is missing {field}")
        statement_id = item["statement_id"]
        finding_id = _require_text(item["id"], f"findings[{index}].id")
        if finding_id in finding_ids:
            raise ValueError(f"duplicate novelty finding ID: {finding_id}")
        finding_ids.add(finding_id)
        if statement_id not in accepted:
            raise ValueError(f"novelty finding targets non-accepted statement: {statement_id}")
        if statement_id in by_statement:
            raise ValueError(f"duplicate novelty finding for statement: {statement_id}")
        if item["classification"] not in ORIGINALITY_CLASSES:
            raise ValueError(f"invalid originality classification: {item['classification']}")
        evidence_ids = _require_list(item["evidence_ids"], f"{statement_id}.evidence_ids")
        if any(evidence_id not in comparison_ids for evidence_id in evidence_ids):
            raise ValueError(f"{statement_id} cites unknown closest-work evidence")
        if item["classification"] != "unclear" and not evidence_ids:
            raise ValueError(f"{statement_id} classification requires closest-work evidence")
        verified_for_statement = {
            evidence_id for evidence_id in evidence_ids if evidence_id in verified_comparison_ids
        }
        if item["classification"] in NEW_RESEARCH_CLASSES and len(verified_for_statement) < 2:
            raise ValueError(
                f"{statement_id} new-contribution classification requires at least two "
                "distinct verified technical comparisons; otherwise use unclear/unverified"
            )
        if item["classification"] in ATTRIBUTED_CLASSES and not verified_for_statement:
            raise ValueError(f"{statement_id} classification requires a verified comparison")
        _require_text(item["reason"], f"{statement_id}.reason")
        by_statement[statement_id] = item
    if set(by_statement) != accepted:
        raise ValueError("novelty audit must classify every accepted statement exactly once")
    verdict = value.get("overall_verdict")
    if verdict not in AUDIT_VERDICTS:
        raise ValueError(f"invalid novelty-audit verdict: {verdict}")
    _require_list(value.get("limitations"), "novelty audit limitations")
    if verdict == "supported" and not comparisons:
        raise ValueError("supported novelty requires closest-work comparisons")
    if verdict in {"supported", "partial"} and len(verified_comparison_ids) < 2:
        raise ValueError(
            f"{verdict} novelty requires at least two distinct verified technical comparisons"
        )
    classes = {item["classification"] for item in findings}
    if verdict == "supported" and ("unclear" in classes or not classes & NEW_RESEARCH_CLASSES):
        raise ValueError("supported novelty requires a defensible new contribution classification")
    if verdict == "not_novel" and not classes <= ATTRIBUTED_CLASSES:
        raise ValueError("not_novel verdict is inconsistent with the statement classifications")
    return value


def validate_contribution(value: Dict[str, Any], accepted_ids: Iterable[str]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("contribution assessment must be an object")
    accepted = set(accepted_ids)
    if value.get("contribution_type") not in CONTRIBUTION_TYPES:
        raise ValueError(f"invalid contribution_type: {value.get('contribution_type')}")
    if value.get("significance_level") not in SIGNIFICANCE_LEVELS:
        raise ValueError(f"invalid significance_level: {value.get('significance_level')}")
    primary = _require_list(value.get("primary_statement_ids"), "primary_statement_ids")
    if accepted and (not primary or any(statement_id not in accepted for statement_id in primary)):
        raise ValueError("primary_statement_ids must be a non-empty subset of accepted statements")
    if not accepted and (primary or value.get("contribution_type") != "null_result"):
        raise ValueError("a run with no accepted statements must use null_result and no primary statements")
    if accepted and value.get("contribution_type") == "null_result":
        raise ValueError(
            "accepted statements cannot be classified as null_result; use provisional_result "
            "when mathematical value exists but originality remains unverified"
        )
    if value.get("publication_goal") not in PUBLICATION_GOALS:
        raise ValueError("publication_goal is invalid")
    paper_argument = value.get("paper_argument")
    legacy_argument = value.get("paper_story")
    if paper_argument is not None and legacy_argument is not None and paper_argument != legacy_argument:
        raise ValueError("paper_argument conflicts with the legacy paper_story value")
    if paper_argument is None:
        paper_argument = legacy_argument
    if not isinstance(paper_argument, dict):
        raise ValueError("paper_argument must be an object")
    for field in ("central_question", "thesis", "coherence_rationale"):
        _require_text(paper_argument.get(field), f"paper_argument.{field}")
    roles = _require_list(value.get("result_roles"), "result_roles")
    by_statement = {}
    for index, item in enumerate(roles):
        if not isinstance(item, dict):
            raise ValueError(f"result_roles[{index}] must be an object")
        statement_id = _require_text(item.get("statement_id"), f"result_roles[{index}].statement_id")
        if statement_id not in accepted or statement_id in by_statement:
            raise ValueError(f"result_roles has unknown or duplicate statement: {statement_id}")
        if item.get("role") not in RESULT_ROLES:
            raise ValueError(f"{statement_id}.role is invalid")
        if item.get("paper_placement") not in PAPER_PLACEMENTS:
            raise ValueError(f"{statement_id}.paper_placement is invalid")
        dependencies = _require_list(item.get("depends_on"), f"{statement_id}.depends_on")
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"{statement_id}.depends_on contains duplicates")
        if statement_id in dependencies or any(dependency not in accepted for dependency in dependencies):
            raise ValueError(f"{statement_id}.depends_on must reference other accepted statements")
        _require_text(item.get("rationale"), f"{statement_id}.rationale")
        by_statement[statement_id] = item
    if set(by_statement) != accepted:
        raise ValueError("result_roles must classify every accepted statement exactly once")
    visiting, visited = set(), set()

    def visit(statement_id: str) -> None:
        if statement_id in visiting:
            raise ValueError("result_roles.depends_on contains a cycle")
        if statement_id in visited:
            return
        visiting.add(statement_id)
        for dependency in by_statement[statement_id]["depends_on"]:
            visit(dependency)
        visiting.remove(statement_id)
        visited.add(statement_id)

    for statement_id in by_statement:
        visit(statement_id)
    selected = {
        statement_id for statement_id, item in by_statement.items()
        if item["paper_placement"] in {"main", "supporting", "appendix"}
    }
    if accepted and not selected:
        raise ValueError("at least one accepted result must be placed in the selected paper")
    if any(by_statement[statement_id]["paper_placement"] != "main" for statement_id in primary):
        raise ValueError("primary statements must use main paper placement")
    if not set(primary) <= selected:
        raise ValueError("primary statements must be included in the selected paper")
    _require_text(value.get("paper_value"), "paper_value")
    policy = value.get("claim_policy")
    if not isinstance(policy, dict):
        raise ValueError("claim_policy must be an object")
    allowed = _require_list(policy.get("allowed_claims"), "allowed_claims")
    if not allowed or any(not isinstance(item, str) or not item.strip() for item in allowed):
        raise ValueError("allowed_claims must contain non-empty text")
    for field in ("allowed_claims", "prohibited_claims", "required_attribution"):
        entries = _require_list(policy.get(field), field)
        if len(entries) != len(set(entries)) or any(not isinstance(item, str) or not item.strip() for item in entries):
            raise ValueError(f"{field} must contain unique non-empty text")
    obligations = _require_list(value.get("development_obligations"), "development_obligations")
    obligation_ids = set()
    for index, item in enumerate(obligations):
        if not isinstance(item, dict):
            raise ValueError(f"development_obligations[{index}] must be an object")
        obligation_id = _require_text(item.get("id"), f"development_obligations[{index}].id")
        if obligation_id in obligation_ids:
            raise ValueError(f"duplicate development obligation: {obligation_id}")
        obligation_ids.add(obligation_id)
        _require_text(item.get("description"), f"{obligation_id}.description")
        if item.get("priority") not in OBLIGATION_PRIORITIES:
            raise ValueError(f"{obligation_id}.priority is invalid")
    empirical = value.get("empirical_requirements")
    if not isinstance(empirical, dict) or empirical.get("status") not in {"required", "recommended", "not_required"}:
        raise ValueError("empirical_requirements.status must be required, recommended, or not_required")
    _require_text(empirical.get("reason"), "empirical_requirements.reason")
    normalized = dict(value)
    normalized["paper_argument"] = paper_argument
    normalized.pop("paper_story", None)
    return normalized


def validate_significance_audit(value: Dict[str, Any], accepted_ids: Iterable[str]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("significance audit must be an object")
    accepted = set(accepted_ids)
    scope = _require_list(value.get("scope_statement_ids"), "significance scope_statement_ids")
    if len(scope) != len(set(scope)) or set(scope) != accepted:
        raise ValueError("significance audit scope must cover every accepted statement exactly")
    framing = value.get("framing_scope")
    if framing not in FRAMING_SCOPES:
        raise ValueError(f"invalid framing_scope: {framing}")
    _require_text(value.get("claimed_application"), "claimed_application")
    application = value.get("application_evidence")
    if not isinstance(application, dict) or application.get("level") not in EVIDENCE_LEVELS:
        raise ValueError("application_evidence.level is invalid")
    _require_text(application.get("description"), "application_evidence.description")
    supported_claims = _require_list(application.get("supports_claims"), "application_evidence.supports_claims")
    if len(supported_claims) != len(set(supported_claims)) or any(
        claim not in accepted for claim in supported_claims
    ):
        raise ValueError("application_evidence.supports_claims must be unique accepted statement IDs")
    assumptions = _require_list(value.get("assumption_operationalization"), "assumption_operationalization")
    for index, item in enumerate(assumptions):
        if not isinstance(item, dict):
            raise ValueError(f"assumption_operationalization[{index}] must be an object")
        for field in ("assumption", "operational_meaning", "observable", "validated",
                      "misspecification_risk", "evidence"):
            if field not in item:
                raise ValueError(f"assumption_operationalization[{index}] is missing {field}")
        for field in ("assumption", "operational_meaning", "observable", "misspecification_risk", "evidence"):
            _require_text(item[field], f"assumption_operationalization[{index}].{field}")
        if not isinstance(item["validated"], bool):
            raise ValueError(f"assumption_operationalization[{index}].validated must be boolean")
    if accepted and framing != "theory_only" and not assumptions:
        raise ValueError("application framing requires assumption operationalization")
    empirical = value.get("empirical_assessment")
    if not isinstance(empirical, dict) or empirical.get("baseline_strength") not in BASELINE_STRENGTH:
        raise ValueError("empirical_assessment.baseline_strength is invalid")
    checks = (
        "calibration_demonstrated", "error_compute_comparison", "misspecification_test",
        "nonstationary_test", "multistate_test", "real_system_test"
    )
    for field in checks:
        if not isinstance(empirical.get(field), bool):
            raise ValueError(f"empirical_assessment.{field} must be boolean")
    missing_experiments = _require_list(
        empirical.get("missing_experiments"), "empirical_assessment.missing_experiments"
    )
    if any(not isinstance(item, str) or not item.strip() for item in missing_experiments):
        raise ValueError("empirical_assessment.missing_experiments must contain non-empty text")
    if application["level"] == "real_system" and not empirical["real_system_test"]:
        raise ValueError("real_system evidence requires a real_system_test")
    if framing == "application_validated" and application["level"] != "real_system":
        raise ValueError("application_validated framing requires real-system evidence")
    if framing == "application_validated" and not supported_claims:
        raise ValueError("application_validated framing must identify the accepted claims it validates")
    theory = value.get("theory_assessment")
    if not isinstance(theory, dict):
        raise ValueError("theory_assessment must be an object")
    if theory.get("specialization_level") not in SPECIALIZATION_LEVELS:
        raise ValueError("invalid theory_assessment.specialization_level")
    if theory.get("bound_practicality") not in BOUND_PRACTICALITY:
        raise ValueError("invalid theory_assessment.bound_practicality")
    if theory.get("known_parameter_burden") not in PARAMETER_BURDEN:
        raise ValueError("invalid theory_assessment.known_parameter_burden")
    _require_text(theory.get("technical_obstacle"), "theory_assessment.technical_obstacle")
    verdict = value.get("significance_verdict")
    if verdict not in SIGNIFICANCE_LEVELS:
        raise ValueError(f"invalid significance_verdict: {verdict}")
    blockers = _require_list(value.get("blocking_findings"), "significance blocking_findings")
    blocker_ids = set()
    for index, item in enumerate(blockers):
        if not isinstance(item, dict):
            raise ValueError(f"blocking_findings[{index}] must be an object")
        for field in ("id", "severity", "category", "description", "required_action"):
            if field not in item:
                raise ValueError(f"blocking_findings[{index}] is missing {field}")
        blocker_id = _require_text(item["id"], f"blocking_findings[{index}].id")
        if blocker_id in blocker_ids:
            raise ValueError(f"duplicate significance finding: {blocker_id}")
        blocker_ids.add(blocker_id)
        if item["severity"] not in {"minor", "major", "fatal"}:
            raise ValueError(f"invalid significance finding severity: {item['severity']}")
        for field in ("category", "description", "required_action"):
            _require_text(item[field], f"{blocker_id}.{field}")
    if theory["specialization_level"] == "direct_specialization" and verdict == "high":
        raise ValueError("a direct specialization cannot receive high significance without a different primary contribution")
    if any(item["severity"] == "fatal" for item in blockers) and verdict in {"high", "moderate"}:
        raise ValueError("fatal significance blockers are inconsistent with high/moderate significance")
    return value


def _novelty_positioning(audit_verdict: str) -> str:
    """Return the strongest manuscript wording justified by the novelty audit."""
    return {
        "supported": "verified_novelty",
        "partial": "plausible_incremental_novelty",
        "unverified": "uncertain_overlap",
        "not_novel": "attributed_existing_result",
    }[audit_verdict]


def derive_route(
    accepted_ids: Iterable[str],
    novelty: Dict[str, Any],
    significance_audit: Dict[str, Any],
    contribution: Dict[str, Any],
) -> Dict[str, Any]:
    accepted_sequence = list(accepted_ids)
    if any(not isinstance(item, str) or not item.strip() for item in accepted_sequence):
        raise ValueError("accepted_ids must contain non-empty statement IDs")
    if len(accepted_sequence) != len(set(accepted_sequence)):
        raise ValueError("accepted_ids contains duplicates")
    accepted = set(accepted_sequence)
    validate_novelty_audit(novelty, accepted)
    validate_significance_audit(significance_audit, accepted)
    contribution = validate_contribution(contribution, accepted)
    primary = set(contribution["primary_statement_ids"])
    finding_map = {item["statement_id"]: item for item in novelty["findings"]}
    primary_classes = {finding_map[statement_id]["classification"] for statement_id in primary}
    comparisons = {item["id"]: item for item in novelty["closest_work_comparisons"]}
    verified_primary = {
        statement_id for statement_id in primary
        if any(comparisons[evidence_id]["verified"] for evidence_id in finding_map[statement_id]["evidence_ids"])
    }
    audit_verdict = novelty["overall_verdict"]
    significance = significance_audit["significance_verdict"]
    if SIGNIFICANCE_RANK[contribution["significance_level"]] > SIGNIFICANCE_RANK[significance]:
        raise ValueError("contribution significance cannot exceed the independent significance audit")
    contribution_type = contribution["contribution_type"]
    compatible = {
        "novel_theorem": bool(primary_classes & {"novel", "new_extension"}) and primary_classes <= STRONG_ORIGINALITY,
        "incremental_extension": "new_extension" in primary_classes and primary_classes <= STRONG_ORIGINALITY | ATTRIBUTED_CLASSES,
        "synthesis": "new_synthesis" in primary_classes and primary_classes <= {"new_synthesis", "attributed", "standard"},
        "counterexample_negative_result": "new_counterexample" in primary_classes and primary_classes <= STRONG_ORIGINALITY | ATTRIBUTED_CLASSES,
        "empirical_validation": "new_empirical_evidence" in primary_classes and primary_classes <= {"new_empirical_evidence", "attributed", "standard"},
        "expository_result": bool(primary_classes) and primary_classes <= ATTRIBUTED_CLASSES,
        "provisional_result": bool(primary_classes) and primary_classes <= {"unclear"},
        "null_result": not primary_classes,
    }[contribution_type]
    if not compatible:
        raise ValueError("contribution_type is inconsistent with the independent novelty classifications")
    reasons = []
    blocking = significance_audit["blocking_findings"]
    has_fatal = any(item["severity"] == "fatal" for item in blocking)
    has_major = any(item["severity"] == "major" for item in blocking)
    framing = significance_audit["framing_scope"]
    application_level = significance_audit["application_evidence"]["level"]
    empirical = significance_audit["empirical_assessment"]
    theory = significance_audit["theory_assessment"]
    application_ready = framing == "theory_only" or application_level == "real_system"
    parameter_ready = theory["known_parameter_burden"] != "strong" or empirical["misspecification_test"]
    baseline_ready = empirical["baseline_strength"] in {"reasonable", "strong"}
    theoretical_depth_ready = theory["specialization_level"] != "direct_specialization"

    submission_evidence_ready = (
        audit_verdict == "supported"
        and primary <= verified_primary
        and bool(primary_classes & STRONG_ORIGINALITY)
        and primary_classes <= STRONG_ORIGINALITY
        and significance in {"high", "moderate"}
        and contribution_type in {"novel_theorem", "incremental_extension", "counterexample_negative_result"}
        and not has_fatal
        and not has_major
        and application_ready
        and parameter_ready
        and theoretical_depth_ready
        and (framing == "theory_only" or baseline_ready)
    )
    manuscript_kind = "full_paper" if accepted else "evidence_report"
    if accepted and submission_evidence_ready:
        reasons.append(
            "the accepted contribution has sufficient verified evidence for submission-oriented framing"
        )
    elif accepted:
        reasons.append(
            "the accepted mathematics receives a complete full paper; unresolved evidence is recorded "
            "as a submission-readiness limitation rather than a different paper category"
        )
    else:
        reasons.append(
            "no mathematical statement was accepted, so the output documents the complete governed "
            "evidence without claiming an established theorem"
        )

    attribution_required = bool(primary_classes & ATTRIBUTED_CLASSES)
    if attribution_required and not contribution["claim_policy"]["required_attribution"]:
        raise ValueError("attributed or standard primary results require explicit attribution policy")
    if audit_verdict == "not_novel" and accepted:
        reasons.append(
            "the novelty audit requires attributed positioning, but the accepted result still receives a full paper"
        )
    if has_fatal or significance == "insufficient":
        submission_evidence_ready = False
        if accepted:
            reasons.append(
                "significance evidence blocks submission readiness but does not change the full-paper output"
            )
    effective_empirical = dict(contribution["empirical_requirements"])
    empirical_reasons = [effective_empirical["reason"]]
    required_by_audit = False
    if not accepted:
        # An evidence report documents the attempted theorem, audits, and failure
        # evidence.  It must not be blocked on experiments intended to support a
        # theorem claim that was not accepted.
        effective_empirical = {
            "status": "not_required",
            "reason": (
                "No theorem claim was accepted; the required output is an honest "
                "evidence report with a complete appendix."
            ),
        }
    elif framing != "theory_only" and application_level != "real_system":
        required_by_audit = True
        empirical_reasons.append("application framing requires real-system validation")
    if accepted and theory["known_parameter_burden"] == "strong" and not empirical["misspecification_test"]:
        required_by_audit = True
        empirical_reasons.append("a required operational parameter lacks misspecification sensitivity analysis")
    if required_by_audit and EMPIRICAL_RANK[effective_empirical["status"]] < EMPIRICAL_RANK["required"]:
        effective_empirical["status"] = "required"
    if accepted:
        effective_empirical["reason"] = "; ".join(empirical_reasons)
    effective_policy = {
        key: list(value) for key, value in contribution["claim_policy"].items()
    }
    if framing != "theory_only" and application_level != "real_system":
        effective_policy["prohibited_claims"].append(
            "Do not claim validated effectiveness on real LLM or deployed application trajectories."
        )
    if theory["specialization_level"] == "direct_specialization":
        effective_policy["prohibited_claims"].append(
            "Do not claim a fundamentally new concentration or sequential-testing method."
        )
    if accepted and audit_verdict == "partial":
        effective_policy["allowed_claims"].append(
            "Describe the verified incremental theorem-level difference as a contribution, while "
            "stating the remaining closest-work overlap."
        )
    elif accepted and audit_verdict == "unverified":
        effective_policy["allowed_claims"].append(
            "Describe the proved result as a technical contribution and state that its exact "
            "originality relative to the closest work remains unresolved."
        )
        effective_policy["prohibited_claims"].append(
            "Do not use first, unique, or definitive novelty claims until the primary-source "
            "comparison is verified."
        )

    goal = contribution["publication_goal"]
    selected_statement_ids = sorted(
        item["statement_id"] for item in contribution["result_roles"]
        if item["paper_placement"] in {"main", "supporting", "appendix"}
    )
    novelty_required = goal in {"original_research", "workshop_or_short_paper"}
    if goal in {"original_research", "workshop_or_short_paper"}:
        goal_satisfied = submission_evidence_ready
    else:
        goal_satisfied = bool(accepted)
    if goal_satisfied:
        unmet_goal_reasons = []
    elif goal == "original_research":
        unmet_goal_reasons = [
            "The requested full original-research route is not supported by the current novelty, "
            "significance, operational-evidence, and theoretical-depth gates."
        ]
    else:
        unmet_goal_reasons = [
            "The requested workshop or short-paper route is not supported by the current verified "
            "novelty, significance, and theoretical-depth evidence."
        ]
    return {
        "schema_version": 3,
        "manuscript_kind": manuscript_kind,
        # A completed full run always has an evidence-consistent document route.
        # With no accepted statements this is an evidence report, not
        # a theorem manuscript and never a submission candidate.
        "writing_allowed": True,
        "submission_readiness": (
            "ready" if submission_evidence_ready
            else "evidence_incomplete" if accepted
            else "not_applicable"
        ),
        "submission_framing_allowed": submission_evidence_ready,
        # Manuscript completeness is independent of novelty verification.  Every
        # accepted-result route receives a full paper and complete proof appendix;
        # submission readiness remains a separate evidence gate.
        "full_length_allowed": bool(accepted),
        "venue_selection_required": True,
        "venue_selection_context": {
            "contribution_type": contribution_type,
            "manuscript_kind": manuscript_kind,
            "submission_readiness": (
                "ready" if submission_evidence_ready
                else "evidence_incomplete" if accepted
                else "not_applicable"
            ),
            "novelty_verdict": audit_verdict,
            "significance_level": significance,
            "framing_scope": framing,
            "empirical_requirement": effective_empirical["status"],
            "selected_statement_count": len(selected_statement_ids),
        },
        "novelty_positioning": _novelty_positioning(audit_verdict),
        "primary_statement_ids": sorted(primary),
        "selected_statement_ids": selected_statement_ids,
        "publication_goal": goal,
        "novelty_required_by_goal": novelty_required,
        "publication_goal_satisfied": goal_satisfied,
        "unmet_publication_goal_reasons": unmet_goal_reasons,
        "paper_argument": contribution["paper_argument"],
        "result_roles": contribution["result_roles"],
        "originality_classifications": {statement_id: finding_map[statement_id]["classification"] for statement_id in sorted(primary)},
        "novelty_verdict": audit_verdict,
        "significance_level": significance,
        "significance_audit": significance_audit,
        "claim_policy": effective_policy,
        "empirical_requirements": effective_empirical,
        "development_obligations": contribution["development_obligations"],
        "review_blockers": blocking,
        "routing_gates": {
            "novelty_supported": audit_verdict == "supported" and primary <= verified_primary,
            "acceptance_strength_sufficient": significance in {"high", "moderate"},
            "application_evidence_ready": application_ready,
            "parameter_sensitivity_ready": parameter_ready,
            "baseline_evidence_ready": framing == "theory_only" or baseline_ready,
            "theoretical_depth_ready": theoretical_depth_ready,
            "no_major_or_fatal_significance_blocker": not has_major and not has_fatal,
        },
        "routing_reasons": reasons,
    }
