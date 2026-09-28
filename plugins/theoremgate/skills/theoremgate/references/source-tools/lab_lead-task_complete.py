SCHEMA = {
    "name": "task_complete",
    "description": "Call this when ALL three artifacts are written: backup_directions.json, selected_direction.json, and discovery.json. This ends Round 1 immediately.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "One sentence confirming what was produced"
            }
        },
        "required": ["summary"]
    },
}


def run(summary):
    return f"TASK_COMPLETE: {summary}"