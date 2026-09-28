from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from datetime import datetime

SCHEMA = {
    "name": "flag_novelty_conflict",
    "description": "Flag a prior work conflict found during literature search. Use when a paper already proves the same or a stronger result under the same or weaker assumptions. Writes to theorem_state.json under novelty_conflicts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "target_id": {
                "type": "string",
                "description": "The theorem, lemma, or claim being conflicted, e.g. 'T1' or 'novelty_hypothesis'"
            },
            "paper_title": {
                "type": "string",
                "description": "Title of the conflicting paper"
            },
            "paper_url": {
                "type": "string",
                "description": "URL or arXiv ID of the conflicting paper"
            },
            "conflicting_result": {
                "type": "string",
                "description": "The specific theorem or result in the paper that conflicts"
            },
            "overlap_type": {
                "type": "string",
                "enum": ["identical", "subsumes", "partial-overlap", "same-technique", "weaker-version"],
                "description": "identical=same result, subsumes=their result is stronger, partial-overlap=some but not full overlap"
            },
            "gap_remaining": {
                "type": "string",
                "description": "What remains novel in our work if anything — what gap this paper does NOT cover"
            },
            "severity": {
                "type": "string",
                "enum": ["fatal", "major", "minor"],
                "description": "fatal=novelty is gone, major=needs significant reframing, minor=still publishable with positioning"
            }
        },
        "required": ["target_id", "paper_title", "conflicting_result", "overlap_type", "severity"]
    }
}


def run(target_id, paper_title, conflicting_result, overlap_type, severity, paper_url="", gap_remaining=""):
    state = load_theorem_state()
    state.setdefault("novelty_conflicts", [])

    conflict = {
        "target_id": target_id,
        "paper_title": paper_title,
        "paper_url": paper_url,
        "conflicting_result": conflicting_result,
        "overlap_type": overlap_type,
        "gap_remaining": gap_remaining,
        "severity": severity,
        "flagged_by": "literature_lead",
        "flagged_at": datetime.utcnow().isoformat(),
        "status": "open"
    }

    state["novelty_conflicts"].append(conflict)
    save_theorem_state(state)
    log_event("flag_novelty_conflict", {
        "target_id": target_id,
        "paper_title": paper_title,
        "overlap_type": overlap_type,
        "severity": severity
    })
    return f"Flagged novelty conflict for {target_id}: '{paper_title}' ({overlap_type}, severity: {severity})"