"""
Literature Lead — third sub-agent of the Attack Team.
Searches arXiv, Semantic Scholar, OpenReview, JMLR for prior work conflicts.
Runs independently of Senior Skeptic and Counterexample Finder.
"""

from runtime import tools as tool_registry
from runtime.loop import run
from runtime.workspace import load_theorem_state, log_event
from agents.attack_team.prompts import build_literature_lead_prompt

import tools.attack_team.flag_novelty_conflict as flag_novelty_conflict
import tools.attack_team.save_reference as save_reference
import tools.lab_lead.read_skill as read_skill
import tools.lab_lead.web_search as web_search
import tools.lab_lead.web_fetch as web_fetch
import tools.lab_lead.run_search_script as run_search_script
import tools.lab_lead.task_complete as task_complete

AGENT_NAME = "literature_lead"

TOOL_MODULES = [
    flag_novelty_conflict,
    save_reference,
    read_skill,
    web_search,
    web_fetch,
    run_search_script,
    task_complete,
]


def register_tools():
    schemas = []
    for module in TOOL_MODULES:
        name = module.SCHEMA["name"]
        tool_registry.register(name, module.run)
        schemas.append(module.SCHEMA)
    return schemas


def run_literature_lead() -> list:
    """Run the Literature Lead and return novelty conflicts found."""
    print("[literature_lead] Starting literature search...")
    log_event("agent_start", {"agent": AGENT_NAME})

    tools = register_tools()
    system_prompt = build_literature_lead_prompt()
    messages = [{"role": "user", "content": (
        "You are the Literature Lead. Load the literature-search skill and follow "
        "its instructions exactly. Search all 5 sources with at least 7 queries. "
        "Fetch theorem sections for relevant papers. Do citation chasing for the top 3. "
        "Call flag_novelty_conflict for every medium or high overlap found. "
        "BUILD THE BIBLIOGRAPHY as you go: whenever you fetch a paper that is genuinely "
        "relevant, immediately call save_reference for it (unique cite_key) — do not discard "
        "relevant papers. Aim for a solid bibliography (roughly 8-15 distinct papers), but "
        "QUALITY OVER QUANTITY. "
        "SEARCH BUDGET — do not loop: use at most ~12 web_search and ~15 web_fetch calls "
        "total, then stop and call task_complete. "
        "STRICT fetching rules (these prevent the spinning/garbage you must avoid): "
        "(1) ONLY fetch a URL that appeared in an actual web_search result — NEVER guess or "
        "construct an arXiv ID/URL from memory (guessed IDs return unrelated papers). "
        "(2) Do NOT fetch raw .pdf URLs — fetch the abstract/HTML landing page instead. "
        "(3) If a search returns empty or a fetch 404s / is blocked, MOVE ON — never retry "
        "the same query or URL. "
        "(4) If two consecutive searches yield no new relevant papers, STOP searching. "
        "Remember: no memory citations — only papers you actually fetched from a real URL and "
        "confirmed are on-topic (discard off-topic fetches). "
        "Call task_complete once you have a reasonable bibliography or hit the budget."
    )}]

    run(
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        agent_name=AGENT_NAME,
    )

    state = load_theorem_state()
    conflicts = state.get("novelty_conflicts", [])

    print(f"[literature_lead] Done — {len(conflicts)} novelty conflicts flagged")
    log_event("agent_complete", {
        "agent": AGENT_NAME,
        "novelty_conflicts": len(conflicts),
    })

    return conflicts