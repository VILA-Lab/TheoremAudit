


# Senior Skeptic flags A5 as "theorem-shaped", A6 as "too-weak", etc. with severity and suggested fix

from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from datetime import datetime

SCHEMA = {
    "name": "flag_assumption",
    "description": "Flag an assumption as weak, circular, unverifiable, or too strong. Writes the flag to theorem_state.json under skeptic_flags. Does not modify the assumption itself — only the Lab Lead can do that.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assumption_id": {
                "type": "string",
                "description": "The assumption ID from discovery.json, e.g. 'A5'"
            },
            "attack_type": {
                "type": "string",
                "enum": ["too-strong", "circular", "unverifiable", "too-weak",
                         "theorem-shaped", "non-standard", "redundant", "inconsistent"],
                "description": "The type of attack. 'redundant' = implied by other "
                               "assumptions/definitions; 'inconsistent' = jointly "
                               "contradictory or defines an empty/degenerate regime."
            },
            "description": {
                "type": "string",
                "description": "Precise description of why this assumption is problematic"
            },
            "severity": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "How likely this is to block the theorem"
            },
            "suggested_fix": {
                "type": "string",
                "description": "Concrete suggestion for how to weaken or replace the assumption"
            }
        },
        "required": ["assumption_id", "attack_type", "description", "severity"]
    }
}


def run(assumption_id, attack_type, description, severity, suggested_fix=""):
    state = load_theorem_state()
    state.setdefault("skeptic_flags", {}).setdefault("assumption_flags", [])

    flag = {
        "assumption_id": assumption_id,
        "attack_type": attack_type,
        "description": description,
        "severity": severity,
        "suggested_fix": suggested_fix,
        "flagged_by": "senior_skeptic",
        "flagged_at": datetime.utcnow().isoformat(),
        "status": "open"
    }

    state["skeptic_flags"]["assumption_flags"].append(flag)
    save_theorem_state(state)
    log_event("flag_assumption", {
        "assumption_id": assumption_id,
        "attack_type": attack_type,
        "severity": severity
    })
    return f"Flagged assumption {assumption_id} as {attack_type} (severity: {severity})"