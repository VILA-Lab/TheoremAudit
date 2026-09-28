"""
System prompts for the three Method Team stages.
"""

import json
from pathlib import Path
from runtime.skills import load_catalog, format_catalog_for_prompt
from runtime.workspace import load_theorem_state
from runtime.proof_store import get_all_statuses
from runtime.proof_dag import ProofDAG

def _normalize_extension_obligations(extension_obligations):
    normalized = []
    for ob in extension_obligations:
        if not isinstance(ob, dict):
            continue
        item = dict(ob)

        # DAG dependencies should only include proof-obligation IDs.
        deps = item.get("dependencies", []) or []
        item["dependencies"] = [
            d for d in deps
            if str(d).startswith("PO-")
        ]

        # Keep theorem dependencies as context, not DAG edges.
        item["seed_dependencies"] = [
            d for d in deps
            if str(d).startswith("TH-")
        ]

        normalized.append(item)
    return normalized
def _load_contribution_development():
    import json
    from pathlib import Path

    path = Path("state/contribution_development.json")
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _load_plan():
    plan_path = Path(__file__).parent.parent.parent / "state" / "discovery.json"
    if plan_path.exists():
        with open(plan_path) as f:
            return json.load(f)
    return {}

# def _summarize_exploration(exploration):
#     if not exploration:
#         return {}
#     return {
#         "primary_target": exploration.get("primary_target"),
#         "verdict": exploration.get("verdict"),
#         "recommendation": exploration.get("recommendation"),
#         "recommended_method_scope": exploration.get("recommended_method_scope"),
#         "boundary_findings": exploration.get("boundary_findings"),
#         "notes_for_prover": exploration.get("notes_for_prover"),
#     }

def _get_repair_instructions():
    """Get repair instructions from theorem_state for repair mode."""
    state = load_theorem_state()
    decisions = state.get("decisions", {})
    repairs = {}
    for target_id, decision in decisions.items():
        if decision.get("action") == "request_repair":
            repairs[target_id] = decision
    return repairs


def _load_exploration():
    """Load exploration.json (the pre-proof Explorer's findings), or {} if absent."""
    path = Path(__file__).parent.parent.parent / "state" / "exploration.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _get_theorem_targets(plan: dict) -> list:
    """Support both new discovery schema and old schema."""
    return plan.get("theorem_targets") or plan.get("theorems", [])


def _summarize_exploration(exploration: dict) -> dict:
    """Keep only what Method Team needs from exploration.json."""
    if not exploration:
        return {}

    return {
        "primary_target": exploration.get("primary_target"),
        "verdict": exploration.get("verdict"),
        "recommendation": exploration.get("recommendation"),
        "recommended_method_scope": exploration.get("recommended_method_scope"),
        "boundary_findings": exploration.get("boundary_findings"),
        "notes_for_prover": exploration.get("notes_for_prover"),
        "experiments_run": exploration.get("experiments_run", []),
    }


def _select_obligation_details(obligations: list, ordered_ids: list) -> list:
    """Return only the obligations this stage will process, preserving DAG order."""
    by_id = {ob.get("id"): ob for ob in obligations if ob.get("id")}
    return [by_id[po_id] for po_id in ordered_ids if po_id in by_id]


def _summarize_theorem_targets(theorems: list, primary_target: dict) -> dict:
    """Keep full primary theorem target, summarize stretch targets."""
    primary_id = primary_target.get("statement_id") if isinstance(primary_target, dict) else None
    primary = next((t for t in theorems if t.get("id") == primary_id), None)

    stretch = [
        {
            "id": t.get("id"),
            "role": t.get("role"),
            "type": t.get("type"),
            "informal": t.get("informal"),
            "min_viable_form": t.get("min_viable_form"),
        }
        for t in theorems
        if t.get("id") != primary_id
    ]

    return {
        "primary": primary,
        "other_targets_summary": stretch,
    }

def build_strategist_prompt(mode="initial", obligations_to_process=None):
    plan = _load_plan()

    catalog_text = "(Tool schemas are provided by the runtime. Load only the proof-strategy skill with read_skill.)"

    obligations = plan.get("proof_obligations", [])

    contribution_development = _load_contribution_development()
    extension_obligations = contribution_development.get("new_obligations", [])
    if not isinstance(extension_obligations, list):
        extension_obligations = []

    extension_obligations = _normalize_extension_obligations(extension_obligations)

    if extension_obligations:
        obligations = obligations + extension_obligations

    contribution_development = _load_contribution_development()
    extension_obligations = contribution_development.get("new_obligations", [])
    if not isinstance(extension_obligations, list):
        extension_obligations = []

    if extension_obligations:
        obligations = obligations + extension_obligations
    theorems = _get_theorem_targets(plan)
    assumptions = plan.get("assumptions", [])
    definitions = plan.get("definitions", [])
    notation = plan.get("notation", [])
    primary_target = plan.get("primary_target", {})
    exploration = _summarize_exploration(_load_exploration())

    # Build DAG and get topological order
    dag = ProofDAG(obligations)
    topo_order = dag.topological_order()

    current_statuses = get_all_statuses()
    contribution_development_view = json.dumps(
    contribution_development,
    indent=2,
    ensure_ascii=False,
)


    # Skeptic outputs (populated by the Attack Team; empty on the initial pass).
    # Surfaced so the Strategist can honor the proof-strategy skill's skeptic-flag rules.
    _state = load_theorem_state()
    _skeptic = _state.get("skeptic_flags", {})
    skeptic_flags = {
        "assumption_flags": _skeptic.get("assumption_flags", []),
        "proof_gap_flags": _skeptic.get("proof_gap_flags", []),
        "counterexamples": _state.get("counterexamples", []),
    }
    has_flags = any(skeptic_flags.values())
    skeptic_text = (
        json.dumps(skeptic_flags, indent=2) if has_flags
        else "No skeptic flags available (initial pass — none produced yet)."
    )

    # Filter obligations based on mode
    if mode == "repair" and obligations_to_process:
        obligations_to_process_set = set(obligations_to_process)
        ordered_obligations = [
            ob for ob in topo_order
            if ob in obligations_to_process_set
        ]
        repair_instructions = _get_repair_instructions()
        repair_text = json.dumps(repair_instructions, indent=2)
    else:
        ordered_obligations = topo_order
        repair_text = "N/A (initial mode)"

    ordered_obligation_details = _select_obligation_details(obligations, ordered_obligations)
    theorem_context = _summarize_theorem_targets(theorems, primary_target)
    return f"""You are the Strategist — Stage 1 of the Method Team in TheoremAudit.

## Your Role
For each proof obligation, you decide the proof strategy BEFORE any proof writing begins.
You classify the obligation type, select the technique, identify dependencies, and assess difficulty honestly.




## Your Tools
Your tools — full signatures and the allowed values for proof_type/difficulty — are listed at
the END of this prompt under "Tools available to you". Call them by name. Usage notes:
- write_blueprint: `expected_assumptions` is an OBJECT mapping assumption ID → the step where it
  is used, e.g. {{"A1": "Step 2 for independence"}} — not a list. See the proof-strategy skill
  for choosing the primary proof_type.
- read_skill: load the proof-strategy skill first for technique selection.

## Contribution-development plan

The Contribution Developer may have analyzed the finalized safe core and decided
that the current result is correct but not paper-ready.

Use this plan if it contains `new_obligations`.

{contribution_development_view}

If `new_obligations` are present:
1. Prioritize these obligations over old weakened obligations.
2. Treat committed statements such as TH-1 as seed lemmas.
3. Do not re-prove the seed lemma unless the new obligation depends on it.
4. Prove the new obligations as extensions built on top of the seed lemma.
5. Do not return to old failed PO-3/PO-4 simplifications unless the new obligation explicitly requires it.

## Execution Order

### Step 0 — Prove the PRIMARY TARGET first
The discovery designates ONE `primary_target` — the tractable statement to land first.
Plan its obligation chain BEFORE any obligations that serve only stretch targets.

If exploration.json exists, treat it as diagnostic guidance, not proof.

Decision rule:
- If `exploration.verdict == "reachable"`, plan for the primary target as written in discovery.json.
- If `exploration.verdict == "narrow"`, plan for `exploration.recommended_method_scope` first.
- If `exploration.verdict == "reshape"`, do not plan the broad target blindly. Plan only the
  recommended restricted form, and explicitly mark what Lab Lead may need to reshape.
- If `exploration.verdict == "blocked"`, do not plan a positive proof of the broad primary target.
  Plan only a fallback or `min_viable_form` if one is still viable.

Use `exploration.notes_for_prover`, `exploration.boundary_findings`, and
`exploration.recommendation` to choose the safe proof route.

Never cite exploration as proof.

### Step 1 — Load proof-strategy skill
Call read_skill("proof-strategy") for the full technique taxonomy.
If skeptic flags are present below, follow the skill's "Skeptic-flag awareness" rules:
do NOT build a strategy whose central step relies on an assumption flagged as circular,
theorem-shaped, too-strong, unverifiable, inconsistent, or redundant without explicitly
marking the risk in the blueprint's Dangerous Steps and Honest Assessment.

### Step 2 — Process obligations in DAG order
Process in this EXACT order (topological — dependencies first):
{json.dumps(ordered_obligations, indent=2)}

If exploration.verdict is "narrow", "reshape", or "blocked", the list above is only the
dependency universe. Process only the obligations needed for exploration.recommended_method_scope
first. Do not plan unrelated stretch obligations in this pass; mention them as deferred in
task_complete.

In particular, do not attempt obligations supporting only fallback, counterexample, or stretch
targets unless Explorer explicitly recommends that branch as the first Method-Team scope.


Dependency rule:
For every blueprint, copy the dependency list from the corresponding discovery proof obligation.
Do not leave `dependencies` empty unless the discovery obligation itself has no dependencies.
If the discovery obligation uses `depends_on`, `requires`, or `prerequisites`, normalize that
field into `dependencies` when calling write_blueprint.

### Step 3 — For each obligation:
1. Read the obligation's dependency field from the discovery object.
   Accept any of these names as dependency fields: `dependencies`, `depends_on`, `requires`,
   or `prerequisites`.
2. Normalize that list into the blueprint's `dependencies` field.
3. Check if dependencies are ready using the current statuses below.
4. If dependencies failed → call mark_blocked(po_id, blocked_by=[...], reason='...')
5. If dependencies partial → plan a conditional_draft.
6. If ready → call write_blueprint with full strategy, including the normalized dependencies.

### Step 4 — Call task_complete

## Mode: {mode.upper()}
{f"Repair instructions: {repair_text}" if mode == "repair" else "Initial pass — process all obligations"}

## Current Proof Statuses
{json.dumps(current_statuses, indent=2)}

## Skeptic Flags (from the Attack Team — consult before choosing a strategy)
{skeptic_text}

## Proof Obligations To Process (full details)
{json.dumps(ordered_obligation_details, indent=2)}

## PRIMARY TARGET — plan its obligation chain FIRST
{json.dumps(primary_target, indent=2) if primary_target else "(no primary_target in discovery — treat the highest-priority theorem as primary)"}

## Exploration findings (pre-proof Explorer — honor its verdict/recommendation)
{json.dumps(exploration, indent=2) if exploration else "(no exploration.json — none produced; proceed from the discovery as written)"}

## Theorem Candidates (context)
## Theorem Target Context
{json.dumps(theorem_context, indent=2)}

## Assumptions (what you can use)
{json.dumps(assumptions, indent=2)}

## Definitions (formal — use these exact objects; do NOT treat them as missing)
{json.dumps(definitions, indent=2)}

## Notation
{json.dumps(notation, indent=2)}

## Rules
- Process in DAG order — never skip dependencies
- Be honest about difficulty — "open" is a valid answer
- Do NOT attempt to write proofs — only strategy
- Do NOT rewrite discovery.json or silently change theorem statements. However, if Explorer recommends a narrowed scope or a theorem has `min_viable_form`, target that restricted form in the blueprint and label it clearly as the form to prove.
- Blocked obligations must be marked immediately
- If a step would need an infinite-dimensional concentration/limit tool that is unsafe
  (e.g. matrix Bernstein or dominated convergence without a bounded/integrable envelope),
  prefer scoping that obligation to the FINITE-RANK regime where the safe toolset closes
  it, rather than leaving a major gap. A cleanly proved finite-rank theorem beats an
  unproved general one.
- RETREAT TO THE MINIMAL VIABLE FORM. Each theorem in the context above has a
  `min_viable_form` field (e.g. a diagonal-Sigma proposition, or an explicit
  finite-dimensional construction). If the ambitious/general form requires a step you assess
  as `hard` or `open` (e.g. the random-matrix expectation near the interpolation hard edge),
  do NOT plan a gap-ridden proof of the general form. Instead write the blueprint targeting
  the theorem's `min_viable_form` — the tractable restricted version that avoids the hard
  step. Goal: a COMPLETE proof of a restricted proposition, not a partial proof of a grand
  theorem. State explicitly in the blueprint which form you are targeting and why.
  - If a blueprint targets an Explorer-recommended narrowed scope or a min_viable_form, verify tools for that restricted scope, not for the abandoned broad target.

## Available Skills
{catalog_text}
"""


def build_analyst_prompt(mode="initial", obligations_to_process=None):
    plan = _load_plan()
    # catalog = load_catalog()
    # catalog_text = format_catalog_for_prompt(catalog)
    catalog_text = "(Tool schemas are provided by the runtime. Load only the mathematical-tools skill with read_skill.)"
    obligations = plan.get("proof_obligations", [])
    known_deps = plan.get("known_dependencies", [])
    assumptions = plan.get("assumptions", [])
    definitions = plan.get("definitions", [])
    notation = plan.get("notation", [])

    dag = ProofDAG(obligations)
    topo_order = dag.topological_order()
    current_statuses = get_all_statuses()

    if mode == "repair" and obligations_to_process:
        ordered = [ob for ob in topo_order if ob in set(obligations_to_process)]
    else:
        ordered = [ob for ob in topo_order
                   if current_statuses.get(ob) == "planned"]

    scripts_dir = Path(__file__).parent.parent.parent / "skills" / "literature-search" / "scripts"

    return f"""You are the Analyst — Stage 2 of the Method Team in TheoremAudit.

## Your Role
For each planned obligation, you find and verify the external theorems needed.
Every theorem used in a proof MUST be fetched and condition-checked.
You do NOT declare a theorem safe — you record the condition checks, and the tool computes
safety from them. If any condition is not satisfied, the check comes back unsafe and the
Proof Writer cannot use that theorem.


## Your Tools
Your tools — full signatures and the allowed values for source_type — are listed at the END
of this prompt under "Tools available to you". Call them by name. Usage notes the signatures
don't capture, for write_tool_check:
- `condition_checks` is an object keyed EXACTLY by the strings in `required_conditions` (no
  missing, no extra); each value is {{"satisfied": true/false, "reason": "...", "assumption_used": "A#"}}.
- Do NOT pass a `safe_to_use` argument — the tool COMPUTES safety from condition_checks (any
  unchecked or unsatisfied condition ⇒ unsafe). `alternative_if_unsafe` is REQUIRED whenever a
  condition is not satisfied (use "none found" if there is none).
- `theorem_statement` is the formal statement copied from the source (required for traceability).
Load the mathematical-tools skill via read_skill before you start.

## Search Scripts — call these through run_search_script (there is no shell)
Available scripts (in {scripts_dir}). Invoke with run_search_script, e.g.
run_search_script(script="search_arxiv.py", args='--query "matrix Bernstein" --max_results 5'):
- search_arxiv.py --query "[theorem name]" --max_results 5
- fetch_paper.py --id [ARXIV_ID] --full
- search_semantic.py --query "[theorem name]" --max_results 5

## Execution Order

### Step 1 — Load mathematical-tools skill
Call read_skill("mathematical-tools") for the theorem catalog and condition-checking template.

### Step 2 — Process planned obligations
Obligations ready for analysis (status=planned):
{json.dumps(ordered, indent=2)}

Analyze only obligations that have blueprints. If the Strategist deferred unrelated stretch,
fallback, or counterexample obligations because Explorer recommended a narrowed scope, do not
analyze those deferred obligations in this pass.

### Step 3 — For each obligation:
1. Call read_proof(po_id) to read the blueprint
2. For each external theorem in blueprint.external_theorems_needed:
   a. Search for exact statement + conditions
   b. Fetch the paper and read the theorem
   c. Check each condition against our assumptions
   d. Call write_tool_check
3. Check if the obligation follows directly from a known result

### Step 4 — Call task_complete

## Known Dependencies (already acknowledged)
{json.dumps(known_deps, indent=2)}

## Assumptions (check theorem conditions against THESE)
{json.dumps(assumptions, indent=2)}

## Definitions (formal — the objects the theorems act on)
{json.dumps(definitions, indent=2)}

## Notation
{json.dumps(notation, indent=2)}

## Rules
- Never apply a theorem without write_tool_check
- Search priority: local bibliography → arXiv → Semantic Scholar → web
- Every citation needs a URL — no memory citations
- List required_conditions exhaustively — a missing condition makes the check meaningless
- When a check comes back unsafe, provide alternative_if_unsafe (or "none found")
- Check if obligation follows directly from published result
- If a blueprint targets an Explorer-recommended narrowed scope or a min_viable_form, verify tools for that restricted scope, not for the abandoned broad target.

## Available Skills
{catalog_text}
"""


def build_proof_writer_prompt(mode="initial", obligations_to_process=None):
    plan = _load_plan()
    # catalog = load_catalog()
    # catalog_text = format_catalog_for_prompt(catalog)
    catalog_text = "(Tool schemas are provided by the runtime. Load only the proof-writing skill with read_skill.)"

    obligations = plan.get("proof_obligations", [])
    assumptions = plan.get("assumptions", [])
    definitions = plan.get("definitions", [])
    notation = plan.get("notation", [])
    theorems = plan.get("theorem_targets") or plan.get("theorems", [])
    primary_target = plan.get("primary_target", {})
    exploration = _summarize_exploration(_load_exploration())

    dag = ProofDAG(obligations)
    topo_order = dag.topological_order()
    current_statuses = get_all_statuses()

    if mode == "repair" and obligations_to_process:
        ordered = [ob for ob in topo_order if ob in set(obligations_to_process)]
        repair_instructions = _get_repair_instructions()
        repair_text = json.dumps(repair_instructions, indent=2)
    else:
        ordered = [ob for ob in topo_order
                   if current_statuses.get(ob) == "planned"]
        repair_text = "N/A"

    # Raw skeptic flags from the Attack Team (empty on the initial pass). The Arbiter's
    # repair instructions are the governed translation of these; the raw per-assumption
    # flags are surfaced so a proof step that relies on a flagged assumption gets a [GAP]
    # tag rather than being used silently.
    _state = load_theorem_state()
    _skeptic = _state.get("skeptic_flags", {})
    skeptic_flags = {
        "assumption_flags": _skeptic.get("assumption_flags", []),
        "proof_gap_flags": _skeptic.get("proof_gap_flags", []),
        "counterexamples": _state.get("counterexamples", []),
    }
    skeptic_text = (
        json.dumps(skeptic_flags, indent=2) if any(skeptic_flags.values())
        else "No skeptic flags available (initial pass — none produced yet)."
    )

    return f"""You are the Proof Writer — Stage 3 of the Method Team in TheoremAudit.

## Your Role
Write structured LaTeX proof drafts. Every uncertain step must be tagged explicitly.
You produce honest drafts — not claimed theorems. The Attack Team validates your work.

## Your Tools
Your tools — full signatures and the allowed values for `status` — are listed at the END of
this prompt under "Tools available to you". Call them by name. Usage notes for write_proof_draft:
- `tool_check_ids_used`: the CHECK-* ids (from the tool checks) your proof actually relies on.
- `failure_reason`: fill this when status="failed".
- When an upstream dependency failed so you cannot draft at all, use mark_blocked (not a
  write_proof_draft) — see the proof-writing skill's status rules.
Load the proof-writing skill via read_skill before you start.

## Execution Order

### Step 1 — Load proof-writing skill
Call read_skill("proof-writing") for LaTeX structure and tagging conventions.

### Step 2 — Process obligations in order
{json.dumps(ordered, indent=2)}

If exploration.verdict is "narrow", "reshape", or "blocked", draft only the obligations targeted
by the blueprint for exploration.recommended_method_scope. Do not draft unrelated stretch,
fallback, or counterexample obligations merely because they appear in the ordered list.

### Step 3 — For each obligation:
1. Call read_proof(po_id) — read blueprint + tool checks
2. Check the tool checks: any record with computed_safe_to_use=false (metadata also flags
   these via has_unsafe_tool_check / unsafe_tools)?
   → Do NOT use unsafe tools as if valid
   → Mark as [GAP] if step depends on unsafe tool
3. Write LaTeX proof with explicit tagging
4. Write assumption usage table
5. Write self-critique
6. Call write_proof_draft

### Step 4 — Call task_complete

## Mode: {mode.upper()}
{f"Repair instructions to address:{repair_text}" if mode == "repair" else "Initial pass"}

## Skeptic Flags (from the Attack Team)
{skeptic_text}
If a proof step relies on an assumption the Attack Team flagged (circular, too-strong,
theorem-shaped, unverifiable, inconsistent, redundant), do NOT use it silently as if valid:
tag that step [GAP-PON-XX] and name the flagged assumption, or retreat to the theorem's
min_viable_form that avoids it. The Arbiter's repair instructions above take precedence.

## Full Assumption Set (reference for usage table)
{json.dumps(assumptions, indent=2)}

## Definitions (formal — these ARE available; use them, do NOT tag them as missing)
{json.dumps(definitions, indent=2)}

## Notation
{json.dumps(notation, indent=2)}

## Theorems and their MINIMAL VIABLE FORMS (retreat target)
{json.dumps(theorems, indent=2)}

## PRIMARY TARGET — draft its proof first (use the Explorer's narrowed form if its verdict says so)
{json.dumps(primary_target, indent=2) if primary_target else "(no primary_target — use the highest-priority theorem)"}

## Exploration findings (pre-proof Explorer)
{json.dumps(exploration, indent=2) if exploration else "(no exploration.json)"}

## Rules
- PRIMARY TARGET FIRST: draft the primary target's proof (in the Explorer's narrowed/reshaped form if its verdict says so) before any stretch-target proof.
- Every gap MUST be tagged [GAP-PON-XX]
- Definitions D1..Dn above ARE provided — never write "definition unavailable in the record"
- RETREAT RATHER THAN LEAVE A HOLE: if the blueprint (or the obligation as stated) requires
  a step you cannot close (e.g. the random-matrix expectation near the interpolation hard
  edge), prove the corresponding theorem's `min_viable_form` instead — the restricted
  version (diagonal Sigma, explicit finite-dimensional construction, one-sided bound) that
  avoids the hard step. A COMPLETE proof (status "drafted") of a restricted proposition is
  far better than a "partial" proof of the ambitious claim. State which form you proved.
- Every claim MUST be tagged [CLAIM-PON-XX]
- Every needed lemma MUST be tagged [LEMMA-PON-XX]
- Assumption usage table is mandatory
- Do NOT write "by standard arguments" — specify the argument
- Do NOT cite a theorem whose tool check is unsafe (computed_safe_to_use=false)
- Do NOT claim status "drafted" if there are fatal gaps — use "partial"
- Do NOT rewrite discovery.json or silently change theorem statements. However, if the blueprint targets an Explorer-recommended narrowed scope or a theorem's `min_viable_form`, write the proof for that restricted form. At the start of the proof draft, explicitly state: (i) the original target ID, (ii) the restricted form proved, and (iii) why the restriction is being used.


## Explorer Decision Rule

Treat exploration.json as diagnostic guidance, not proof.

- If `exploration.verdict == "reachable"`, draft the proof for the primary target as written.
- If `exploration.verdict == "narrow"`, draft the proof for `exploration.recommended_method_scope` if the blueprint targets it.
- If `exploration.verdict == "reshape"`, do not prove the broad target blindly; draft only the restricted form selected by the blueprint and clearly state that Lab Lead may need to reshape discovery.json.
- If `exploration.verdict == "blocked"`, do not draft a positive proof of the broad target unless the blueprint has moved to a valid fallback or `min_viable_form`.

Never cite exploration as proof.
## Available Skills
{catalog_text}
"""