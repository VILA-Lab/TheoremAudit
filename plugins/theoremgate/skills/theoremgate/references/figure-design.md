# Professional Figure Design

Design figures as arguments, not decorations. Before plotting, state the single comparison or
relationship the reader must see, the visual encoding that reveals it, the uncertainty that must
remain visible, and the final paper size. Choose dimensions within each experiment from its evidence
and declared manuscript size; do not inherit a global plotting profile.

Derive at least two visual principles from `paper/writing_exemplars.json`, such as restrained color,
direct labeling, panel density, legend placement, or typography hierarchy. Learn cross-paper design
patterns only; do not reproduce a distinctive figure composition.

Render at least two genuine design candidates for every main figure. Vary a meaningful choice such
as layout, visual encoding, panel grouping, scale, annotation, or legend strategy—not merely a color
shade. Compare the candidates at their declared paper width and retain both files until review.

Prefer:

- one visual question and one panel per figure by default; several curves are appropriate when they
  answer the same comparison;
- vector PDF or SVG masters with a 300-DPI preview;
- direct labels or legends placed outside evidence-dense regions;
- colorblind-safe colors reinforced by markers or line styles;
- uncertainty bands, intervals, or distributional summaries when the experiment has repeated runs;
- descriptive axis labels with units and a concise figure-level visual focus;
- aligned axes and shared scales only when comparison remains honest;
- enough whitespace to separate groups without wasting page area;
- captions that explain encoding, uncertainty, sample count, and scope.

Avoid rainbow maps, default Matplotlib styling, saturated backgrounds, unnecessary borders, 3-D
effects, crowded legends, unbalanced panels, tiny axes or text, excessive whitespace, redundant titles, decorative
gradients, and dense annotations that compete with the data.

Open every hash-bound PNG rendering with the available local image-viewing tool and inspect it at
actual paper size; source code and structural metadata are not visual inspection. Score the selected design from 1–5 on visual hierarchy,
typography, color design, layout balance, data-ink efficiency, statistical communication,
caption alignment, and cross-figure consistency. `publication_ready` requires every score to be at
least 4 and an average of at least 4.25, plus all structural checks. Use a fresh reviewer role,
independent subagent, or external check; the plotting pass must not simply approve itself.

Pass `review-figure` an object with this exact shape:

```json
{
  "schema_version": 2,
  "legible_at_paper_size": true,
  "labels_correct": true,
  "palette_accessible": true,
  "no_clipping": true,
  "notation_consistent": true,
  "effect_readable": true,
  "uncertainty_not_dominant": true,
  "single_scientific_question": true,
  "crowded_legends": false,
  "unbalanced_panels": false,
  "tiny_axes_or_text": false,
  "excessive_whitespace": false,
  "design_scores": {
    "visual_hierarchy": 4,
    "typography": 4,
    "color_design": 4,
    "layout_balance": 4,
    "data_ink_efficiency": 4,
    "statistical_communication": 5,
    "caption_alignment": 5,
    "cross_figure_consistency": 4
  },
  "overall_score": 4.25,
  "independence_mode": "fresh_role_review",
  "reviewer_identity": "visual_editor",
  "strengths": ["...", "..."],
  "remaining_tradeoffs": ["..."],
  "blocking_tradeoffs": [],
  "exemplar_principles_applied": ["...", "..."],
  "design_candidates": [
    {"path": "experiments/figure-a.pdf", "sha256": "...", "design_rationale": "...",
     "rendered_preview_path": "experiments/rendered/figure-a.png",
     "rendered_preview_sha256": "...", "render_source_sha256": "...",
     "rendered_size_class": "single_column", "paper_size_inspection": "..."},
    {"path": "experiments/figure-b.pdf", "sha256": "...", "design_rationale": "...",
     "rendered_preview_path": "experiments/rendered/figure-b.png",
     "rendered_preview_sha256": "...", "render_source_sha256": "...",
     "rendered_size_class": "single_column", "paper_size_inspection": "..."}
  ],
  "selected_candidate_path": "experiments/figure-a.pdf",
  "selection_reason": "...",
  "writing_exemplars_sha256": "include when paper/writing_exemplars.json exists",
  "notes": "..."
}
```

Compute `overall_score` as the arithmetic mean of the eight design scores. Do not round it in a way
that differs from the exact mean by more than 0.01.
