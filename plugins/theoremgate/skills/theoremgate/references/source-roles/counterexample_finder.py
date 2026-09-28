"""
Counterexample Finder — second sub-agent of the Attack Team.
Tries to break theorem candidates with concrete mathematical constructions.
Runs after Senior Skeptic so it can target flagged assumptions.
"""

from runtime import tools as tool_registry
from runtime.loop import run
from runtime.workspace import load_theorem_state, log_event
from agents.attack_team.prompts import build_counterexample_finder_prompt

import tools.attack_team.propose_counterexample as propose_counterexample
import tools.lab_lead.read_skill as read_skill
import tools.lab_lead.web_search as web_search
import tools.lab_lead.web_fetch as web_fetch
import tools.lab_lead.task_complete as task_complete

AGENT_NAME = "counterexample_finder"

TOOL_MODULES = [
    propose_counterexample,
    read_skill,
    web_search,
    web_fetch,
    task_complete,
]


def register_tools():
    schemas = []
    for module in TOOL_MODULES:
        name = module.SCHEMA["name"]
        tool_registry.register(name, module.run)
        schemas.append(module.SCHEMA)
    return schemas


def run_counterexample_finder(focus=None) -> list:
    """Run the Counterexample Finder and return proposed counterexamples.

    When `focus` is given, it tries to break only the just-drafted result(s) described there —
    used by the targeted mid-loop attack.
    """
    print("[counterexample_finder] Starting counterexample search...")
    log_event("agent_start", {"agent": AGENT_NAME, "targeted": bool(focus)})

    tools = register_tools()
    system_prompt = build_counterexample_finder_prompt(focus=focus)
    messages = [{"role": "user", "content": (
        "You are the Counterexample Finder. Read the Senior Skeptic's flags above "
        "and use them to target your counterexample constructions. "
        "Load the counterexample-search skill, try at least 3 concrete constructions "
        "per theorem candidate, search for known impossibility results, "
        "and call propose_counterexample for each plausible finding. "
        "Call task_complete when done."
    )}]

    run(
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        agent_name=AGENT_NAME,
    )

    state = load_theorem_state()
    counterexamples = state.get("counterexamples", [])

    print(f"[counterexample_finder] Done — {len(counterexamples)} counterexamples proposed")
    log_event("agent_complete", {
        "agent": AGENT_NAME,
        "counterexamples": len(counterexamples),
    })

    return counterexamples