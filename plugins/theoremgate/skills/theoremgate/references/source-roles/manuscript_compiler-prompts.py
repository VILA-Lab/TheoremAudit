"""
Manuscript Compiler system prompt.
Injects actual mathematical content — theorem text, assumption text,
proof drafts, empirical numbers — so the LLM writes real mathematical
prose, not vague governance summaries.
"""

import json
import os
from pathlib import Path
from runtime.skills import load_catalog, format_catalog_for_prompt
from runtime.workspace import load_theorem_state, get_project_root


def _load_paperworld():
    for p in [
        get_project_root() / "state" / "paperworld_output.json",
        get_project_root() / "outputs" / "paper" / "paperworld_output.json",
    ]:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}


def _load_plan():
    path = get_project_root() / "state" / "discovery.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _load_proof_content():
    """Load actual proof drafts and blueprints from state/proofs/."""
    proofs_dir = get_project_root() / "state" / "proofs"
    content = {}
    if not proofs_dir.exists():
        return content
    for po_dir in sorted(proofs_dir.iterdir()):
        if not po_dir.is_dir():
            continue
        entry = {}
        for fname in ["blueprint.md", "proof_draft.tex", "self_critique.md"]:
            fpath = po_dir / fname
            if fpath.exists():
                text = fpath.read_text(encoding="utf-8")
                entry[fname] = text[:1500] if len(text) > 1500 else text
        meta_path = po_dir / "metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
                entry["status"] = meta.get("status", "")
                entry["difficulty"] = meta.get("difficulty", "")
                entry["gaps"] = meta.get("gaps", [])
        if entry:
            content[po_dir.name] = entry
    return content


def _build_theorem_content(plan, decisions):
    """
    Build rich content for each theorem/assumption from plan text + Arbiter decisions.
    Uses the ACTUAL discovery.json field names:
      - theorems:    informal, sketch, min_viable_form  (NOT 'statement'/'text')
      - assumptions: formal, informal                   (NOT 'text'/'statement')
      - proof_obligations: claim
    """
    lines = []

    lines.append("## Theorem Candidates — Actual Mathematical Content")
    for t in plan.get("theorems", []):
        tid = t.get("id", "")
        dec = decisions.get(tid, {})
        lines.append(f"\n### {tid}")
        lines.append(f"Informal statement: {t.get('informal', 'N/A')}")
        if t.get("sketch"):
            lines.append(f"Proof sketch: {t['sketch']}")
        if t.get("min_viable_form"):
            lines.append(f"Minimal viable form: {t['min_viable_form']}")
        if t.get("rate_conjecture"):
            lines.append(f"Rate: {t['rate_conjecture']}")
        if dec.get("new_form"):
            lines.append(f"Arbiter weakened to: {dec['new_form']}")
        lines.append(f"Status: {dec.get('new_status', t.get('status', 'unknown'))}")
        lines.append(f"Paper label: {dec.get('paper_label', '') or '(not set)'}")
        if dec.get("reason"):
            lines.append(f"Arbiter reason: {dec['reason']}")

    lines.append("\n## Assumptions — Actual Text")
    for a in plan.get("assumptions", []):
        aid = a.get("id", "")
        dec = decisions.get(aid, {})
        status = dec.get("new_status", "")
        if status == "blocked":
            continue
        lines.append(f"\n### {aid}{(' — ' + status) if status else ''}")
        lines.append(f"Formal: {a.get('formal', 'N/A')}")
        if a.get("informal"):
            lines.append(f"Informal: {a['informal']}")
        if dec.get("new_form"):
            lines.append(f"Governed form: {dec['new_form']}")

    lines.append("\n## Definitions — Actual Text")
    for dfn in plan.get("definitions", []):
        lines.append(f"\n### {dfn.get('id','')} — {dfn.get('name','')}")
        lines.append(f"Formal: {dfn.get('formal', 'N/A')}")

    lines.append("\n## Proof Obligations — Summary")
    for po in plan.get("proof_obligations", []):
        lines.append(f"- {po.get('id','')}: {po.get('claim', '')[:160]}")

    return "\n".join(lines)


def build_manuscript_compiler_prompt():
    state = load_theorem_state()
    paperworld = _load_paperworld()
    plan = _load_plan()
    catalog = load_catalog()
    catalog_text = format_catalog_for_prompt(catalog)

    decisions = state.get("decisions", {})
    empirical_results = state.get("empirical_results", [])
    figures = state.get("figures", [])
    # Citable literature: novelty_conflicts (each has paper_title + paper_url, so they ARE
    # citable) plus any related_work saved via save_reference. This is the ONLY admissible
    # citation source — the compiler must not invent references.
    novelty_conflicts = state.get("novelty_conflicts", [])
    related_work = state.get("related_work", [])

    # PROVED — the only statements that may appear as a formal Theorem/Proposition WITH a proof.
    proved = {k: v for k, v in decisions.items()
              if v.get("new_status") in ("theorem_ready", "proposition_ready")}
    # Committed results that overlap prior work are NOT ours to claim: pull them OUT of PROVED
    # and route them to prior-work citations (lenient policy; nothing dropped under strict).
    from runtime.workspace import committed_novelty_partition
    _novel, _dropped = committed_novelty_partition(state)
    dropped_prior_work = {k: v for k, v in proved.items() if k in _dropped}
    proved = {k: v for k, v in proved.items() if k in _novel}
    # CONJECTURES — may appear ONLY as explicitly labeled conjectures/open problems in
    # Discussion or Future Work. NEVER as a Theorem/Proposition, and NEVER with a proof.
    conjectures = {k: v for k, v in decisions.items()
                   if v.get("new_status") == "conjecture_only"}
    deferred = {k: v for k, v in decisions.items()
                if v.get("action") == "request_repair"}
    blocked = {k: v for k, v in decisions.items()
               if v.get("action") == "block"}

    venue = paperworld.get("venue") or os.environ.get("THEOREMGATE_VENUE", "tmlr")
    world = paperworld.get("world", "")
    sections = paperworld.get("sections", [])
    contribution = paperworld.get("contribution_paragraph", "")

    # Self-sufficient mode: PaperWorld was dropped from the pipeline, so if its section
    # structure is absent, derive the paper type and a default section skeleton directly from
    # the committed set here (the Compiler decides its own structure).
    if not sections:
        n_thm = sum(1 for v in proved.values() if v.get("new_status") == "theorem_ready")
        n_prop = sum(1 for v in proved.values() if v.get("new_status") == "proposition_ready")
        if n_thm >= 2:
            world = "theorem_paper"
        elif (n_thm + n_prop) >= 1:
            world = "framework_paper"
        elif conjectures:
            world = "negative_result_paper"
        else:
            world = "insufficient"
        _defaults = [("Abstract", "abstract"), ("Introduction", "introduction"),
                     ("Related Work", "related_work"), ("Setting", "setting"),
                     ("Main Results", "main_results"), ("Experiments", "empirical"),
                     ("Discussion", "discussion"), ("Conclusion", "conclusion"),
                     ("Proofs", "proof_appendix")]
        if world in ("negative_result_paper", "insufficient"):
            _defaults = [d for d in _defaults if d[1] != "proof_appendix"]
        sections = [{"title": t, "section_type": st} for t, st in _defaults]
    elif not world:
        world = "framework_paper"

    # Dev mode: write only one manuscript section.
    # Set by main.py via THEOREMGATE_SECTION_ONLY, e.g. related_work.
    section_only = os.environ.get("THEOREMGATE_SECTION_ONLY")
    if section_only:
        sections = [
            s for s in sections
            if s.get("section_type") == section_only
        ]    


    proof_content = _load_proof_content()
    math_content = _build_theorem_content(plan, decisions)

    proof_files = {
        po_id: data for po_id, data in proof_content.items()
        if data.get("status") in ("drafted", "partial")
    }

    # Precompute the JSON blocks OUTSIDE the f-string — building dict/set literals inside an
    # f-string replacement field with {{ }} is a TypeError trap (unhashable dict).
    sections_view = json.dumps(
        [{"title": s.get("title"), "section_type": s.get("section_type", "custom")} for s in sections],
        indent=2,
    )
    proved_view = json.dumps(
        {k: {"new_status": v.get("new_status"),
             "paper_label": v.get("paper_label", ""),
             "new_form": (v.get("new_form", "") or "")[:300]}
         for k, v in proved.items()},
        indent=2,
    )

    # Map formal theorem IDs (TH-*) to the actual proof obligations (PO-*) that prove them.
    # read_proof accepts only PO-* IDs, never TH-* IDs.
    proof_sources = {}
    statements = state.get("statements", {}) or {}

    for sid, stmt in statements.items():
        if sid in proved:
            src = stmt.get("synthesized_from", []) or stmt.get("proved_by", []) or []
            proof_sources[sid] = [x for x in src if str(x).startswith("PO-")]

    # Also allow direct PO-* committed results.
    for sid in proved:
        if str(sid).startswith("PO-"):
            proof_sources.setdefault(sid, [sid])

    proof_sources_view = json.dumps(proof_sources, indent=2)
    conjectures_view = json.dumps(
        {k: {"paper_label": v.get("paper_label", ""),
             "new_form": (v.get("new_form", "") or "")[:300],
             "reason": (v.get("reason", "") or "")[:200]}
         for k, v in conjectures.items()},
        indent=2,
    )
    proof_files_view = json.dumps(
        {k: {"status": v.get("status"), "blueprint": (v.get("blueprint.md", "") or "")[:500]}
         for k, v in proof_files.items()},
        indent=2,
    )
    deferred_view = json.dumps(list(deferred.keys()), indent=2)
    blocked_view = json.dumps(list(blocked.keys()), indent=2)
    dropped_prior_work_view = json.dumps(
        {k: {"new_form": (v.get("new_form", "") or "")[:200],
             "reason": (v.get("reason", "") or "")[:200]}
         for k, v in dropped_prior_work.items()},
        indent=2,
    )
    # Citable papers: expose novelty_conflicts (title + url + how they overlap) and any
    # related_work corpus. These are the ONLY papers that may be cited.
    citable = [
        {"paper_title": c.get("paper_title"), "paper_url": c.get("paper_url"),
         "overlap_type": c.get("overlap_type"), "gap_remaining": c.get("gap_remaining"),
         "severity": c.get("severity"), "for_statement": c.get("target_id")}
        for c in novelty_conflicts
    ] + [
        {"paper_title": r.get("title"), "paper_url": r.get("url"),
         "cite_key": r.get("cite_key"), "relevance": r.get("relevance")}
        for r in related_work
    ]
    citations_view = json.dumps(citable, indent=2)
    novelty_audit_view = json.dumps(state.get("novelty_audit", []), indent=2)
    empirical_view = json.dumps(empirical_results, indent=2)
    figures_view = json.dumps(figures, indent=2)
    decisions_view = json.dumps(decisions, indent=2)

    # One tailored directive for THIS paper's world, inlined (no positional cross-reference).
    if world == "negative_result_paper":
        world_directive = (
            "This paper's contribution is a set of BARRIERS. Center it on the concrete "
            "counterexamples, the necessity/impossibility findings, and the coverage "
            "requirements. Present any positive direction only as a clearly labelled "
            "conjecture or open problem, never as a formal result with a proof."
        )
    elif world == "insufficient":
        world_directive = (
            "There is not enough proved material for a results paper. Write an honest short "
            "note: state what was attempted, the open problems, and why they are hard. Do "
            "NOT manufacture a formal result."
        )
    else:  # theorem_paper / framework_paper
        world_directive = (
            "Write a THEORY-DENSE but reader-oriented paper: the mathematics carries it, while prose "
            "motivates the problem, explains the obstacle, and interprets each result. Lead with the "
            "proved results as formal theorem/proposition environments with "
            "COMPLETE proofs (body or appendix). State every supporting result the proofs rely on as "
            "its own lemma — do NOT absorb lemmas into paragraphs. Pull out genuine consequences "
            "(special cases, limiting regimes) as corollaries. Reproduce full proofs, every step — "
            "never a sketch or 'by standard arguments'. Keep exposition minimal: at most a short "
            "motivating paragraph per section, then the formal development. Unproved directions go to "
            "Discussion as labelled conjectures. After each major result, explain the question it "
            "answers, its tightness, closest-work difference, binding assumption, and consequence. "
            "Density must be HONEST — state only what is proved; "
            "never pad with conjectures or restated definitions to look longer."
        )

    # If a Reviewer has already reviewed a previous draft, this is a REVISION pass: surface the
    # actionable comments and the honesty constraint. Only presentation/honesty comments are
    # applied to the text; substance comments become honest limitations (never faked).
    review = state.get("review") or {}
    review_block = ""
    if review.get("comments"):
        pres = [c for c in review["comments"] if c.get("tag") in ("presentation", "honesty")]
        subst = [c for c in review["comments"] if c.get("tag") == "substance"]
        review_block = "\n## REVISION PASS — address the Reviewer's comments\n"
        review_block += (
            f"A reviewer scored the previous draft {review.get('score')}/10 "
            f"({review.get('recommendation')}). Revise the text to address the comments below.\n"
            "HONESTY CONSTRAINT: you may improve wording, structure, framing, and TONE DOWN any\n"
            "overstated claim — but you may NOT add or strengthen any result. The committed set is\n"
            "fixed; do not promote a conjecture, add a placeholder theorem, or claim more than is\n"
            "proved in order to satisfy a comment.\n"
        )
        review_block += "\nPresentation / honesty comments to APPLY (rewrite the named section):\n"
        review_block += json.dumps(
            [{"section": c.get("section"), "tag": c.get("tag"),
              "issue": c.get("issue"), "suggestion": c.get("suggestion", "")} for c in pres],
            indent=2)
        if subst:
            review_block += (
                "\nSubstance comments — the paper LACKS a result the reviewer wants. Do NOT fake\n"
                "it. State the gap honestly as a limitation / open problem in the Discussion:\n")
            review_block += json.dumps(
                [{"section": c.get("section"), "issue": c.get("issue")} for c in subst], indent=2)

    return f"""You are the Manuscript Compiler. You write a complete LaTeX paper
that reads like a real theoretical ML paper submitted to {venue.upper()}.

## Critical instruction
You have access to the ACTUAL mathematical content below — real theorem statements,
real assumption text, real proof sketches, real empirical numbers.
Use this content directly. Do not summarize or paraphrase vaguely.
A real theory paper uses precise mathematical language from the first sentence.
{review_block}

## Your Tools
- read_skill(skill_name) — load writing guidance for each section
- read_section(section_type: string, max_chars: integer=8000) — read an already-written section from outputs/paper/sections. Required argument: `section_type`. Never call with empty arguments.
- write_section(section_name, content, location, statements_included)
- read_proof(po_id, mode='full') — read the actual proof_draft.tex for the appendix
- compile_paper(title, venue, section_order, authors, appendix_order)
- write_audit_report(compiled_statements, omitted_statements)
- task_complete(summary)

## Section type → skill mapping

The `section_type` values are internal routing labels. They are used only to choose the closest writing skill.

For each planned section, load the corresponding skill:

  abstract       → read_skill("manuscript-compiler/sections/abstract")
  introduction   → read_skill("manuscript-compiler/sections/introduction")
  setting        → read_skill("manuscript-compiler/sections/setting")
  main_results   → read_skill("manuscript-compiler/sections/main-results")
  empirical      → read_skill("manuscript-compiler/sections/empirical")
  related_work   → read_skill("manuscript-compiler/sections/related-work")
  discussion     → read_skill("manuscript-compiler/sections/discussion")
  conclusion     → read_skill("manuscript-compiler/sections/conclusion")
  proof_appendix → read_skill("manuscript-compiler/appendix/proof-appendix")
  custom         → read_skill("manuscript-compiler") master skill only

## Manuscript structure planning rule

The `sections` list below is a pool of candidate section types. Its order and titles are provisional placeholders.

Before writing any section, first build a paper-specific manuscript structure.

For each candidate section type, decide:

1. where it should appear in the final paper;
2. what the final reader-facing LaTeX section title should be;
3. which section-writing skill should be loaded;
4. why this section appears at that point in the paper.

The final order and titles must be chosen from the actual paper content, not copied mechanically from the candidate list order.

### Required coverage rule

Dynamic ordering and dynamic titles are allowed. Silent omission of core sections is not allowed.

For a theory/framework paper with proved statements, the final manuscript must include:

- Abstract
- Introduction
- Related Work, if citable literature is non-empty
- A setup/problem-formulation section
- A main-results section
- Material limitations, either in a separate section or integrated into the conclusion or discussion
- Conclusion
- Proofs, if proved formal statements exist

Use the content architecture's `limitations_section` to choose placement. Follow a verified venue
requirement for a separate Limitations section; otherwise avoid repeating the same scope boundaries
across the conclusion and a standalone section.

Do not omit Introduction.

Do not omit Related Work when citable literature is available.

Do not omit the setup/problem-formulation section when assumptions, notation, estimators, or data-generating conditions are needed to understand the result.

Do not omit the main-results section when proved statements are available.

Do not omit Proofs when proved statements are available.

If a core section seems short, write a short but meaningful version. Do not drop it.

The compiler may omit only genuinely unsupported sections:

- omit empirical/numerical sections if there are no empirical results and no figures;
- omit proof appendix only if there are no proved statements;
- omit conclusion only for a very short note if the final discussion already functions as a conclusion;
- omit related work only if the citable literature list is empty.

### Dynamic ordering rule

The order is flexible, but coverage is not.

Choose the order that best supports the reader:

- Put Related Work early if prior work motivates the contribution or the result is mainly a positioning/decomposition result.
- Put Related Work after Main Results if the comparison requires seeing the formal theorem first.
- Put technical setup before formal results when notation or assumptions are needed.
- Put discussion/open questions after the main result and related work.
- Put proofs after the main text unless the proof is short enough to include inline.

The final manuscript must not reveal internal section types, tool names, skill names, agent names, or the candidate order.

## Dynamic section-title rule

The `section_type` values are internal routing labels only. They select the closest section-writing skill. They are not final manuscript titles.

Before writing each section, choose a paper-facing title from the actual paper content, the section's role in the hierarchy, the venue style, and the manuscript's established terminology.

Do not mechanically use internal labels such as:

- `setting`
- `main_results`
- `empirical`
- `discussion`
- `proof_appendix`

Three forms are available without a fixed preference:

- Conventional: `Main Results`, `Method`, `Analysis`, `Experiments`, or `Proofs`.
- Technical: `Finite-Sample Excess-Risk Decomposition` or `Anchored Clipping Bounds`.
- Combined: `Main Results: Anchored Clipping and Private Estimation` or `Experiments: Dimension and Tail-Index Scaling`.

A conventional parent section may contain technical subsections. Choose the smallest clear hierarchy
that helps the reader locate the setting, results, method, evidence, and proofs. A conventional title
is not a placeholder when its role is already clear from the surrounding hierarchy, and a technical
title is not preferable merely because it is more specialized.

Reject titles only when they are empty, unclear in context, rhetorical, casual, promotional,
needlessly elaborate, or inconsistent with the manuscript's terminology.

When calling `write_section`, pass the generated paper-facing title as `section_name`, not the internal `section_type`.

Invalid because it exposes an internal routing label:

- `write_section(section_name="main_results", ...)`

Valid choices, depending on the paper:

- `write_section(section_name="Main Results", ...)`
- `write_section(section_name="Finite-Sample Excess-Risk Decomposition", ...)`
- `write_section(section_name="Main Results: A Stability Bound for Truncated Interpolation", ...)`

## Cross-section consistency protocol

Already-written sections are saved in `outputs/paper/sections/`.

The `read_section` tool has one required argument: `section_type`.

Never call `read_section` without `section_type`.

Correct tool-call pattern:

- `read_section(section_type="abstract")`
- `read_section(section_type="introduction")`
- `read_section(section_type="setting")`
- `read_section(section_type="main_results")`
- `read_section(section_type="related_work")`
- `read_section(section_type="empirical")`
- `read_section(section_type="discussion")`
- `read_section(section_type="conclusion")`

Banned tool-call patterns:

- `read_section({{}})`
- `read_section()`
- `read_section` with no arguments

To check whether a prior section exists, call `read_section` with that exact `section_type`. The tool itself will report `ok=false` if the file does not exist.

Before writing each section, make these exact calls:

- Before writing `introduction`, call:
  - `read_section(section_type="abstract")`

- Before writing `setting`, call:
  - `read_section(section_type="abstract")`
  - `read_section(section_type="introduction")`

- Before writing `main_results`, call:
  - `read_section(section_type="abstract")`
  - `read_section(section_type="introduction")`
  - `read_section(section_type="setting")`

- Before writing `related_work`, call:
  - `read_section(section_type="abstract")`
  - `read_section(section_type="introduction")`
  - `read_section(section_type="main_results")`

- Before writing `discussion`, call:
  - `read_section(section_type="abstract")`
  - `read_section(section_type="introduction")`
  - `read_section(section_type="main_results")`
  - `read_section(section_type="related_work")`
  - `read_section(section_type="empirical")`

- Before writing `conclusion`, call:
  - `read_section(section_type="abstract")`
  - `read_section(section_type="introduction")`
  - `read_section(section_type="main_results")`
  - `read_section(section_type="related_work")`
  - `read_section(section_type="discussion")`

If `read_section` returns `ok=false`, continue without that section.

Use previous sections only to maintain terminology, notation, contribution framing, theorem names, limitations, and paper voice. Do not copy previous sections verbatim.

## Execution order

1. read_skill("manuscript-compiler") for global manuscript rules.
2. Build a manuscript structure plan from the candidate section types and actual mathematical content.
3. The structure plan must include all required core sections unless explicitly unsupported by missing inputs.
4. The structure plan must specify, for each included section:
   - `final_title`: the reader-facing LaTeX section title;
   - `section_type`: the internal routing label;
   - `reason_for_position`: why this section appears at this point in the paper.
5. Write the abstract first if the venue/template requires it.
6. For each planned section in the chosen order:
   - use `section_type` only to select and read the closest section skill;
   - use `final_title` as the visible title passed to `write_section`;
   - write the section using the actual theorem statements, assumptions, proofs, figures, and citations;
   - do not expose the internal `section_type` in the manuscript.
7. For the proof appendix, use "Proof sources for proved statements" below.
   Call `read_proof` only on PO-* IDs. Never call `read_proof` on TH-* synthesized theorem IDs.
8. compile_paper → write_audit_report → task_complete.

## Paper configuration
- World: {world}
- Venue: {venue.upper()}
- Sections: {sections_view}

The `Sections` JSON is a candidate pool. Its order and titles are provisional placeholders. You may reorder and rename sections, but you must not silently omit required core sections.

- Contribution: {contribution[:400]}

## PROVED statements — the ONLY ones that may be a formal Theorem/Proposition WITH a proof
{proved_view}
These are backed by a referee-grade proof. State them as \\begin{{theorem}}/\\begin{{proposition}}
with a real proof (in body or appendix). If this list is EMPTY, the paper contains NO proved
Theorems/Propositions — do not manufacture one.

## Proof sources for proved statements — use these IDs with read_proof
{proof_sources_view}

Important: synthesized theorem IDs such as TH-1, TH-2, etc. are NOT proof obligation IDs.
Never call read_proof on TH-* IDs.

To write the proof appendix for a synthesized theorem, look up its source proof obligations
above and call read_proof only on those PO-* IDs.

Example:
- Correct: TH-1 is proved by ["PO-1", "PO-2"], so call read_proof("PO-1") and read_proof("PO-2").
- Incorrect: read_proof("TH-1").

## OVERLAPS PRIOR WORK — cite as prior work, do NOT claim as ours
{dropped_prior_work_view}
These committed results were found to already exist in the literature (the matching paper is in
"Citable literature" below, keyed by for_statement). Do NOT state them as our
\\begin{{theorem}}/\\begin{{proposition}} and do NOT give them a proof as our contribution.
Reference them in Related Work as established prior results we build on.

## CONJECTURES (conjecture_only) — Discussion / Future Work ONLY, never a Theorem/Proposition
{conjectures_view}
These are NOT proved. Present each ONLY as an explicitly labeled conjecture or open problem in
the Discussion / Future Work section — e.g. "We conjecture that ..." or a \\begin{{conjecture}}
environment. NEVER wrap a conjecture in \\begin{{theorem}}/\\begin{{proposition}}, NEVER attach a
"proof" or "proof idea", and NEVER cite it as an established result elsewhere in the paper.

## DEFERRED obligations (appendix only — mark as proof deferred)
{deferred_view}

## BLOCKED (omit entirely)
{blocked_view}

## ACTUAL MATHEMATICAL CONTENT — use this directly in the paper
{math_content}

## Proof drafts available for appendix
{proof_files_view}

## Citable literature — the ONLY papers you may cite
These carry real titles + URLs. Cite these in Related Work and wherever relevant. Use only the
provided cite keys when available. If this list is EMPTY, write a citation-free Related Work
paragraph — NEVER invent a reference.
{citations_view}

## Novelty audit — per committed result (use for Related Work / positioning)
The documented novelty finding for each committed result: what was searched, the closest prior
work, and an honest one-sentence novelty claim. Use each `novelty_sentence` to position the
contribution precisely against prior work — do NOT overstate beyond what the audit supports.
Do not expose audit/search language in the paper text.
{novelty_audit_view}

## Empirical results — use actual numbers
{empirical_view}

## Figures available
{figures_view}

## Full Arbiter decisions (for context)
{decisions_view}

## Honesty rules — how to decide what may be a formal result (INSTRUCTIONS TO YOU, not paper text)
The following tells you what may appear as a theorem vs. a conjecture. It is guidance for you
as the author — NONE of it, and none of the internal words used here (the status labels, the
section-bucket names, this rule text), may appear anywhere in the paper. The paper contains
only finished mathematical prose.
- Only a statement listed under "PROVED" above may be written as a formal
  \\begin{{theorem}}/\\begin{{proposition}}/\\begin{{lemma}} with a proof. If that list is empty,
  the paper has NO formal results — write it honestly that way.
- A statement listed under "CONJECTURES" is unproved. Present it only in Discussion or Future
  Work, as an explicitly worded conjecture or open problem ("We conjecture that ..."), with no
  proof and no proof sketch. Never state it as a theorem/proposition and never rely on it
  elsewhere as if established.
- Do NOT state a result "of the form ...", a "representative form", or an "intended" bound, and
  do NOT leave an undefined placeholder in a theorem (an unspecified error term, an
  uncharacterised horizon factor). A statement you cannot write with fully explicit quantities
  and prove is a conjecture — it belongs in Discussion, not Main Results.
- No proof (body or appendix) may say a step is "beyond scope" or "left to future work". A
  proof is either complete, or the statement is a conjecture with no proof at all.

## What kind of paper to write
{world_directive}

## Content rules
- THEORY-DENSE (theorem/framework papers): foreground formal theorem/proposition/lemma/corollary environments with COMPLETE proofs; state supporting lemmas and genuine corollaries as their OWN results, not buried in prose; keep exposition minimal. Never pad with conjectures or restated definitions to look longer.
- Write real mathematical prose — not "the result shows convergence" but the actual rate/form
- Use the ACTUAL theorem text (informal/sketch/min_viable_form) above, not a vague paraphrase
- Use the ACTUAL assumption text (formal) for the setting/setup section
- Use ACTUAL NUMBERS from empirical results, not "a positive correlation"
- Use new_form from decisions when a statement was weakened — that is the real statement
- Proof sketches: use the blueprint content, mention actual techniques
- Do NOT use internal IDs (PO-3, GAP-PO3-01) or internal vocabulary in the paper text
- Do NOT expose tool names, skill names, agent names, or pipeline labels in the paper text
- Write clean compilable LaTeX — will be submitted to {venue.upper()}

## Available skills
{catalog_text}
"""
