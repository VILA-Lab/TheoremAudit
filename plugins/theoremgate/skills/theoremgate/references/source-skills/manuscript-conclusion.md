---
name: conclusion
description: "Write the conclusion section. Brief summary, broader implications, and future work. No new content."
version: 1.1
used_by: manuscript_compiler
---

# Conclusion Writing Skill

## Purpose
Close the paper cleanly. Summarize, situate, and point forward.
No new mathematical content — this is a narrative section.


## Pre-writing check

Before writing the conclusion, identify:
- the central contribution to summarize;
- the main implication that follows from the committed results;
- limitations already stated in Discussion, so they are not repeated;
- whether `content_architecture.limitations_section` assigns scope coverage to the conclusion;
- future directions that naturally follow from the paper without introducing new claims.

Use this check silently. Do not expose it in the conclusion.
## Structure
Summarize the main contribution and its implication briefly. If the conclusion is the planned
location for limitations, include a compact passage on material mathematical or empirical
boundaries, following `manuscript-discussion.md`. Close with a supported implication or specific
open question. Combine these functions when natural; do not target a fixed page or paragraph count.

## Rules
- Brief — do not repeat the abstract
- Do not introduce new mathematical claims, assumptions, rates, experiments, or applications
- Do not repeat the limitations section
- Match the contribution level to each result's `paper_label`, but do not force the nouns "theorem" or "proposition" unless they aid clarity. Use `paper_label` to calibrate confidence and verb strength, not to expose internal governance labels.
- If multiple results have different `paper_label` values, calibrate claim strength per result rather than flattening the conclusion to one global level of confidence.
- Forward-looking: end on what this work enables, not what it failed to prove
- Future directions must be grounded in the paper's actual setting and results. Do not introduce new applications, experiments, conjectures, or extensions as if they were established.
- State limitations as precise boundaries and evidence gaps, not blanket self-criticism. Do not
  hide a material weakness, contradict the findings, or soften an unresolved mathematical defect.
- Avoid generic closing phrases such as "we hope this work inspires future research" unless followed by a specific technical direction.
- End with a precise mathematical implication or open question, not an author task list. Do not tell
  the authors to verify literature, collect evidence, run experiments, prepare a submission, or
  improve the manuscript.
- Keep novelty-review status and publication readiness out of the conclusion. The conclusion
  synthesizes the scientific contribution; Related Work carries comparative attribution and
  the planned limitations passage carries technical scope boundaries, whether separate or integrated.
- Avoid deictic and editorial phrases such as "here," "the next step," "evidential rather than
  cosmetic," "this paper does not claim," and "novelty remains incomplete."

## Language
Calibrate verbs to `paper_label`, matching the other sections:
- `paper_label="theorem"` → strong verbs are permitted: such as  "we have established", "we have proved", "we have demonstrated"
- `paper_label="proposition"` or weaker → use measured verbs such as "we have shown", "we have introduced", "we identify", "we give a construction showing"
- "This framework provides a foundation for..."
- "A central open question is whether..."
- "The analysis therefore isolates..."

## What NOT to do
- Do not add new mathematical statements
- Do not repeat limitations already stated in Discussion
- Do not make stronger claims than the committed results support.
- Do not fix the label to "proposition" or "theorem" independently of `paper_label`
- Do not end with a checklist of missing citations, experiments, verification, or submission tasks.
