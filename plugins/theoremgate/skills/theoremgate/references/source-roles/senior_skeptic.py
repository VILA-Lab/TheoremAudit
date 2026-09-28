"""
Senior Skeptic — first sub-agent of the Attack Team.
Attacks assumptions and proof gaps.
Runs before Counterexample Finder and Literature Lead.
"""

from runtime import tools as tool_registry
from runtime.loop import run
from runtime.workspace import load_theorem_state, log_event
from agents.attack_team.prompts import build_senior_skeptic_prompt

import tools.attack_team.flag_assumption as flag_assumption
import tools.attack_team.flag_proof_gap as flag_proof_gap
import tools.lab_lead.read_skill as read_skill
import tools.lab_lead.task_complete as task_complete

AGENT_NAME = "senior_skeptic"

TOOL_MODULES = [
    flag_assumption,
    flag_proof_gap,
    read_skill,
    task_complete,
]


def register_tools():
    schemas = []
    for module in TOOL_MODULES:
        name = module.SCHEMA["name"]
        tool_registry.register(name, module.run)
        schemas.append(module.SCHEMA)
    return schemas


def run_senior_skeptic(focus=None) -> dict:
    """Run the Senior Skeptic and return its flags.

    When `focus` is given (a dict describing just-drafted result(s)), the skeptic runs a fast,
    scoped re-check of those items only — used by the targeted mid-loop attack.
    """
    print("[senior_skeptic] Starting assumption + proof gap attack...")
    log_event("agent_start", {"agent": AGENT_NAME, "targeted": bool(focus)})

    tools = register_tools()
    system_prompt = build_senior_skeptic_prompt(focus=focus)
    messages = [{"role": "user", "content": (
        "You are the Senior Skeptic. Read the assumptions and proof obligations "
        "from the plan above and systematically attack them. "
        "Call flag_assumption for every problematic assumption and "
        "flag_proof_gap for every proof gap you find. "
        "Call task_complete when you have reviewed everything."
    )}]

    run(
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        agent_name=AGENT_NAME,
    )

    state = load_theorem_state()
    flags = state.get("skeptic_flags", {})
    n_assumption_flags = len(flags.get("assumption_flags", []))
    n_gap_flags = len(flags.get("proof_gap_flags", []))

    print(f"[senior_skeptic] Done — {n_assumption_flags} assumption flags, {n_gap_flags} proof gap flags")
    log_event("agent_complete", {
        "agent": AGENT_NAME,
        "assumption_flags": n_assumption_flags,
        "proof_gap_flags": n_gap_flags,
    })

    return flags