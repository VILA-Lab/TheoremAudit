---
name: venue-formatting
description: Select and apply packaged conference or journal templates to a TheoremAudit manuscript while preserving content and checking asset freshness. Use for PaperWorld-style venue selection, section structure, and LaTeX packaging.
---

# Venue Formatting

Read `../theoremgate/references/source-skills/paperworld.md` for the preserved venue-selection logic,
but treat PaperWorld as formatting guidance rather than a research stage. Templates are under
`../../assets/conference-templates/`.

Choose and stage the best-fit venue after literature audit and exemplar study but before content
architecture. Bind schema-v3 `paper/venue_selection.json` to the immutable theory bundle and the
completed exemplar study. Copy selected assets into the paper output; never edit the packaged
originals. The subsequent architecture binds to this venue-selection hash and derives its page plan
from the venue snapshot. Venue constraints control template, length, appendix placement, anonymity,
and compliance; accepted theory and scientific claims remain immutable.

Every packaged venue metadata file declares `page_limit_scope`: `main_text`,
`main_plus_references`, `total_manuscript`, or `none`. After architecture is written, validate its
schema-v3 page plan against that exact scope. For a hard main-text limit, set both
`target_main_pages` and `maximum_main_pages` to the full venue allowance and set
`minimum_main_pages` no lower than one page below it. Do not treat reference or appendix pages as
main-text pages when the official scope excludes them.

References continue after the Conclusion without a forced page break by default. Declare
`references_start_new_page: true` in venue metadata only when a verified venue rule requires a fresh
References page. A shared boundary page counts once for a combined main-plus-references limit.

Every venue metadata record declares `publication_format` as `conference`, `journal`, or `neutral`.
When a journal has `page_limit_scope: none`, do not invent a venue maximum or a minimum total page
count. Set `minimum_total_pages: null` and `minimum_main_pages: 10`; references and appendices do not
count toward that journal main-text floor. Inspect three to six matched full-text exemplars, record
their main/reference/appendix/total page profiles with exact PDF locators, and set
`target_main_pages` to the larger of 10 and the largest observed main-text length. That target guides
section allocation but underfilling it is not itself a review finding. A small layout tolerance may
raise `maximum_main_pages` by at most two pages. The plan separately records minimum and target
appendix pages and a reference-page ceiling. References precede the explicitly labeled appendix.
The neutral `Research-Draft` evidence-report format is not a journal and has no minimum page count.
Use an evidence-scoped provisional component plan, set all minimum page fields to `null`, and treat
targets as organization guidance rather than an underfill gate. Do not derive its length from
full-paper exemplars or pad it to a journal-style floor.
Template staging alone never satisfies a request to rewrite the manuscript.

Before submission or public distribution, verify the selected venue's current official template,
year, anonymity rules, page limits, checklist, and redistribution license. Keep these three statuses
distinct: package integrity, official-rule verification, and redistribution authorization. A
hash-complete local snapshot may be stageable while still being neither submission-ready nor cleared
for public redistribution.

Use `../../scripts/venue_tools.py list` to audit snapshots and `candidates --run RUN_ID` to obtain
the evidence-compatible candidate set. The candidate order is alphabetical for display only and
carries no preference. Independently compare three to five candidates, or every candidate when fewer
than three exist, against the persisted contribution, theorem/proof burden, empirical evidence,
length and appendix needs, and current template/rule status. Select the strongest scholarly fit by
reasoned agent judgment; do not use a hard-coded venue, numeric score, fixed ranking, or list position.
Then use `stage` to copy only the selected venue's declared LaTeX assets into the active paper run.
Treat any `error` or `fatal` integrity finding as a
staging blocker. The generated schema-v3 `venue_snapshot.json` records metadata and asset hashes,
audit findings, local integrity, official-rule status, submission readiness, and redistribution
status. Never change an unverified field to verified without primary-source evidence.

Persist `paper/venue_selection.json` with `selection_method: agent_comparative_judgment`, the exact
`candidate_set_sha256`, the candidates considered, concrete strengths and limitations, evidence
references, the five required decision factors, and `order_invariance_attestation: true`. Exactly one
considered candidate is selected. If validation rejects the decision, revise the venue analysis
automatically within the same stage; do not ask the researcher to choose.

For every `full_paper`, choose the best-fit named venue and stage its
locally integrity-checked template so the manuscript is written to a concrete venue standard.
Preserve unverified-rule, freshness, and redistribution warnings, and keep
`submission_ready: false` when evidence is incomplete; provisional formatting is not a claim of
venue eligibility or acceptance readiness. Use the packaged neutral `Research-Draft` only for an
`evidence_report`. Do not ask the researcher to choose a template.

When `submission_readiness` is `ready`, the selected snapshot must have `submission_ready: true`.
That field requires valid local integrity plus verified, fresh official rules. When the route is not
submission-ready, rule freshness remains a decision factor and warning but does not hard-code which
named full-paper venue the agent must select. Do not promote an unverified snapshot to
submission-ready and do not pause for a venue choice.

After staging, run `venue_tools.py verify`. Staging is transactional: every copied file is checked
against the audit hash before the venue directory is activated. Replacing or changing a staged venue
requires `--replace --reason`; the prior directory is moved to `paper/venue-history/` and stale files
do not leak into the new package. When `paper/venue_selection.json` exists, the staged venue must
match it. A verified-rules flag is submission-ready only while its ISO-dated primary-source check is
fresh; local package integrity remains a separate decision.
