from runtime.workspace import load_theorem_state, save_theorem_state, log_event

SCHEMA = {
    "name": "commit",
    "description": "Commit a governed transition to theorem_state.json. Only the Lab Lead can call this.",
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {"type": "string", "description": "State section to write to (e.g. 'statements', 'decisions')"},
            "key": {"type": "string", "description": "Key within the section"},
            "value": {"description": "Value to commit"},
        },
        "required": ["section", "key", "value"],
    },
}


def run(section: str, key: str, value) -> str:
    state = load_theorem_state()
    if section not in state:
        state[section] = {}
    state[section][key] = value
    save_theorem_state(state)
    log_event("commit", {"section": section, "key": key})
    return f"Committed {section}.{key}"
