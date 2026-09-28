"""
save_figure — register a figure from an experiment for inclusion in the paper.
"""

import json
from runtime.workspace import load_theorem_state, save_theorem_state, log_event

SCHEMA = {
    "name": "save_figure",
    "description": "Register a figure produced by an experiment for inclusion in the paper.",
    "input_schema": {
        "type": "object",
        "properties": {
            "experiment_id": {"type": "string"},
            "figure_path": {
                "type": "string",
                "description": "Path to the figure file e.g. 'outputs/empirical/figures/EC1.pdf'",
            },
            "caption": {
                "type": "string",
                "description": "Full LaTeX caption for the figure",
            },
            "label": {
                "type": "string",
                "description": "LaTeX label e.g. 'fig:ec1_alignment'",
            },
            "section": {
                "type": "string",
                "description": "Which paper section this figure belongs to",
            },
        },
        "required": ["experiment_id", "figure_path", "caption", "label"],
    },
}


def run(experiment_id, figure_path, caption, label, section="Empirical Illustration"):
    state = load_theorem_state()
    state.setdefault("figures", [])
    state["figures"].append({
        "experiment_id": experiment_id,
        "figure_path": figure_path,
        "caption": caption,
        "label": label,
        "section": section,
    })
    save_theorem_state(state)
    log_event("save_figure", {"experiment_id": experiment_id, "label": label})
    return f"Figure registered: {label} → {figure_path}"