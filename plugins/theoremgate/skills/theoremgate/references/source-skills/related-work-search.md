---
name: related-work-search
description: "Build the paper's related-work bibliography for the finalized contribution. Constructive rather than adversarial: find and save papers a reader expects to see cited, using save_reference. Run late, after the Arbiter has decided what survives, so citations position the actual committed contribution."
version: 1.1
used_by: paperworld_builder
inputs: committed decisions + committed statements + finalized contribution paragraph + novelty_conflicts already found
outputs: canonical records and usage in the run literature registry
----------------------------------------

# Related-Work Search — Build the Bibliography

## Purpose

Build the bibliography that a polished theoretical ML paper needs in order to position its finalized contribution.

This is different from novelty/conflict detection. Conflict detection asks whether the proposed result already exists. Related-work search asks what the final paper should cite so readers understand the problem, setting, technical lineage, closest prior results, and distinction from existing work.

Run this skill late, after the surviving contribution is known. Search for the finalized contribution, not the original ambitious plan.

## Source of search themes

Before searching, identify 3–5 themes from the finalized paper:

* the main mathematical setting;
* the method family or estimator;
* the closest prior theoretical phenomenon;
* the proof tools or technical lineage;
* empirical or numerical regime, if relevant.

Use committed statements, finalized contribution text, and surviving assumptions to form search queries. Do not search based on claims that were blocked, removed, or weakened away.

## Procedure

1. **Reuse carefully.**
   Inspect papers already present in `novelty_conflicts`. Save them only if they remain relevant to the finalized contribution. Minor or resolved overlaps may become related work. Major or fatal conflicts should be saved only if the final contribution has been reframed to clearly distinguish itself.

2. **Search by theme.**
   For each identified theme, run targeted searches for canonical papers, recent top-venue papers, closest technical prior work, and useful survey/background papers.
   Use the dedicated search scripts via the `run_search_script` tool for structured candidate
   retrieval:
   * `run_search_script(script="search_arxiv", args="--query '...' --max_results 10")`
   * `run_search_script(script="search_semantic", args="--query '...' --max_results 10")`
   * `run_search_script(script="search_openreview", args="--query '...' --max_results 10")`
   * `run_search_script(script="search_jmlr", args="--query '...' --include_pmlr")`
   * `run_search_script(script="chase_citations", args="--arxiv_id ... --topic '...'")`
   Independently use `web_search` for the main themes with alternative terminology, author/venue
   searches, and citation paths. Structured adapters and web search are complementary; a nonempty
   result from one does not establish complete coverage.

3. **Fetch before saving.**
   Save only papers whose URL was actually returned by search and successfully fetched. Do not cite papers from memory.
   Fetch with `run_search_script(script="fetch_paper", args="--id <arxiv_id>")` for arXiv
   papers, or `web_fetch` for non-arXiv landing pages.

4. **Save structured references.**
   Store each item as `literature_record.v1`, set `metadata.role`, and ingest it with
   `literature_tools.py` into the selected run registry. Register its purpose and cite it by
   canonical `record_id`. Preserve:

   * title
   * authors, if available
   * year, if available
   * venue, if available
   * URL
   * theme
   * relation to this paper
   * one-sentence reason for relevance

   Do not invent or manually assign `cite_key`; the registry creates a stable collision-safe key.

5. **Deduplicate.**
   Save each distinct paper once. If multiple URLs refer to the same paper, prefer the canonical abstract page or publisher page over raw PDFs.

## Target bibliography size

The finished paper's bibliography should contain **at least 15 distinct references, and
ideally 20–30** — a thorough related-work section for an established ML area. Treat 15 as a
floor to actively reach, not a ceiling.

* Mature, well-studied ML area: aim for **25–35** distinct references.
* Narrower or emerging area: aim for **15–25**.
* Never complete a paper below 15. If an initial pass finds fewer, broaden the query families,
  citation-chase the closest papers, and continue primary-source triage.

You are usually not starting from zero: papers already in `novelty_conflicts` count toward
this total, so reuse them first (save the still-relevant ones) and then top up by theme
until you reach the target.

Never fabricate, guess, or pad the bibliography to hit a number. Reach the floor by broadening the
relevant search rather than adding unrelated work.

The numerical floor is not the search objective. Do not stop when the validator's minimum is met,
and do not stop merely because the current registry is small. Search saturation is a signal to
change query decomposition and citation-chasing strategy, not a waiver of the manuscript floor.

## Search and fetch bounds

Be thorough but bounded.

* Use up to about 35 web searches and 45 fetches for mature areas.
* Use fewer calls for narrow topics once the relevant literature is exhausted.
* Fetch only URLs that appeared in search results.
* Do not guess or construct arXiv IDs.
* Prefer HTML abstract pages, official proceedings pages, OpenReview pages, Semantic Scholar pages, DBLP pages, or publisher pages.
* Avoid raw PDF URLs when an abstract or landing page is available.
* If a search is empty or a fetch fails, move on.
* Stop after three consecutive empty or irrelevant searches for a theme.

## Quality and relevance priorities

Prioritize references in this order:

1. closest prior theoretical results;
2. canonical papers in the setting;
3. papers introducing or analyzing the estimator/model family;
4. papers using closely related proof techniques;
5. recent top-venue papers that readers would expect;
6. surveys or background papers when useful;
7. peripheral applications only if they directly motivate the paper.

Do not over-collect loosely related papers.

## Hard rules

* No memory citations: only papers fetched from real URLs during this run may be saved.
* Do not save a paper only because it has a famous author or popular keyword.
* Do not cite fields that do not exist.
* Do not fabricate titles, authors, years, venues, URLs, or cite keys.
* Do not save duplicate papers under multiple cite keys.
* Do not save papers related only to abandoned, blocked, or removed claims.
* If no citable papers are genuinely found, leave `related_work` empty and let the writer produce an honest short related-work paragraph.

## Citation-key rule

Use the registry-generated key exactly. If a paper lacks enough metadata for a readable key, repair
its canonical record rather than inventing a parallel key in manuscript text.
