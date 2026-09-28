---
name: manuscript-compiler/sections/related-work
description: "Drafts a top-tier ML/theory Related Work section from verified fetched references using adaptive thematic structuring, close-work comparison, precise technical positioning, and an explicit gap statement."
version: 3.0
used_by: manuscript_compiler
---

# Related Work Writing Skill

## Purpose

Write the Related Work section as it would appear in a polished ML/theory paper targeting a top-tier venue such as NeurIPS, ICML, COLT, or JMLR — not as a generic literature summary.

The section must argue and position, not enumerate. It identifies the intellectual landscape, narrows to the closest technical lineage, draws a precise boundary between what prior work establishes and what it does not, and ends with an explicit statement of the remaining gap that the present results close. A reader who reads only this section should be able to state, in one sentence, what is new.

This skill writes prose only. It does not search for new sources and does not create bibliography entries.

Before drafting, load the schema-v2 `closest_work_comparisons` from the literature audit. Use it as a
technical comparison matrix: prior result, prior assumptions, present difference, and remaining
overlap. Every closest-work record must appear in the direct-comparison portion of the section. Do not
merely say that the present analysis is different; state the axis and direction of the difference.

Also  introduce cleane separation between related-work positioning and limitations.
---

## Core Operational Directives

### 1. Hard Grounding and Citation Rules

- **Strict corpus isolation:** use only references provided in `related_work` and `novelty_conflicts` within `theorem_state`.
- Never cite from memory. Never speculate about papers not provided. Never invent authors, titles, venues, years, URLs, or bibkeys.
- Use `cite_key` values exactly as provided.

Corpus roles:
- **`related_work`** is the primary source for the broad landscape, theoretical lineage, and background.
- **`novelty_conflicts`** is secondary. Use it only for point-by-point positioning against the closest overlaps — never as a broad survey list.
- If a `novelty_conflicts` entry lacks a valid `cite_key`, use it only as positioning context. Do not invent a LaTeX citation key.
- **Conflict resolution:** if a paper appears in both corpora with differing descriptions of its contribution, the `novelty_conflicts` description governs *only* the direct-comparison sentence about that paper; the `related_work` description governs its role everywhere else. Never let the two descriptions contradict each other in the drafted prose — resolve silently by choosing the more specific/technical of the two claims.

### 2. Deduplication Protocol

Before drafting, deduplicate the citable corpus:
1. Canonicalize papers appearing across both `related_work` and `novelty_conflicts` by DOI, arXiv ID, URL, or normalized title.
2. Map duplicates to a single canonical `cite_key`, preferring the `related_work` key.
3. Cite each distinct paper where its contribution is primary.
4. Mention a paper in multiple places only if it serves genuinely different technical roles (e.g., broad background *and* closest comparator).

### 3. Grammatical and Voice Constraints

**Banned document subjects.** Never use self-referential document subjects: "the paper," "our paper," "this manuscript," "this note," "the present paper."

**Use result nouns as subjects instead** — the bound, the identity, the estimator, the decomposition, the analysis, the argument.

```
Bad:  This paper's contribution over [X] is that we don't require the
      isotropic assumption, and our analysis also covers the
      misspecified case.
Good: The present decomposition relaxes the isotropic assumption used
      in the analysis of [X] and extends to the misspecified setting,
      where the excess risk is measured against the best linear
      predictor rather than a realizable parameter.

Bad:  Unlike prior work, in this paper we don't stop at an asymptotic
      formula — we go further and get an exact identity.
Good: Unlike the asymptotic risk formulas of [X], the identity
      established here holds exactly at finite sample size, on the
      event that the design matrix has full row rank.

Bad:  This note's main technical device is a projector-based argument,
      which the paper uses throughout to isolate the misspecification
      term.
Good: The argument turns on a projector-based decomposition, used
      throughout to isolate the misspecification term as an explicit,
      unreduced remainder.
```

Note the failure mode in the second "Bad" example above: swapping "the paper" for "the result" is not sufficient on its own if the sentence still narrates the paper's *effort* ("we go further") rather than stating the technical fact plainly. The fix is not lexical substitution — it is rewriting the sentence so a mathematical object, not the act of writing, is doing the work.

**First-person verbs are permitted** ("we prove," "we contrast," "we isolate") — only self-referential *noun phrases* are restricted.

**Banned meta-phrases.** Never write search-log or execution chatter into the prose ("the literature search did not establish...", "we found no evidence that...", "based on the fetched references..."). State the technical boundary directly instead: "While related projector algebra appears across existing analyses, the explicit finite-sample decomposition remains unestablished."

**Tense.** Describe prior results in present tense ("establishes," "requires," "achieves") — this is the field convention and signals that the result still stands. Reserve past tense for describing a superseded or since-corrected claim.

---

## The Precision Taxonomy for Technical Comparison

"Precise positioning" is not a vibe — it means anchoring every comparison to at least one concrete axis. When contrasting the present result against a prior result, select from (and name explicitly) the axes that actually differ:

- **Rate / order:** e.g., $O(1/\sqrt{n})$ vs. $O(1/n)$, not "faster."
- **Assumption strength:** e.g., sub-Gaussian vs. bounded, strong convexity vs. convexity, realizability vs. agnostic — name the specific assumption being relaxed or added.
- **Dimension / complexity dependence:** explicit dependence on $d$, condition number, VC dimension, etc.
- **Generality of setting:** which structural restriction is lifted (isotropic → anisotropic, linear → nonlinear, fixed design → random design).
- **Tightness:** matching upper/lower bounds vs. one-sided; whether a prior bound was known to be loose.
- **Computational cost:** sample complexity vs. time complexity vs. oracle complexity — do not conflate these.
- **Proof technique / mechanism:** only worth stating as a point of comparison if the mechanism itself explains *why* the scope or rate differs (e.g., "the argument avoids a union bound over the covering number, which is the source of the extra $\log d$ factor in [X]").

**Rule:** every sentence that claims prior work is weaker, narrower, or less general than the present result must name at least one axis above. Sentences like "this extends the idea further" or "this work goes beyond prior efforts" are disallowed — they are unfalsifiable and read as filler.

---

## Structural and Narrative Architecture

Do not enforce a rigid paragraph count. Adapt structure to corpus depth (see length calibration below), but preserve the narrative arc: **landscape → lineage → boundary → gap**. Each block should end on a sentence that motivates the next, not just stop.

### 1. Broad Intellectual Landscape (1+ paragraphs)
- Group citations by technical sub-theme, not by chronology or by author. Chronology is only a valid ordering principle *within* a sub-theme, where it clarifies how a technique evolved.
- State established results, standard assumptions, and baselines in this cluster as settled fact — this paragraph is not the place to critique them.
- **Avoid list-dumps.** Do not string more than two or three citations behind a single generic verb ("X, Y, and Z study risk asymptotics [1,2,3]"). Instead, differentiate: state what each cluster of work actually shows, and only group citations together when they genuinely share a technique or conclusion, not merely a keyword.

### 2. Closest Technical Lineage (1+ paragraphs)
- Narrow to the specific line of work the present result builds on or modifies directly.
- Order candidates so the *closest* comparator appears last, immediately before the boundary/gap discussion — this is the natural handoff point into direct contrast.
- Name the specific technique being inherited (a projector decomposition, a peeling argument, a particular concentration inequality) rather than gesturing at "similar methods."

### 3. Direct Contrast and Precise Scope Boundaries (1+ paragraphs)
- Draw on `novelty_conflicts` for point-by-point positioning against the closest overlaps identified in §2.
- Every comparative claim must use the Precision Taxonomy above.
- State limitations or boundaries of the present result without false modesty or over-claiming — e.g., "the argument establishes the exact identity but does not yield a finite-sample rate" is a legitimate, precise boundary statement, not a weakness to be hidden.

### 4. Gap Statement (required, 1–2 sentences, typically closing the section)
- State explicitly, in a single load-bearing sentence, what remains unestablished by the cited corpus and is closed by the present result.
- This sentence must be traceable to specific comparators named in §3 — it should never introduce a new, uncited claim about "the literature" in general.
- Template pattern (adapt, do not copy verbatim): "What remains open after [comparator, cite_key] is [specific gap along a Precision Taxonomy axis]; the present analysis closes this by [one-clause mechanism]."

---

## Hedging Calibration

Claims about what prior work does *not* establish are the highest-risk sentences in the section — too strong and they misrepresent the literature; too soft and the contribution disappears.

- When a limitation of prior work is explicit in that paper (stated as an open problem, an acknowledged restriction, or a stated assumption), state it directly with no hedge: "requires," "assumes," "is restricted to."
- When the limitation is inferred rather than stated by the prior authors (e.g., their techniqe does not obviously extend, but they never claim it can't), hedge precisely: "does not appear to extend to," "the argument relies on [X], which is not available in," rather than an unhedged "cannot handle" or "fails to."
- Never use vague hedges that hide the absence of a citation ("it is believed that," "prior work generally assumes") — every hedge must still resolve to a specific `cite_key`.
- **Paragraph-level grounding.** This rule applies at the paragraph level, not only the sentence level: a paragraph labeled or functioning as "closest overlap" / "closest technical lineage" must name at least one `cite_key` from that paragraph's own sentences. It is not sufficient for the *surrounding* paragraphs to carry citations while the overlap paragraph itself describes "existing analyses" or "neighboring works" in the abstract — that is the single most common way a Direct Contrast paragraph quietly loses its grounding while appearing, at the sentence level, to hedge correctly.

---

## Length Calibration

- Small corpus (roughly ≤ 6 references): a single unified block covering landscape, lineage, and boundary is acceptable; the gap statement is still mandatory and should close the section.
- Medium corpus (roughly 7–20 references): the four-part structure above, each as one paragraph.
- Large corpus (20+ references, multiple sub-themes): consider `\subsection*{}` breaks per sub-theme within the landscape block, but keep the lineage → boundary → gap arc as a single continuous close, so the section still ends on one argument rather than fragmenting into independent mini-surveys.

---

## Pre-Output Quality Scan

Before emitting final text, verify:
- [ ] No banned document subjects ("the paper," "this manuscript," "this note") survive — replace with result nouns ("the bound," "the identity," "the estimator," "the result").
- [ ] No meta-language about literature searches, fetched records, or corpus contents survived into the prose.
- [ ] Every comparative claim against prior work names at least one Precision Taxonomy axis.
- [ ] No sentence strings more than two or three citations behind one generic verb.
- [ ] Every paragraph functioning as "closest lineage" or "direct contrast" contains at least one `cite_key` in its own sentences — not merely in neighboring paragraphs.
- [ ] A gap statement is present, is traceable to a specific `cite_key` from §3, and closes (or clearly anchors) the section.
- [ ] All `\cite{...}` keys match the exact strings provided in the input corpus.
- [ ] Present tense used for standing prior results; past tense reserved for superseded claims.

---

## Output Format

- Output clean LaTeX/Markdown ready for direct compiler inclusion.
- Use standard LaTeX citation commands (`\cite{key1, key2}`).
- Omit introductory meta-commentary, code fences around output, or closing summaries. Output only the body prose.
