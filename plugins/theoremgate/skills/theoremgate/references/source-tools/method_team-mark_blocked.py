"""
mark_blocked.py
The ONLY status update tool for the Method Team.

Method Team can ONLY mark obligations as blocked_by_dependency.
All other status transitions happen through:
  - write_proof_draft  (sets drafted/partial/failed/conditional_draft)
  - Lab Lead Arbiter   (sets repair_requested/accepted/rejected)
  - proof_dag.py       (computes blocking automatically)

This tool is intentionally narrow.
"""

import json
from pathlib import Path
from runtime.proof_store import read_metadata, write_metadata
from runtime.workspace import get_project_root, load_theorem_state, save_theorem_state, log_event

# Only these statuses can be blocked
BLOCKABLE_STATUSES = {"unstarted", "planned", "analysis_in_progress"}

# Statuses that cannot be blocked (already governed)
PROTECTED_STATUSES = {
    "drafted", "partial", "failed", "conditional_draft",
    "repair_requested", "accepted_by_arbiter", "rejected_by_arbiter",
}

SCHEMA = {
    "name": "mark_blocked",
    "description": (
        "Mark a proof obligation as blocked_by_dependency. "
        "Only allowed when current status is: unstarted, planned, analysis_in_progress. "
        "Cannot block obligations already drafted, accepted, or under repair. "
        "blocked_by list must reference real obligations from discovery.json."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "po_id": {
                "type": "string",
                "description": "Obligation to mark as blocked"
            },
            "blocked_by": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "List of upstream obligation IDs causing the block e.g. ['PO-1', 'PO-3']"
            },
            "reason": {
                "type": "string",
                "description": "Why this obligation is blocked"
            }
        },
        "required": ["po_id", "blocked_by", "reason"]
    }
}


def _load_valid_po_ids():
    try:
        plan_path = get_project_root() / "state" / "discovery.json"
    except Exception:
        plan_path = Path(__file__).parent.parent.parent / "state" / "discovery.json"
    if not plan_path.exists():
        return None, "discovery.json not found"
    try:
        with open(plan_path) as f:
            plan = json.load(f)
        return {ob["id"] for ob in plan.get("proof_obligations", []) if "id" in ob}, None
    except Exception as e:
        return None, f"discovery.json unreadable: {e}"


def run(po_id, blocked_by, reason):
    errors = []

    # ── 1. Basic validation ────────────────────────────────────────
    if not po_id or not str(po_id).strip():
        errors.append("po_id is empty")
    if not isinstance(blocked_by, list) or len(blocked_by) == 0:
        errors.append("blocked_by must be a non-empty list")
    if not reason or not str(reason).strip():
        errors.append("reason is empty")

    if errors:
        return "ERROR mark_blocked: " + "; ".join(errors)

    # ── 2. discovery.json validation ────────────────────────────────────
    valid_ids, plan_error = _load_valid_po_ids()
    if plan_error:
        return f"ERROR mark_blocked({po_id}): {plan_error}"

    if valid_ids and po_id not in valid_ids:
        return (
            f"ERROR mark_blocked({po_id}): "
            f"po_id not found in discovery.json. Valid IDs: {sorted(valid_ids)}"
        )

    # Validate each blocking obligation exists
    bad_blockers = [b for b in blocked_by if valid_ids and b not in valid_ids]
    if bad_blockers:
        return (
            f"ERROR mark_blocked({po_id}): "
            f"blocked_by references unknown obligations: {bad_blockers}. "
            f"Valid IDs: {sorted(valid_ids)}"
        )

    # Cannot block itself
    if po_id in blocked_by:
        return f"ERROR mark_blocked({po_id}): obligation cannot block itself"

    # ── 3. Status gate ─────────────────────────────────────────────
    meta = read_metadata(po_id)
    current_status = meta.get("status", "unstarted")

    if current_status in PROTECTED_STATUSES:
        return (
            f"ERROR mark_blocked({po_id}): "
            f"status '{current_status}' is protected — cannot be blocked. "
            f"Only Lab Lead Arbiter can change protected statuses."
        )

    if current_status not in BLOCKABLE_STATUSES and current_status != "unstarted":
        return (
            f"ERROR mark_blocked({po_id}): "
            f"unexpected status '{current_status}'. "
            f"Can only block obligations with status: {sorted(BLOCKABLE_STATUSES)}"
        )

    # ── 4. Write — metadata first, then theorem_state ─────────────
    meta["status"]     = "blocked_by_dependency"
    meta["blocked_by"] = blocked_by
    meta["block_reason"] = reason

    try:
        write_metadata(po_id, meta)
    except Exception as e:
        return f"ERROR mark_blocked({po_id}): metadata write failed: {e}"

    try:
        state = load_theorem_state()
        state.setdefault("proof_obligation_statuses", {})[po_id] = "blocked_by_dependency"
        save_theorem_state(state)
    except Exception as e:
        return (
            f"WARNING mark_blocked({po_id}): metadata written but theorem_state update failed: {e}. "
            f"Run state sync to fix."
        )

    log_event("mark_blocked", {
        "po_id": po_id,
        "blocked_by": blocked_by,
        "previous_status": current_status,
    })

    return (
        f"Marked {po_id} as blocked_by_dependency. "
        f"Blocked by: {blocked_by}. "
        f"Reason: {reason}"
    )