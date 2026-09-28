---
name: discussion
description: "Write discussion and limitations for a theoretical ML paper, either separately or integrated into the conclusion. Interpret results and clarify material scope boundaries without overclaiming or exposing internal proof-audit language."
version: 1.5
used_by: manuscript_compiler
----------------------------

# Discussion Writing Skill

## Purpose

Interpret the results, clarify their mathematical scope, and identify natural directions that follow from the paper. The discussion should help readers understand what the results mean, where the assumptions matter, and which questions remain open. It should not read like an internal proof audit, a list of failures, or a duplicate conclusion.

## Section mode

Use the placement recorded in `content_architecture.limitations_section`. Keep limitations separate
when the selected venue requires that format; otherwise choose a concise standalone or integrated
treatment according to the argument, without duplicating the same caveats across sections.

1. Integrated discussion (`limitations_section: discussion`)

   * Use when the venue does not require a separate limitations section.
   * Integrate scope boundaries naturally into the discussion.
   * Do not create a limitations-style bullet list unless it improves clarity.

2. Standalone limitations (`limitations_section: limitations`)

   * Use when the venue requires limitations or when the paper has major scope restrictions that reviewers must see clearly.
   * Write a separate Limitations section; a Discussion section is optional.

3. Integrated conclusion (`limitations_section: conclusion`)

   * State the material boundaries briefly within the conclusion, following `manuscript-conclusion.md`.
   * Use `Conclusion` or `Conclusion and Limitations` as the title. Do not add a separate limitations section.

The same mathematical scope information should be used in both modes; only the presentation changes.

## Structure

Use the following structure flexibly:

This outline is for a full discussion. When writing only the limitations passage, omit result
summaries and technical interpretation already given elsewhere; state the material boundaries directly.

1. Briefly restate what was established, in 2–3 sentences.
2. Explain the technical meaning of the result, especially what the assumptions, construction, or proof technique reveal.
3. Clarify the main scope boundary when it affects interpretation.
4. State open problems or future directions that naturally follow from the analysis.

Do not repeat the abstract or conclusion. The discussion should interpret and contextualize; the conclusion should close the paper.

When discussing broader implications, focus on what the result's scope, assumptions, construction, or proof mechanism reveals about the problem. Do not merely restate why the main result matters; that framing belongs in the Conclusion.

## Mapping theorem_state to reader-facing content

Read from `decisions` in `theorem_state`, but translate all internal statuses into natural mathematical prose.

* `action == "request_repair"` or `new_status == "repair_requested"`:
  Every repair-requested item must be inspected for relevance. Surface it if it affects a committed result, stated assumption, proof-dependent claim, or interpretation of the paper's scope. Group related repair items into one mathematical limitation or scope statement. If uncertain whether a repair-requested item affects the paper's claims, err toward surfacing it briefly. Silently omitting a material limitation is a failure of this skill.

* Blocked statements:
  Treat a statement as blocked if any of the following hold: `action == "block"`, `new_status == "blocked"`, or `status == "blocked"`. Include it as an open problem only if it is scientifically meaningful and connected to the paper's main thesis. Do not list blocked auxiliary proof attempts or abandoned internal routes unless they clarify the boundary of the final result.

* `new_status == "conjecture_only"` or `status == "conjecture_only"`:
  Mention as a conjecture or future direction only. Never present it as an established contribution. If the conjecture is not central to the paper's scientific argument, fold it into a short future-work sentence rather than giving it excessive space.

* `action == "note"` or `status == "noted"`:
  Acknowledge internally; no reader-facing action is needed unless it affects interpretation.

## Coverage discipline

Before writing, perform an internal coverage pass over all repair-requested, blocked, and conjecture-only items.

* Every repair-requested item must be classified as material or immaterial to the final paper.
* Material repair-requested items must be represented in the discussion or limitations, possibly through grouped themes.
* Immaterial repair-requested items may be omitted only if they correspond to abandoned claims, unused proof paths, or auxiliary attempts that do not affect any committed result.
* If materiality is unclear, include the scope boundary briefly.
* Every scientifically meaningful blocked statement connected to the paper's main thesis must be represented as an open problem or future direction.
* Do not expose this internal coverage pass in the written paper.

Assess the final claim version: a repaired defect does not remain a limitation simply because it
appears in an earlier audit. If an unresolved defect undermines a result presented as established,
return it for mathematical revision or withhold the claim; a limitations paragraph cannot make an
unsupported theorem acceptable.

## Claim-strength calibration

Use `paper_label` to calibrate confidence and verb strength, consistent with the abstract and main-results sections.

* If `paper_label="theorem"`, stronger verbs are permitted: "we establish", "we prove", "the analysis shows".
* If `paper_label="proposition"` or weaker, use measured verbs: "we show", "we identify", "we give a construction showing", "under the stated assumptions".
* If multiple results have different `paper_label` values, calibrate claim strength per result. Do not let a theorem-level result make weaker results sound more general, and do not let a weaker auxiliary result downgrade the central contribution.

Use the nouns "theorem" or "proposition" only when they aid clarity. Do not expose internal governance labels.

## Proportionality rule

Limitations, open problems, and future directions should remain concise and balanced. Prefer one
or two compact paragraphs when they cover the material boundaries; add detail only when needed for
accurate interpretation or required by the venue. There is no word or page quota. Group related
issues, refer back to assumptions or experiments already explained, and omit unused internal paths.
Do not expand the section to fill the manuscript's page budget.

## Scope and limitations style

Write limitations as precise mathematical or empirical scope boundaries, not apologies or blanket
judgments about the work's quality. Neutral wording must still make material weaknesses explicit.

* Prefer prose over bullets unless the venue requires a limitations list.
* Follow the Proportionality rule for prose as well as bullets or enumerated entries.
* Group related gaps into themes rather than listing every proof obligation separately.
* Mention limitations that materially affect interpretation of the committed results.
* Do not expose internal proof debt, abandoned claims, or unused proof paths.
* Do not say “proof incomplete,” “we failed to prove,” or “the system could not establish.”
* Prefer: “Extending the argument to X would require...”, “The present analysis focuses on...”, “A remaining question is whether...”, or “This construction leaves open...”
* Do not report novelty-audit or publication status. Sentences such as “novelty remains incomplete,”
  “application significance is unverified,” and “the paper does not claim priority” are author-facing
  review notes, not scientific limitations.
* Express literature uncertainty through concrete, attributed comparisons in Related Work. Express
  empirical limitations through the exact untested regime, baseline, data-generating process, or
  operational quantity—not through a generic statement that evidence is missing.
* State scope positively. Replace “the paper does not claim conditional coverage” with “the theorem
  establishes marginal coverage for a fixed target law,” followed, when material, by the precise
  obstacle to conditional or adaptive extensions.

## Open problems and future directions

Open problems and future directions should be specific, mathematical, and connected to the paper.

* State what would need to be proved or extended.
* State what is currently unknown.
* Follow the Proportionality rule when grouping blocked statements, conjectures, or future directions.
* Keep open problems proportionate to the established results and to the limitations discussion.
* Do not imply that an open problem is nearly solved unless the evidence supports that.
* Do not introduce unrelated applications, experiments, conjectures, or extensions.
* Do not let open problems dominate the section.

## Tone

The tone should be confident, precise, and scientifically honest.

Avoid:

* “we were unable to”
* “unfortunately”
* “this remains a failure”
* “the proof is incomplete”
* “our result is only limited to”
* “novelty remains incomplete”
* “the paper does not claim”
* “the next step is”
* “here” when a specific mathematical object can be named

Prefer:

* “the current analysis focuses on”
* “the construction isolates”
* “extending this argument beyond X remains open”
* “the result suggests a natural question”
* “closing this gap would require”

Explain what each material restriction changes about the result's interpretation. Distinguish a
deliberately bounded setting from an actual evidence gap; do not hide negative results or imply
that an untested extension is supported.

## Internal IDs — never expose them

The theorem state, decisions, and self-critique files may contain internal identifiers such as `PO-3`, `GAP-PO5-01`, `CHECK-PO-4-02`, `D1`, or `D4`.

Never print these identifiers. Translate every internal reference into a plain mathematical description of the object, assumption, proof gap, or unresolved direction.

## Internal IDs — never expose them

The proof sources may contain internal identifiers such as:

* `PO-3`
* `GAP-PO5-01`
* `CHECK-PO-4-02`
* `D1`, `D4`
* `repair_requested`
* `proposition_ready`
* `theorem_ready`
* `new_status`
* `paper_label`
* `Arbiter`
* `TheoremAudit`

Never print these identifiers in the proof appendix.

Translate every internal reference into a public mathematical description, public theorem label, public assumption label, or ordinary prose.

## What to draw from inputs

* `decisions` in `theorem_state` for classifying committed results, repair items, blocked statements, and conjectures
* committed statements for the short summary of what was established
* `paper_label` for calibrating claim strength, consistent with the abstract and main-results sections
* `state/proofs/<PO-ID>/self_critique.md` only for mathematical descriptions of real gaps that affect final claims
* `empirical_results` only if they contain concrete, nontrivial findings relevant to the discussion
* venue/template requirements and `limitations_section` to determine placement

## What NOT to do

* Do not introduce new mathematical claims, assumptions, rates, experiments, or applications.
* Do not present conjectures or blocked statements as established results.
* Do not mechanically list every internal repair request.
* Do not silently omit repair-requested items that materially affect final claims.
* Do not hide major scope boundaries that affect interpretation of the final claims.
* Do not use internal IDs, proof-obligation names, audit labels, or governance statuses.
* Do not repeat the abstract, conclusion, or limitations section verbatim.
* Do not make the paper sound weaker than the committed results justify.
* Do not make the paper sound more general than the committed results support.
