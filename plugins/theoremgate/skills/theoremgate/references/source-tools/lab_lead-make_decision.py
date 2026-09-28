from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from datetime import datetime
from pathlib import Path
import json

# Keys under which the Attack Team flags record the item they target. Any of these,
# wherever they appear in theorem_state, is a legitimate decision target.
_FLAG_TARGET_KEYS = (
    "target_id", "assumption_id", "obligation_id", "po_id",
    "theorem_id", "statement_id", "id",
)


def _load_valid_target_ids():
    """Union of every ID the Arbiter could legitimately decide on.

    = all `{id: ...}` entries in discovery.json (theorems, assumptions, obligations,
      definitions, lemmas — discovered generically, nothing idea-specific hardcoded)
    ∪ every target ID referenced by a flag/counterexample/conflict in theorem_state
    ∪ the special target 'novelty_hypothesis'.

    Returns None on ANY failure so validation fails OPEN — a legitimate decision must
    never be blocked just because a state file was momentarily unreadable.
    """
    try:
        ids = {"novelty_hypothesis"}

        plan_path = Path(__file__).parent.parent.parent / "state" / "discovery.json"
        if plan_path.exists():
            plan = json.loads(plan_path.read_text())
            for value in plan.values():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get("id"):
                            ids.add(str(item["id"]))

        state = load_theorem_state()
        skeptic = state.get("skeptic_flags", {}) or {}

        def _harvest(container):
            if isinstance(container, list):
                for entry in container:
                    if isinstance(entry, dict):
                        for k in _FLAG_TARGET_KEYS:
                            if entry.get(k):
                                ids.add(str(entry[k]))

        for key in ("assumption_flags", "proof_gap_flags"):
            _harvest(skeptic.get(key, []))
        _harvest(state.get("counterexamples", []))
        _harvest(state.get("novelty_conflicts", []))

        # Synthesized statements (written post-proof by the synthesis pass, keys TH-*) are
        # legitimate commit targets too — this is how a proved-but-smaller result gets committed.
        for sid in (state.get("statements", {}) or {}):
            ids.add(str(sid))

        return ids or None
    except Exception:
        return None

SCHEMA = {
    "name": "make_decision",
    "description": "Record a governance decision on a flagged item. Use this for every assumption, proof obligation, theorem, lemma, or novelty conflict that has been flagged by the Attack Team. This writes the decision to theorem_state.json under 'decisions'.",
    "input_schema": {
        "type": "object",
        "properties": {
            "target_id": {
                "type": "string",
                "description": "ID of the item being decided on: assumption ID (e.g. 'A5'), obligation ID (e.g. 'PO-3'), theorem ID (e.g. 'T1'), or 'novelty_hypothesis'",
            },
            "action": {
                "type": "string",
                "enum": ["commit", "weaken", "block", "request_repair", "note"],
                "description": "commit=ready as-is, weaken=downgrade to softer form, block=remove from manuscript, request_repair=send back to Method Team, note=flag acknowledged but no action needed",
            },
            "reason": {
                "type": "string",
                "description": "One clear sentence explaining why this decision was made, referencing the specific flag that triggered it",
            },
            "new_form": {
                "type": "string",
                "description": "For weaken actions: the new weakened form of the statement or assumption. Empty for other actions.",
            },
            "new_status": {
                "type": "string",
                "enum": ["theorem_ready", "proposition_ready", "conjecture_only", "blocked", "repair_requested", "noted"],
                "description": "New epistemic status after decision",
            },
            "flags_addressed": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of flag IDs or descriptions this decision resolves",
            }
        },
        "required": ["target_id", "action", "reason", "new_status"],
    },
}


def run(target_id, action, reason, new_status, new_form="", flags_addressed=None):
    # ── target_id validation — reject hallucinated / typo'd IDs ────────
    # Fail open: only reject when we successfully built the valid set AND the id is absent.
    valid_ids = _load_valid_target_ids()
    if valid_ids is not None and target_id not in valid_ids:
        log_event("make_decision_unknown_target", {
            "target_id": target_id, "action": action,
        })
        sample = sorted(valid_ids)
        return (
            f"ERROR make_decision({target_id}): '{target_id}' is not a known target. "
            f"It must be an ID from the plan (a theorem, assumption, proof obligation, "
            f"definition, or lemma), a target flagged by the Attack Team, or "
            f"'novelty_hypothesis'. Valid targets: {sample}"
        )

    state = load_theorem_state()
    state.setdefault("decisions", {})

    decision = {
        "action": action,
        "reason": reason,
        "new_status": new_status,
        "new_form": new_form,
        "flags_addressed": flags_addressed or [],
        "decided_by": "lab_lead_arbiter",
        "decided_at": datetime.utcnow().isoformat(),
    }

    state["decisions"][target_id] = decision
    save_theorem_state(state)

    # If this is a repair request on a proof obligation, unfreeze its proof metadata so the
    # Method Team repair round can re-blueprint it. write_blueprint gates on metadata.json
    # status (frozen for drafted/partial/failed/blocked); 'repair_requested' is allowed.
    # Without this, a repair decision recorded here never actually reopens the proof.
    if action == "request_repair":
        try:
            from runtime.proof_store import read_metadata, write_metadata, get_proof_dir
            if get_proof_dir(target_id).exists():
                meta = read_metadata(target_id)
                meta["status"] = "repair_requested"
                meta["repair_reason"] = reason
                write_metadata(target_id, meta)
        except Exception as e:
            log_event("make_decision_unfreeze_error", {"target_id": target_id, "error": str(e)})

    log_event("arbiter_decision", {
        "target_id": target_id,
        "action": action,
        "new_status": new_status,
    })

    return f"Decision recorded: {target_id} → {action} ({new_status})"