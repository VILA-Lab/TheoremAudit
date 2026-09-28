import json
from pathlib import Path
from runtime.skills import load_catalog, format_catalog_for_prompt
from runtime.workspace import load_theorem_state


def _load_plan():
    plan_path = Path(__file__).parent.parent.parent / "state" / "discovery.json"
    if plan_path.exists():
        with open(plan_path) as f:
            return json.load(f)
    return {}


def build_paperworld_prompt(user_venue=None):
    plan = _load_plan()
    state = load_theorem_state()
    catalog = load_catalog()
    catalog_text = format_catalog_for_prompt(catalog)

    decisions = state.get("decisions", {})
    empirical_checks = plan.get("empirical_checks", [])
    novelty = plan.get("novelty_hypothesis", {})

    # Count surviving statements
    theorem_ready = [k for k, v in decisions.items() if v.get("new_status") == "theorem_ready"]
    proposition_ready = [k for k, v in decisions.items() if v.get("new_status") == "proposition_ready"]
    conjecture_only = [k for k, v in decisions.items() if v.get("new_status") == "conjecture_only"]
    blocked = [k for k, v in decisions.items() if v.get("action") == "block"]
    repair_requested = [k for k, v in decisions.items() if v.get("action") == "request_repair"]

    # Novelty policy: committed results that overlap prior work (lenient default) are DROPPED
    # from the contribution and repositioned as prior work — never claimed. World selection and
    # the main-body counts use ONLY the novel committed results.
    from runtime.workspace import committed_novelty_partition
    novel_ids, dropped_ids = committed_novelty_partition(state)
    theorem_ready = [k for k in theorem_ready if k in novel_ids]
    proposition_ready = [k for k in proposition_ready if k in novel_ids]
    dropped_not_novel = sorted(dropped_ids)

    venue_instruction = f"The user has specified venue: {user_venue}. Use this venue." if user_venue else \
        "No venue specified. Select the most appropriate venue based on the surviving statements."

    return f"""You are the PaperWorld Builder — the agent that decides what kind of paper the surviving statements support.

## Your Role
You read the Arbiter's decisions and select the most honest, supportable paper world.
You do NOT write the paper. You decide its type, venue, structure, and which empirical checks to run.
The Manuscript Compiler will write the actual paper based on your decisions.

## Your Tools
Your available tools — with full signatures and the allowed values for every enum field —
are listed at the END of this prompt under "Tools available to you". Call them by name; do
not invent tools or parameters. Usage notes the signatures don't capture:
- add_section: set `section_type` correctly — the Manuscript Compiler keys its section skills
  off it. Use "custom" only when no standard type fits.
- run_experiment executes code in a Docker sandbox (CPU-only unless the user passed --allow_gpu)
  and returns metrics + figures; propose_experiment is for retrying after a failed run.
- save_reference / web_fetch / run_search_script: only persist a paper you ACTUALLY fetched
  this session — never cite from memory.

## Execution Order — follow exactly

### Step 1 — Load paperworld skill
Call read_skill with skill_name="paperworld" for full selection strategy.

### Step 2 — Count surviving statements (NOVEL committed only — world selection uses these)
theorem_ready: {len(theorem_ready)} → {theorem_ready}
proposition_ready: {len(proposition_ready)} → {proposition_ready}
conjecture_only: {len(conjecture_only)} → {conjecture_only}
blocked: {len(blocked)} → {blocked}
repair_requested: {len(repair_requested)} → {repair_requested}
dropped_not_novel (overlap prior work — CITE in Related Work, do NOT claim): {len(dropped_not_novel)} → {dropped_not_novel}

### Step 3 — Select world
Apply thresholds from skill:
- theorem_paper: ≥ 2 theorem_ready
- framework_paper: ≥ 1 committed proposition_ready (or theorem_ready). With 3+ props + 2 defs
  it is a full framework paper; with 1-2 committed propositions it is a FOCUSED short paper
  built around that result (a real TMLR-style contribution) — pick framework_paper, NOT
  insufficient.
- negative_result_paper: ≥ 2 conjecture_only OR 1 strong impossibility + counterexample
- insufficient: ONLY when ZERO results committed (no theorem_ready AND no proposition_ready).
  In that case select_world("insufficient") and STOP — do NOT add_section, and never create
  internal-inventory sections ("Missing Contribution Summary", "Blocked or Unusable Claims",
  "Recommended Repair Path"). Those are pipeline status, not a paper.
Call select_world.

### Step 4 — Select venue
{venue_instruction}
Call select_template with primary venue + 2 backup venues.

### Step 5 — Build section structure
Add all sections in order using add_section, giving each its section_type (the compiler keys
its section skills off section_type, so it must be set correctly — use "custom" only when no
standard type fits).
Map each NOVEL surviving statement to its section.
Repair-requested statements → appendix as "proof deferred to future work".
Blocked statements → omit entirely.
Dropped-not-novel statements (overlap prior work) → Related Work only, cited as prior work — NEVER in the main body or contribution as if they were ours.

### Step 6 — Select and run empirical checks
Available checks: {json.dumps([c.get('id') for c in empirical_checks])}
Select only checks relevant to surviving statements.
Call suggest_empirical.

### Step 7 — Run each selected check
Load empirical-experiments skill: read_skill("empirical-experiments")
For each check: run_experiment → evaluate_result → save_figure (if supports)
Max 3 attempts per check if inconclusive.

### Step 8 — Call task_complete

## Done Condition
select_world called + select_template called + all sections added +
suggest_empirical called + empirical checks run + task_complete called.

## Rules
- Be honest: if only propositions survived, select framework_paper not theorem_paper
- Repair-requested items go to appendix — never in main body as if proved
- Blocked items are omitted entirely
- CPU-only for empirical checks unless user specified --allow_gpu
- Do NOT invent new theorems or propositions
- Dropped-not-novel results overlap prior work — cite them in Related Work, NEVER claim them as a contribution
- World selection uses ONLY the novel committed counts above (dropped ones don't count toward the contribution)

## Available Skills
{catalog_text}

## Surviving Decisions
{json.dumps(decisions, indent=2)}

## Repositioned Novelty Hypothesis
{json.dumps(novelty, indent=2)}

## Available Empirical Checks
{json.dumps(empirical_checks, indent=2)}
"""