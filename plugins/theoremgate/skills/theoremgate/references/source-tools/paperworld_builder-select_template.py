import json
from pathlib import Path
from runtime.workspace import load_theorem_state, save_theorem_state, log_event

SCHEMA = {
    "name": "select_template",
    "description": "Select a venue template for the paper. Loads template details and commits to theorem_state.",
    "input_schema": {
        "type": "object",
        "properties": {
            "venue": {
                "type": "string",
                "enum": ["neurips", "iclr", "icml", "colt", "jmlr", "tmlr", "colm"],
                "description": "The target venue"
            },
            "reason": {
                "type": "string",
                "description": "Why this venue was selected"
            },
            "backup_venues": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Alternative venues if primary is rejected"
            }
        },
        "required": ["venue", "reason"]
    }
}


def run(venue, reason, backup_venues=None):
    templates_dir = Path(__file__).parent.parent.parent / "skills" / "paperworld" / "templates"
    template_path = templates_dir / f"{venue}.json"

    template = {}
    if template_path.exists():
        with open(template_path) as f:
            template = json.load(f)

    state = load_theorem_state()
    state.setdefault("paperworld", {})
    state["paperworld"]["venue"] = venue
    state["paperworld"]["venue_reason"] = reason
    state["paperworld"]["backup_venues"] = backup_venues or []
    state["paperworld"]["template"] = template
    save_theorem_state(state)
    log_event("select_template", {"venue": venue})

    page_limit = template.get("page_limit", "unlimited")
    empirical = template.get("empirical_expected", False)
    return f"Template selected: {venue} ({page_limit} pages, empirical_expected={empirical})"