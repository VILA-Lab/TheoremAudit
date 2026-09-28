---
name: setting
description: "Write sections related to  setting/preliminaries. Covers notation, problem setup, and assumptions. Only include definitions and assumptions that appear in committed statements."
version: 1.1
used_by: manuscript_compiler
---

# Setting and Preliminaries Writing Skill

## Purpose
Establish the mathematical framework precisely so all subsequent results are well-defined.
Every symbol used in the main results must be defined here.
Cross-check `main_text_math_plan.setup_objects` before finishing the section. Every probability
space, sample split, estimator, loss, candidate class, stopping rule, radius, event, operator, and
parameter used by a planned main-text derivation must be introduced with its domain and dependence.
Do not postpone essential setup to the proof appendix.

## Structure
1. Notation — define all symbols used in committed statements
2. Problem setup — the statistical learning problem
3. Assumptions — formal statement of each assumption
4. Key definitions — only definitions referenced in committed statements

## Preamble requirement
`\begin{assumption}` and `\begin{remark}` are NOT standard LaTeX and are not declared by
`amsthm` or by the venue template. The preamble skill / venue template must declare them
via `\newtheorem{assumption}{Assumption}` and `\newtheorem{remark}{Remark}`. If they are
missing the LaTeX will not build.

## Which assumptions/definitions to include (exclusion is authoritative)
Include an assumption or definition ONLY if it is referenced by at least one committed
statement AND it is not blocked. Treat a statement as blocked if ANY of these hold — there
are two block paths in the pipeline:
- `action == "block"` (via make_decision), or
- `new_status == "blocked"`, or
- `status == "blocked"` (via the standalone block tool, which sets no `action` field)

A result being `repair_requested` does NOT remove its premises: an assumption or definition
that a committed result depends on is still stated here, since it is a premise, not a result.
Do not, however, import definitions that exist ONLY to support a blocked statement.

## Which form to use
For each assumption/definition, pick the controlling content in this priority order and use
the first non-empty field:
- if the assumption was **weakened** (`action == "weaken"`): `new_form`
- else: `governed_form` → `form`

`new_form` is populated only for weaken actions, so for un-weakened assumptions it is empty
and the real content lives in `governed_form`/`form` (often as rough prose). Do NOT copy
rough text verbatim if it is not valid LaTeX — rewrite it formally, preserving meaning
exactly. Never present the ORIGINAL form of an assumption the Arbiter weakened.

## Assumption presentation rules
- State each assumption in a formal \begin{assumption} environment
- Give a brief justification (1 sentence) after each
- Add a \begin{remark} when an assumption differs from standard formulations

## Notation — introduce it in prose, NOT a table (default)
Experienced authors introduce notation inline, as part of describing the setup: "We observe
$n$ i.i.d. samples $(x_i, y_i)$ with $x_i \in \mathbb{R}^d$ drawn from ...". Define each symbol
at the moment it is first needed, in a sentence, so the reader learns the objects and their
roles together. This is how theory papers at ICLR/TMLR/COLT actually read.

Do NOT dump every symbol into a notation table by default — a wall of "symbol | meaning" rows
reads like an auto-generated glossary, not a paper. Only use a compact notation table when the
notation is genuinely heavy (many non-obvious symbols reused across several results) AND a
table measurably helps the reader; even then, still introduce the key objects in prose first
and place the table as a reference, not as the main exposition. When in doubt, prose.
Define only symbols that appear in committed statements; never introduce unused notation.

## Definitions
Only include definitions that:
- Are referenced in at least one committed statement, AND
- Appear in the paperworld sections list

## What to draw from theorem_state
- Assumptions/definitions referenced by committed statements and not blocked (see exclusion
  rule above) — in the current state these are the A-entries (e.g. A1-A4, A7)
- The weakened `new_form` for any assumption with `action == "weaken"`; otherwise
  `governed_form`/`form`
- Definitions from discovery.json that appear in committed statements

## What NOT to do
- Do not include anything blocked by any of the three block signals above
- Do not use the original form of a weakened assumption
- Do not introduce notation not used in the paper
- Do not state results here — only definitions and setup


