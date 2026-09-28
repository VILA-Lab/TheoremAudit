from runtime.workspace import load_theorem_state, save_theorem_state, log_event

SCHEMA = {
    "name": "weaken",
    "description": "Weaken a statement to a softer form (e.g. theorem → proposition → conjecture).",
    "input_schema": {
        "type": "object",
        "properties": {
            "statement_id": {"type": "string"},
            "new_form": {"type": "string", "description": "The weakened statement text"},
            "new_status": {
                "type": "string",
                "enum": ["proposition_ready", "conjecture_only"],
            },
        },
        "required": ["statement_id", "new_form", "new_status"],
    },
}


def run(statement_id: str, new_form: str, new_status: str) -> str:
    state = load_theorem_state()
    stmts = state.setdefault("statements", {})
    if statement_id in stmts:
        stmts[statement_id]["text"] = new_form
        stmts[statement_id]["status"] = new_status
    state.setdefault("decisions", {})[statement_id] = {"status": new_status, "weakened_to": new_form}
    save_theorem_state(state)
    log_event("weaken", {"statement_id": statement_id, "new_status": new_status})
    return f"Weakened {statement_id} to {new_status}"
