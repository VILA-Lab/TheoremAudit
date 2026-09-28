---
name: assumption-attack
description: "Systematically evaluates every assumption used by the proposed theoretical results. Identifies assumptions that are too strong, circular, unverifiable, redundant, non-standard, inconsistent, or insufficient for the proof strategy. Produces flag_assumption calls with calibrated severity and concrete fixes."
version: 1.1
used_by: senior_skeptic
domain: theoretical machine learning
inputs: discovery.json, theorem_state.json
outputs: skeptic_flags.assumption_flags via flag_assumption
---

# Assumption Attack Skill

## Purpose

Evaluate whether the assumptions supporting the proposed theoretical results are mathematically appropriate, scientifically defensible, and aligned with the proof strategy.

Assumptions are not automatically bad because they are restrictive. In theoretical ML, restricted regimes are often legitimate. The goal is to distinguish useful scope conditions from assumptions that make the result trivial, circular, unverifiable, contradictory, unnecessarily strong, or disconnected from the proof.

This skill should be adversarial but calibrated. It should improve the paper, not reject every assumption by default.

## When to use this skill

Run this skill as the first step of the Senior Skeptic pass, before attacking theorem statements or proofs.

A theorem can be formally correct but scientifically weak if its assumptions do too much of the work, exclude the intended regime, or cannot be justified to readers.

## Inputs to inspect

Use:

* assumptions from `discovery.json`;
* assumptions, decisions, statuses, and committed statements from `theorem_state.json`;
* theorem conclusions that depend on each assumption;
* proof sketches or proof dependencies, if available;
* literature evidence only if it is explicitly available from the pipeline.

Do not rely on memory to decide whether an assumption is standard in a subfield.

## Attack taxonomy

Use `circular` when the assumption directly assumes the conclusion or an equivalent statement.

Use `theorem-shaped` when the assumption is not literally circular but encodes the hard part of the theorem, making the result scientifically weak or nearly immediate.

### 1. Circular or theorem-shaped

The assumption essentially states the desired conclusion or makes the theorem immediate.

Flag when:

* the assumption uses the same target quantity as the theorem conclusion in a way that already implies the conclusion;
* the theorem becomes trivial once the assumption is accepted;
* the assumption hides the main quantity that the theorem claims to control.

Do not flag as circular merely because the same object appears in both the assumption and conclusion. Check whether the assumption actually does the theorem's work.

### 2. Too strong

The assumption is stronger than needed, excludes the intended setting, or weakens the scientific value of the result.

Flag when:

* a weaker common condition would plausibly support the proof;
* the assumption rules out the main motivating examples;
* the assumption imposes exact realizability, exact alignment, boundedness, finite rank, or independence where the paper motivates a broader regime;
* the assumption makes the result true for an overly narrow or artificial class.

Do not flag merely because the assumption is restrictive. Restricted regimes can be valid if they are clearly framed and technically meaningful.

### 3. Too weak or insufficient

The assumption does not support the stated theorem or proof strategy.

Flag when:

* the proof requires stronger concentration, moment, smoothness, spectral, stability, or identifiability conditions than the assumption provides;
* the theorem claims high-probability or uniform control but the assumptions support only expectation-level or pointwise control;
* a conclusion requires independence, boundedness, compactness, or regularity that is not assumed.

### 4. Unverifiable or opaque

The assumption cannot be checked, motivated, or interpreted in the intended setting.

Flag when:

* it depends on unknown population quantities without giving a way to interpret or estimate them;
* it uses hidden constants, asymptotic regimes, or spectral quantities without explanation;
* it is stated in a way that makes the regime hard to recognize.

Do not automatically reject population-level assumptions in theory papers. Many are acceptable if they are standard, interpretable, or clearly tied to the mathematical setting.

### 5. Non-standard or poorly motivated

The assumption is unusual for the subfield or differs from common formulations.

Flag when:

* the assumption is marked non-standard in the plan;
* available literature records suggest closely related work uses a different or weaker condition;
* the assumption is new but the paper does not justify why it is natural.

If no literature evidence is available, do not invent claims about standardness. Instead, flag the assumption as needing justification if it appears unusual from the mathematical context.

### 6. Redundant

The assumption is implied by other assumptions or by definitions already stated.

Flag when:

* it follows directly from another assumption;
* it is a special case of a stronger assumption already imposed;
* it repeats a condition already embedded in the setup.

Severity is usually low unless redundancy causes confusion or hides a stronger condition.

### 7. Inconsistent or jointly empty

Assumptions may be individually plausible but jointly impossible, contradictory, or so restrictive that no interesting examples remain.

Flag when:

* two assumptions contradict in an edge case;
* the assumption set implies a degenerate model;
* the assumptions together imply the theorem conclusion directly;
* the assumptions exclude the motivating examples.

## Step-by-step procedure

### Step 1 — Build the assumption dependency map

For each assumption, identify:

* its ID or name;
* its formal content;
* whether it is marked standard or non-standard;
* which theorem/proposition/result depends on it;
* which proof step appears to use it, if available;
* whether it is used only by blocked, conjectural, or abandoned claims.

Do not surface internal IDs in the final paper, but use them internally for flagging.

### Step 2 — Attack each assumption individually

For each assumption, check:

* Does it make the target theorem trivial?
* Is it stronger than needed for the proof strategy?
* Is it too weak for the theorem or proof?
* Is it interpretable and mathematically meaningful?
* Is it standard or justified by available literature evidence?
* Is it redundant with another assumption?

### Step 3 — Attack assumption interactions

Check the assumption set jointly:

* Do multiple assumptions together imply the conclusion?
* Are any assumptions mutually inconsistent?
* Do they define an empty or degenerate regime?
* Do they exclude the examples used to motivate the theorem?
* Does the combined assumption set make the paper's claimed scope misleading?

### Step 4 — Calibrate severity

Use:

* `high` — likely to make the theorem trivial, invalid, misleading, or scientifically unacceptable.
* `medium` — likely to draw reviewer scrutiny and requires justification, weakening, or reframing.
* `low` — minor redundancy, naming issue, clarity issue, or fixable presentation problem.

Do not rate everything high. Severity should reflect impact on the final claim.

### Step 5 — Produce flags

For every genuine issue, call `flag_assumption` with:

* assumption ID or name;
* attack type;
* precise mathematical description of the issue;
* severity;
* concrete suggested fix.

Suggested fixes should be actionable, such as:

* weaken the assumption;
* justify it with related work;
* rename it as a specific regime;
* move it from an implicit condition to a formal assumption;
* add an example showing the assumption is non-empty;
* add a counterexample showing why the assumption is needed;
* reduce the theorem's scope;
* strengthen the assumption if the proof requires more.

### Step 6 — Summary

After flagging, write a short summary:

* number of assumptions inspected;
* number and severity of flags;
* the highest-risk assumptions;
* whether the assumption set is defensible after fixes;
* whether the theorem should proceed to proof attack or be reframed first.

## Quality checklist

* Every assumption was inspected.
* Non-standard assumptions were checked for circularity and motivation.
* Assumption interactions were checked, not just individual assumptions.
* Flags distinguish circular, too-strong, too-weak, unverifiable, non-standard, redundant, and inconsistent issues.
* Every flag has a concrete suggested fix.
* Severity is calibrated to impact on the final theorem.
* The skill does not force flags where assumptions are actually defensible.
* The skill does not accept assumptions merely because they are convenient for the proof.

## What NOT to do

* Do not flag standard assumptions as problematic without a specific mathematical reason.
* Do not flag an assumption as circular merely because it mentions an object from the theorem.
* Do not claim an assumption is standard or non-standard based on memory alone.
* Do not suggest removing an assumption without considering whether the proof still needs it.
* Do not rate every issue as high severity.
* Do not skip interaction checks.
* Do not treat restrictive assumptions as automatically invalid.
* Do not ignore assumptions used only indirectly through proof steps.
