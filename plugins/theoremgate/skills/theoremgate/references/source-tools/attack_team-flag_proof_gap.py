from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from datetime import datetime

SCHEMA = {
    "name": "flag_proof_gap",
    "description": "Flag a gap in a proof obligation or lemma proof. Use when the proof strategy is incomplete, uses an unjustified step, or when a key tool is applied incorrectly. Writes to theorem_state.json under skeptic_flags.",
    "input_schema": {
        "type": "object",
        "properties": {
            "obligation_id": {
                "type": "string",
                "description": "The proof obligation ID, e.g. 'PO-3'"
            },
            "gap_type": {
                "type": "string",
                "enum": ["unjustified-step", "wrong-tool", "missing-case", "circular-argument", "bound-too-loose", "independence-assumption", "distribution-shift"],
                "description": "The type of gap found"
            },
            "description": {
                "type": "string",
                "description": "Precise description of the gap — what step fails and why"
            },
            "severity": {
                "type": "string",
                "enum": ["fatal", "major", "minor"],
                "description": "fatal=proof is broken, major=needs significant fix, minor=fixable easily"
            },
            "suggested_fix": {
                "type": "string",
                "description": "Suggested way to fix or work around the gap"
            }
        },
        "required": ["obligation_id", "gap_type", "description", "severity"]
    }
}


def run(obligation_id, gap_type, description, severity, suggested_fix=""):
    state = load_theorem_state()
    state.setdefault("skeptic_flags", {}).setdefault("proof_gap_flags", [])

    flag = {
        "obligation_id": obligation_id,
        "gap_type": gap_type,
        "description": description,
        "severity": severity,
        "suggested_fix": suggested_fix,
        "flagged_by": "senior_skeptic",
        "flagged_at": datetime.utcnow().isoformat(),
        "status": "open"
    }

    state["skeptic_flags"]["proof_gap_flags"].append(flag)
    save_theorem_state(state)
    log_event("flag_proof_gap", {
        "obligation_id": obligation_id,
        "gap_type": gap_type,
        "severity": severity
    })
    return f"Flagged proof gap in {obligation_id}: {gap_type} (severity: {severity})"