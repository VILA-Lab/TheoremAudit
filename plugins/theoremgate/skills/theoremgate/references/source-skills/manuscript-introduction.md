---
name: manuscript-compiler/sections/introduction
description: "Write a polished introduction for a theoretical ML paper at the standard expected by strong ML/NLP venues. Build a coherent scientific narrative around the problem, technical tension, closest literature, precise gap, central insight, audited contributions, and scientific consequence while preserving claim strength, novelty, significance, scope, and citation constraints."
version: 2.1
used_by: manuscript_compiler
---

# Introduction Writing Skill

## Purpose

Write the introduction of a theoretical machine learning paper at the standard expected by strong ML/NLP research venues.

The introduction should make an expert reader understand:

1. what scientific problem the paper studies;
2. why the problem is technically or practically meaningful;
3. what the closest relevant work already establishes;
4. what precise question or gap remains;
5. what setting or information regime the paper studies;
6. what conceptual insight, reduction, construction, or mechanism enables progress;
7. what the paper establishes;
8. how the main and supporting results fit together;
9. what those results change about our understanding of the problem.

The introduction is not a theorem inventory, proof-status report, literature dump, limitations section, or expanded abstract.

It should present one coherent scientific argument while remaining exactly faithful to the audited manuscript state.

Return only manuscript-ready introduction text. Perform all planning and internal reasoning silently.
Do not copy or lightly paraphrase wording from this guidance. Draft every sentence from the
paper-specific definitions, results, literature comparisons, and verified evidence.

Note: The introduction must contain an explicit contribution summary after the central insight. Use concise prose or bullets, whichever makes the paper-level contributions easiest for a reviewer to identify. Do not rely on the reader to infer the contributions from theorem discussion alone.
---

# Pre-writing reasoning

Before drafting, silently determine the following.

## Central scientific question

Identify the question that best unifies the paper.

Organize the introduction around the scientific question rather than the order in which results were proved or numbered.

A paper may contain several formal results while answering one central question.

---

## Scientific tension

Identify the tension that motivates the paper.

Examples include:

- a guarantee holds under one regime but breaks under distribution shift;
- asymptotic behavior is known but finite-sample behavior remains unclear;
- a result depends on an assumption whose necessity is unresolved;
- an upper bound is known but sharpness or a matching lower bound is missing;
- a guarantee depends on a theoretical quantity that is not observable;
- existing methods require information unavailable in the setting studied here;
- a phenomenon is empirically visible but its governing mechanism is unknown;
- positive and negative results leave the true boundary unclear.

Prefer a concrete technical tension over generic statements of importance.

---

## Closest known approaches

From admissible literature records, determine:

- which papers or lines of work are genuinely closest;
- what assumptions, information, regime, or guarantee they use;
- which distinctions are needed to explain the present paper's question;
- whether any overlap constrains novelty wording.

Do not turn the introduction into a broad literature review.

---

## Precise gap

Identify the exact missing guarantee, characterization, certificate, bound, construction, explanation, or boundary.

State the gap along a meaningful technical axis whenever possible:

- source vs. target distribution;
- marginal vs. conditional;
- finite-sample vs. asymptotic;
- population vs. observable quantity;
- known shift radius vs. data-dependent certificate;
- sufficient condition vs. necessity;
- upper bound vs. matching lower bound;
- well-specified vs. misspecified;
- fixed vs. adaptive environment;
- existence vs. computable or certifiable guarantee;
- qualitative phenomenon vs. quantitative dependence.

Avoid vague claims that prior work is merely "limited," "underexplored," or "incomplete."

State only distinctions supported by the literature evidence.

---

## Paper setting

Identify the information pattern, estimator class, distributional regime, structural assumptions, or observational access that defines the scientific problem.

Distinguish between:

- assumptions that define the setting;
- assumptions that are merely technical;
- restrictions that materially affect interpretation.

Foreground the defining setting. Mention technical assumptions only when they are necessary to understand the contribution.

---

## Central insight

Identify the conceptual mechanism that makes the results form a coherent paper rather than a collection of statements.

Examples include:

- reducing a high-dimensional problem to a scalar discrepancy;
- decomposing an error into interpretable sources;
- isolating the quantity through which distribution shift changes a guarantee;
- identifying a geometric or spectral mechanism controlling an estimator;
- converting an inaccessible theoretical quantity into an observable certificate;
- constructing a matching example that reveals the correct boundary;
- separating calibration from transfer, approximation from estimation, or positive from negative regimes.

Communicate this insight explicitly when one is genuinely supported by the results.

Do not invent a "central insight" when the paper's contribution is instead primarily a sharp theorem, construction, or impossibility result.

---

## Contribution hierarchy

Determine the paper-level role of each accepted result.

Possible roles include:

- primary result;
- co-primary result;
- supporting result;
- sharpness result;
- lower bound;
- impossibility result;
- counterexample;
- construction;
- certificate;
- reduction;
- corollary;
- operational consequence;
- empirical validation;
- technical support.

Do not give all accepted results equal rhetorical weight.

Do not force exactly one primary result when the paper naturally has a co-primary pair, such as:

- upper and lower bounds;
- theorem and matching counterexample;
- guarantee and impossibility boundary.

Group formal statements that constitute one intellectual contribution.

---

## Scientific consequence

Determine what the results teach us.

Examples:

- which quantity is fundamental;
- which assumption is necessary;
- which failure mechanism is isolated;
- which unknown quantity becomes certifiable;
- where a guarantee is possible or impossible;
- how two previously conflated regimes differ;
- what finite-sample behavior replaces an asymptotic understanding.

This interpretation should guide how the introduction ends its substantive argument.

---

## Empirical support

If `empirical_results` exists, determine whether any completed result materially helps interpret, validate, or illustrate the theory.

Do not include experiments merely because they exist.

---

## Excluded statements

Identify conjecture-only, blocked, repair-requested, superseded, dropped, or prior-work-attributed statements that must not be presented as original established contributions.

Perform all of these decisions silently.

---

# Authoritative sources and precedence

Use only claims supported by the current manuscript state.

When sources conflict, use the following precedence:

1. current accepted / proved statements in `theorem_state`;
2. final theorem-governance decisions;
3. novelty audit;
4. significance audit;
5. contribution-development output;
6. supporting proof records;
7. verified empirical results;
8. verified literature-search records;
9. `contribution_paragraph` from `paperworld_output.json` as non-authoritative framing guidance.

`contribution_paragraph` may predate later theorem weakening, novelty resolution, scope changes, or prior-work attribution.

Never restore:

- a dropped result;
- an earlier stronger theorem statement;
- a conjecture as an established contribution;
- a novelty claim rejected or left unresolved by the novelty audit;
- significance language unsupported by the significance audit;
- an attributed existing result as an original theorem.

---

# Core narrative principle

The introduction must present one coherent scientific argument.

Make clear both:

- **what was established**, and
- **why the results belong together**.

A useful research narrative often contains:

**problem → scientific tension → closest approaches → precise gap → paper setting → central insight → main results → scientific interpretation**

This is a reasoning scaffold, not a required paragraph structure.

Do not precommit to a fixed number of paragraphs, contribution bullets, displayed equations, or roadmap sentences.

Choose the structure that best communicates the paper.

---

# Opening: problem and tension

Open with the scientific problem itself.

The opening should quickly establish:

- the object being studied;
- the important guarantee, phenomenon, or difficulty;
- the tension or unresolved question motivating the paper.

Good openings state something technically substantive.

Prefer:

> Split conformal prediction gives finite-sample marginal coverage under exchangeability, but the rank symmetry underlying this guarantee disappears when calibration and deployment distributions differ.

over:

> Conformal prediction has recently received substantial attention because uncertainty quantification is important.

Avoid generic openings such as:

- "Machine learning has achieved remarkable success..."
- "There has been growing interest in..."
- "X is an important problem..."
- "In recent years..."

unless the sentence immediately reaches the paper's technical question.

---

# Relevant prior approaches

Use the introduction to establish the literature context necessary for understanding the gap.

Organize prior work by the distinction that matters scientifically, such as:

- assumptions;
- information available;
- distributional regime;
- guarantee type;
- robustness model;
- finite-sample vs. asymptotic analysis;
- static vs. adaptive setting;
- positive vs. negative result.

Prefer conceptual grouping over paper-by-paper chronology.

For example:

> Existing approaches handle distribution shift through density-ratio information, ambiguity sets, or sequential feedback.

Then explain how the present setting differs.

Do not duplicate the Related Work section.

Do not misrepresent prior work merely to sharpen the paper's contrast.

---

# Precise research gap

State what remains unresolved in the setting studied by the paper.

A strong gap statement should make the main result feel like a natural response to a concrete theoretical need.

Prefer:

> What remains missing is a finite-sample target-coverage guarantee depending only on observable source and target score distributions.

over:

> Existing approaches do not fully address the problem.

Prefer:

> Existing bounds depend on a known shift radius, leaving open how to certify the required quantity from finite audit data.

over:

> Previous work has several limitations.

Do not use priority language unless novelty has been verified.

---

# Paper setting and information regime

Describe the paper's setting as part of the scientific question.

When useful, explain both:

- what information is available;
- which stronger information is not assumed.

For example:

> We study a fixed target distribution with independent source and target conformity-score audits, without assuming access to density ratios or sequential target feedback.

This is often more informative than listing assumptions separately.

Do not make the setting sound apologetic.

---

# Central conceptual insight

When the paper has a genuine reduction, decomposition, representation, or mechanism, explain it before presenting the detailed results.

Useful forms include:

- "The key observation is..."
- "The analysis reduces the problem to..."
- "The governing quantity is..."
- "The main decomposition separates..."
- "The construction reveals..."
- "The distinction becomes transparent after..."

State the mathematical content of the insight.

Avoid vague phrases such as:

> Our key insight is a novel framework.

Do not hide the main conceptual idea inside a contribution bullet.

---

# Presenting the main results

Present accepted results according to their scientific role, not their internal order.

Lead with the result or result pair that best answers the motivating question.

Then explain supporting results according to what they add.

Common structures include:

**primary guarantee → sharpness → observable certificate → operational consequence**

**upper bound → lower bound → sharp boundary**

**decomposition → rate → interpretation**

**construction → impossibility result → necessary condition**

**positive theorem → counterexample outside the regime → boundary**

These are examples, not fixed templates.

Do not mechanically write:

> First...
> Second...
> Third...
> Fourth...

unless the contributions are genuinely distinct and that presentation improves clarity.

Connected prose is often effective when later results sharpen or operationalize the main one.

For example:

> We show that target coverage deteriorates by at most the discrepancy between source and target score distributions. A matching construction establishes that the source-rank dependence is sharp. We then make the transfer guarantee observable by estimating this discrepancy from independent audits, yielding an adjusted calibration rule with finite-sample target coverage.

---

# Contributions presentation

Use the contribution format that best serves the paper.

A dedicated contribution list is optional.

## Prose

Use prose when the results form a tightly connected mathematical argument and separating them into bullets would obscure their relationship.

## Bullets

Use bullets when:

- the paper has several genuinely distinct major contributions;
- explicit separation improves reviewer scanability;
- the venue style favors a contribution list;
- theory, methodology, and empirical evidence form distinct contribution axes.

If bullets are used:

- list paper-level contributions rather than theorem environments;
- order them by scientific importance;
- combine tightly connected results;
- state what is established and why it matters;
- avoid bullets for assumptions, definitions, notation, or routine lemmas.

## Hybrid

A hybrid form is allowed and often effective:

- explain the central idea and main result in prose;
- summarize major distinct contributions in a concise list.

Do not force prose.

Do not force bullets.

## Reader-facing contribution language

Novelty, attribution, proof status, and routing classifications are editorial controls, not
reader-facing descriptions of a contribution. Never introduce a contribution list with phrases such
as "attributed contribution," "proof-complete synthesis," "audit-supported result," or equivalent
workflow language. When prior work constrains originality, cite that work and state the concrete
scholarly value directly—for example, a unified derivation, a clarified boundary, an exact
specialization, or a reproducible comparison—without naming the internal classification.

Use `synthesis` in the manuscript only when synthesis is itself the scholarly contribution and the
sentence identifies what mathematical ideas, regimes, or results are unified. Do not use the word as
a generic substitute for a result or as a signal that novelty was downgraded.

## Editing after the contribution summary

Treat the contribution summary as the end of contribution enumeration. Do not follow bullets with
paragraphs that paraphrase the same bullets, recount which bullets are primary, or repeat their
scope in slightly different language. Retain a following paragraph only when it contributes a
distinct scientific interpretation needed to understand what the results establish together.

Keep detailed literature comparisons in Related Work unless a concise comparison is necessary to
state the introductory gap. A scope condition may remain in the introduction when it is necessary
to interpret the result correctly, but state it once and do not repeat it merely to lengthen the
section. Include a roadmap only when it materially improves navigation through a genuinely complex
manuscript; never use a roadmap as filler after an already complete introduction.

Before finalizing the introduction, compare every paragraph after the contribution summary with the
summary itself. Remove or consolidate any paragraph whose substantive content is already present.
An introduction that fully establishes the problem, gap, mechanism, results, and interpretation is
complete; do not add another rhetorical component solely to increase its length.

---

# Contribution hierarchy

Treat contributions as intellectual units, not theorem counts.

A single paper-level contribution may include several accepted statements.

For example:

**finite-sample transfer under score shift**

may include:

- a transfer inequality;
- a total-variation specialization;
- a sharpness construction.

These need not be advertised as three unrelated contributions.

Conversely, genuinely independent results should not be artificially merged.

Paper coherence should determine grouping.

---

# Scientific interpretation

After stating the main results, explain what they reveal.

The introduction should answer one or more of:

- What quantity is fundamental?
- What source of failure is isolated?
- What previously theoretical quantity becomes observable?
- What assumption is shown to matter?
- What distinction between regimes becomes clear?
- What boundary between possible and impossible behavior is established?
- What guarantee becomes available from the stated information?

Prefer explicit interpretation.

For example:

> Together, the results separate the exchangeability argument used for source calibration from the distributional transfer required at deployment.

is stronger than:

> These results demonstrate the effectiveness of our approach.

---

# Scope and restrictions

Present the technical regime as the problem being studied, not as an apology.

Prefer:

- "We study the fixed-target setting with independent source and target audits."
- "Our analysis concerns marginal coverage under a fixed deployment distribution."
- "The result applies to the minimum-norm interpolant under the specified spectral construction."
- "The guarantee uses only scalar score-distribution information."

Avoid:

- "The contribution is narrowly mathematical."
- "We only consider..."
- "Our result is limited to..."
- "We fail to..."
- "Our method cannot..."
- "It neither handles X nor Y nor Z."

Mention an excluded regime when it:

1. is necessary to interpret the theorem correctly;
2. distinguishes the paper from the closest literature;
3. is itself part of the scientific boundary.

Do not create a standalone limitations paragraph unless the boundary is scientifically central.

Detailed limitations belong elsewhere.

---

# Scope versus limitation

A scope statement says what problem is being solved.

A limitation statement emphasizes what is not solved.

Prefer the former when both communicate the same fact.

Prefer:

> We focus on a fixed target distribution observed through independent score audits, separating this setting from sequential methods that update calibration online.

over:

> We do not handle adaptive target distributions or sequential feedback.

---

# Citation policy

Use only citations provided by verified literature-search outputs.

Preferred sources, in order:

1. `related_work`, when present with valid citation keys;
2. `background_papers`, when present with valid citation keys;
3. `novelty_conflicts`, only for papers returned by the Literature Lead and relevant to the claim.

Use exactly the citation key stored in the record.

Never:

- fabricate citations;
- reconstruct citations from memory;
- invent BibTeX keys;
- use placeholder citations;
- cite from fields that do not exist.

If no admissible citations exist, write the relevant background without citation commands.

Treat `novelty_conflicts` as overlap evidence, not automatically as a complete bibliography.

Do not claim that prior work lacks a result unless the available literature evidence supports that distinction.

---

# Novelty calibration

Follow the novelty audit.

## `verified_novelty`

State the supported technical distinction confidently within the verified comparison scope.

Prefer describing what is different rather than using generic labels such as "novel."

Use "first" or equivalent priority language only when specifically supported.

## `plausible_incremental_novelty`

State the concrete increment, such as:

- weaker assumptions;
- sharper bound;
- finite-sample version;
- new information regime;
- observable certificate;
- broader regime;
- complementary lower bound;
- simpler derivation.

Do not inflate the contribution.

## `uncertain_overlap`

Present the proved mathematics clearly and confidently.

Avoid unsupported priority language such as:

- "first";
- "novel";
- "new";
- "previously unknown";
- "unprecedented";
- "for the first time".

Do not turn unresolved overlap into defensive prose.

## `attributed_existing_result`

Attribute the existing result correctly.

Present only the supported value, such as:

- synthesis;
- clarification;
- derivation;
- reproducibility;
- simplification;
- unification;
- exposition.

Never transform an attributed specialization into an original theorem through framing.

---

# Significance calibration

Use the significance audit to calibrate the breadth and emphasis of the introduction.

Do not claim broad importance for a narrow result without supporting evidence.

Do not undersell a result whose significance is well supported.

Significance affects framing, not mathematical truth.

---

# Claim-strength calibration

Use `paper_label` to calibrate language, not to mechanically insert theorem nouns.

## `paper_label="theorem"`

When accurate, stronger verbs are permitted:

- "we prove";
- "we establish";
- "we show";
- "we derive".

## `paper_label="proposition"` or restricted result

Prefer measured formulations:

- "we show";
- "we establish under...";
- "we derive in the setting of...";
- "we give a construction showing...";
- "we identify...".

## Missing `paper_label`

Use neutral scientific language:

- "we show";
- "we study";
- "we derive";
- "we construct";
- "we identify".

Calibrate each result independently.

Do not weaken a strong primary result because supporting results are weaker.

Do not strengthen a restricted result because another theorem is strong.

---

# Technical language

Use strong mathematical terms when justified.

## Characterize

Use "characterize" when the accepted results genuinely identify the governing dependence, behavior, or boundary with sufficient completeness.

Do not use it for a loose one-sided bound.

## Sharp

Use "sharp" only when supported by:

- an attaining example;
- a matching lower bound;
- a matching construction;
- an equality case;
- another accepted sharpness argument.

## Exact

Use "exact" only for a formally exact identity, expression, probability, threshold, decomposition, or equivalent statement.

## Optimal

Use "optimal" only when an accepted result establishes optimality in the stated sense.

## Resolve

Use "resolve" or "fully characterize" only when the accepted results genuinely close the stated question within the declared regime.

---

# Mathematical detail

Include enough mathematical detail to make the contribution concrete and distinguish it from nearby work.

Useful details may include:

- the governing discrepancy or complexity measure;
- the main finite-sample guarantee;
- important dependence on a parameter;
- the sharpness or lower-bound statement;
- the observable certificate;
- the operational calibration or decision rule.

Avoid reproducing technical sections or full theorem statements unnecessarily.

## Equations

Use displayed equations when they materially improve understanding.

An equation may be useful when it:

- identifies the central quantity;
- states the main bound clearly;
- exposes the key reduction;
- communicates a memorable finite-sample guarantee.

Avoid equations that primarily:

- enumerate constants;
- reproduce secondary theorem details;
- introduce notation used only later;
- interrupt the narrative without clarifying the contribution.

There is no required number of equations.

---

# Empirical or numerical evidence

Include empirical evidence only when:

1. the run is completed;
2. the verdict supports inclusion;
3. the result is concrete and nontrivial;
4. it materially strengthens or illustrates the theoretical conclusions.

Useful roles include:

- demonstrating tightness;
- illustrating a phase transition;
- showing which theoretical term dominates;
- verifying predicted parameter dependence;
- demonstrating the practical magnitude of a theoretically identified effect.

Avoid generic claims such as:

> Experiments validate our theory.

State the actual observed phenomenon.

Do not advertise failed, inconclusive, contradictory, planned, or `bug_in_code` runs as positive contributions.

---

# Avoid theorem bookkeeping

The introduction should not mirror the theorem-state file.

Do not mention:

- theorem or statement IDs;
- number of accepted statements;
- proof status;
- repair history;
- audit status;
- internal result roles;
- governance decisions.

The reader needs the scientific hierarchy, not the internal inventory.

Do not expose planning statements such as:

> TH-5 will be primary while TH-2 provides sharpness.

Translate internal result roles into natural manuscript prose.

---

# Avoid defensive writing

Do not pre-answer hypothetical reviewer objections unless necessary to define the scientific problem or boundary.

Avoid phrases such as:

- "The contribution is narrowly mathematical."
- "We emphasize that..."
- "We stress that our result does not..."
- "We make no claim that..."
- "This should not be interpreted as..."
- "Our result is only..."
- "The rule is deliberately non-informative..."

Prefer direct scientific statements.

Instead of:

> The rule is deliberately non-informative when the radius exceeds the miscoverage budget.

prefer:

> Certification is available whenever the estimated shift radius fits within the target miscoverage budget.

If the failure regime is itself a theoretical contribution, state it directly.

---

# Avoid duplicating the abstract

The introduction should expand the scientific reasoning behind the paper rather than repeat the abstract sentence by sentence.

The abstract typically communicates:

**problem → main result → consequence**

The introduction should additionally explain:

- why the problem arises;
- what the closest approaches assume;
- what exact gap remains;
- what setting the paper isolates;
- what conceptual idea drives the analysis;
- how the results fit together;
- what the results teach us.

Do not copy abstract phrasing mechanically.

---

# Paper outline

A roadmap is optional.

Include one when:

- the venue or template expects it;
- the manuscript is long or structurally complex enough that navigation helps;
- the actual section structure is available.

Keep it short.

Mention only sections that actually exist.

Avoid repeating the contribution summary.

Omit the roadmap when it adds only boilerplate.

---

# Alternative narrative patterns

Choose the pattern that best matches the mathematics.

These patterns guide reasoning; they do not prescribe paragraph counts.

## Guarantee under broken assumptions

**known guarantee → assumption failure → available information → central reduction → transferred guarantee → certificate**

Useful for robustness, distribution shift, and conformal prediction.

## Unexplained estimator behavior

**known or observed phenomenon → gap in existing analysis → decomposition or mechanism → main rate/characterization → interpretation**

Useful for statistical learning theory and optimization.

## Upper/lower boundary

**desired guarantee → positive theorem → lower bound or counterexample → sharp boundary → implication**

Useful for minimax and impossibility papers.

## Assumption relaxation

**known result under strong assumption → role of the assumption → new mechanism → relaxed result → remaining boundary**

Useful for generalization and theory-extension papers.

## Observable certification

**guarantee depends on unknown quantity → observable evidence → finite-sample certificate → resulting decision/calibration rule**

Useful for uncertainty quantification and robust statistics.

## Positive/negative pair

**candidate principle → positive regime → failure outside the regime → boundary or necessity result**

Useful when the paper combines constructive and impossibility results.

Do not force a paper into a pattern that does not match its contribution.

---

# Length and pacing

Do not over-expand the introduction merely because more material is available.

The introduction should be long enough to establish:

- motivation;
- literature position;
- precise gap;
- setting;
- central insight when present;
- main results;
- scientific interpretation.

It should not absorb the full roles of:

- Related Work;
- Background;
- Formal Setup;
- Discussion;
- Limitations;
- Appendix.

If two paragraphs perform the same rhetorical function, compress them.

Once these functions are complete, do not add repeated motivation, restated contributions, filler
transitions, unnecessary scope recitations, or a boilerplate outline to increase the introduction's
page count. A page target is not evidence that another paragraph is needed.

---

# What to draw from inputs

Use:

- accepted / committed statements from `theorem_state`;
- current `new_form` statements;
- `paper_label` from final decisions;
- contribution-development output for:
  - coherent scientific argument;
  - primary or co-primary statement IDs;
  - result roles;
  - placements;
  - contribution type;
  - claim policy;
- novelty audit for originality calibration;
- significance audit for scientific emphasis;
- supporting proof records when needed to determine exact scope, sharpness, or dependence;
- `contribution_paragraph` only as a non-authoritative framing seed;
- verified literature-search records for citations;
- verified `empirical_results`;
- venue/template metadata for formatting conventions and roadmap expectations.

---

# What NOT to do

Do not:

- overclaim beyond accepted results;
- introduce unsupported assumptions, rates, datasets, experiments, applications, or mathematical claims;
- fabricate or guess citations;
- use placeholder citations;
- present conjecture-only, blocked, repair-requested, dropped, superseded, or failed statements as established;
- list assumptions, definitions, or notation as contributions;
- advertise every accepted theorem equally;
- force one primary result when the paper genuinely has co-primary contributions;
- force unrelated accepted results into one manuscript argument;
- manufacture novelty from the publication goal;
- confuse unresolved novelty with mathematical uncertainty;
- turn the introduction into Related Work;
- turn it into Discussion or Limitations;
- repeat the abstract sentence by sentence;
- force contribution bullets or prohibit them;
- force a predetermined paragraph count;
- force a predetermined number of equations;
- expose internal workflow, governance, audit, routing, review, or artifact bookkeeping.

---

# Final quality check

Before returning the introduction, silently verify the following.

## Scientific faithfulness

- Every claimed result is accepted and current.
- No conjecture or dropped statement appears as established fact.
- No result is stated more broadly than its accepted form.
- Novelty wording respects the novelty audit.
- Significance framing respects the significance audit.
- Sharpness, exactness, optimality, and characterization language is formally supported.

## Scientific argument

- The central scientific question is clear.
- The technical tension appears early.
- The closest work leads naturally to the paper's gap.
- The paper's setting or information regime is explicit.
- The central insight is visible when one exists.
- The main contribution or co-primary contributions are easy to identify.
- Supporting results are described according to what they add.
- The results form a coherent paper rather than a theorem inventory.

## Positioning

- Closest work is represented fairly.
- Literature distinctions are concrete and evidence-supported.
- No unsupported priority claim appears.
- The contribution is positioned at the strength supported by novelty and significance audits.
## Explicit contribution summary

The introduction must contain a clearly identifiable summary of the paper-level contributions after the problem, gap, and central insight have been established.

Do not require the reader to infer the contributions only from the surrounding theorem discussion.

Choose the clearest form for the manuscript:

- a concise contribution paragraph;
- a short contribution list;
- or a hybrid in which the main contribution is introduced in prose and the remaining major contributions are summarized explicitly.

The summary should identify the paper-level intellectual contributions, not enumerate theorem environments.

When several formal results form one contribution, group them together according to their scientific role. For example, a transfer bound, its sharpness result, and an observable certificate may form two or three paper-level contributions depending on how they support the central research question.

The contribution summary should make clear:
- what the primary contribution or contribution pair is;
- what supporting results materially strengthen, sharpen, certify, or operationalize it;
- what is technically different from the closest prior work, when verified.

Use natural signposting when helpful, such as:
- "This perspective yields three main contributions."
- "Our main contributions are as follows."
- "The analysis leads to two complementary results."
- "Together, these arguments establish three contributions."

Do not force any specific phrase, number of contributions, or bullet format.

Do not count definitions, assumptions, notation, routine lemmas, or technical proof machinery as contributions.
## Mathematical communication

- The reader can understand the main mathematical contribution without reading the theorem section.
- Important finite-sample/asymptotic, marginal/conditional, source/target, or other qualifiers are correct.
- Equations are included only when they improve understanding.
- Technical detail is sufficient to distinguish the paper from nearby work without reproducing proofs.

## Style

- The opening is substantive rather than generic.
- The prose is confident and calibrated.
- Contribution formatting serves the paper rather than a template.
- Scope is presented naturally.
- Defensive limitation language is avoided unless scientifically necessary.
- Internal pipeline terminology does not appear.
- The introduction does not read like an enlarged abstract.

## Scientific interpretation

A reviewer should be able to answer:

1. What problem is being studied?
2. Why is it nontrivial?
3. What do the closest existing approaches provide?
4. What precise gap remains?
5. What setting or information regime does this paper isolate?
6. What is the central idea, if one exists?
7. What is the main contribution or contribution pair?
8. What role do the supporting results play?
9. What do the results teach us?

If any of these answers is unclear, revise before returning the introduction.


<!-- ---
name: manuscript-compiler/sections/introduction
description: "Write the introduction section of a theoretical ML paper. Motivates the problem, identifies the gap, states calibrated contributions, and gives a concise paper outline. Venue-agnostic."
version: 1.3
used_by: manuscript_compiler
---

# Introduction Writing Skill

## Purpose

The introduction motivates the problem, explains why the setting matters, identifies the specific gap this paper addresses, and states the paper's contributions clearly. It should read like the opening of a polished theoretical ML paper: confident, precise, and grounded in the actual committed results.

The introduction should not read like an internal proof audit, a theorem-state summary, or a list of limitations.

## Pre-writing check

Before writing, silently identify:

* the central problem and why it matters;
* the most relevant known background from the available literature records;
* the specific gap this paper fills;
* the central committed result;
* the binding assumption or restriction that most limits generality;
* which committed results are genuine contributions rather than definitions, assumptions, or setup conventions;
* whether empirical results exist and whether their verdict supports inclusion;
* any conjecture-only, blocked, or repair-requested statements that must not be presented as contributions.

Use this check to write the introduction, but do not expose it in the paper.

## Structure

Use the following structure flexibly:

1. Opening motivation — introduce the problem and why it matters in 1–2 paragraphs.
2. What is known — briefly situate the problem using only admissible citations.
3. What is missing — state the specific gap this paper fills.
4. Contributions — list the main established contributions in calibrated language.
5. Paper outline — one short paragraph, if appropriate for the venue/template.

Do not over-expand the introduction. It should orient the reader, not duplicate the abstract, related work, discussion, or conclusion.

## Contributions list rules

* Each bullet should state one concrete contribution.
* List only genuine result contributions: theorems, propositions, constructions, bounds, examples, reductions, impossibility statements, or validated empirical/numerical findings.
* Do not list assumptions, definitions, estimator conventions, notation, or scope restrictions as contributions, even if they appear as committed statements.
* If a result was weakened before writing, describe the weakened form.
* If multiple committed results have different `paper_label` values, calibrate claim strength per result rather than flattening the whole contribution list to one level of confidence.
* Use `paper_label` to calibrate confidence and reference style, but do not force the nouns “theorem” or “proposition” unless they aid clarity.
* If referring to a formal result, use the same label and reference used by the main-results section, such as `Theorem~\ref{...}` or `Proposition~\ref{...}`. Do not invent labels or hardcode a result type independently of `paper_label`.
* Lead with the result that best represents the paper's central contribution, regardless of whether its `paper_label` is “theorem” or “proposition.”
* Include empirical or numerical checks as a contribution only if `empirical_results` contains a completed run with a verdict that supports the relevant theoretical claim.
* Do not present planned, failed, inconclusive, contradictory, or `bug_in_code` runs as successful empirical contributions.
* Do not list `repair_requested`, blocked, or conjecture-only statements as contributions. They may be discussed as scope boundaries, open problems, or future directions elsewhere.

## Citation policy

Use only citations provided by the pipeline's literature-search output. Do not fabricate citations, reconstruct citations from memory, or use placeholder citations.

Preferred citation sources, in order:

1. `related_work`, if the pipeline provides it and each entry has a valid citation key.
2. `background_papers`, if the pipeline provides it and each entry has a valid citation key.
3. `novelty_conflicts`, only for papers actually returned by the Literature Lead.

If the current pipeline provides only `novelty_conflicts`, then `novelty_conflicts` is the only admissible citation source.

Rules:

* Cite only papers present in the available literature records.
* Every citation must use the citation key from the record.
* Do not cite from fields that do not exist.
* Do not use placeholder citations such as `[CITATION]`, `\cite{TODO}`, or guessed BibTeX keys.
* If the literature-search output is empty, write the “what is known” paragraph without citation commands.
* A citation-free background paragraph is acceptable when no admissible citations are available.
* Treat `novelty_conflicts` carefully: it is evidence of overlap, not necessarily a complete related-work bibliography.
* Do not parade a major or fatal novelty conflict as supportive related work unless the governance process has already resolved the conflict and the final paper explicitly distinguishes itself.

## Claim-strength calibration

Calibrate verbs to each result's `paper_label`, consistent with the abstract and main-results sections.

* `paper_label="theorem"` → stronger verbs are permitted: “we prove,” “we establish,” “we show.”
* `paper_label="proposition"` or weaker → use measured verbs: “we show,” “we establish under the stated assumptions,” “we give a construction showing,” “we identify.”
* Missing or empty `paper_label` → use neutral language: “we show,” “we introduce,” “we construct,” or “we study.”
* For partial or restricted results, name the restriction directly as part of the setting.
* For open problems, use language such as “a full characterization remains open” or “extending the argument beyond this regime remains an open direction.”

Do not make a weaker result sound more general because another result is theorem-level. Do not downgrade a central theorem-level result because auxiliary results are weaker.

## Framing restrictions

Restrictions should be presented as part of the technical setting, not as apologies.

Prefer:

* “in a finite-rank kernel regression setting”
* “under an explicit spectral construction”
* “for the minimum-norm interpolant”
* “within this regime”

Avoid:

* “we only prove”
* “our result is limited to”
* “we fail to show”
* “the proof is incomplete”

The introduction may mention the binding restriction when needed for accuracy, but detailed limitations belong in the Discussion or Limitations section.

## Paper outline

If the venue or template expects an outline, include one short paragraph.

The outline should:

* mention only actual sections present in the manuscript;
* avoid over-detailed roadmap language;
* avoid internal component names;
* avoid repeating the contributions list.

If the paper is short or the template discourages explicit outlines, omit the outline.

## What to draw from inputs

* committed statements from `theorem_state`
* `paper_label` from each decision for claim-strength calibration
* contribution paragraph from `paperworld_output.json`, if available
* admissible literature-search records for citations
* `empirical_results` only if the run completed and the verdict supports inclusion
* venue/template metadata for whether to include a paper outline

## What NOT to do

* Do not overclaim beyond the committed results.
* Do not introduce new mathematical claims, assumptions, rates, datasets, experiments, or applications.
* Do not fabricate citations or use placeholder citations.
* Do not describe the internal system, pipeline, Arbiter, governance, TheoremAudit, proof obligations, or repair process.
* Do not mention internal IDs such as `PO-3`, `GAP-PO3-01`, `CHECK-*`, or `D#`.
* Do not list assumptions, definitions, notation, or estimator conventions as contributions.
* Do not present conjecture-only, blocked, repair-requested, failed, or bug-in-code items as established contributions.
* Do not make the introduction a duplicate of the abstract, related work, discussion, or conclusion. -->
