"""
read_proof.py
Read all proof artifacts for an obligation.

Supports two modes:
  full    — returns all artifacts (blueprint, tool_checks, proof_draft, self_critique, metadata)
  summary — returns only metadata + status + gap/claim counts (faster, less context)

Missing artifacts are explicitly marked rather than silently omitted.
"""

import json
from pathlib import Path
from runtime.proof_store import (
    read_metadata, read_blueprint, read_tool_checks,
    read_proof_draft, read_self_critique,
)
from runtime.workspace import get_project_root

VALID_MODES = {"full", "summary"}

SCHEMA = {
    "name": "read_proof",
    "description": (
        "Read proof artifacts for a proof obligation. "
        "mode='summary' returns status + counts only (fast). "
        "mode='full' returns all artifacts including LaTeX draft. "
        "Missing artifacts are marked explicitly."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "po_id": {
                "type": "string",
                "description": "Proof obligation ID e.g. 'PO-1'"
            },
            "mode": {
                "type": "string",
                "enum": ["full", "summary"],
                "description": "full=all artifacts, summary=status+counts only (default: full)"
            }
        },
        "required": ["po_id"]
    }
}


def _load_valid_po_ids():
    """Load valid PO IDs from discovery.json. Returns (set, error_or_None)."""
    try:
        plan_path = get_project_root() / "state" / "discovery.json"
    except Exception:
        plan_path = Path(__file__).parent.parent.parent / "state" / "discovery.json"

    if not plan_path.exists():
        return set(), "discovery.json not found"
    try:
        with open(plan_path) as f:
            plan = json.load(f)
        return {ob["id"] for ob in plan.get("proof_obligations", []) if "id" in ob}, None
    except Exception as e:
        return set(), f"discovery.json unreadable: {e}"


def _mark_missing(value, artifact_name):
    """Return value if non-empty, else a clear MISSING marker."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return f"[MISSING: {artifact_name} not yet written]"
    if isinstance(value, dict) and not value:
        return {"_status": f"[MISSING: {artifact_name} not yet written]"}
    return value


def run(po_id, mode="full"):
    # ── 1. Basic validation ────────────────────────────────────────
    if not po_id or not str(po_id).strip():
        return "ERROR read_proof: po_id is empty"

    if mode not in VALID_MODES:
        return (
            f"ERROR read_proof({po_id}): "
            f"mode '{mode}' invalid. Must be one of: {sorted(VALID_MODES)}"
        )

    # ── 2. PO validation against discovery.json ────────────────────────
    # Warn but don't hard-block — read is safe even without discovery.json
    valid_ids, plan_error = _load_valid_po_ids()
    po_warning = None
    if plan_error:
        po_warning = f"discovery.json unavailable ({plan_error}) — cannot validate po_id"
    elif valid_ids and po_id not in valid_ids:
        return (
            f"ERROR read_proof({po_id}): "
            f"po_id not found in discovery.json. Valid IDs: {sorted(valid_ids)}"
        )

    # ── 3. Read metadata ───────────────────────────────────────────
    try:
        meta = read_metadata(po_id)
    except Exception as e:
        return f"ERROR read_proof({po_id}): failed to read metadata: {e}"

    # ── 4. Summary mode ────────────────────────────────────────────
    if mode == "summary":
        result = {
            "po_id":        po_id,
            "mode":         "summary",
            "status":       meta.get("status", "unstarted"),
            "difficulty":   meta.get("difficulty"),
            "proof_type":   meta.get("proof_type"),
            "technique":    meta.get("technique"),
            "n_gaps":       len(meta.get("gaps", [])),
            "n_claims":     len(meta.get("claims", [])),
            "n_lemmas":     len(meta.get("lemmas", [])),
            "gap_ids":      meta.get("gap_ids", []),
            "has_unsafe_tool_check": meta.get("has_unsafe_tool_check", False),
            "unsafe_tools": meta.get("unsafe_tools", []),
            "dependencies": meta.get("dependencies", []),
            "blocked_by":   meta.get("blocked_by", []),
            "revised":      meta.get("revised", False),
        }
        if po_warning:
            result["warning"] = po_warning
        return json.dumps(result, indent=2, ensure_ascii=False)

    # ── 5. Full mode — read all artifacts ─────────────────────────
    try:
        blueprint = read_blueprint(po_id)
    except Exception as e:
        blueprint = f"[ERROR reading blueprint: {e}]"

    try:
        tool_checks = read_tool_checks(po_id)
    except Exception as e:
        tool_checks = {"error": f"[ERROR reading tool_checks: {e}]"}

    try:
        proof_draft = read_proof_draft(po_id)
    except Exception as e:
        proof_draft = f"[ERROR reading proof_draft: {e}]"

    try:
        self_critique = read_self_critique(po_id)
    except Exception as e:
        self_critique = f"[ERROR reading self_critique: {e}]"

    result = {
        "po_id":        po_id,
        "mode":         "full",
        "metadata":     meta,
        "blueprint":    _mark_missing(blueprint,    "blueprint.md"),
        "tool_checks":  _mark_missing(tool_checks,  "tool_checks.json"),
        "proof_draft":  _mark_missing(proof_draft,  "proof_draft.tex"),
        "self_critique":_mark_missing(self_critique, "self_critique.md"),
    }

    if po_warning:
        result["warning"] = po_warning

    return json.dumps(result, indent=2, ensure_ascii=False)