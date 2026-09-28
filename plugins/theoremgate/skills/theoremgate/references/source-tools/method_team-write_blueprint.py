"""
write_blueprint.py
Strategist writes the proof strategy for an obligation.

Write rules:
- ALLOWED only when status is: unstarted, planned, repair_requested
- FROZEN (rejected) for all other statuses
- Dependencies come from discovery.json DAG — never from Strategist
- Full runtime validation including discovery.json existence check
"""

import json
from pathlib import Path
from runtime.proof_store import read_metadata, write_metadata, write_blueprint as _write_blueprint_file
from runtime.workspace import get_project_root, log_event

# ── Status gates ───────────────────────────────────────────────────────────
ALLOWED_STATUSES = {"unstarted", "planned", "repair_requested"}

FROZEN_STATUSES = {
    "drafted", "partial", "failed",
    "blocked_by_dependency", "conditional_draft",
    "verified_by_attack", "accepted_by_arbiter", "rejected_by_arbiter",
}

# ── Enum values ────────────────────────────────────────────────────────────
VALID_PROOF_TYPES = {
    "decomposition", "concentration", "bias_bound", "rate_balancing",
    "assembly", "high_probability", "lower_bound", "stability",
    "generalization", "existence", "equivalence", "direct_citation",
}

VALID_DIFFICULTIES = {"routine", "moderate", "hard", "open"}

# Proof types where empty expected_assumptions is acceptable
ASSUMPTIONS_OPTIONAL_TYPES = {"direct_citation", "assembly"}


def _load_valid_po_ids():
    """
    Load valid proof obligation IDs from discovery.json.
    Returns (set_of_ids, error_message_or_None).
    """
    try:
        plan_path = get_project_root() / "state" / "discovery.json"
    except Exception:
        plan_path = Path(__file__).parent.parent.parent / "state" / "discovery.json"

    if not plan_path.exists():
        return set(), "discovery.json not found — cannot validate po_id"

    try:
        with open(plan_path) as f:
            plan = json.load(f)
        ids = {ob["id"] for ob in plan.get("proof_obligations", []) if "id" in ob}
        if not ids:
            return set(), "discovery.json has no proof_obligations"
        return ids, None
    except Exception as e:
        return set(), f"discovery.json could not be read: {e}"


SCHEMA = {
    "name": "write_blueprint",
    "description": (
        "Write the proof strategy blueprint for a proof obligation. "
        "Only allowed when status is: unstarted, planned, or repair_requested. "
        "Frozen statuses are rejected. "
        "Does NOT modify dependencies — those come from discovery.json."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "po_id": {
                "type": "string",
                "description": "Proof obligation ID — must exist in discovery.json"
            },
            "proof_type": {
                "type": "string",
                "enum": sorted(VALID_PROOF_TYPES),
            },
            "technique": {
                "type": "string",
                "description": "Primary proof technique"
            },
            "key_steps": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "expected_assumptions": {
                "type": "object",
                "description": "Mapping assumption ID → step where it is used e.g. {'A1': 'Step 2 for independence'}",
                "additionalProperties": {"type": "string"}
            },
            "external_theorems_needed": {
                "type": "array",
                "items": {"type": "string"},
                "description": "External theorems Analyst must fetch and condition-check"
            },
            "may_follow_directly_from": {
                "type": "string",
                "description": "Named result this obligation might follow directly from. Empty if not applicable."
            },
            "dangerous_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Steps most likely to fail and why"
            },
            "difficulty": {
                "type": "string",
                "enum": sorted(VALID_DIFFICULTIES),
            },
            "blueprint_text": {
                "type": "string",
                "description": "Full blueprint in markdown — must be non-empty"
            }
        },
        "required": [
            "po_id", "proof_type", "technique", "key_steps",
            "expected_assumptions", "difficulty", "blueprint_text"
        ]
    }
}


def run(
    po_id,
    proof_type="",
    technique="",
    key_steps=None,
    expected_assumptions=None,
    difficulty="",
    blueprint_text="",
    external_theorems_needed=None,
    may_follow_directly_from="",
    dangerous_steps=None,
    **_ignored,  # tolerate hallucinated/extra params (e.g. expected_dependencies) instead of crashing the run
):
    if _ignored:
        log_event("write_blueprint_extra_args", {"po_id": po_id, "ignored": list(_ignored)})

    errors = []

    # ── 1. Field presence + type validation ────────────────────────
    if not po_id or not str(po_id).strip():
        errors.append("po_id is empty")

    if not blueprint_text or not str(blueprint_text).strip():
        errors.append("blueprint_text is empty — write the actual strategy")

    if not isinstance(key_steps, list) or len(key_steps) == 0:
        errors.append("key_steps must be a non-empty list of strings")

    if not technique or not str(technique).strip():
        errors.append("technique is empty — specify the proof technique")

    # ── 2. Enum validation ─────────────────────────────────────────
    if proof_type not in VALID_PROOF_TYPES:
        errors.append(
            f"proof_type '{proof_type}' is invalid. "
            f"Must be one of: {sorted(VALID_PROOF_TYPES)}"
        )

    if difficulty not in VALID_DIFFICULTIES:
        errors.append(
            f"difficulty '{difficulty}' is invalid. "
            f"Must be one of: {sorted(VALID_DIFFICULTIES)}"
        )

    # ── 3. expected_assumptions validation ────────────────────────
    if not isinstance(expected_assumptions, dict):
        errors.append(
            "expected_assumptions must be a dict mapping assumption ID → step description"
        )
    elif len(expected_assumptions) == 0 and proof_type not in ASSUMPTIONS_OPTIONAL_TYPES:
        errors.append(
            f"expected_assumptions is empty for proof_type '{proof_type}'. "
            f"List which assumptions are used in which steps. "
            f"(Empty is only allowed for: {ASSUMPTIONS_OPTIONAL_TYPES})"
        )

    # ── 4. Optional list field validation ─────────────────────────
    if external_theorems_needed is not None and not isinstance(external_theorems_needed, list):
        errors.append("external_theorems_needed must be a list if provided")

    if dangerous_steps is not None and not isinstance(dangerous_steps, list):
        errors.append("dangerous_steps must be a list if provided")

    # ── Return field-level errors first ──────────────────────────────
    if errors:
        msg = f"ERROR write_blueprint({po_id}): " + "; ".join(errors)
        log_event("write_blueprint_rejected", {"po_id": po_id, "errors": errors})
        return msg

    # ── 5. Status gate — before discovery.json check ────────────────────
    # Check status first so frozen obligations are rejected immediately
    # even when discovery.json is missing or unreadable
    meta = read_metadata(po_id)
    current_status = meta.get("status", "unstarted")

    if current_status in FROZEN_STATUSES:
        msg = (
            f"ERROR write_blueprint({po_id}): status is frozen as '{current_status}'. "
            f"Only the Lab Lead Arbiter can unfreeze via request_repair."
        )
        log_event("write_blueprint_frozen", {"po_id": po_id, "status": current_status})
        return msg

    if current_status not in ALLOWED_STATUSES:
        msg = (
            f"ERROR write_blueprint({po_id}): unexpected status '{current_status}'. "
            f"Allowed: {sorted(ALLOWED_STATUSES)}"
        )
        log_event("write_blueprint_rejected", {"po_id": po_id, "status": current_status})
        return msg

    # ── 6. PO ID existence validation (after status gate) ─────────
    if po_id and str(po_id).strip():
        valid_ids, id_error = _load_valid_po_ids()
        if id_error:
            return f"ERROR write_blueprint({po_id}): {id_error}"
        elif po_id not in valid_ids:
            return (
                f"ERROR write_blueprint({po_id}): "
                f"po_id not found in discovery.json. "
                f"Valid IDs: {sorted(valid_ids)}"
            )

    # ── 7. Prepare metadata updates ────────────────────────────────
    # Never touch meta["dependencies"] — those come from discovery.json
    meta["proof_type"] = proof_type
    meta["technique"] = technique
    meta["key_steps"] = key_steps
    meta["expected_assumptions"] = expected_assumptions
    meta["external_theorems_needed"] = external_theorems_needed or []
    meta["may_follow_directly_from"] = may_follow_directly_from or ""
    meta["dangerous_steps"] = dangerous_steps or []
    meta["difficulty"] = difficulty

    if current_status == "repair_requested":
        meta["repair_blueprint_written"] = True
        # status stays "repair_requested"
    elif current_status == "unstarted":
        meta["status"] = "planned"
    # "planned" stays "planned"

    # ── 8. Atomic write — blueprint file first ─────────────────────
    # Write blueprint file first so if metadata write fails,
    # file is recoverable. Metadata is the authoritative status.
    try:
        _write_blueprint_file(po_id, blueprint_text)
    except Exception as e:
        msg = f"ERROR write_blueprint({po_id}): failed to write blueprint file: {e}"
        log_event("write_blueprint_error", {"po_id": po_id, "error": str(e)})
        return msg

    try:
        write_metadata(po_id, meta)
    except Exception as e:
        msg = f"ERROR write_blueprint({po_id}): blueprint written but metadata failed: {e}"
        log_event("write_blueprint_error", {"po_id": po_id, "error": str(e)})
        return msg

    log_event("write_blueprint", {
        "po_id": po_id,
        "difficulty": difficulty,
        "proof_type": proof_type,
        "status": meta.get("status"),
        "repair_mode": current_status == "repair_requested",
        "may_follow_directly": bool(may_follow_directly_from),
    })

    mode_note = " [repair mode — status preserved]" if current_status == "repair_requested" else ""
    direct_note = (
        f" [check direct result: {may_follow_directly_from}]"
        if may_follow_directly_from else ""
    )
    return (
        f"Blueprint written for {po_id} — "
        f"type: {proof_type}, difficulty: {difficulty}{mode_note}{direct_note}"
    )