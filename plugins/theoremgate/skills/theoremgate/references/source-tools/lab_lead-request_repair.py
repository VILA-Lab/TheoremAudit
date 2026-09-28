from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from runtime.proof_store import read_metadata, write_metadata

SCHEMA = {
    "name": "request_repair",
    "description": "Flag a proof obligation as needing repair. Does not commit — signals to Method Team.",
    "input_schema": {
        "type": "object",
        "properties": {
            "obligation_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["obligation_id", "reason"],
    },
}


def run(obligation_id: str, reason: str) -> str:
    state = load_theorem_state()
    state.setdefault("proof_obligations", {}).setdefault(obligation_id, {})["repair_requested"] = reason
    save_theorem_state(state)

    # CRITICAL: also unfreeze the proof's metadata status so the Method Team repair round
    # can re-blueprint it. write_blueprint checks metadata.json status, NOT theorem_state —
    # without this, a repair-requested obligation stays frozen as 'drafted'/'partial' and
    # the Strategist is blocked. 'repair_requested' is in write_blueprint's ALLOWED_STATUSES.
    meta = read_metadata(obligation_id)
    meta["status"] = "repair_requested"
    meta["repair_reason"] = reason
    write_metadata(obligation_id, meta)

    log_event("request_repair", {"obligation_id": obligation_id, "reason": reason,
                                  "unfroze_metadata": True})
    return f"Repair requested for {obligation_id} (proof status unfrozen to repair_requested)"
