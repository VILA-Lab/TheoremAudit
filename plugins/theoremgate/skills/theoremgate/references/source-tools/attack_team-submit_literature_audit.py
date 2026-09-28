"""
submit_literature_audit — records the Literature Auditor's findings before the paper is written:

  * reference_verdicts: each saved reference marked verified / unverifiable against a REAL fetch
    this session. Unverifiable ones are DROPPED from the bibliography (fabrication guard). A
    reference is dropped ONLY when explicitly marked verified=false — never on a network error.
  * novelty_audit: per committed statement, whether its exact formulation was found in the
    literature (verdict novel/partial/subsumed) with evidence + one honest novelty sentence. Stored
    for the manuscript's positioning. (Subsumed results are additionally routed to the gate via
    flag_novelty_conflict by the auditor, which drops them from the contribution.)
"""
from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from runtime.citations import dedupe_references

SCHEMA = {
    "name": "submit_literature_audit",
    "description": (
        "Record the literature audit. `reference_verdicts` marks each saved reference verified or "
        "unverifiable against a REAL fetch this session (unverifiable ones are dropped from the "
        "bibliography). `novelty_audit` records, per committed statement, whether its exact "
        "formulation was found in the literature (novel/partial/subsumed) with evidence. Only mark "
        "a reference unverifiable if a real fetch DEFINITIVELY failed — never on a network error "
        "(leave it verified if unsure)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reference_verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cite_key": {"type": "string"},
                        "verified": {"type": "boolean",
                                     "description": "true if a real fetch confirmed it exists; keep true if unsure"},
                        "evidence": {"type": "string", "description": "what the fetch returned / why unverifiable"},
                    },
                    "required": ["cite_key", "verified"],
                },
            },
            "novelty_audit": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "statement_id": {"type": "string", "description": "committed statement id, e.g. TH-1"},
                        "verdict": {"type": "string", "enum": ["novel", "partial", "subsumed"]},
                        "closest_paper": {"type": "string"},
                        "evidence": {"type": "string",
                                     "description": "queries run + what the closest work does/doesn't cover"},
                        "novelty_sentence": {"type": "string",
                                             "description": "one honest sentence for the paper, given a documented search"},
                    },
                    "required": ["statement_id", "verdict", "evidence"],
                },
            },
        },
        "required": [],
    },
}


def run(reference_verdicts=None, novelty_audit=None, **_ignored):
    state = load_theorem_state()
    refs = state.get("related_work", []) or []

    dropped = []
    if reference_verdicts:
        unverified = {v.get("cite_key") for v in reference_verdicts if v.get("verified") is False}
        if unverified:
            dropped = [r.get("cite_key") for r in refs if r.get("cite_key") in unverified]
            refs = [r for r in refs if r.get("cite_key") not in unverified]

    # Belt-and-suspenders: dedup while we are here.
    refs, dups = dedupe_references(refs)
    state["related_work"] = refs
    if novelty_audit is not None:
        state["novelty_audit"] = novelty_audit
    save_theorem_state(state)

    log_event("submit_literature_audit", {
        "dropped_refs": dropped, "deduped": len(dups), "audited": len(novelty_audit or []),
    })
    return (f"Literature audit recorded: dropped {len(dropped)} unverifiable ref(s) {dropped}, "
            f"deduped {len(dups)}, audited {len(novelty_audit or [])} committed statement(s).")
