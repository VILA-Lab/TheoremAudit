from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from datetime import datetime

SCHEMA = {
    "name": "propose_counterexample",
    "description": (
        "Record an explicit construction that attacks a target statement. Writes to "
        "theorem_state.json under counterexamples. Distinguish a TRUE counterexample "
        "(satisfies ALL of the statement's assumptions yet violates its conclusion — this "
        "refutes the statement) from a NECESSITY example (violates one assumption to show "
        "that assumption is required) and a BOUNDARY example (an in-scope extreme case that "
        "probes tightness). Attack the CURRENT/committed form of the statement, not an "
        "earlier, stronger version."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target_id": {
                "type": "string",
                "description": "Statement under attack, e.g. 'T2' or a lemma id. Use its current (possibly weakened) form."
            },
            "example_type": {
                "type": "string",
                "enum": ["counterexample", "necessity", "boundary"],
                "description": "counterexample = satisfies ALL assumptions and violates the "
                               "conclusion (refutes); necessity = violates one assumption to "
                               "show it is needed; boundary = in-scope extreme probing tightness"
            },
            "construction": {
                "type": "string",
                "description": "The explicit construction — dimensions, covariance/spectrum, "
                               "target, distribution — concrete enough for a reader to check."
            },
            "violates": {
                "type": "string",
                "description": "Which conclusion/inequality it breaks, and by how much."
            },
            "satisfies_all_assumptions": {
                "type": "boolean",
                "description": "True only if the construction satisfies EVERY assumption of the "
                               "target. MUST be true for example_type='counterexample'."
            },
            "confidence": {
                "type": "string",
                "enum": ["verified", "plausible", "speculative"],
                "description": "verified = computed/checked explicitly; plausible = strong "
                               "analytic argument, not fully computed; speculative = heuristic"
            },
            "severity": {
                "type": "string",
                "enum": ["fatal", "major", "minor"],
                "description": "fatal = refutes the committed statement; major = forces "
                               "reframing or a new assumption; minor = tightness/scope note"
            },
            "suggested_action": {
                "type": "string",
                "description": "e.g. add the needed assumption, restrict scope, or withdraw the claim"
            }
        },
        "required": ["target_id", "example_type", "construction", "confidence"]
    }
}


def run(target_id, example_type, construction, confidence,
        violates="", satisfies_all_assumptions=False, severity="",
        suggested_action="", **_ignored):
    state = load_theorem_state()
    state.setdefault("counterexamples", [])

    entry = {
        "target_id": target_id,
        "example_type": example_type,
        "construction": construction,
        "violates": violates,
        "satisfies_all_assumptions": bool(satisfies_all_assumptions),
        "confidence": confidence,
        "severity": severity,
        "suggested_action": suggested_action,
        "flagged_by": "counterexample_finder",
        "flagged_at": datetime.utcnow().isoformat(),
        "status": "open",
    }

    # Soft consistency guard: a "counterexample" that does NOT satisfy all assumptions is
    # really a necessity/boundary example. Record it, but relabel and note the mismatch
    # rather than letting a mislabeled refutation through.
    note = ""
    if example_type == "counterexample" and not entry["satisfies_all_assumptions"]:
        entry["example_type"] = "necessity"
        entry["consistency_note"] = (
            "Reclassified counterexample→necessity: it does not satisfy all assumptions, so "
            "it does not refute the statement; it shows an assumption is needed."
        )
        note = " (reclassified to necessity — did not satisfy all assumptions)"

    state["counterexamples"].append(entry)
    save_theorem_state(state)
    log_event("propose_counterexample", {
        "target_id": target_id,
        "example_type": entry["example_type"],
        "confidence": confidence,
        "severity": severity,
    })
    return (f"Recorded {entry['example_type']} against {target_id} "
            f"(confidence: {confidence}){note}")
