from runtime.workspace import load_theorem_state, save_theorem_state, log_event

SCHEMA = {
    "name": "block",
    "description": "Block a statement — marks it as ineligible for compilation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "statement_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["statement_id", "reason"],
    },
}


def run(statement_id: str, reason: str) -> str:
    state = load_theorem_state()
    state.setdefault("decisions", {})[statement_id] = {"status": "blocked", "reason": reason}
    save_theorem_state(state)
    log_event("block", {"statement_id": statement_id, "reason": reason})
    return f"Blocked {statement_id}"
