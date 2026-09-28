import json
from pathlib import Path

from runtime.skills import load_catalog, format_catalog_for_prompt
from runtime.workspace import load_theorem_state, committed_novelty_partition


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_discovery() -> dict:
    root = Path(__file__).parent.parent.parent
    return _load_json(root / "state" / "discovery.json")


def _build_final_paper_context(discovery: dict, state: dict, committed_ids: set[str]) -> dict:
    statements = state.get("statements", {}) or {}
    decisions = state.get("decisions", {}) or {}

    committed_results = {}
    for result_id in sorted(committed_ids):
        stmt = statements.get(result_id, {}) or {}
        dec = decisions.get(result_id, {}) or {}

        committed_results[result_id] = {
            "formal": stmt.get("formal") or dec.get("new_form"),
            "informal": stmt.get("informal") or dec.get("reason"),
            "paper_label": stmt.get("paper_label") or dec.get("paper_label"),
            "assumptions_used": stmt.get("assumptions_used", []),
            "synthesized_from": stmt.get("synthesized_from", []),
            "scope": stmt.get("proven_scope") or stmt.get("scope") or dec.get("scope"),
        }

    blocked = []
    for result_id, dec in decisions.items():
        status = dec.get("new_status") or dec.get("status")
        if status in {"blocked", "rejected", "dropped", "not_ready", "repair_failed"}:
            blocked.append({
                "id": result_id,
                "status": status,
                "reason": dec.get("reason"),
            })

    return {
        "research_question": (
            discovery.get("research_question")
            or discovery.get("problem_statement")
            or discovery.get("problem")
        ),
        "selected_direction": discovery.get("selected_direction"),
        "setting": discovery.get("setting"),
        "model": discovery.get("model") or discovery.get("statistical_model"),
        "estimator_or_method": discovery.get("estimator") or discovery.get("method"),
        "assumptions": discovery.get("assumptions", []),
        "definitions": discovery.get("definitions", []),
        "final_contribution": (
            state.get("final_contribution")
            or state.get("contribution_summary")
            or discovery.get("contribution")
            or discovery.get("novelty_hypothesis")
        ),
        "committed_results": committed_results,
        "blocked_or_removed_results": blocked,
        "open_problem": (
            state.get("open_problem")
            or discovery.get("open_problem")
            or discovery.get("remaining_gap")
        ),
    }


def _collect_reference_candidates(discovery: dict, state: dict) -> list[dict]:
    candidates = []

    # Already saved bibliography
    for ref in state.get("related_work", []) or []:
        candidates.append({
            "title": ref.get("title"),
            "authors": ref.get("authors"),
            "year": ref.get("year"),
            "venue": ref.get("venue"),
            "url": ref.get("url"),
            "relevance": ref.get("relevance"),
            "source": "state.related_work",
        })

    # Novelty conflicts
    for item in state.get("novelty_conflicts", []) or []:
        candidates.append({
            "title": item.get("paper_title"),
            "url": item.get("paper_url"),
            "relevance": item.get("gap_remaining"),
            "source": "state.novelty_conflicts",
        })

    # Novelty audit closest papers
    for audit in state.get("novelty_audit", []) or []:
        papers = audit.get("closest_papers", []) or []
        closest = audit.get("closest_paper")
        if isinstance(closest, dict):
            papers.append(closest)

        for paper in papers:
            if isinstance(paper, dict):
                candidates.append({
                    "title": paper.get("title") or paper.get("paper_title"),
                    "authors": paper.get("authors"),
                    "year": paper.get("year"),
                    "venue": paper.get("venue"),
                    "url": paper.get("url") or paper.get("paper_url"),
                    "relevance": (
                        paper.get("relevance")
                        or paper.get("comparison")
                        or audit.get("gap_remaining")
                    ),
                    "source": "state.novelty_audit",
                })

    # Discovery-level references
    for field in ("related_work", "references", "literature", "closest_papers", "prior_work"):
        for paper in discovery.get(field, []) or []:
            if isinstance(paper, dict):
                candidates.append({
                    "title": paper.get("title") or paper.get("paper_title"),
                    "authors": paper.get("authors"),
                    "year": paper.get("year"),
                    "venue": paper.get("venue"),
                    "url": paper.get("url") or paper.get("paper_url"),
                    "relevance": paper.get("relevance") or paper.get("relation"),
                    "source": f"discovery.{field}",
                })

    return [c for c in candidates if c.get("title") or c.get("url")]


def build_related_work_search_prompt() -> str:
    discovery = _load_discovery()
    state = load_theorem_state()
    catalog_text = format_catalog_for_prompt(load_catalog())

    novel_ids, _ = committed_novelty_partition(state)
    committed_ids = set(novel_ids)

    final_context = _build_final_paper_context(discovery, state, committed_ids)
    candidates = _collect_reference_candidates(discovery, state)

    scripts_dir = Path(__file__).parent.parent.parent / "skills" / "literature-search" / "scripts"

    return f"""You are the Related-Work Search agent in TheoremAudit.

Your job is to build the final citable bibliography for the manuscript.

You are constructive, not adversarial. The Literature Auditor checks novelty conflicts. You build
the bibliography that a polished theoretical ML paper should cite.

Use only real searches and fetched papers. Never cite from memory.

## Search tools

Prefer:
- run_search_script(script="search_arxiv", args="--query '...' --max_results 10")
- run_search_script(script="search_semantic", args="--query '...' --max_results 10")
- run_search_script(script="search_openreview", args="--query '...' --max_results 10")
- run_search_script(script="search_jmlr", args="--query '...' --include_pmlr")
- run_search_script(script="fetch_paper", args="--id ... --full")

Scripts live in:
{scripts_dir}

Use web_search and web_fetch only when needed.

## Final paper context

{json.dumps(final_context, indent=2)}

## Prior reference candidates

{json.dumps(candidates, indent=2) if candidates else "(none)"}

## Procedure

1. Call read_skill("related-work-search").

2. Read the final paper context carefully. Identify 3-5 search themes from the final paper only.
   Do not build bibliography around blocked or removed claims.

3. Reuse prior candidates:
   For each prior candidate, fetch it using URL, arXiv id, or exact title.
   If it is real and relevant to the final contribution, call save_reference.
   If it only concerns a blocked/removed claim, skip it.

4. Search missing themes:
   Find canonical, closest, and recent papers for the final contribution.
   For this paper, likely themes include:
   - minimum-norm interpolation / ridgeless least squares;
   - benign overfitting;
   - high-dimensional linear regression risk formulas;
   - misspecified regression / general regression errors;
   - exact finite-sample decompositions or projection-based risk analysis.

5. Fetch before saving:
   Save only papers that appeared in a real search result and were fetched/opened.

6. For every saved paper, call save_reference with:
   - cite_key;
   - title;
   - authors;
   - year;
   - venue if available;
   - url;
   - relevance.

   The relevance sentence must explain exactly how this paper relates to the final manuscript.
   Example:
   "Analyzes asymptotic risk of ridgeless least squares, whereas the present paper gives an
   exact finite-sample decomposition under misspecification and leaves the remainder explicit."

7. Require at least 15 focused references for every paper and at least 20 for mature or
   original-research work, but never pad with irrelevant papers. If the initial search finds fewer,
   broaden the query families and citation-chase relevant primary sources until the floor is met.

8. Deduplicate by title, URL, and arXiv id.

9. Call task_complete with:
   - number of prior candidates reused;
   - number of new papers saved;
   - themes covered;
   - any missing themes or search limitations.

## Hard rules

- Do not invent papers, authors, years, venues, URLs, or cite keys.
- Do not save papers from memory.
- Do not cite blocked or abandoned claims.
- Do not leave the bibliography empty if relevant papers are found.
- Do not write the related-work section yourself; only build the bibliography.
- The Manuscript Compiler will later write the prose using your saved references.

## Available Skills

{catalog_text}
"""
