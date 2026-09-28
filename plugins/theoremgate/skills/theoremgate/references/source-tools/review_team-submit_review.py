"""
submit_review.py
The Reviewer records a venue-style review of the compiled paper: a score, a recommendation,
and a list of comments each TAGGED by type so the Lab Lead can route them:
  - presentation → Manuscript Compiler rewrites the section (text only)
  - substance    → Method Team (only if provable) or recorded as an honest limitation
  - honesty      → Manuscript Compiler tones the claim down to what is committed

The Reviewer JUDGES; it never edits the paper. Writes to state/review_output.json and
theorem_state["review"].
"""

import json
from datetime import datetime, timezone
from runtime.workspace import load_theorem_state, save_theorem_state, write_artifact, log_event

VALID_TAGS = {"presentation", "substance", "honesty", "correctness"}
VALID_SEVERITY = {"minor", "major"}
VALID_RECOMMENDATION = {
    "accept", "weak_accept", "borderline", "weak_reject", "reject",
}

SCHEMA = {
    "name": "submit_review",
    "description": (
        "Record a single venue-style review of the compiled paper. Provide a score (1-10), a "
        "recommendation, a one-paragraph summary, and a list of comments. TAG every comment: "
        "'presentation' (writing/clarity/structure/notation), 'substance' (a missing/weak "
        "result or proof — cannot be fixed by rewording), 'honesty' (a claim that overstates "
        "what is actually proved), or 'correctness' (a stated result is mathematically WRONG or "
        "imprecise as written — a missing hypothesis, wrong constant, conflated definition — "
        "fixable by correcting the statement/proof). You judge only; you do not edit the paper."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "minimum": 1, "maximum": 10,
                      "description": "Overall score, 1 (strong reject) to 10 (strong accept)."},
            "recommendation": {"type": "string", "enum": sorted(VALID_RECOMMENDATION)},
            "summary": {"type": "string", "description": "One-paragraph reviewer summary."},
            "comments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tag": {"type": "string", "enum": sorted(VALID_TAGS)},
                        "section": {"type": "string",
                                    "description": "Section the comment targets (e.g. 'introduction', 'main_results') or 'global'."},
                        "issue": {"type": "string", "description": "The problem, concretely."},
                        "suggestion": {"type": "string", "description": "Concrete fix (optional)."},
                        "severity": {"type": "string", "enum": sorted(VALID_SEVERITY)},
                    },
                    "required": ["tag", "section", "issue", "severity"],
                },
                "description": "Tagged review comments.",
            },
            "strengths": {"type": "array", "items": {"type": "string"},
                          "description": "What the paper genuinely does well (2-5 bullets)."},
            "weaknesses": {"type": "array", "items": {"type": "string"},
                           "description": "The paper's weaknesses (2-5). A weakness that names a "
                                          "MISSING or TOO-WEAK result is the signal that routes to "
                                          "the Method Team to prove more — be concrete about what "
                                          "result/bound is needed and where."},
            "questions": {"type": "array", "items": {"type": "string"},
                          "description": "Questions to the authors (optional)."},
        },
        "required": ["score", "recommendation", "summary", "comments"],
    },
}


def run(score, recommendation, summary, comments,
        strengths=None, weaknesses=None, questions=None, **_ignored):
    errors = []
    if not isinstance(score, int) or not (1 <= score <= 10):
        errors.append("score must be an integer 1-10")
    if recommendation not in VALID_RECOMMENDATION:
        errors.append(f"recommendation must be one of {sorted(VALID_RECOMMENDATION)}")
    if not isinstance(comments, list):
        errors.append("comments must be a list")
        comments = []
    clean = []
    for i, c in enumerate(comments):
        if not isinstance(c, dict):
            errors.append(f"comment {i} must be an object")
            continue
        tag = c.get("tag")
        if tag not in VALID_TAGS:
            errors.append(f"comment {i}: tag must be one of {sorted(VALID_TAGS)}")
        if c.get("severity") not in VALID_SEVERITY:
            errors.append(f"comment {i}: severity must be one of {sorted(VALID_SEVERITY)}")
        if not c.get("issue"):
            errors.append(f"comment {i}: issue is empty")
        clean.append({
            "tag": tag,
            "section": c.get("section", "global"),
            "issue": c.get("issue", ""),
            "suggestion": c.get("suggestion", ""),
            "severity": c.get("severity", "minor"),
        })
    if errors:
        log_event("submit_review_rejected", {"errors": errors})
        return "ERROR submit_review: " + "; ".join(errors)

    review = {
        "score": score,
        "recommendation": recommendation,
        "summary": summary,
        "strengths": strengths or [],
        "weaknesses": weaknesses or [],
        "questions": questions or [],
        "comments": clean,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            t: sum(1 for c in clean if c["tag"] == t) for t in sorted(VALID_TAGS)
        },
    }
    state = load_theorem_state()
    state["review"] = review
    save_theorem_state(state)
    write_artifact("review_output.json", review)
    log_event("submit_review", {"score": score, "recommendation": recommendation,
                                 "counts": review["counts"]})
    return (f"Review recorded: score {score}/10 ({recommendation}); "
            f"{len(clean)} comments {review['counts']}.")
