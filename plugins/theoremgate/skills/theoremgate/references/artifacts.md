# Artifact schemas

Use JSON unless a proof draft is explicitly Markdown or LaTeX. Preserve IDs across stages.

## `direction_generation`

Use one candidate when the user has specified a clear direction. Use multiple candidates only for a
vague direction or an explicit request for ideas, alternatives, or comparison.

```json
{
  "candidates": [
    {"id": "D1", "title": "...", "question": "...", "rationale": "..."}
  ]
}
```

## `direction_selection`

```json
{
  "selected_id": "D1",
  "rationale": "...",
  "novelty_evidence": [
    {"title": "...", "url": "...", "comparison": "...", "fetched": true}
  ]
}
```

Do not invent a novelty citation. An empty evidence list is valid when search was unavailable, but
state that limitation in the rationale. With one user-specified candidate, `selected_id` must preserve
that same direction; literature and feasibility findings inform discovery rather than replace the topic.

## `discovery`

```json
{
  "setting": {"domain": "...", "objective": "..."},
  "assumptions": [{"id": "A1", "statement": "..."}],
  "theorem_targets": [
    {"id": "T1", "statement": "...", "result_type": "upper-bound"},
    {"id": "T2", "statement": "...", "result_type": "necessity"}
  ],
  "primary_target_id": "T1",
  "publication_strength": {
    "technical_obstacle": "The nonstandard mathematical obstacle resolved by T1.",
    "novelty_delta": "The precise hypothesized difference from the closest theorem.",
    "closest_work_boundary": "The assumption, rate, object, or regime boundary.",
    "nonvacuity_check": "A concrete parameter regime where T1 is informative.",
    "complete_proof_route": "A route whose central step is executable rather than open.",
    "companion_result_id": "T2",
    "exceptional_depth_justification": ""
  },
  "proof_obligations": [
    {
      "id": "PO-1",
      "supports": "T1",
      "description": "...",
      "depends_on": [],
      "assumptions_expected": ["A1"]
    }
  ]
}
```

Proof dependencies must reference known obligations and form a DAG.
Full runs targeting original research or a workshop paper must include `publication_strength`.
Every target in those runs needs a recognized `result_type`. The primary target and its distinct
companion must each have a proof obligation. A genuinely deep standalone primary result may replace
`companion_result_id` with a non-empty `exceptional_depth_justification`, but never provide both.

## `exploration`

```json
{
  "probes": [
    {"id": "P1", "kind": "analytical", "setup": "...", "result": "..."}
  ],
  "recommendation": "continue",
  "rationale": "..."
}
```

Allowed recommendations: `continue`, `narrow`, `reshape`, `blocked`.

## `proof_development`

Write proof drafts under `proofs/`, then index every discovery obligation:

```json
{
  "schema_version": 2,
  "proofs": [
    {
      "id": "PO-1",
      "status": "drafted",
      "blueprint_path": "proofs/PO-1/blueprint.json",
      "blueprint_sha256": "...",
      "draft_path": "proofs/PO-1.md",
      "draft_sha256": "...",
      "depends_on": [],
      "assumptions_used": ["A1"],
      "proved_scope": "...",
      "gaps": [],
      "status_history": [
        {"from": "planned", "to": "drafted", "actor": "proof_team", "reason": "...", "recorded_at": "..."}
      ]
    }
  ]
}
```

Use statuses `unstarted`, `planned`, `analysis_in_progress`, `drafted`, `partial`,
`conditional_draft`, `failed`, `blocked`, `blocked_by_dependency`, `repair_requested`,
`accepted_by_arbiter`, or `rejected_by_arbiter`. Strict records require structured gaps with `id`,
`severity`, `description`, `status`, and `resolution`; assumption IDs are checked against discovery.
A `drafted` proof cannot contain an open major/fatal gap, an accepted proof cannot contain any open
gap, and only governance may assign Arbiter statuses. Legacy indexes remain readable as unverified
records and can be moved to the strict schema with an explicitly labeled migration baseline.

## Audit artifacts

Both audit stages use:

```json
{
  "schema_version": 3,
  "artifact": "adversarial_audit",
  "stage": "local_adversarial_audit",
  "findings": [
    {
      "id": "LOCAL-F1",
      "target_id": "PO-1",
      "kind": "boundary_case",
      "subtype": null,
      "severity": "major",
      "description": "...",
      "attack_method": "...",
      "evidence": {"summary": "..."},
      "source": {"path": "...", "location": "...", "sha256": "..."},
      "resolution_condition": "...",
      "scope_affected": ["T1"],
      "resolved": false,
      "_provenance": {
        "actor": "auditor", "operation": "append",
        "recorded_at": "...", "record_sha256": "..."
      }
    }
  ],
  "events": [
    {
      "id": "AMEND-0001",
      "event_type": "amendment",
      "finding_id": "LOCAL-F1",
      "reason": "...",
      "changes": {"severity": {"from": "major", "to": "fatal"}},
      "actor": "auditor",
      "recorded_at": "...",
      "previous_event_sha256": null,
      "event_sha256": "..."
    }
  ]
}
```

Controlled kinds are `proof_gap`, `counterexample`, `assumption_failure`, `boundary_case`,
`definition_error`, `dependency_error`, `citation_mismatch`, `novelty_issue`, `scope_overclaim`,
`numerical_contradiction`, `reproducibility_issue`, and `other` (which requires a subtype). Targets
may include assumptions, theorem targets, proof obligations, definitions, exploration probes,
synthesized statements during final audit, or `RUN`. Base findings are immutable. Amendments and
false-positive/preexisting-evidence resolutions are hash-chained events. A pre-synthesis repairable
local finding may use bounded same-run correction after the failed pass is preserved beneath
`corrections/`. A post-bundle or materially changed repair is performed in a child run;
`verify-repair` records the ancestor audit/finding hashes, child-run artifact hash, outcome, and
verification mode (`independent_subagent`, `fresh_role_review`, or `external_check`) without changing
the parent. Schema-v2 and
legacy artifacts remain readable but do not acquire schema-v3 integrity retroactively.

## `governance_review`

```json
{
  "schema_version": 3,
  "artifact": "governance_review",
  "stage": "governance_review",
  "decisions": [
    {"finding_id": "LOCAL-F1", "action": "repair_requested", "reason": "..."}
  ]
}
```

Allowed strict actions: `cleared`, `repair_requested`, `invalidated`, and `deferred`. Use `cleared`
only for findings already resolved by evidence. `invalidated` requires an unresolved fatal
mathematical finding; novelty, citation, scope, or reproducibility concerns cannot by themselves
declare a theorem mathematically invalid. `excluded` is accepted only in legacy artifacts.

## `theorem_synthesis`

```json
{
  "statements": [
    {
      "id": "TH-1",
      "formal": "...",
      "informal": "...",
      "assumptions_used": ["A1"],
      "proven_scope": "...",
      "synthesized_from": ["PO-1"],
      "based_on": ["T1"],
      "honest_caveats": "..."
    }
  ]
}
```

## `arbiter`

```json
{
  "schema_version": 4,
  "artifact": "arbiter_decisions",
  "stage": "arbiter",
  "decisions": [
    {
      "statement_id": "TH-1",
      "status": "theorem_ready",
      "reason": "...",
      "weakened_form": null,
      "findings_addressed": []
    }
  ]
}
```

Allowed statuses: `theorem_ready`, `proposition_ready`, `repair_requested`, `conjecture_only`,
`rejected`, `invalid`. Use `invalid` only when the statement is false, contradicted, or fatally
unsound and `findings_addressed` contains a relevant unresolved fatal mathematical finding.
Addressed IDs must be unique, existent, and relevant through the statement's assumptions, theorem
targets, proofs, statement ID, explicit affected scope, or a run-wide finding. `repair_requested`,
`conjecture_only`, and legacy `rejected` remain retained non-final
research objects rather than established results. When accepting only a narrower statement, put its exact formal text in
`weakened_form`; the bundle preserves both the original and effective forms.
The theory bundle also exports `repair_verification_lineage` for verified parent-to-child repairs.

## `novelty_audit`

```json
{
  "scope_statement_ids": ["TH-1"],
  "closest_work_comparisons": [
    {
      "id": "CW-1",
      "statement_id": "TH-1",
      "title": "...",
      "source_url": "...",
      "verified": true,
      "literature_record": {
        "schema_version": 1,
        "record_type": "literature_record",
        "record_id": "arxiv:2401.00001",
        "canonical_ids": {"arxiv": "2401.00001", "doi": "", "openreview": "", "semantic_scholar": ""},
        "source": {"provider": "arxiv", "source_type": "preprint", "landing_url": "...", "pdf_url": "...", "is_primary": true},
        "bibliographic": {"title": "...", "authors": ["..."], "year": 2024, "venue": "...", "version": "v1", "abstract": "..."},
        "retrieval": [{"adapter": "fetch_paper", "provider": "arxiv", "query": "...", "query_variant": "", "retrieval_queries": [], "retrieved_at": "...", "result_url": "...", "raw_response_sha256": "..."}],
        "verification": {"status": "primary_source_verified", "verified_at": "...", "evidence": [{"theorem": "Theorem 3", "section": "", "pages": "8--10", "assumptions": ["..."], "conclusion": "...", "supports_claim_ids": ["TH-1"]}]},
        "metrics": {},
        "metadata": {"role": "novelty_neighbor"}
      },
      "theorem_location": "Theorem 3",
      "prior_result": "...",
      "current_result": "...",
      "delta": "...",
      "overlap": "..."
    }
  ],
  "findings": [
    {
      "id": "NF-1",
      "statement_id": "TH-1",
      "classification": "new_extension",
      "reason": "...",
      "evidence_ids": ["CW-1"]
    }
  ],
  "overall_verdict": "supported",
  "limitations": []
}
```

The scope and findings must cover every Arbiter-accepted statement exactly once. Allowed
classifications: `novel`, `new_extension`, `new_counterexample`, `new_synthesis`,
`new_empirical_evidence`, `attributed`, `standard`, and `unclear`. Allowed overall verdicts:
`supported`, `partial`, `not_novel`, and `unverified`. A comparison with `verified: true` requires a
valid `literature_record.v1` whose state is `primary_source_verified`; use `unverified` when sources
could not be checked. The full record contract is in `literature-record.md`.

## `significance_audit`

```json
{
  "scope_statement_ids": ["TH-1"],
  "framing_scope": "application_motivated",
  "claimed_application": "...",
  "application_evidence": {
    "level": "synthetic_model",
    "description": "...",
    "supports_claims": ["..."]
  },
  "assumption_operationalization": [
    {
      "assumption": "...",
      "operational_meaning": "...",
      "observable": "...",
      "validated": false,
      "misspecification_risk": "...",
      "evidence": "..."
    }
  ],
  "empirical_assessment": {
    "baseline_strength": "weak",
    "calibration_demonstrated": false,
    "error_compute_comparison": true,
    "misspecification_test": false,
    "nonstationary_test": false,
    "multistate_test": false,
    "real_system_test": false,
    "missing_experiments": ["real-system calibration"]
  },
  "theory_assessment": {
    "specialization_level": "direct_specialization",
    "bound_practicality": "loose",
    "known_parameter_burden": "strong",
    "technical_obstacle": "..."
  },
  "significance_verdict": "narrow",
  "blocking_findings": [
    {
      "id": "SF-1",
      "severity": "major",
      "category": "application_evidence",
      "description": "...",
      "required_action": "..."
    }
  ]
}
```

Framing is `theory_only`, `application_motivated`, or `application_validated`; evidence is `none`,
`synthetic_model`, `semi_synthetic`, or `real_system`. A validated application requires real-system
evidence. Significance is `high`, `moderate`, `narrow`, `unclear`, or `insufficient`. This independent
audit caps the contribution developer's significance and supplies deterministic route blockers.

## `contribution_assessment`

```json
{
  "contribution_type": "incremental_extension",
  "significance_level": "moderate",
  "publication_goal": "original_research",
  "primary_statement_ids": ["TH-1"],
  "paper_argument": {
    "central_question": "...",
    "thesis": "...",
    "coherence_rationale": "..."
  },
  "result_roles": [
    {
      "statement_id": "TH-1",
      "role": "primary_result",
      "paper_placement": "main",
      "depends_on": [],
      "rationale": "..."
    }
  ],
  "paper_value": "...",
  "claim_policy": {
    "allowed_claims": ["..."],
    "prohibited_claims": ["..."],
    "required_attribution": ["..."]
  },
  "development_obligations": [
    {"id": "EXT-1", "description": "...", "priority": "high"}
  ],
  "empirical_requirements": {
    "status": "recommended",
    "reason": "..."
  }
}
```

Allowed contribution types: `novel_theorem`, `incremental_extension`, `synthesis`,
`counterexample_negative_result`, `empirical_validation`, `expository_result`,
`provisional_result`, and `null_result`.
Allowed significance: `high`, `moderate`, `narrow`, `unclear`, or `insufficient`. Empirical status is `required`,
`recommended`, or `not_required`. Attributed or standard primary results require an explicit
attribution policy. Use `provisional_result` for accepted mathematics whose originality remains
unclear. If no statement was accepted, use `null_result` with an empty primary list; the
resulting bundle is non-writable.

Result roles classify every accepted statement exactly once. Roles include `primary_result`,
`supporting_theorem`, `supporting_proposition`, `lemma`, `corollary`, `lower_bound`,
`counterexample`, `boundary_result`, `negative_result`, and `empirical_result`. Placements are
`main`, `supporting`, `appendix`, `separate_paper`, or `deferred`. Positive and negative results may
share a paper when `paper_argument.coherence_rationale` explains their common scientific role.

## `content_architecture` limitations placement

`limitations_section` names the planned section that discusses material mathematical and empirical
boundaries: `limitations`, `conclusion`, or `discussion`. A standalone Limitations section is optional
unless required by the selected venue. Existing architectures with that section may omit the field.
Integrated architectures must name a main-text destination, describe its scope coverage in the
section purpose, and omit the standalone section and its page allocation. The internal name remains
`conclusion` whether its title is `Conclusion` or `Conclusion and Limitations`.
The validator checks placement; manuscript review checks substantive coverage and venue compliance.

## `content_architecture` visual evidence

Every schema-v3 accepted-result architecture includes an empirical visual-evidence contract in
addition to its venue-bound length, proof-detail, proof-appendix, and main-text mathematics plans:

```json
{
  "schema_version": 3,
  "visual_evidence_plan": {
    "empirical_claim_ids": ["TH-1"],
    "empirical_section": "numerical_separation",
    "empirical_question": "How does the theorem-predicted separation vary with sample size?"
  }
}
```

`empirical_claim_ids` is the complete set of selected statements classified as empirically testable;
no selected statement may remain deferred in the completed full-paper strategy. A non-empty set
requires a planned main section whose `evidence_types` include both `empirical` and `visual`, plus a
non-empty scientific question. An empty set requires `empirical_section` and `empirical_question` to
be `null`. Table design is handled during manuscript writing and review rather than in this artifact.

## `empirical_validation`

The post-theory empirical artifact uses adaptive experiment selection:

```json
{
  "schema_version": 2,
  "status": "completed",
  "reason": "The selected tests probe the main prediction and strongest reviewer risk.",
  "strategy": {
    "objective": "...",
    "selection_criteria": ["claim relevance", "falsification value", "feasibility"],
    "reviewer_risks": ["..."],
    "candidate_experiments": [
      {
        "id": "EXP-1",
        "claim_ids": ["TH-1"],
        "purpose": "...",
        "expected_information": "...",
        "feasibility": "...",
        "selected": true,
        "decision_reason": "..."
      }
    ],
    "selected_experiment_ids": ["EXP-1"],
    "claim_coverage": [
      {
        "claim_id": "TH-1",
        "status": "selected",
        "experiment_ids": ["EXP-1"],
        "rationale": "The experiment directly tests the theorem-predicted phenomenon."
      },
      {
        "claim_id": "TH-2",
        "status": "not_empirically_testable",
        "experiment_ids": [],
        "rationale": "The claim is a proof-level structural statement."
      }
    ]
  },
  "experiments": [
    {
      "id": "EXP-1",
      "claim_ids": ["TH-1"],
      "status": "evaluated",
      "evaluation": {"verdict": "supports", "raw_results_sha256": "..."}
    }
  ],
  "coverage_tags": ["scaling"],
  "limitations": ["..."],
  "figures": [
    {
      "figure_id": "FIG-0001",
      "experiment_id": "EXP-1",
      "role": "main",
      "status": "publication_ready",
      "latex_snippet_path": "figures/fig-0001.tex"
    }
  ],
  "evidence_registry_sha256": "..."
}
```

Experiment types and tags are flexible. Every selected experiment must connect accepted claims to a
theory prediction, design, falsification criteria, uncertainty, raw-result hash, verdict, and
claim-bounded interpretation. The completed strategy's selected claims must exactly equal
`visual_evidence_plan.empirical_claim_ids`; every other selected statement is
`not_empirically_testable`. `deferred` is permitted during candidate planning but not in the final
full-paper artifact. A `completed` or `contradictory` artifact requires publication-ready main
figures collectively covering every declared testable claim. `not_required` is used when none is
testable, and `blocked` only when every selected experiment records an honest blocker. Tables remain
an optional manuscript-writing decision rather than an empirical artifact requirement. See
`empirical-evidence.md` for the complete contracts. Status is `not_required`, `planned`,
`completed`, `contradictory`, or `blocked`.

## `literature_audit` manuscript coverage

Schema version 2 adds a deterministic manuscript-coverage gate. `coverage_assessment` records
`area_maturity`, an `area_maturity_rationale` about the surrounding literature rather than the
surviving theorem, `target_reference_count`, `reference_count`, at least three `search_themes`, at
least three `closest_work_record_ids`, `search_protocol`, and `status: adequate`. Mature areas and
original-conference research goals require at least 20 relevant references; every other paper
requires at least 15. There is no shortfall waiver. `search_protocol` binds at least three structured
query IDs across two sources, at least two completed structured searches, at least two independent
web queries, and a triage summary. Every closest-work record must be primary-source theorem verified.

`closest_work_comparisons` contains exactly one record for every closest-work ID with
`prior_result`, `prior_assumptions`, `our_difference`, and `remaining_overlap`. These records ground
the Introduction and Related Work comparison instead of leaving positioning to memory.

## `writing_exemplars`

The pre-writing exemplar stage produces `paper/writing_exemplars.json`. A submission-framed paper
requires three to six distinct audited papers whose full text was inspected. Every exemplar records
its selection reason, analyzed sections, and structural observations. `cross_paper_patterns` covers
the abstract, introduction, related work, result exposition, transitions, and visual presentation.
The artifact also records adopted principles and the required safeguards
`no_sentence_copying`, `no_author_style_imitation`, and `cite_borrowed_technical_ideas`.

The content architecture binds to this artifact by SHA-256. Exemplars influence exposition and
organization only; they cannot modify accepted theory or serve as uncited technical evidence.

## `venue_selection`

The venue-formatting stage produces `paper/venue_selection.json` after reading the hash-bound
candidate set from `venue_tools.py candidates`. The controller does not name, score, or rank a
venue. The venue-formatting agent compares at least three locally stageable candidates when
available and selects one through scholarly judgment grounded in the persisted contribution,
theorem and proof burden, empirical evidence, page and appendix needs, and template/rule status.

Schema version 3 records `selection_method: agent_comparative_judgment`, the exact
`candidate_set_sha256`, `considered_venues`, five textual `decision_factors`, a nonempty
`selection_rationale`, and `order_invariance_attestation: true`. Every considered venue records its
compatibility, selection status, fit summary, strengths, limitations, and evidence references.
Exactly one compatible venue is selected. The staged `venue_snapshot` must match that venue and pass
package-integrity checks. Submission-ready routes additionally require verified, fresh official
rules; full-paper routes use a named scholarly venue, while evidence reports use the neutral format.

## `theory_bundle`

Do not write this artifact manually. Complete the final stage with actor `controller`; the
controller composes schema version 5 from proofs, adversarial audits, synthesis, Arbiter decisions,
the independent novelty and significance audits, and contribution assessment. It derives `paper_route`; no agent writes
or promotes that route manually. The bundle separates `accepted_statements`,
`retained_nonfinal_statements`, and `excluded_statements`. Only `invalid` decisions or unresolved
fatal mathematical findings are excluded; repair candidates, conjectures, and unresolved/deferred
statements remain visible but cannot be presented as established results.

Every accepted `effective_statement` includes a deterministic `assumption_closure` containing the
complete discovery text and the proof obligations that require it, plus `standalone_formal`, which
combines that closure with the governed claim. Downstream reports and manuscripts must use the
standalone form so proof-level conditions cannot disappear during summarization.

The bundle also includes `refinement`: lineage depth, a progress vector, the next governed action,
and a bounded stopping rule for immutable child repair or contribution-extension runs.
