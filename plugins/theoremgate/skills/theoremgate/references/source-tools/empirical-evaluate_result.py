"""
evaluate_result — LLM evaluates whether experiment result supports the theory.
"""

import json
from runtime.workspace import log_event

SCHEMA = {
    "name": "evaluate_result",
    "description": (
        "Evaluate whether an experiment result supports, contradicts, or is inconclusive "
        "with respect to a surviving theoretical statement. "
        "Call after run_experiment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "experiment_id": {"type": "string"},
            "target_statement_id": {
                "type": "string",
                "description": "Which statement this checks e.g. 'T1', 'P2'",
            },
            "result_summary": {
                "type": "string",
                "description": "Brief description of what the experiment showed",
            },
            "verdict": {
                "type": "string",
                "enum": ["supports", "contradicts", "inconclusive", "bug_in_code"],
                "description": (
                    "supports: result aligns with the theoretical prediction. "
                    "contradicts: result clearly disagrees with the prediction. "
                    "inconclusive: result is ambiguous or noisy. "
                    "bug_in_code: experiment failed due to a coding error, not a theory issue."
                ),
            },
            "explanation": {
                "type": "string",
                "description": "One paragraph explaining the verdict",
            },
            "include_in_paper": {
                "type": "boolean",
                "description": "Whether to include this result in the paper",
            },
            "suggested_caption": {
                "type": "string",
                "description": "Suggested figure/table caption if include_in_paper is true",
            },
        },
        "required": ["experiment_id", "target_statement_id", "result_summary", "verdict", "explanation", "include_in_paper"],
    },
}


def run(experiment_id, target_statement_id, result_summary, verdict,
        explanation, include_in_paper, suggested_caption=""):
    from runtime.workspace import load_theorem_state, save_theorem_state

    state = load_theorem_state()
    state.setdefault("empirical_results", [])

    record = {
        "experiment_id": experiment_id,
        "target_statement_id": target_statement_id,
        "result_summary": result_summary,
        "verdict": verdict,
        "explanation": explanation,
        "include_in_paper": include_in_paper,
        "suggested_caption": suggested_caption,
    }
    state["empirical_results"].append(record)
    save_theorem_state(state)

    log_event("evaluate_result", {
        "experiment_id": experiment_id,
        "verdict": verdict,
        "include_in_paper": include_in_paper,
    })

    if verdict == "contradicts":
        return (
            f"CONTRADICTION: {experiment_id} contradicts {target_statement_id}. "
            f"Reason: {explanation}. "
            f"Consider: 1) Check code for bugs first. 2) If real contradiction, flag to Lab Lead for further weakening."
        )
    elif verdict == "bug_in_code":
        return f"BUG: {experiment_id} failed due to code error. Fix the code and re-run."
    elif verdict == "inconclusive":
        return f"INCONCLUSIVE: {experiment_id} is ambiguous. Consider proposing a cleaner experiment."
    else:
        return f"SUPPORTS: {experiment_id} supports {target_statement_id}. Include in paper: {include_in_paper}."