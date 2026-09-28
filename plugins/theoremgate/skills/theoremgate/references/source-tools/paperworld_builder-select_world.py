from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from datetime import datetime

SCHEMA = {
    "name": "select_world",
    "description": "Commit the selected paper world to theorem_state.json. Must be called after counting surviving statements.",
    "input_schema": {
        "type": "object",
        "properties": {
            "world": {
                "type": "string",
                "enum": ["theorem_paper", "framework_paper", "negative_result_paper", "insufficient"],
                "description": "The selected paper world"
            },
            "reason": {
                "type": "string",
                "description": "Why this world was selected — reference surviving statement counts"
            },
            "theorem_ready_count": {"type": "integer"},
            "proposition_ready_count": {"type": "integer"},
            "conjecture_only_count": {"type": "integer"},
            "contribution_paragraph": {
                "type": "string",
                "description": "One paragraph stating what this paper contributes"
            }
        },
        "required": ["world", "reason", "contribution_paragraph"]
    }
}


def run(world, reason, contribution_paragraph,
        theorem_ready_count=0, proposition_ready_count=0, conjecture_only_count=0):
    state = load_theorem_state()
    state.setdefault("paperworld", {})
    state["paperworld"]["world"] = world
    state["paperworld"]["reason"] = reason
    state["paperworld"]["contribution_paragraph"] = contribution_paragraph
    state["paperworld"]["statement_counts"] = {
        "theorem_ready": theorem_ready_count,
        "proposition_ready": proposition_ready_count,
        "conjecture_only": conjecture_only_count,
    }
    state["paperworld"]["selected_at"] = datetime.utcnow().isoformat()
    save_theorem_state(state)
    log_event("select_world", {"world": world})
    return f"World selected: {world}"