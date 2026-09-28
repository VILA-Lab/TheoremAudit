---
name: abstract
description: "Write a polished abstract for a theoretical machine learning paper. Prioritizes a clear scientific argument, central technical insight, precise theorem-level claims, and calibrated scope while remaining faithful to audited results. Designed for top-tier ML/NLP venue standards without venue-specific wording."
version: 4.0
used_by: manuscript_compiler
---

# Abstract Writing Skill

## Purpose

Write an abstract that makes a theoretical ML paper immediately understandable and compelling to an expert reviewer.

The abstract should communicate:

1. the scientific problem or tension;
2. the central insight of the paper;
3. the strongest supported technical result;
4. the most important supporting result, construction, certificate, or consequence when needed;
5. why the result changes what can be understood, guaranteed, or done in the stated setting.

The abstract is not a theorem inventory, governance summary, proof-status report, or catalogue of limitations. It should read like a polished research abstract for a strong theoretical ML paper while remaining exactly faithful to the proved results and audited evidence.

---

# Pre-writing reasoning

Before drafting, silently determine:

- **Central question:** What single research question does the manuscript answer?
- **Main gap:** What does existing theory fail to establish, distinguish, certify, or explain?
- **Central insight:** What is the conceptual idea that makes the paper more than a collection of results?
- **Primary result:** Which committed result best carries the paper's contribution?
- **Supporting result:** Which additional theorem, lower bound, construction, certificate, or empirical result materially strengthens the central argument?
- **Binding scope condition:** What one assumption or restriction most changes how a skeptical expert should interpret the main result?
- **Scientific consequence:** What becomes possible, identifiable, guaranteed, or better understood because of the result?

Use these judgments to construct one coherent narrative.

Do not expose this reasoning in the abstract.
Do not copy or lightly paraphrase wording from this guidance. Draft every sentence from the
paper-specific problem, results, and verified evidence.

---

# Authoritative sources and precedence

Use only claims supported by the current manuscript state.

`contribution_paragraph` from `paperworld_output.json` is useful for framing but may be stale.

The authoritative order is:

1. current accepted / proved statements in `theorem_state`;
2. final theorem-governance decisions;
3. novelty and significance audits when available;
4. contribution-development output;
5. supporting proof records;
6. verified empirical results;
7. `contribution_paragraph` as non-authoritative framing guidance.

If any earlier artifact states a stronger, broader, or superseded claim, rewrite it to match the current accepted state.

Never restore:
- a dropped claim;
- a conjecture as an established result;
- a stronger theorem version than the accepted one;
- novelty language rejected by the novelty audit;
- significance language unsupported by the significance audit.

---

# Core output requirements

- Write the abstract **body only**.
- Do not add an `Abstract` heading.
- Do not wrap the output in `\begin{abstract}` or `\end{abstract}`.
- Write one paragraph unless a venue template explicitly requires another format.
- Target **150–200 words** by default.
- Prefer approximately **165–190 words** when the scientific argument can be expressed naturally in that range.
- Count and trim before finishing.
- No citations.
- No section references.
- No internal IDs or governance terminology.
- No undefined notation.
- Prefer words over symbols unless a symbol materially simplifies the main result.
- Do not introduce results, assumptions, datasets, rates, bounds, methods, comparisons, or generality not supported by the authoritative sources.

---

# Abstract coherence rule

The abstract must advance **one dominant scientific argument**.

Do not summarize every accepted result independently.

Choose one primary contribution and organize other results around it as:
- support;
- certification;
- extension;
- converse;
- lower bound;
- construction;
- operational consequence;
- boundary result;
- empirical validation.

A reviewer should be able to answer after reading the abstract:

> What is the main thing this paper establishes?

If several results are mathematically important, explain how they jointly answer the same central question rather than presenting them as a flat list.

Prefer a smaller coherent argument over maximal result coverage.

---

# Contribution hierarchy

Give the strongest scientific result the most rhetorical weight.

A useful hierarchy is:

**central insight → primary mathematical result → supporting mechanism or consequence**

Do not give equal space to:
- a main theorem;
- a technical lemma;
- an audit condition;
- a corollary;
- a sanity check.

If a secondary result is necessary to make the primary result operational or meaningful, explain its role explicitly.

Examples:

- "We first establish ... and then show how to certify the required quantity from data."
- "The bound identifies ..., while a matching construction shows that the dependence is unavoidable."
- "We derive ..., which in turn yields an observable certificate for ..."

Avoid a sequence of disconnected "We show..." sentences.

---

# Preferred abstract arcs

Use the structure best suited to the paper. Do not force every paper into one template.

## Arc A — gap → result → consequence

Best for a single dominant theorem.

1. State the problem or tension.
2. Identify the precise missing guarantee or understanding.
3. State the central result.
4. Explain the key consequence.
5. State the binding scope naturally if needed.

## Arc B — phenomenon → insight → theorem → implication

Best when the paper explains why something happens.

1. Introduce the theoretical phenomenon.
2. State the conceptual insight.
3. Give the main mathematical result.
4. Explain what the result reveals or changes.

## Arc C — guarantee → robustness/certification → operational consequence

Best for papers with a theorem plus a data-dependent certificate or practical theoretical extension.

1. State the existing guarantee and where it fails.
2. Identify the quantity controlling the failure.
3. Give the primary bound or characterization.
4. Show how that quantity can be estimated, certified, or compensated for.
5. State the resulting guarantee.

## Arc D — upper result → lower bound/counterexample → boundary

Best for papers whose contribution is a sharp boundary.

1. State the unresolved question.
2. Give the positive result.
3. Give the matching lower bound, counterexample, or impossibility result.
4. Explain the resulting boundary.

## Arc E — negative result

For a genuine negative or impossibility paper:

1. State the widely expected or desired guarantee.
2. Identify the setting in which it fails.
3. State the counterexample, lower bound, or impossibility result.
4. Explain what assumption or mechanism is therefore necessary.

Negative results should be framed as scientific findings, not failed attempts.

---

# Opening

Open with the scientific problem, tension, or unresolved theoretical issue.

Good openings usually establish a contrast:

- a guarantee is known in one regime but not another;
- an estimator works empirically but lacks a theoretical explanation;
- an existing theorem depends on an assumption whose necessity is unclear;
- asymptotic behavior is known but finite-sample behavior is unresolved;
- a guarantee holds under source conditions but deployment changes the distribution;
- two apparently similar regimes behave fundamentally differently.

Avoid generic openings such as:

- "Machine learning has achieved remarkable success..."
- "In recent years, there has been growing interest..."
- "The study of X is important..."
- "We consider the problem of..."

unless the sentence immediately states the precise technical tension.

---

# State the gap precisely

Describe what is missing using a concrete technical axis when possible:

- finite-sample vs. asymptotic;
- source vs. shifted distribution;
- marginal vs. conditional;
- upper bound vs. matching lower bound;
- existence vs. observable certification;
- well-specified vs. misspecified;
- known parameter vs. data-dependent quantity;
- average-case vs. worst-case;
- sufficient condition vs. necessity;
- fixed design vs. random design;
- population vs. empirical quantity.

Avoid vague gap statements such as:

- "existing work is limited";
- "this problem remains understudied";
- "prior work does not fully address the problem";
- "we go beyond previous approaches".

Say exactly what existing analysis does not provide.

---

# Central technical message

Every abstract must contain a sentence that communicates the main result precisely enough that a theoretical ML reviewer can understand what was proved.

Prefer statements of mathematical content:

- "We show that..."
- "We establish that..."
- "We derive..."
- "We construct..."
- "We identify..."
- "We give a matching lower bound showing..."
- "We show that the coverage loss is controlled by..."
- "We establish a finite-sample decomposition that separates..."

Do not substitute labels for content.

Avoid:

- "We present a theorem..."
- "Our main proposition states..."
- "We provide theoretical analysis..."
- "We derive several interesting results..."

---

# Claim-strength calibration

Read `paper_label` from theorem-governance decisions to calibrate confidence, not to mechanically insert theorem nouns.

Never use internal values such as:
- `theorem_ready`;
- `proposition_ready`;
- `repair_requested`.

## Strongly established results

When `paper_label = "theorem"` and the statement supports the wording:

Preferred verbs include:
- "we prove";
- "we establish";
- "we show";
- "we derive".

## Restricted or proposition-level results

When `paper_label = "proposition"` or the statement depends on a narrower construction:

Prefer:
- "we show";
- "we establish under...";
- "we derive in the setting of...";
- "we construct an example showing...".

## Mixed result strengths

Calibrate each result independently.

Do not weaken a strong primary theorem merely because a supporting result is proposition-level.

Do not strengthen a restricted supporting proposition merely because the paper contains another theorem.

---

# Use precise high-level verbs

Do not ban strong scientific verbs mechanically. Use them when their mathematical meaning is justified.

## "Characterize"

Use **characterize** only when the result genuinely identifies the relevant behavior, dependence, boundary, or governing quantity with sufficient completeness.

Good:
- "We characterize how target coverage deteriorates with score-distribution shift."

Not good if the paper gives only one loose upper bound:
- "We characterize the phenomenon completely."

## "Sharp"

Use **sharp** only when supported by a matching construction, equality case, matching lower bound, or other formal sharpness result.

## "Exact"

Use **exact** only for an equality, exact finite-sample expression, exact threshold, or equivalent formally exact statement.

## "Optimal"

Use **optimal** only when an appropriate lower bound or optimization argument establishes optimality in the claimed sense.

## "Resolve"

Use "resolve" or "fully characterize" only when the accepted results genuinely close the stated question in the specified setting.

---

# Scope and assumptions

State the **single most important scope condition** needed to interpret the main result.

Integrate it naturally into the mathematical claim whenever possible.

Prefer:

- "for a target distribution fixed independently of calibration";
- "under a finite-rank spectral model";
- "for the minimum-norm interpolant";
- "with independent calibration and audit samples";
- "under bounded density-ratio shift";
- "in the misspecified linear regime".

Avoid attaching a defensive catalogue of exclusions to the end of the abstract.

Do not write:

- "Our result is only valid when..."
- "We are limited to..."
- "We do not address..."
- "The result does not extend to A, B, C, or D..."

unless the excluded regime is itself essential to the scientific boundary being established.

If several technical assumptions appear in the theorem, mention only the one whose omission would most mislead the reader about the scope.

Detailed assumptions belong in the paper body.

---

# Ending

End on the paper's strongest scientific implication, operational guarantee, conceptual boundary, or interpretation.

Strong endings often answer:

- What does the theorem now let us guarantee?
- What quantity does the result reveal as fundamental?
- What can now be certified from data?
- What assumption is shown to be necessary?
- What previously qualitative phenomenon is now quantitatively understood?

Prefer positive scientific closure.

Avoid ending primarily with:

- a list of limitations;
- future work;
- omitted cases;
- defensive qualifications;
- governance status.

A scope condition may appear near the end when mathematically necessary, but the final rhetorical emphasis should remain on the scientific result.

---

# Novelty and significance calibration

When novelty and significance audits are available, obey them.

## Verified novelty

The abstract may state the technical distinction confidently within the verified comparison scope.

Prefer describing what is new rather than writing "novel".

## Plausible incremental novelty

State the precise extension, relaxation, bound, construction, or clarification.

Do not imply broad priority.

## Uncertain overlap

Foreground the proved technical result.

Do not use:
- "first";
- "new";
- "novel";
- "previously unknown";
- "unprecedented";
- "for the first time".

The abstract should remain a complete scientific abstract; unresolved literature separation does not require defensive language.

## Attributed existing result

Do not present the underlying result as original.

Frame the contribution according to supported value, such as:
- synthesis;
- simplification;
- alternative derivation;
- clarification;
- reproducibility;
- unification;
- exposition.

Never invent a novelty probability.

---

# Avoid governance language

The abstract must never read like the output of the research-control system.

Do not mention:

- accepted statements;
- theorem governance;
- audit outcomes;
- novelty verification status;
- significance blockers;
- submission readiness;
- development obligations;
- paper routing;
- proof repair;
- claim policy;
- result IDs.

Translate all internal state into natural scientific prose.

---

# Empirical or numerical evidence

Include one empirical or numerical sentence only when `empirical_results` contains a concrete, nontrivial finding that materially supports the paper's central argument.

Good uses include:
- validating a predicted phase transition;
- confirming the tightness of a bound;
- illustrating which theoretical term dominates;
- showing a construction behaves as predicted;
- demonstrating the practical magnitude of a theoretically identified effect.

Do not add experiments merely because they exist.

Do not use generic claims such as:
- "Experiments validate our theory."
- "Results demonstrate effectiveness."

Name the actual observed phenomenon.

For a purely theoretical paper, no empirical sentence is required.

---

# Style

Use compact, natural research prose.

Prefer:
- concrete nouns;
- active verbs;
- explicit technical contrasts;
- short causal connections;
- sentences with one main purpose.

Avoid unnecessary rhetorical decoration.

Do not use generic marketing adjectives such as:
- novel;
- powerful;
- significant;
- groundbreaking;
- comprehensive;
- remarkable;
- state-of-the-art;
- surprising;

unless immediately substantiated by a precise technical fact.

Prefer:

> "The dependence is sharp."

over:

> "We obtain a powerful and surprisingly tight result."

Prefer:

> "The same score-level radius controls the loss for the data-dependent conformal threshold."

over:

> "Our framework provides a general and effective robustness guarantee."

---

# Avoid repetitive generated phrasing

Do not make every abstract sound like the same template.

In particular, avoid mechanically producing:

> "X is important, but Y remains challenging. In this work, we..."

Vary sentence structure according to the scientific content.

Possible transitions include:

- "The obstacle is that..."
- "We isolate this failure to..."
- "The key quantity is..."
- "This yields..."
- "A matching construction shows..."
- "We then make the bound observable by..."
- "Consequently..."
- "Together, these results..."
- "This identifies..."
- "The resulting guarantee..."

Use transitions only when they clarify logical relationships.

---

# What to draw from inputs

Use:

- accepted statements and `new_form` from `theorem_state` for exact mathematical content;
- `paper_label` for claim-strength calibration;
- contribution-development output for the coherent scientific argument and result hierarchy;
- novelty audit for originality wording;
- significance audit for scientific emphasis;
- `contribution_paragraph` as a non-authoritative framing seed;
- `empirical_results` only when concrete and nontrivial;
- proof records when needed to understand the exact scope or sharpness of a statement.

---

# What not to do

Do not:

- enumerate all theorems;
- use theorem IDs;
- expose internal statuses;
- call accepted mathematics a `provisional_result` in the prose;
- include conjecture-only claims as contributions;
- revive dropped prior-work-overlap claims;
- inflate an attributed specialization into an original theorem;
- infer a broader distributional, algorithmic, or asymptotic regime than was proved;
- claim sharpness without evidence;
- claim characterization from a one-sided loose bound;
- claim optimality without a lower bound or optimization result;
- describe a known constant or classical technique as a contribution;
- spend the final sentence listing exclusions;
- turn assumptions into apologies;
- use vague phrases such as "extensive theoretical analysis";
- write a miniature introduction instead of an abstract.

---

# Final quality check

Before returning the abstract, silently verify all of the following.

## Scientific faithfulness
- Every technical claim is supported by an accepted result or verified empirical finding.
- No conjecture is written as fact.
- The stated scope matches the theorem.
- Any claim of sharpness, exactness, characterization, or optimality is formally justified.

## Scientific argument
- The abstract answers one central research question.
- One result is visibly primary.
- Supporting results strengthen that result rather than competing with it.
- The conceptual insight is visible, not buried under theorem details.

## Reviewer readability
- A domain expert can understand the contribution without reading the paper.
- The gap is specific.
- The main guarantee is concrete.
- The most important scope condition is clear.
- No internal pipeline terminology appears.

## Rhetorical quality
- The opening establishes a real technical tension.
- The abstract does not read as a theorem list.
- Restrictions are integrated naturally.
- The final sentence emphasizes the scientific consequence rather than limitations.
- Marketing language has been replaced by technical substance.

## Format
- 150–200 words unless the caller specifies otherwise.
- One paragraph.
- No citations.
- No heading.
- No abstract environment.
- No undefined notation.




<!-- ---
name: abstract
description: "Write the abstract section of a theoretical ML paper. Venue-agnostic. Uses paper_label from decisions for natural language — does not force proposition or theorem labels."
version: 3.1
used_by: manuscript_compiler
---

# Abstract Writing Skill

## Purpose

The abstract is the first thing reviewers read. It must present the paper's contribution clearly, confidently, and precisely, while staying faithful to the actual proved results and stated assumptions. It should read like a polished theoretical ML abstract: focused on the scientific insight, the technical contribution, and why the result matters — not like an internal governance report or a list of limitations.

## Pre-writing check

Before writing the abstract, identify:
- the central committed result;
- the binding assumption or restriction that most limits generality;
- any empirical finding that is concrete and nontrivial;
- any conjecture-only or blocked statement that must not be presented as a contribution.

Use this check silently. Do not expose it in the abstract.

## Precedence when sources conflict

`contribution_paragraph` (from `paperworld_output.json`) may predate the Arbiter's final
decisions and can describe a claim that was since weakened, moved to `conjecture_only`, or
dropped as prior-work overlap. The current PROVED / conjectures / dropped_prior_work state in
`theorem_state` is always authoritative. If `contribution_paragraph` names a result not present
in PROVED, or states it more strongly than its current `paper_label` supports, follow the
current state and rewrite the framing — never echo a stale claim from `contribution_paragraph`.

## Content rules
- Write the abstract BODY ONLY. Do NOT wrap it in `\begin{abstract}...\end{abstract}` and
  do NOT add an "Abstract" heading — the compiler adds the environment. Including it here
  produces a duplicate "Abstract".
- 150-200 words — count the words before finishing and trim to fit.
- No citations
- No undefined notation; prefer words over symbols — introduce a symbol only if the result cannot be stated without it
- No section references — name the setting directly
- Name the assumption or restriction that most limits the result's generality. If several restrictions are present, mention the binding one: the condition a skeptical reviewer would most likely ask about first. Do not satisfy this rule by mentioning a minor technical condition while leaving the main restriction implicit.
- Do not introduce new claims, assumptions, datasets, rates, lower bounds, estimators, or generality that are not present in `theorem_state`, `paperworld_output.json`, or `empirical_results`.
- No venue-specific keywords — those come from the venue template.
- Conjecture-only statements: mention only as motivation or future work, never as contributions
- Frame restrictions as part of the technical setting, not as apologies. Avoid defensive phrases such as “only,” “merely,” “limited to,” or “we do not solve.” Prefer confident phrasing such as “in the setting of,” “under explicit assumptions,” “for a finite-rank construction,” or “within this regime.”
- The abstract must contain a clear central technical message.
- Write as a single paragraph unless the venue template explicitly requires otherwise.

## Language — do not force labels

Do NOT use internal governance labels (proposition_ready, theorem_ready).

Read `paper_label` from each decision in theorem_state to CALIBRATE CLAIM STRENGTH,
not to inject the literal noun. The strongest theory abstracts state the mathematical
claim directly ("We show that any minimum-norm interpolant...") and rarely announce
"we prove a theorem" at all — reviewers care what you proved, not what you call it.
- If paper_label = "theorem" → strong verbs are permitted ("we prove", "we establish")
- If paper_label = "proposition" → hedge ("we show", "we establish under the stated assumptions")
- If paper_label = "" or missing → natural language: "we show", "we establish", "we construct"
- Use the noun "theorem"/"proposition" only when it genuinely aids clarity, never by default
- If `theorem_state` contains multiple committed results with different `paper_label` values, calibrate claim strength per result rather than using one global level of confidence. Use stronger verbs for theorem-level results and more measured verbs for proposition-level or restricted results. Lead with the result that best represents the paper's central contribution, regardless of label.

The abstract should use natural mathematical language:

Use:
- "we establish"
- "we show"
- "we construct"
- "we give a [construction] showing" (name your paper's actual construction)

Avoid:
- "we prove a general theorem" (unless paper_label="theorem" AND result is strong)
- "we characterize"
- "we fully resolve"
- "we show in full generality"
-  generic marketing adjectives such as “novel,” “powerful,” “significant,” “state-of-the-art,” and “surprising” unless the abstract immediately substantiates the claim with a precise technical contrast. Prefer stating what is new or counterintuitive directly, rather than labeling it.

For restricted results, name the restriction directly. Substitute your paper's
actual setting — the following are illustrative examples, not fixed vocabulary:
- "in a [restricted class] setting" (e.g. "in a finite-rank misspecified kernel regression setting")
- "under an explicit [construction]" (e.g. "under an explicit spectral construction")
- "for the [specific estimator]" (e.g. "for the minimum-norm ridgeless interpolant")

## Structure
1. The problem and why it matters
2. What is known and what gap remains
3. What this paper introduces
4. The main result — named naturally, not by governance label
5. Empirical or numerical sanity-check finding — one sentence only if `empirical_results` contains a concrete, nontrivial finding

Not every abstract needs all 5 beats in this exact order — omit or reorder a beat where
the paper does not need it. This is a scaffold, not a mold; two abstracts produced by
this skill should not read as though generated from the same template.

## Worked example, beat by beat

Each beat below is illustrative phrasing for the *pattern*, not fixed vocabulary —
substitute your paper's actual objects and results.

**Beat 1 — problem and why it matters.** Open with the tension the paper resolves,
stated as a fact about the world, not about the paper:
> Minimum-norm interpolation is now well understood when the underlying model is
> correctly specified, but practical estimators are routinely fit under model
> misspecification, where existing risk characterizations do not directly apply.

**Beat 2 — what is known and what gap remains.** Name the closest prior result and
the specific thing it does not give, using a Precision-Taxonomy-style axis (rate,
assumption, generality) rather than a vague "goes further":
> Existing analyses of the ridgeless interpolator give asymptotic risk formulas under
> a well-specified model; the finite-sample behavior of the parameter error under
> misspecification, relative to the best linear predictor, has not been isolated
> explicitly.

**Beat 3 — what this paper introduces.** State the object or technique directly,
not "a novel approach":
> We derive an exact finite-sample decomposition of the interpolator's parameter
> error, on the event that the design matrix has full row rank, that separates the
> null-space contribution, the noise term, and an explicit misspecification remainder.

**Beat 4 — the main result, named naturally.** State the mathematical content, not
the label:
> The resulting excess-risk expansion holds without asymptotic assumptions on the
> covariance spectrum and identifies exactly which term absorbs the model
> misspecification.

**Beat 5 — empirical or numerical finding (only if concrete and nontrivial).**
> Numerical illustrations on synthetic misspecified designs confirm that the
> remainder term, not the noise term, dominates the excess risk once the
> misspecification magnitude exceeds the noise level.

Note what these beats avoid: no "novel," "powerful," or "significant gains" (banned
marketing adjectives with no technical substantiation); no benchmark-style "gains
over X models" framing, which belongs to empirical papers, not theorem-driven ones;
every claim of improvement is anchored to a specific object (the remainder term, the
full-row-rank event, the misspecification magnitude) rather than an unquantified
comparison.

## What to draw from inputs
- contribution_paragraph from paperworld_output.json as a starting point
- paper_label from each decision for how to refer to each result
- new_form of committed statements for accurate mathematical content
- Key finding from empirical_results only if it is concrete and nontrivial

## What NOT to do
- Do not use internal IDs like PO-3 or repair_requested
- Do not force "proposition" just because new_status=proposition_ready
- Do not include conjecture-only statements as contributions
- Do not refer to section numbers -->
