"""
write_tool_check.py
Analyst records a theorem condition check for a proof obligation.

Safety rules:
- Only allowed when obligation status is: planned, repair_requested, analysis_in_progress
- Computes safe_to_use from condition_checks (does not trust LLM)
- Validates all required_conditions have a matching condition_check
- Validates assumption IDs against discovery.json
- Prevents duplicate theorem checks (deduplicates by theorem_name + needed_for)
- Updates obligation metadata when unsafe theorems found
- Requires theorem_statement and source_type for provenance
- Requires alternative_if_unsafe when safe_to_use is False
"""

import json
from pathlib import Path
from runtime.proof_store import read_metadata, write_metadata, read_tool_checks, write_tool_checks
from runtime.workspace import get_project_root, log_event

# ── Status gates ───────────────────────────────────────────────────────────
ALLOWED_STATUSES = {"planned", "repair_requested", "analysis_in_progress"}
# Note: orchestrator sets analysis_in_progress before calling Analyst stage

FROZEN_STATUSES = {
    "unstarted",          # Strategist hasn't planned yet
    "drafted", "partial", "failed",
    "blocked_by_dependency", "conditional_draft",
    "accepted_by_arbiter", "rejected_by_arbiter",
}

VALID_SOURCE_TYPES = {
    "local_bib", "arxiv", "pmlr", "jmlr", "acl",
    "semantic_scholar", "neurips", "iclr", "icml", "web"
}


def _load_plan():
    try:
        plan_path = get_project_root() / "state" / "discovery.json"
    except Exception:
        plan_path = Path(__file__).parent.parent.parent / "state" / "discovery.json"

    if not plan_path.exists():
        return None, "discovery.json not found"
    try:
        with open(plan_path) as f:
            return json.load(f), None
    except Exception as e:
        return None, f"discovery.json unreadable: {e}"


def _load_valid_po_ids(plan):
    if not plan:
        return set()
    return {ob["id"] for ob in plan.get("proof_obligations", []) if "id" in ob}


def _load_valid_assumption_ids(plan):
    if not plan:
        return set()
    return {a["id"] for a in plan.get("assumptions", []) if "id" in a}


def _make_check_id(po_id, existing_checks):
    n = len(existing_checks) + 1
    return f"CHECK-{po_id}-{n:02d}"


def _compute_safe_to_use(required_conditions, condition_checks):
    """
    Compute safe_to_use from condition_checks.
    Returns (computed_safe: bool, issues: list[str])
    """
    issues = []

    # Every required condition must have a check
    for cond in required_conditions:
        if cond not in condition_checks:
            issues.append(f"Required condition '{cond}' has no condition_check entry")

    if issues:
        return False, issues

    # All checked conditions must be satisfied
    for cond, check in condition_checks.items():
        if not isinstance(check, dict):
            issues.append(f"condition_checks['{cond}'] must be a dict")
            continue
        if "satisfied" not in check:
            issues.append(f"condition_checks['{cond}'] missing 'satisfied' field")
        elif not check["satisfied"]:
            issues.append(f"Condition '{cond}' is not satisfied: {check.get('reason', 'no reason given')}")

    computed_safe = len(issues) == 0
    return computed_safe, issues


SCHEMA = {
    "name": "write_tool_check",
    "description": (
        "Record whether an external theorem's conditions are satisfied for a proof obligation. "
        "safe_to_use is computed from condition_checks — not trusted from input. "
        "Every required_condition must have a matching entry in condition_checks. "
        "Only allowed when obligation status is: planned, repair_requested, analysis_in_progress."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "po_id": {
                "type": "string",
                "description": "Proof obligation ID — must exist in discovery.json"
            },
            "theorem_name": {
                "type": "string",
                "description": "Full name of the theorem e.g. 'Matrix Bernstein inequality'"
            },
            "theorem_statement": {
                "type": "string",
                "description": "Short formal statement of the theorem — copy from the paper. Required for traceability."
            },
            "source": {
                "type": "string",
                "description": "Citation e.g. 'Tropp 2012, Theorem 1.4'"
            },
            "source_url": {
                "type": "string",
                "description": "URL where this theorem was fetched — required for provenance"
            },
            "source_type": {
                "type": "string",
                "enum": sorted(VALID_SOURCE_TYPES),
                "description": "Provenance category of the source"
            },
            "needed_for": {
                "type": "string",
                "description": "Which proof step needs this theorem e.g. 'PO-3 Step 4: variance control'"
            },
            "required_conditions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "All conditions required by the theorem — must be exhaustive"
            },
            "condition_checks": {
                "type": "object",
                "description": (
                    "For each condition in required_conditions: "
                    "{'satisfied': bool, 'reason': str, 'assumption_used': str}. "
                    "Every required condition must have an entry here."
                ),
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "satisfied": {"type": "boolean"},
                        "reason": {"type": "string"},
                        "assumption_used": {"type": "string"}
                    },
                    "required": ["satisfied", "reason"]
                }
            },
            "alternative_if_unsafe": {
                "type": "string",
                "description": (
                    "Required when any condition fails: what to use instead. "
                    "Use 'none found' if no alternative is known."
                )
            }
        },
        "required": [
            "po_id", "theorem_name", "theorem_statement", "source",
            "source_url", "source_type", "needed_for",
            "required_conditions", "condition_checks"
        ]
    }
}


def run(
    po_id,
    theorem_name,
    theorem_statement,
    source,
    source_url,
    source_type,
    needed_for,
    required_conditions,
    condition_checks,
    alternative_if_unsafe="",
    **_ignored,  # tolerate hallucinated/extra params instead of crashing the run
):
    errors = []

    # ── 1. Field presence validation ───────────────────────────────
    if not po_id or not str(po_id).strip():
        errors.append("po_id is empty")
    if not theorem_name or not str(theorem_name).strip():
        errors.append("theorem_name is empty")
    if not theorem_statement or not str(theorem_statement).strip():
        errors.append("theorem_statement is empty — copy the formal statement from the paper")
    if not source or not str(source).strip():
        errors.append("source is empty — provide author/year/theorem number")
    if not source_url or not str(source_url).strip():
        errors.append("source_url is empty — provide the URL where this was fetched")
    if not needed_for or not str(needed_for).strip():
        errors.append("needed_for is empty — specify which proof step needs this")

    # ── 2. Enum validation ─────────────────────────────────────────
    if source_type not in VALID_SOURCE_TYPES:
        errors.append(
            f"source_type '{source_type}' invalid. "
            f"Must be one of: {sorted(VALID_SOURCE_TYPES)}"
        )

    # ── 3. Required conditions validation ─────────────────────────
    if not isinstance(required_conditions, list) or len(required_conditions) == 0:
        errors.append("required_conditions must be a non-empty list")

    if not isinstance(condition_checks, dict):
        errors.append("condition_checks must be a dict")

    # ── Return early if basic structure is broken ──────────────────
    if errors:
        msg = f"ERROR write_tool_check({po_id}): " + "; ".join(errors)
        log_event("write_tool_check_rejected", {"po_id": po_id, "errors": errors})
        return msg

    # ── 4. Status gate — before plan check ───────────────────────────
    meta = read_metadata(po_id)
    current_status = meta.get("status", "unstarted")

    if current_status in FROZEN_STATUSES:
        msg = (
            f"ERROR write_tool_check({po_id}): "
            f"status is frozen as '{current_status}'. "
            f"Analyst cannot modify frozen obligations."
        )
        log_event("write_tool_check_frozen", {"po_id": po_id, "status": current_status})
        return msg

    if current_status not in ALLOWED_STATUSES:
        msg = (
            f"ERROR write_tool_check({po_id}): "
            f"unexpected status '{current_status}'. "
            f"Allowed: {sorted(ALLOWED_STATUSES)}"
        )
        log_event("write_tool_check_rejected", {"po_id": po_id, "status": current_status})
        return msg

    # ── 6. Load plan + PO/assumption validation ──────────────────────
    plan, plan_error = _load_plan()
    if plan_error:
        log_event("write_tool_check_no_plan", {"po_id": po_id, "error": plan_error})
        return f"ERROR write_tool_check({po_id}): cannot validate without discovery.json: {plan_error}"

    # ── 7. PO ID existence validation ─────────────────────────────
    if plan:
        valid_po_ids = _load_valid_po_ids(plan)
        if valid_po_ids and po_id not in valid_po_ids:
            return (
                f"ERROR write_tool_check({po_id}): "
                f"po_id not found in discovery.json. "
                f"Valid IDs: {sorted(valid_po_ids)}"
            )

    # ── 8. Validate assumption IDs ─────────────────────────────────
    valid_assumption_ids = _load_valid_assumption_ids(plan)
    bad_assumptions = []
    if valid_assumption_ids:
        for cond, check in condition_checks.items():
            if isinstance(check, dict):
                asm = check.get("assumption_used", "")
                if asm and asm not in valid_assumption_ids:
                    bad_assumptions.append(f"'{asm}' (in condition '{cond}')")
    if bad_assumptions:
        errors.append(
            f"Invalid assumption IDs in condition_checks: {bad_assumptions}. "
            f"Valid IDs: {sorted(valid_assumption_ids)}"
        )

    # ── 9. Exact condition key matching ──────────────────────────────
    req_set = set(required_conditions)
    check_set = set(condition_checks.keys())
    if req_set != check_set:
        extra = sorted(check_set - req_set)
        missing = sorted(req_set - check_set)
        parts = []
        if missing:
            parts.append(f"missing checks for: {missing}")
        if extra:
            parts.append(f"extra unchecked conditions: {extra}")
        errors.append(
            "condition_checks keys must exactly match required_conditions. " +
            "; ".join(parts)
        )

    # ── 10. Validate satisfied is boolean + reason is non-empty ────
    for cond, check in condition_checks.items():
        if not isinstance(check, dict):
            errors.append(f"condition_checks['{cond}'] must be a dict")
            continue
        if "satisfied" not in check:
            errors.append(f"condition_checks['{cond}'] missing 'satisfied' field")
        elif not isinstance(check["satisfied"], bool):
            errors.append(
                f"condition_checks['{cond}']['satisfied'] must be boolean True/False, "
                f"got {type(check['satisfied']).__name__}: {check['satisfied']!r}"
            )
        reason = check.get("reason", "")
        if not reason or not str(reason).strip():
            errors.append(
                f"condition_checks['{cond}']['reason'] is empty — "
                f"provide a non-empty justification for proof auditing"
            )

    if errors:
        msg = f"ERROR write_tool_check({po_id}): " + "; ".join(errors)
        log_event("write_tool_check_rejected", {"po_id": po_id, "errors": errors})
        return msg

    # ── 11. Compute safe_to_use from condition_checks ───────────────
    computed_safe, safety_issues = _compute_safe_to_use(
        required_conditions, condition_checks
    )

    # ── 12. Require alternative when unsafe ────────────────────────
    if not computed_safe:
        if not alternative_if_unsafe or not str(alternative_if_unsafe).strip():
            errors.append(
                "alternative_if_unsafe is required when conditions are not satisfied. "
                "Provide an alternative theorem or write 'none found'."
            )

    if errors:
        msg = f"ERROR write_tool_check({po_id}): " + "; ".join(errors)
        log_event("write_tool_check_rejected", {"po_id": po_id, "errors": errors})
        return msg

    # ── 13. Deduplication — replace existing check if same theorem ─
    tool_checks = read_tool_checks(po_id)
    existing_tools = tool_checks.setdefault("tools", [])

    # Find existing check with same theorem_name + needed_for
    existing_idx = None
    for i, t in enumerate(existing_tools):
        if (t.get("theorem_name") == theorem_name and t.get("source") == source and t.get("needed_for") == needed_for):
            existing_idx = i
            break

    check_id = (
        existing_tools[existing_idx].get("check_id")
        if existing_idx is not None
        else _make_check_id(po_id, existing_tools)
    )

    record = {
        "check_id": check_id,
        "theorem_name": theorem_name,
        "theorem_statement": theorem_statement,
        "source": source,
        "source_url": source_url,
        "source_type": source_type,
        "needed_for": needed_for,
        "required_conditions": required_conditions,
        "condition_checks": condition_checks,
        "computed_safe_to_use": computed_safe,
        "safety_issues": safety_issues,
        "alternative_if_unsafe": alternative_if_unsafe if not computed_safe else "",
    }

    if existing_idx is not None:
        existing_tools[existing_idx] = record
        action = "updated"
    else:
        existing_tools.append(record)
        action = "added"

    write_tool_checks(po_id, tool_checks)

    # ── 14. Recompute unsafe metadata from all records ────────────
    all_unsafe = sorted({
        t["theorem_name"]
        for t in existing_tools
        if not t.get("computed_safe_to_use", True)
    })
    meta["has_unsafe_tool_check"] = len(all_unsafe) > 0
    meta["unsafe_tools"] = all_unsafe
    write_metadata(po_id, meta)

    log_event("write_tool_check", {
        "po_id": po_id,
        "check_id": check_id,
        "theorem": theorem_name,
        "computed_safe": computed_safe,
        "source_type": source_type,
        "action": action,
    })

    if not computed_safe:
        return (
            f"WARNING [{check_id}]: '{theorem_name}' is NOT safe to use for {po_id}. "
            f"Issues: {safety_issues}. "
            f"Alternative: {alternative_if_unsafe}. "
            f"Proof Writer must NOT use this theorem as if valid."
        )

    return (
        f"OK [{check_id}]: '{theorem_name}' ({source}) — "
        f"all {len(required_conditions)} conditions satisfied. "
        f"Safe to use for {po_id} ✓"
    )