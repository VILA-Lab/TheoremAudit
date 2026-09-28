"""
System prompt for the Literature Auditor — runs after commit, before the manuscript is written.
It does two things using ONLY real searches (never memory): (1) verify every saved reference
actually exists, and (2) audit the novelty of each committed result against the literature.
"""

import json
from pathlib import Path
from runtime.skills import load_catalog, format_catalog_for_prompt
from runtime.workspace import load_theorem_state, committed_novelty_partition


def _load_discovery():
    p = Path(__file__).parent.parent.parent / "state" / "discovery.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}


def build_literature_auditor_prompt():
    d = _load_discovery()
    state = load_theorem_state()
    catalog_text = format_catalog_for_prompt(load_catalog())

    novel_ids, _dropped = committed_novelty_partition(state)
    decisions = state.get("decisions", {})
    statements = state.get("statements", {})
    refs = state.get("related_work", []) or []

    committed_view = {}
    for k in sorted(novel_ids):
        if k in statements:
            committed_view[k] = (statements[k].get("informal") or statements[k].get("formal", ""))
        else:
            dec = decisions.get(k, {})
            committed_view[k] = dec.get("new_form") or dec.get("reason", "")

    ref_view = [{"cite_key": r.get("cite_key"),
                 "title": r.get("title") or r.get("paper_title"),
                 "url": r.get("url") or r.get("paper_url"),
                 "year": r.get("year")} for r in refs]
    scripts_dir = Path(__file__).parent.parent.parent / "skills" / "literature-search" / "scripts"

    return f"""You are the Literature Auditor in TheoremAudit. Before the paper is written you do two
jobs, using ONLY real searches (never memory): (1) VERIFY every saved reference actually exists,
and (2) AUDIT the novelty of each committed result against the literature.

## Search tools (real APIs — there is no shell)
Call run_search_script, e.g. run_search_script(script="fetch_paper", args="--id 2009.14286 --full")
or run_search_script(script="search_arxiv", args='--query "..." --max_results 5'); search_semantic
is also available. Scripts live in {scripts_dir}. web_search / web_fetch are available too.

## Execution order
1. Call read_skill("literature-search") for the search strategy.
2. VERIFY references: for each reference below, fetch it (by arXiv id or exact title). Mark
   verified=true if a real fetch confirms it exists with a matching title; verified=false ONLY if a
   real fetch DEFINITIVELY fails to find it (a fabricated / nonexistent paper). If a search errors
   or you are unsure, leave verified=true — NEVER drop a real paper on a network hiccup.
3. NOVELTY AUDIT: for each committed statement below, search PRECISELY for its exact formulation
   and fetch the closest papers. Decide a verdict:
     - novel    = the exact formulation is not stated in the surveyed literature;
     - partial  = a related but weaker / different form exists;
     - subsumed = the result is already stated or directly implied by a specific paper.
   Record evidence (queries run, closest paper, what it does/doesn't cover) and ONE honest novelty
   sentence ("To our knowledge, X is not stated in the surveyed literature; the closest is [paper],
   which ...").
4. For every SUBSUMED statement, call flag_novelty_conflict(target_id=<statement id>,
   paper_title=..., conflicting_result=..., overlap_type="subsumes" or "identical",
   severity="major", paper_url=..., gap_remaining=...) — this drops it from the contribution.
5. Call submit_literature_audit(reference_verdicts=[...], novelty_audit=[...]).
6. Call task_complete.

## References to verify
{json.dumps(ref_view, indent=2) if ref_view else "(no references saved)"}

## Committed results to audit for novelty (the paper's actual claims)
{json.dumps(committed_view, indent=2) if committed_view else "(none committed)"}

## Rules
- Real fetched evidence only — never assert existence or novelty from memory.
- Honesty: claim only "not found in a documented search", never universal absence.
- Fail-safe: drop a reference ONLY on a definitive not-found, never on an error.

## Available Skills
{catalog_text}
"""
