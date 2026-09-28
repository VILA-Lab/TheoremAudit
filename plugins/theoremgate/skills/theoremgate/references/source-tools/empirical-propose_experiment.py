"""
propose_experiment — propose a new experiment when the previous one failed or was inconclusive.
"""

import json
from runtime.workspace import log_event

SCHEMA = {
    "name": "propose_experiment",
    "description": (
        "Propose a new experiment design when the previous attempt contradicted or was inconclusive. "
        "Use this to iterate toward a clean supporting experiment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "New experiment ID e.g. 'EC1b', 'EC1c'",
            },
            "target_statement_id": {"type": "string"},
            "previous_experiment_id": {
                "type": "string",
                "description": "ID of the previous failed/inconclusive experiment",
            },
            "why_previous_failed": {
                "type": "string",
                "description": "Why the previous experiment failed or was inconclusive",
            },
            "new_approach": {
                "type": "string",
                "description": "What is different about this new design",
            },
            "new_code": {
                "type": "string",
                "description": "Complete new Python experiment code",
            },
        },
        "required": ["experiment_id", "target_statement_id", "previous_experiment_id",
                     "why_previous_failed", "new_approach", "new_code"],
    },
}


def run(experiment_id, target_statement_id, previous_experiment_id,
        why_previous_failed, new_approach, new_code):
    log_event("propose_experiment", {
        "experiment_id": experiment_id,
        "previous": previous_experiment_id,
        "why_failed": why_previous_failed,
    })
    return json.dumps({
        "experiment_id": experiment_id,
        "new_code": new_code,
        "new_approach": new_approach,
        "message": f"New experiment {experiment_id} proposed. Call run_experiment next.",
    })