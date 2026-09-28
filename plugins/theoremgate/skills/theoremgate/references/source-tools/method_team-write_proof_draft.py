r"""
write_proof_draft.py
Proof Writer writes the structured LaTeX proof draft for an obligation.

Safety rules:
- discovery.json + PO validation FIRST (hard block if missing)
- Status gate SECOND (only planned, analysis_in_progress, repair_requested)
- Failed status handled AFTER all validation passes
- Unsafe tool state recomputed from tool_checks.json (not metadata cache)
- Status enforced from gap severity: minor->partial/drafted, major->partial, fatal->failed
- GAP/CLAIM/LEMMA IDs validated: format PO3->GAP-PO3-XX + presence in proof_latex
- Gap severity validated at runtime
- Assumption IDs validated against discovery.json
- proof structure (begin/end proof) required unless status=failed
- Files written only after all validation passes
- Repair mode: marks revised=True
"""

import json
from pathlib import Path
from runtime.proof_store import (
    write_proof_draft as _write_proof_file,
    write_self_critique as _write_critique_file,
    read_metadata, write_metadata,
    read_tool_checks,
)
from runtime.workspace import get_project_root, log_event

# ── Status gates ───────────────────────────────────────────────────────────
ALLOWED_WRITE_STATUSES = {"planned", "analysis_in_progress", "repair_requested"}

FROZEN_WRITE_STATUSES = {
    "unstarted",
    "drafted", "partial", "failed",
    "blocked_by_dependency", "conditional_draft",
    "accepted_by_arbiter", "rejected_by_arbiter",
}

VALID_OUTPUT_STATUSES = {"drafted", "partial", "failed", "conditional_draft"}
VALID_GAP_SEVERITIES  = {"minor", "major", "fatal"}

# ── Gap severity → required output status ─────────────────────────────────
# fatal  → must be "failed"
# major  → must be "partial" (not "drafted")
# minor  → "partial" or "drafted" (depends on tool safety)
# none   → "drafted" (if tool checks all safe)


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
    return {ob["id"] for ob in plan.get("proof_obligations", []) if "id" in ob}


def _load_valid_assumption_ids(plan):
    return {a["id"] for a in plan.get("assumptions", []) if "id" in a}


def _normalize_po(po_id):
    """PO-3 -> PO3,  PO-10 -> PO10."""
    return po_id.replace("-", "")


def _recompute_unsafe_from_tool_checks(po_id):
    """
    Recompute unsafe tool state directly from tool_checks.json.
    Returns (has_unsafe: bool, unsafe_names: list[str])
    Ignores metadata cache to avoid stale state.
    """
    data = read_tool_checks(po_id)
    unsafe = sorted({
        t["theorem_name"]
        for t in data.get("tools", [])
        if not t.get("computed_safe_to_use", True)
    })
    return len(unsafe) > 0, unsafe


def _compute_required_status(gaps, has_unsafe):
    """
    Compute minimum allowed output status from gap severity + tool safety.
    Returns (required_status: str, reason: str)
    """
    if not gaps and not has_unsafe:
        return "drafted", "no gaps, all tool checks safe"

    severities = {g.get("severity", "minor") for g in gaps}

    if "fatal" in severities:
        return "failed", "contains fatal gaps — proof cannot proceed"
    if "major" in severities:
        return "partial", "contains major gaps"
    if has_unsafe:
        return "partial", "has unsafe tool checks"
    # only minor gaps
    return "partial", "has minor gaps"


def _validate_tag_ids(po_id, tags, tag_type, proof_latex, errors):
    """
    Validate tag IDs:
    1. Format must be TAG-PON-XX  (e.g. GAP-PO3-01)
    2. Must appear as [TAG-PON-XX] in proof_latex
    """
    po_norm   = _normalize_po(po_id)          # PO3
    prefix    = f"{tag_type}-{po_norm}-"       # GAP-PO3-
    id_field  = f"{tag_type.lower()}_id"

    for tag in tags:
        tag_id = tag.get(id_field, "")
        if not tag_id:
            errors.append(f"{tag_type} entry missing '{id_field}' field")
            continue
        if not tag_id.startswith(prefix):
            errors.append(
                f"{tag_type} ID '{tag_id}' must start with '{prefix}' "
                f"(e.g. {prefix}01) for obligation {po_id}"
            )
        if f"[{tag_id}]" not in proof_latex:
            errors.append(
                f"{tag_type} ID '{tag_id}' listed in metadata but "
                f"'[{tag_id}]' not found in proof_latex"
            )


def _validate_gap_severities(gaps, errors):
    for g in gaps:
        sev = g.get("severity", "")
        if sev not in VALID_GAP_SEVERITIES:
            errors.append(
                f"Gap '{g.get('gap_id', '?')}' has invalid severity '{sev}'. "
                f"Must be one of: {sorted(VALID_GAP_SEVERITIES)}"
            )


SCHEMA = {
    "name": "write_proof_draft",
    "description": (
        "Write the structured LaTeX proof draft for an obligation. "
        "All validation (discovery.json, status gate, gap severity, tool safety) "
        "runs before any file is written. "
        "Failed status is handled after validation — not as an early bypass. "
        "Status is enforced: fatal gaps require 'failed', major require 'partial'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "po_id": {
                "type": "string",
                "description": "Proof obligation ID — must exist in discovery.json"
            },
            "proof_latex": {
                "type": "string",
                "description": (
                    "Full LaTeX proof draft. Required unless status='failed'. "
                    "Must contain \\begin{proof}...\\end{proof}. "
                    "Tag gaps: % [GAP-PO3-01]: description"
                )
            },
            "assumption_usage": {
                "type": "object",
                "description": "Assumption ID -> step description. e.g. {'A1': 'Step 2 for independence'}",
                "additionalProperties": {"type": "string"}
            },
            "gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "gap_id":      {"type": "string"},
                        "description": {"type": "string"},
                        "severity":    {"type": "string", "enum": ["minor", "major", "fatal"]}
                    },
                    "required": ["gap_id", "description", "severity"]
                }
            },
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim_id":   {"type": "string"},
                        "statement":  {"type": "string"},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]}
                    },
                    "required": ["claim_id", "statement", "confidence"]
                }
            },
            "lemmas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "lemma_id":     {"type": "string"},
                        "statement":    {"type": "string"},
                        "proof_status": {"type": "string"}
                    },
                    "required": ["lemma_id", "statement"]
                }
            },
            "self_critique": {
                "type": "string",
                "description": "Honest: weakest step, what could break, what is missing"
            },
            "status": {
                "type": "string",
                "enum": ["drafted", "partial", "failed", "conditional_draft"],
                "description": (
                    "drafted: complete draft, safe tool checks, no fatal/major gaps. "
                    "partial: major gaps or unsafe tool checks. "
                    "failed: fatal gaps or cannot produce strategy. "
                    "conditional_draft: depends on upstream partial."
                )
            },
            "failure_reason": {
                "type": "string",
                "description": "Required when status='failed'. Explain why."
            },
            "tool_check_ids_used": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "check_ids of tool checks used in this proof. "
                    "e.g. ['CHECK-PO3-01', 'CHECK-PO3-02']. "
                    "Use check_id from write_tool_check output, not theorem names. "
                    "Pass empty list [] explicitly if no external theorems used."
                )
            }
        },
        "required": ["po_id", "assumption_usage", "self_critique", "status"]
    }
}


def run(
    po_id,
    assumption_usage=None,
    self_critique="",
    status="",
    proof_latex="",
    gaps=None,
    claims=None,
    lemmas=None,
    failure_reason="",
    tool_check_ids_used=None,
    **_ignored,  # tolerate hallucinated/extra params instead of crashing the run
):
    gaps                = gaps or []
    claims              = claims or []
    lemmas              = lemmas or []
    tool_check_ids_used = tool_check_ids_used or []
    errors              = []

    # ── 1. Basic field presence ────────────────────────────────────
    if not po_id or not str(po_id).strip():
        errors.append("po_id is empty")

    if not self_critique or not str(self_critique).strip():
        errors.append("self_critique is empty — provide honest assessment")

    if status not in VALID_OUTPUT_STATUSES:
        errors.append(
            f"status '{status}' invalid. Must be one of: {sorted(VALID_OUTPUT_STATUSES)}"
        )

    if not isinstance(assumption_usage, dict):
        errors.append("assumption_usage must be a dict")

    if errors:
        return "ERROR write_proof_draft: " + "; ".join(errors)

    # ── 2. discovery.json validation (hard block) ───────────────────────
    plan, plan_error = _load_plan()
    if plan_error:
        return (
            f"ERROR write_proof_draft({po_id}): "
            f"cannot proceed without discovery.json: {plan_error}"
        )

    valid_po_ids = _load_valid_po_ids(plan)
    if valid_po_ids and po_id not in valid_po_ids:
        return (
            f"ERROR write_proof_draft({po_id}): "
            f"po_id not found in discovery.json. Valid IDs: {sorted(valid_po_ids)}"
        )

    # ── 3. Status gate ─────────────────────────────────────────────
    meta           = read_metadata(po_id)
    current_status = meta.get("status", "unstarted")

    if current_status in FROZEN_WRITE_STATUSES:
        return (
            f"ERROR write_proof_draft({po_id}): "
            f"status is frozen as '{current_status}'. "
            f"Only Lab Lead Arbiter can unfreeze via request_repair."
        )

    if current_status not in ALLOWED_WRITE_STATUSES:
        return (
            f"ERROR write_proof_draft({po_id}): "
            f"unexpected current status '{current_status}'. "
            f"Allowed: {sorted(ALLOWED_WRITE_STATUSES)}"
        )

    # ── 4. Assumption ID validation ────────────────────────────────
    valid_assumption_ids = _load_valid_assumption_ids(plan)
    if valid_assumption_ids:
        bad_asms = [k for k in assumption_usage if k not in valid_assumption_ids]
        if bad_asms:
            errors.append(
                f"Invalid assumption IDs in assumption_usage: {bad_asms}. "
                f"Valid: {sorted(valid_assumption_ids)}"
            )

    # ── 5. Gap severity runtime validation ─────────────────────────
    _validate_gap_severities(gaps, errors)

    # ── 6. Failed status branch — AFTER all validation above ───────
    if status == "failed":
        if not failure_reason or not str(failure_reason).strip():
            errors.append(
                "failure_reason required when status='failed'. "
                "Explain why the proof cannot be written."
            )
        if errors:
            return "ERROR write_proof_draft: " + "; ".join(errors)

        # Recompute unsafe tool state even for failed proofs
        has_unsafe_fail, unsafe_names_fail = _recompute_unsafe_from_tool_checks(po_id)

        # Write failure record only (no proof_latex needed)
        meta["status"]                = "failed"
        meta["failure_reason"]        = failure_reason
        meta["self_critique"]         = self_critique
        meta["gaps"]                  = gaps
        meta["has_unsafe_tool_check"] = has_unsafe_fail
        meta["unsafe_tools"]          = unsafe_names_fail
        if current_status == "repair_requested":
            meta["revised"] = True
        write_metadata(po_id, meta)
        log_event("write_proof_draft_failed", {"po_id": po_id, "reason": failure_reason})
        return f"Proof marked as failed for {po_id}. Reason: {failure_reason}"

    # ── 7. proof_latex required for non-failed statuses ───────────
    if not proof_latex or not str(proof_latex).strip():
        errors.append(
            "proof_latex is empty. "
            "Write the LaTeX draft or use status='failed' with failure_reason."
        )
        return "ERROR write_proof_draft: " + "; ".join(errors)

    # ── 8. Proof structure check ───────────────────────────────────
    if r"\begin{proof}" not in proof_latex:
        errors.append(r"proof_latex must contain \begin{proof}")
    if r"\end{proof}" not in proof_latex:
        errors.append(r"proof_latex must contain \end{proof}")

    # ── 9. GAP/CLAIM/LEMMA ID format + presence in LaTeX ──────────
    _validate_tag_ids(po_id, gaps,   "GAP",   proof_latex, errors)
    _validate_tag_ids(po_id, claims, "CLAIM", proof_latex, errors)
    _validate_tag_ids(po_id, lemmas, "LEMMA", proof_latex, errors)

    # ── 10. Recompute unsafe tool state from tool_checks.json ──────
    has_unsafe, unsafe_names = _recompute_unsafe_from_tool_checks(po_id)

    # ── 11. Validate tool_check_ids_used against stored checks ─────
    if tool_check_ids_used:
        stored_check_ids = {
            t.get("check_id", "")
            for t in read_tool_checks(po_id).get("tools", [])
        }
        bad_ids = [cid for cid in tool_check_ids_used if cid not in stored_check_ids]
        if bad_ids:
            errors.append(
                f"tool_check_ids_used references unknown check_ids: {bad_ids}. "
                f"Known IDs: {sorted(stored_check_ids)}"
            )

    # ── 12. Enforce status from gap severity + tool safety ─────────
    required_status, status_reason = _compute_required_status(gaps, has_unsafe)

    STATUS_RANK = {"drafted": 0, "partial": 1, "failed": 2, "conditional_draft": 1}
    claimed_rank  = STATUS_RANK.get(status, 0)
    required_rank = STATUS_RANK.get(required_status, 0)

    if claimed_rank < required_rank:
        errors.append(
            f"Status '{status}' not allowed: {status_reason}. "
            f"Must use at least '{required_status}'."
        )

    # ── 13. conditional_draft requires upstream partial dependency ──
    if status == "conditional_draft":
        upstream_deps = meta.get("dependencies", [])
        if not upstream_deps:
            errors.append(
                "Status 'conditional_draft' requires at least one upstream dependency. "
                "This obligation has no dependencies — use 'partial' instead."
            )
        else:
            # Check if any upstream dependency is actually partial/unresolved
            from runtime.proof_store import read_metadata as _rm
            partial_deps = [
                d for d in upstream_deps
                if _rm(d).get("status") in ("partial", "conditional_draft", "unstarted", "planned")
            ]
            if not partial_deps:
                errors.append(
                    f"Status 'conditional_draft' requires at least one upstream dependency "
                    f"to be unresolved (partial/unstarted). "
                    f"All dependencies {upstream_deps} are resolved — use 'partial' or 'drafted'."
                )

    if errors:
        msg = f"ERROR write_proof_draft({po_id}): " + "; ".join(errors)
        log_event("write_proof_draft_rejected", {"po_id": po_id, "errors": errors})
        return msg

    # ── 13. All validation passed — write files ────────────────────
    try:
        _write_proof_file(po_id, proof_latex)
    except Exception as e:
        return f"ERROR write_proof_draft({po_id}): failed to write proof file: {e}"

    try:
        _write_critique_file(po_id, self_critique)
    except Exception as e:
        return f"ERROR write_proof_draft({po_id}): proof written but critique failed: {e}"

    # ── 14. Update metadata ────────────────────────────────────────
    meta["status"]               = status
    meta["assumption_usage"]     = assumption_usage
    meta["gaps"]                 = gaps
    meta["claims"]               = claims
    meta["lemmas"]               = lemmas
    meta["gap_ids"]              = [g["gap_id"]   for g in gaps   if "gap_id"   in g]
    meta["claim_ids"]            = [c["claim_id"] for c in claims if "claim_id" in c]
    meta["lemma_ids"]            = [l["lemma_id"] for l in lemmas if "lemma_id" in l]
    meta["tool_check_ids_used"]  = tool_check_ids_used
    meta["has_unsafe_tool_check"] = has_unsafe
    meta["unsafe_tools"]         = unsafe_names

    if current_status == "repair_requested":
        meta["revised"]          = True
        meta["repair_resolved"]  = True

    write_metadata(po_id, meta)

    log_event("write_proof_draft", {
        "po_id":        po_id,
        "status":       status,
        "n_gaps":       len(gaps),
        "n_claims":     len(claims),
        "has_unsafe":   has_unsafe,
        "repair_mode":  current_status == "repair_requested",
    })

    gap_summary  = (
        f"{len(gaps)} gaps ({', '.join(g.get('severity','?') for g in gaps)})"
        if gaps else "no gaps"
    )
    repair_note = " [repair — revised=True]" if current_status == "repair_requested" else ""
    return (
        f"Proof draft written for {po_id} — "
        f"status: {status}, {gap_summary}{repair_note}"
    )