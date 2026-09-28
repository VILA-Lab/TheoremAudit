from runtime.skills import read_skill as _read_skill

SCHEMA = {
    "name": "read_skill",
    "description": "Load full instructions for a skill by name. Only load when you need it — prefer the catalog for awareness.",
    "input_schema": {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "The skill folder name, e.g. 'direction-generation'",
            }
        },
        "required": ["skill_name"],
    },
}


def run(skill_name: str) -> str:
    return _read_skill(skill_name)
