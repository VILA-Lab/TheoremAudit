---
name: literature-audit
description: Search, verify, deduplicate, and audit primary literature for theorem provenance, assumption mapping, novelty, related work, and citation integrity. Use whenever TheoremAudit needs literature evidence or paper citations.
---

# Literature Audit

Read `literature-search.md` and `related-work-search.md` under
`../theoremgate/references/source-skills/`. Use hybrid retrieval: run the structured adapters in
`../../scripts/literature/` and independently search the web with alternative terminology, theorem
forms, authors, venues, and citation paths. Neither channel is a fallback for the other. If either
channel is unavailable, record the coverage gap. Prefer papers and official proceedings over
summaries.

Read `../theoremgate/references/literature-record.md`. Preserve every result as
`literature_record.v1`; do not flatten away canonical identifiers, query provenance, retrieval time,
raw-response hash, source type, venue/version, verification state, or exact evidence.

For every cited result, record title, authors, venue/year, stable URL or identifier, exact theorem or
section, assumptions, conclusion, and how it supports the current claim. Never infer theorem support
from an abstract. Mark inaccessible or unverified sources; do not fabricate BibTeX fields.

For arXiv full text, prefer semantic HTML and use real PDF extraction only as fallback. Treat
`fulltext_extracted` as successful text acquisition, not theorem verification. Inspect the extracted
theorem and surrounding assumptions before recording `primary_source_verified`. If extraction fails
or looks incoherent, keep the metadata lead and mark its theorem support unverified.

Deduplicate across every canonical identifier and normalized title with
`../../scripts/citations.py`. Separate
provenance support, novelty neighbors, and contextual related work.

Use `../../scripts/literature_tools.py search-and-save` for allow-listed packaged adapters so the
exact adapter output, query arguments, response hash, and normalized records are retained under the
selected run. Use `ingest` for records obtained through independent web search, `register-use` every
time a paper supports a claim or manuscript section, and `export-bib` to generate deterministic
BibTeX. `run` is inspection-only and must not be the final path for evidence used by the workflow.
Treat retrieved metadata as leads until primary-source verification is complete.

`search-and-save` intentionally records broad retrieval as `discovery_candidate` unless an explicit
purpose is supplied. Promote only a deliberate theorem-level shortlist with `register-use`. If a
broad batch was mistakenly labeled `closest_work` or `novelty_neighbor`, use `curate-novelty` or
`reclassify-use`; these commands preserve the original usage link as reclassified audit history.
Never solve over-registration by deleting the registry or verifying dozens of irrelevant hits.

The run-level source of truth is `.theoremgate/runs/<run>/literature/registry.json`. Do not maintain
parallel informal paper lists. Resolve aliases to canonical `record_id` values and use the registry's
generated `citation_keys` in LaTeX. Before completing literature or manuscript work, run
`validate-registry` and `coverage`; explain every registered-but-unused paper and repair every used
record whose verification is too weak for its stated purpose.

For manuscript preparation, write schema-v2 coverage evidence. Classify the surrounding research
literature as mature, narrow, or emerging; never infer maturity from the breadth of the surviving
theorem or the eventual document route. Record an explicit `area_maturity_rationale`, at least three
search themes, and a `search_protocol` containing at least three structured query IDs across two
sources, at least two independent web queries, and a substantive triage summary. Set a hard minimum
of 20 references for mature areas and every original-conference research goal, and 15 otherwise; and
identify at least three closest technical works. For every closest
work, record its result, assumptions, exact difference from the accepted contribution, and remaining
overlap. Verify every closest work against primary theorem text. Do not pad the bibliography, but do
not bypass the minimum by declaring search saturation or by downgrading the document. Continue the
hybrid search and triage process until the relevant-source floor is met.

Identify three to six full-text papers suitable for the pre-writing exemplar study. Exemplar
suitability is separate from theorem support: choose clear and structurally relevant papers, but
require `fulltext_extracted` or `primary_source_verified` status before analyzing their prose structure.
For a run created before the registry existed, run `seed-theory` once before continuing.

Never infer comprehensive coverage from one query family, one ranking system, or one source. For a
novelty conclusion, preserve the structured queries and web queries used, deduplicate their union,
and fetch every close candidate from a primary source. If coverage or primary-source verification is
insufficient, use `unverified` rather than claiming that no conflict exists.
Incomplete verification must lower the novelty verdict, not strand the workflow. Finish the novelty
artifact with `unclear` classifications and an `unverified` verdict when necessary, record the exact
coverage limitation, and continue through significance, contribution assessment, and honest routing.

During the governed `novelty_audit` stage, classify every Arbiter-accepted statement exactly once.
Compare theorem text, assumptions, conclusions, constants, and scope—not titles or abstracts. Use
`novel`, `new_extension`, `new_counterexample`, `new_synthesis`, `new_empirical_evidence`,
`attributed`, `standard`, or `unclear`. Use `unverified` when primary sources cannot be checked.

Validator minima are integrity floors, not search targets. Never respond to a failed gate by adding
one convenient record, promoting an abstract page to theorem evidence, or constructing a compact
audit only from papers already in the registry. A `new_*` classification requires at least two
distinct primary-source-verified technical comparisons. If two genuine theorem-level comparisons
cannot be completed, classify the statement `unclear` and the overall verdict `unverified`; the
workflow continues to honest routing instead of manufacturing compliance.

Do not justify a bibliography shortfall. If fewer relevant papers have been retained than the hard
floor, continue searching with decomposed mathematical-object, theorem-form, assumption, method,
foundational, and recent-work queries. Preserve at least three structured query IDs across two
sources, at least two completed structured searches, two independent web queries, and the complete
triage summary even after the floor has been reached.

When a completed paper receives a request to expand citations, bibliography, closest-work evidence,
or Related Work coverage, route through `$research-revision` with `revise_literature`. Start that
plan so the controller archives and reopens the same paper at `literature_audit`. Never overwrite the
completed audit during `revision` or `section_writing`, and never reopen only the prose stages when
the audited source set must change.
