---

name: paperworld
description: "Select the most supportable paper world from surviving theorem_state decisions. Determines paper type, venue strategy, section structure, contribution framing, and which empirical checks to run. Called by PaperWorld Builder after Lab Lead Arbiter completes."
version: 1.1
used_by: paperworld_builder
domain: theoretical machine learning
inputs: theorem_state.json, discovery.json, empirical_results.json if available, user constraints if available
outputs: paperworld_output.json via select_world, add_section, select_template, suggest_empirical
-------------------------------------------------------------------------------------------------

# PaperWorld Selection Skill

## Purpose

Select the most honest and supportable paper framing from the surviving theorem-state decisions.

After the Arbiter, the surviving statements determine what kind of paper can actually be written. A system should not frame the paper as a theorem paper if only proposition-level results survived, and it should not present conjectures or repair-requested statements as established results.

This skill maps the governed theorem state into:

* paper world/type;
* venue strategy;
* section structure;
* claim-to-section mapping;
* empirical-check plan;
* contribution paragraph.

The output should support a normal, professional theoretical ML paper.

## Core principle

The paper world must match the strongest committed results that survived.

Do not choose the most impressive framing. Choose the most defensible framing.

The selected paper world should be based on:

* centrality of surviving results;
* result strength;
* proof readiness;
* novelty;
* coherence of the contribution;
* empirical or numerical support, if relevant;
* venue expectations;
* user constraints.

Counts are useful signals, but they are not sufficient. One central theorem can support a theorem paper; several weak propositions may still be insufficient.

## Statement inclusion rules

Use theorem-state decisions honestly.

* `theorem_ready`: may appear as a main result if central and coherent.
* `proposition_ready`: may appear as a main result or supporting result depending on strength.
* `conjecture_only`: may appear only in discussion, limitations, or future work. It must not be presented as an established result.
* `repair_requested`: exclude from the main paper unless repaired and recommitted. Do not include it as a deferred proof.
* `blocked`: exclude from the paper. It may be mentioned only as future work or a limitation if scientifically useful.
* Any statement with unresolved proof gaps must not be framed as proved.

Do not include internal status labels in the paper text.

## World selection rules

### World 1 — Theory/Theorem Paper

Use when the surviving state contains at least one central theorem-level result, or multiple theorem-ready results, with enough supporting lemmas/propositions to form a coherent technical contribution.

Typical shape:

* 1–3 central theorem-level results;
* supporting propositions, lemmas, or corollaries;
* detailed proofs in appendix;
* optional numerical illustration if it clarifies the theory.

Empirical checks are optional. Include them only if they help readers understand the theorem, validate a qualitative prediction, or illustrate a non-obvious regime.

### World 2 — Framework/Proposition Paper

Use when the surviving state contains several proposition-level results, definitions, constructions, or analyses that together introduce a coherent framework, but not enough theorem-level strength for a theorem-first paper.

Typical shape:

* several proposition-level results;
* new definitions or formal objects;
* conceptual framework or decomposition;
* proof sketches or supporting proofs;
* empirical or numerical illustration if helpful.

Empirical or numerical checks are recommended when they make the framework easier to understand or demonstrate the behavior of a new object.

### World 3 — Negative/Impossibility Paper

Use when the surviving state contains at least one committed impossibility result, lower bound, separation, impossibility theorem, or explicit counterexample.

Typical shape:

* formal negative result;
* constructive example or lower-bound construction;
* implications for existing assumptions, methods, or evaluation practices;
* optional empirical/numerical demonstration of the failure mode.

Conjecture-only statements cannot be the main contribution. They may appear only as motivation, discussion, or future work.

### World 4 — Methodological/Diagnostic Paper

Use when the surviving state does not contain a strong theorem, but contains a coherent diagnostic framework, validated definitions, empirical/numerical checks, and proposition-level analysis.

Typical shape:

* formal diagnostic or framework;
* proposition-level guarantees;
* carefully designed numerical/empirical evidence;
* clear limitations.

Use this world only if the contribution is still scientifically meaningful and not just a collection of weak claims.

### Insufficient Paper World

Use ONLY when NOTHING committed — zero `theorem_ready` and zero `proposition_ready` results.

Examples:

* no theorem-ready or proposition-ready statements survived;
* only conjectures survived;
* all central claims are blocked or repair-requested.

If even ONE proposition committed, this is a Focused Proposition Paper (World 2), not
insufficient — build the paper around that result. Insufficient is reserved for a truly empty
committed set.

When genuinely insufficient, select `world="insufficient"` and return to the Lab Lead for
repair/weakening/direction revision. Do NOT write a manuscript, and never emit internal status
sections ("Missing Contribution Summary", "Blocked or Unusable Claims", "Recommended Repair
Path") — those expose the pipeline and are not a paper.

## World selection procedure

### Step 1 — Count surviving statements

Read `theorem_state.json` and count:

* theorem-ready statements;
* proposition-ready statements;
* conjecture-only statements;
* blocked statements;
* repair-requested statements;
* committed counterexamples, separations, lower bounds, or impossibility statements.

Use counts as evidence, not as hard rules.

### Step 2 — Identify the central contribution

Determine whether the surviving statements support one coherent scientific argument.

Ask:

* What is the strongest committed result?
* Is there a central theorem-level claim?
* Do the propositions build a coherent framework?
* Is there a committed negative result or counterexample?
* Are the surviving statements enough for a paper, or only for notes/future work?
* Are empirical checks needed to make the contribution legible?

### Step 3 — Select the paper world

Choose the highest honest world supported by the state.

If borderline, prefer the more conservative world.

Examples:

* theorem-ready central result exists → likely Theory/Theorem Paper;
* no theorem-ready result, but several coherent proposition-ready statements and definitions → Framework/Proposition Paper;
* committed lower bound, separation, or counterexample → Negative/Impossibility Paper;
* only conjectures or repair-requested statements → Insufficient Paper World.

Do not inflate proposition-level work into theorem-level framing.

## Venue selection rules

If the user specified a venue, use that venue unless the surviving results clearly cannot support it. If the requested venue is mismatched, record the mismatch in the rationale.

If no venue is specified, assign a best-fit provisional named venue for every accepted-result paper.
Use that venue to shape a full-length manuscript, but keep venue targeting separate from
`submission_ready`: unverified novelty, incomplete experiments, or stale official rules may prevent
submission readiness without removing the venue target or shortening the paper.

### Venue guidance

| Paper world                     | Strong fits                | Possible fits         | Notes                                                            |
| ------------------------------- | -------------------------- | --------------------- | ---------------------------------------------------------------- |
| Theory/Theorem Paper            | COLT, JMLR                 | NeurIPS, ICML, ICLR   | Best when formal results are strong and central                  |
| Framework/Proposition Paper     | ICLR, TMLR                 | NeurIPS, ICML         | Best when conceptual contribution is clear and broadly relevant  |
| Negative/Impossibility Paper    | COLT, ICLR, NeurIPS        | ICML, JMLR, workshops | Needs strong formal negative result or compelling counterexample |
| Methodological/Diagnostic Paper | ICLR, TMLR, workshops      | NeurIPS, ICML         | Needs strong empirical/numerical support or broad relevance      |
| Insufficient                    | workshop only after repair | none                  | Return to Lab Lead first                                         |

### Venue modifiers

* If the paper is proof-heavy and needs space, prefer JMLR or TMLR.
* If the paper has strong theory and broad ML relevance, consider NeurIPS or ICML.
* If the paper is theory-first and technically deep, consider COLT.
* If the paper is conceptual, framework-oriented, representation-oriented, or agent/model-behavior focused, consider ICLR.
* If novelty is promising but not yet verified, still target the best-fit named venue and use
  calibrated contribution language; do not make first/unique claims without primary-source support.
* If the user asks for current deadlines or requirements, verify them using web search before finalizing.

Do not describe venues as easy, biased, or guaranteed.

## Section structure by world

Section titles must be normal, idiomatic academic titles.

Never encode internal process, status, governance, repair, Arbiter decisions, proof obligations, or conjectural status into section titles.

### World 1 — Theory/Theorem Paper

Use a structure like:

```text
1. Introduction
2. Related Work
3. Preliminaries
4. Main Results
5. Numerical Illustration or Empirical Illustration, if included
6. Discussion
7. Conclusion
Appendix A: Proofs
Appendix B: Additional Results
Appendix C: Experimental Details, if needed
```

### World 2 — Framework/Proposition Paper

Use a structure like:

```text
1. Introduction
2. Related Work
3. Problem Setup
4. Framework
5. Main Analysis
6. Numerical Illustration or Empirical Illustration, if included
7. Discussion
8. Conclusion
Appendix A: Proofs
Appendix B: Additional Details
Appendix C: Experimental Details, if needed
```

### World 3 — Negative/Impossibility Paper

Use a structure like:

```text
1. Introduction
2. Related Work
3. Problem Setup
4. Main Negative Results
5. Constructions or Counterexamples
6. Implications
7. Discussion
8. Conclusion
Appendix A: Proofs
Appendix B: Additional Constructions
```

### World 4 — Methodological/Diagnostic Paper

Use a structure like:

```text
1. Introduction
2. Related Work
3. Problem Setup
4. Diagnostic Framework
5. Analysis
6. Experiments or Numerical Illustration
7. Discussion
8. Conclusion
Appendix A: Additional Analysis
Appendix B: Experimental Details
```

### Insufficient Paper World

Do not build a full paper structure.

Return a repair-oriented structure for internal use only:

```text
1. Missing Contribution Summary
2. Surviving Claims
3. Blocked or Unusable Claims
4. Recommended Repair Path
```

This internal structure is not a manuscript template.

## Section title rules

Use ordinary paper section titles.

Preferred titles:

* `Introduction`
* `Related Work`
* `Preliminaries`
* `Problem Setup`
* `Framework`
* `Main Results`
* `Main Analysis`
* `Negative Results`
* `Counterexamples`
* `Numerical Illustration`
* `Empirical Illustration`
* `Discussion`
* `Conclusion`
* `Proofs`
* `Additional Results`
* `Experimental Details`

Avoid weak or internal titles:

* do not use `Setting` if `Preliminaries` or `Problem Setup` is clearer;
* do not use titles with `conjectural`, `obligation`, `governance`, `repair`, `Arbiter`, or `proof debt`;
* do not title an appendix `Deferred Proof Obligations`;
* do not expose internal status labels.

A reviewer must see a normal paper.

## Claim-to-section mapping

Every surviving committed statement must be mapped to a section.

Use:

* central theorem-ready results → `Main Results`;
* supporting propositions/lemmas → `Main Results`, `Main Analysis`, or appendix;
* framework definitions → `Problem Setup`, `Preliminaries`, or `Framework`;
* committed counterexamples or separations → `Negative Results` or `Counterexamples`;
* empirical/numerical checks → `Numerical Illustration`, `Empirical Illustration`, or appendix;
* conjecture-only material → `Discussion` or future work only;
* repair-requested and blocked material → exclude unless used as internal repair guidance.

Do not map blocked claims to manuscript sections.

## Empirical check selection rules

For each empirical check in `discovery.json` or `empirical_results.json`, decide whether it belongs in the paper world.

Include an empirical or numerical check only if:

* it directly illustrates a surviving committed statement;
* it measures the key theoretical quantity or a justified proxy;
* it clarifies the paper's main contribution;
* it is feasible under the available compute and data constraints;
* it can be reported honestly with uncertainty or repeated runs when needed.

Exclude an empirical or numerical check if:

* it relates only to a blocked or repair-requested statement;
* it requires unavailable data, models, network access, GPU resources, or excessive compute;
* it is only loosely connected to the theory;
* it is inconclusive and not useful for discussion;
* it would make the paper look weaker or unfocused.

### Venue-sensitive empirical guidance

* COLT/JMLR theory papers: empirical checks are optional and should be included only if they sharpen understanding.
* NeurIPS/ICML/ICLR: empirical or numerical illustration can help if it is directly connected to the theory.
* TMLR/workshops: empirical checks can help clarify a framework or diagnostic contribution.

Do not include experiments just because a venue often has experiments.

## Contribution paragraph

Write a short contribution paragraph of 2–3 sentences, approximately 60–100 words.

The paragraph should be in normal paper voice, not meta-commentary.

It should state:

* the central object or problem;
* the strongest committed result;
* the key conceptual insight;
* empirical/numerical support if included.

Forbidden phrasing:

* `This paper would honestly be framed as...`
* `what survives governance...`
* `a negative/conjectural study...`
* `the Arbiter decided...`
* `proof obligations...`
* `repair-requested...`
* `the system found...`

Good style:

```text
We study [object/problem] in [regime]. We show that [central committed result], revealing that [key insight]. Numerical experiments illustrate [phenomenon] and confirm the predicted dependence on [quantity].
```

Only mention numerical or empirical evidence if selected empirical checks support it.

## Step-by-step instructions

### Step 1 — Read inputs

Read:

* `theorem_state.json`;
* `discovery.json`;
* `empirical_results.json`, if available;
* user venue constraints, if available.

### Step 2 — Count and classify statements

Count theorem-ready, proposition-ready, conjecture-only, repair-requested, blocked, and negative/counterexample-style statements.

Classify each surviving statement by:

* result type;
* strength;
* proof readiness;
* centrality;
* manuscript role.

### Step 3 — Select paper world

Apply the world selection rules.

If uncertain, choose the more conservative world and explain why.

### Step 4 — Select venue strategy

If the user specified a venue, use it or explain mismatch.

If no venue is specified, select a suitable venue strategy from the venue guidance.

If current deadlines or requirements are needed, verify them before finalizing.

### Step 5 — Build section structure

Call `add_section` for each section in the selected manuscript structure.

Map each committed surviving statement to a section.

Do not add sections for blocked statements.

### Step 6 — Select empirical checks

Read empirical checks from `discovery.json` and/or `empirical_results.json`.

Select only checks tied to surviving committed statements.

Call `suggest_empirical` with selected check IDs.

### Step 7 — Write contribution paragraph

Write a short, normal-paper contribution paragraph.

Do not include internal process language.

### Step 8 — Commit world and template

Call:

* `select_world`;
* `select_template`;
* `add_section` for each selected section;
* `suggest_empirical` if empirical checks are selected.

### Step 9 — Complete

Call `task_complete`.

## Output expectations

The resulting `paperworld_output.json` should contain:

```json
{
  "world": "theory_theorem | framework_proposition | negative_impossibility | methodological_diagnostic | insufficient",
  "venue_strategy": {
    "selected_venue": "COLT | NeurIPS | ICML | ICLR | JMLR | TMLR | workshop | user_specified",
    "rationale": "Brief rationale",
    "deadline_checked": false
  },
  "section_structure": [
    {
      "section_title": "Main Results",
      "purpose": "State and explain the central committed results",
      "mapped_statements": ["statement-id-1", "statement-id-2"]
    }
  ],
  "empirical_plan": {
    "include_empirical": true,
    "selected_checks": ["check-id-1"],
    "rationale": "Why these checks are included"
  },
  "contribution_paragraph": "Normal paper-style contribution paragraph.",
  "excluded_material": {
    "blocked": ["statement-id"],
    "repair_requested": ["statement-id"],
    "conjecture_only": ["statement-id"]
  },
  "rationale": "One paragraph explaining why this paper world is the most supportable."
}
```

## Quality checklist

* The selected world matches actual committed surviving results.
* The decision is not based only on raw counts.
* Venue strategy matches paper world, strength, and user constraints.
* No blocked statement is included in the manuscript structure.
* No repair-requested statement is included as a result.
* Conjecture-only statements are not presented as established contributions.
* Every committed surviving statement is mapped to a section.
* Section titles are normal academic titles.
* Empirical checks are tied to surviving committed statements.
* The contribution paragraph is honest and paper-like.
* Internal status labels and process language are not exposed.

## What NOT to do

* Do not frame the paper as a theorem paper if no central theorem-level result survived.
* Do not frame conjecture-only material as a negative-result paper.
* Do not include repair-requested results as deferred proofs.
* Do not include blocked statements in the manuscript.
* Do not choose a venue using unprofessional language.
* Do not claim venue acceptance probability.
* Do not add empirical checks unrelated to surviving statements.
* Do not expose internal labels such as Arbiter, governance, proof obligation, proof debt, blocked, repair-requested, or theorem-state decisions in the manuscript.
* Do not write manuscript prose beyond the short contribution paragraph.




<!-- ---
name: paperworld
description: "Select the most supportable paper world from surviving theorem_state decisions. Determines paper type (theorem/framework/negative-result), venue, section structure, and which empirical checks to run. Called by PaperWorld Builder after Lab Lead Arbiter completes."
version: 1.0
used_by: paperworld_builder
domain: theoretical machine learning
inputs: theorem_state.json (decisions), discovery.json (empirical_checks)
outputs: paperworld_output.json (via select_world + add_section + select_template + suggest_empirical)
---

# PaperWorld Selection Skill

## Why this skill exists
After the Arbiter, the surviving statements determine what kind of paper is actually supportable. A system that generates a "theorem paper" when only propositions survived is dishonest. This skill forces an honest mapping from governed state to paper type before any writing begins.

## World Selection Rules

### World 1 — Theorem Paper
**Requires:** at least 2 `theorem_ready` statements
**Ideal:** 2-3 theorems + 2-4 propositions
**Venues:** COLT (best fit), NeurIPS, ICML, JMLR
**Empirical checks:** optional — include if they illustrate the bound

### World 2 — Framework / Focused Proposition Paper
**Requires:** at least 1 committed `proposition_ready` (or `theorem_ready`) result that forms a
coherent contribution.
- 3+ committed propositions + 2+ definitions → a full **framework paper**.
- 1–2 committed propositions (with setup + empirical illustration + honest discussion) → a
  **focused short paper** built around that single clean result. This is a legitimate
  contribution (TMLR in particular welcomes focused single-result papers) — it is NOT
  "insufficient". Do not discard a real committed proposition just because there is only one.
**Venues:** ICLR / TMLR (TMLR is ideal for a focused single-result note), NeurIPS
**Empirical checks:** recommended — illustrate the committed result

### World 3 — Negative Result Paper
**Requires:** at least 2 `conjecture_only` or impossibility statements
**OR:** 1 strong impossibility + concrete counterexample
**Venues:** COLT, ICLR, specialized workshops
**Empirical checks:** required — impossibility needs concrete demonstration

### Insufficient
**ONLY when ZERO statements committed** — no `theorem_ready` AND no `proposition_ready`
survived (only conjectures, blocked, or repair-requested). If even ONE proposition committed,
use World 2 (a focused paper), NOT insufficient.
When genuinely insufficient: call `select_world(world="insufficient", ...)` and STOP. Do NOT
`add_section` and do NOT fabricate a manuscript. NEVER create internal-inventory sections such
as "Missing Contribution Summary", "Blocked or Unusable Claims", or "Recommended Repair Path" —
those are pipeline status, not a paper. Return control to the Lab Lead.

## Venue Selection Rules

### If user specified venue → use it
### If not specified, select based on:

| World | Primary | Secondary | Avoid |
|---|---|---|---|
| Theorem Paper | COLT | NeurIPS, JMLR | TMLR (too easy) |
| Framework Paper | ICLR | TMLR, NeurIPS | COLT (theory only) |
| Negative Result | COLT | ICLR | ICML (empirical bias) |

### Venue modifiers:
- If empirical checks are strong → prefer NeurIPS/ICML over COLT
- If proofs are long and detailed → prefer JMLR/TMLR (no page limit)
- If novelty is borderline → prefer TMLR (rolling review, less competitive)
- If novelty is strong → target NeurIPS/ICLR

## Section Structure by World

### World 1 — Theorem Paper
```
1. Introduction
2. Related Work
3. Setting and Preliminaries
4. Main Results (theorems)
5. Proof Sketches
6. Discussion
7. Conclusion
Appendix A: Full Proofs
Appendix B: Additional Results
```

### World 2 — Framework Paper
```
1. Introduction
2. Related Work
3. Setting and Framework
4. Main Propositions
5. Analysis and Discussion
6. Empirical Illustration
7. Conclusion
Appendix A: Proofs
Appendix B: Experimental Details
```

### World 3 — Negative Result Paper
```
1. Introduction
2. Related Work
3. Setting
4. Impossibility Results
5. Constructive Examples
6. Implications
7. Conclusion
Appendix A: Proofs
```

## Empirical Check Selection Rules

For each empirical check in discovery.json:
- Is it relevant to a surviving statement?
- Does it illustrate the key quantity (effective dimension, alignment score)?
- Is it CPU-only and feasible?
- Does the selected venue expect/require empirical work?

### Include if:
- Check directly tests a surviving proposition's prediction
- Check illustrates the novel object (e.g. A_h(λ) behavior)
- Venue expects empirical work (NeurIPS, ICML)

### Exclude if:
- Check relates to a blocked statement
- Check requires GPU or large data
- Venue is pure theory (COLT) and check adds no value

## Step-by-step instructions

### Step 1 — Count surviving statements
Read theorem_state.json decisions and count:
- theorem_ready: N1
- proposition_ready: N2
- conjecture_only: N3
- blocked: N4
- repair_requested: N5

### Step 2 — Select world
Apply rules above. If borderline, prefer lower world (framework > theorem if uncertain).

### Step 3 — Select venue
Check if user specified venue in discovery.json metadata.
If not, apply venue selection rules above.
Use web_search to verify current venue deadlines and requirements if needed.

### Step 4 — Build section structure
Call add_section for each section in the selected world template.
Map surviving statements to sections explicitly.

### Step 5 — Select empirical checks
Read discovery.json empirical_checks.
Apply inclusion rules above.
Call suggest_empirical with selected check IDs.

### Step 6 — Write contribution paragraph
One paragraph stating what the paper contributes based on surviving statements and repositioned novelty hypothesis.

### Step 7 — Call select_world to commit the decision
### Step 8 — Call select_template to commit venue
### Step 9 — Call task_complete

## Quality checklist
- [ ] World matches actual surviving statement counts
- [ ] Venue matches world type and statement strength
- [ ] Every surviving statement is mapped to a section
- [ ] Blocked statements are NOT included
- [ ] Repair-requested statements go to appendix as "proof deferred"
- [ ] Empirical checks are relevant to surviving statements
- [ ] Contribution paragraph is honest about what is proposition vs theorem -->
