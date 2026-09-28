import json
from runtime.workspace import write_artifact as _write_artifact

SCHEMA = {
    "name": "write_artifact",
    "description": "Write a named artifact to the workspace (e.g. discovery.json, selected_direction.json).",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Filename, e.g. 'discovery.json'"},
            "content": {"type": "object", "description": "JSON content to write"},
        },
        "required": ["name", "content"],
    },
}


def run(name: str, content: dict) -> str:
    path = _write_artifact(name, content)
    return f"Artifact written to {path}"
