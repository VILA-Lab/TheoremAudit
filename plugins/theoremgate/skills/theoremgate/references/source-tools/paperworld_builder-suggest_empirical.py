from runtime.workspace import load_theorem_state, save_theorem_state, log_event

SCHEMA = {
    "name": "suggest_empirical",
    "description": "Select which empirical checks from discovery.json to run. These will be executed by the Empirical Agent.",
    "input_schema": {
        "type": "object",
        "properties": {
            "check_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "IDs of empirical checks to run e.g. ['EC1', 'EC2']"
            },
            "reason": {
                "type": "string",
                "description": "Why these checks were selected"
            },
            "cpu_only": {
                "type": "boolean",
                "description": "Whether to enforce CPU-only constraint",
                "default": True
            }
        },
        "required": ["check_ids", "reason"]
    }
}


def run(check_ids, reason, cpu_only=True):
    state = load_theorem_state()
    state.setdefault("paperworld", {})
    state["paperworld"]["empirical_checks_to_run"] = check_ids
    state["paperworld"]["empirical_reason"] = reason
    state["paperworld"]["cpu_only"] = cpu_only
    save_theorem_state(state)
    log_event("suggest_empirical", {"checks": check_ids, "cpu_only": cpu_only})
    return f"Empirical checks selected: {check_ids} (cpu_only={cpu_only})"