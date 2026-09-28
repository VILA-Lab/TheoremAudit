---
name: literature-search
description: "Comprehensive hybrid literature search for prior work that conflicts with or subsumes theorem candidates. Combines arXiv, Semantic Scholar, OpenReview, JMLR, and PMLR adapters with independent web search. Ground-truth only — no memory citations allowed. Called by Literature Lead in the Attack Team."
version: 4.0
used_by: literature_lead
domain: theoretical machine learning
inputs: discovery.json
outputs: novelty_conflicts (via flag_novelty_conflict tool)
scripts:
  - scripts/search_arxiv.py        # arXiv REST API — primary source
  - scripts/fetch_paper.py         # fetch abstract + theorem section from a paper
  - scripts/search_semantic.py     # Semantic Scholar — indexes all venues
  - scripts/search_openreview.py   # OpenReview — NeurIPS/ICLR/ICML/COLT
  - scripts/search_jmlr.py         # JMLR + PMLR — journals and conference proceedings
  - scripts/chase_citations.py     # follow citation trails from relevant papers
---

# Literature Search Skill

## Purpose

Identify prior work that conflicts with, subsumes, or materially overlaps with the paper's theorem candidates or committed mathematical claims.

This is a novelty/conflict-detection skill, not the final related-work bibliography builder. Conflict detection asks whether the proposed theorem already exists or is subsumed by prior work. Final bibliography construction is handled separately by `related-work-search`.

A theorem that already exists, even under different notation or in another venue, is not a contribution. This skill therefore performs a systematic, ground-truth-only, multi-source search before major proof work begins.

## Strict rule — no memory citations

Never name, cite, or flag any paper unless it was fetched from a real URL during this run or appeared in trusted pipeline context with a URL.

Do not rely on training knowledge of what papers exist. Do not assume a paper exists without verifying it. Even famous papers must be searched for and fetched before they can be referenced.

All six adapters return `literature_record.v1` objects. Preserve their canonical identifiers,
retrieval provenance, raw-response hashes, venue/version fields, and verification states when
combining structured search with independent web search. Normalize web-search discoveries into the
same schema before deduplication. Only primary-source inspection may advance a record to
`primary_source_verified`.

If you cannot provide a URL that was actually fetched or returned by a trusted search source, you cannot name the paper.

## Critical distinction — topic overlap vs. idea-level overlap

Topic overlap is not a novelty conflict.

Examples of topic overlap:

* a paper studies the same broad model class;
* a paper uses the same proof technique;
* a paper analyzes the same general area;
* a paper shares keywords with the proposal.

Idea-level overlap is a potential novelty conflict.

Examples of idea-level overlap:

* a paper proves a bound for the same mathematical object under comparable or weaker assumptions;
* a paper establishes the same separation, lower bound, impossibility result, or characterization;
* a paper's theorem subsumes the current theorem candidate after translating notation;
* a paper proves the same qualitative phenomenon in the same regime.

Do not flag topic overlap. Only flag after reading enough of the paper to compare the theorem statement, assumptions, conclusion, and regime.

## Source coverage

Use multiple sources because theoretical ML prior work appears across preprints, proceedings, journals, OpenReview submissions, and older venue archives.

| Source                   | Script/tool                      | What it covers                                          | Why it matters                     |
| ------------------------ | -------------------------------- | ------------------------------------------------------- | ---------------------------------- |
| arXiv relevance search   | `search_arxiv.py`                | cs.LG, stat.ML, math.ST, cs.IT and related preprints    | Primary source for recent theory   |
| arXiv date-sorted search | `search_arxiv.py --sort_by date` | recent preprints                                        | Catches new work                   |
| Semantic Scholar         | `search_semantic.py`             | broad scholarly index                                   | Finds papers outside arXiv         |
| OpenReview               | `search_openreview.py`           | ICLR, NeurIPS, ICML, COLT and workshops where available | Catches submissions and reviews    |
| JMLR/PMLR                | `search_jmlr.py --include_pmlr`  | JMLR, ICML, AISTATS, COLT proceedings                   | Foundational and conference theory |
| independent web search   | `web_search`                     | general web, authors, venues, citation paths             | Finds papers missed by adapters    |

If a script is unavailable, fails, times out, or returns malformed output, record that source as unavailable and continue with the remaining sources. Do not fabricate coverage for a failed source.

## Available scripts

**HOW TO RUN THEM:** you do not have a shell. Invoke every script below through the
`run_search_script` tool — pass the script name (no path/extension) and its args as a string:
```
run_search_script(script="search_arxiv",   args="--query '...' --theory --max_results 10 --pretty")
run_search_script(script="fetch_paper",     args="--id [ID] --full --max_chars 12000 --pretty")
run_search_script(script="search_semantic", args="--query '...' --max_results 10 --pretty")
run_search_script(script="search_openreview", args="--query '...' --max_results 10 --pretty")
run_search_script(script="search_jmlr",     args="--query '...' --include_pmlr --max_results 10 --pretty")
run_search_script(script="chase_citations", args="--arxiv_id [ID] --topic '...' --max_results 15 --pretty")
```
The `python skills/.../foo.py …` blocks below show each script's arguments; translate them
into a `run_search_script(script="foo", args="…")` call. Run independent web searches in addition
to the adapters for the core mathematical fingerprint; do not reserve web search only for adapter
failure.

### `search_arxiv.py`

```bash
python skills/literature-search/scripts/search_arxiv.py \
  --query "effective dimension kernel ridge regression" \
  --theory --max_results 10 --pretty
```

```bash
python skills/literature-search/scripts/search_arxiv.py \
  --query "benign overfitting kernel interpolation" \
  --sort_by date --recent 24 --max_results 10 --pretty
```

```bash
python skills/literature-search/scripts/search_arxiv.py \
  --id 2301.13812 --pretty
```

### `fetch_paper.py`

```bash
python skills/literature-search/scripts/fetch_paper.py \
  --id 2301.13812 --pretty
```

```bash
python skills/literature-search/scripts/fetch_paper.py \
  --id 2301.13812 --full --max_chars 12000 --pretty
```

### `search_semantic.py`

```bash
python skills/literature-search/scripts/search_semantic.py \
  --query "kernel interpolation generalization misspecification" \
  --max_results 10 --year_from 2018 --pretty
```

### `search_openreview.py`

```bash
python skills/literature-search/scripts/search_openreview.py \
  --query "kernel regression spectral bound" --max_results 10 --pretty
```

```bash
python skills/literature-search/scripts/search_openreview.py \
  --query "benign overfitting" --venue NeurIPS --year_from 2021 --pretty
```

### `search_jmlr.py`

```bash
python skills/literature-search/scripts/search_jmlr.py \
  --query "Rademacher complexity kernel" --max_results 10 --pretty
```

```bash
python skills/literature-search/scripts/search_jmlr.py \
  --query "source condition kernel regression" \
  --include_pmlr --max_results 10 --pretty
```

```bash
python skills/literature-search/scripts/search_jmlr.py \
  --query "generalization bounds kernel machines" \
  --year_from 2000 --year_to 2015 --max_results 10 --pretty
```

### `chase_citations.py`

```bash
python skills/literature-search/scripts/chase_citations.py \
  --arxiv_id 2301.13812 \
  --topic "kernel regression spectral effective dimension" \
  --max_results 15 --pretty
```

### Independent `web_search` coverage

For every novelty audit, use web search as a complementary retrieval lane unless web access is
unavailable. Do not merely repeat the adapter query. Search alternative terminology, theorem
conclusions, author or venue paths, and references/citations of the closest candidates. Record a
coverage gap if web search is unavailable.

Examples:

```text
"[query] site:arxiv.org OR site:openreview.net OR site:jmlr.org"
"[theorem topic] NeurIPS 2024 2023 paper"
"[author name] [topic] generalization bound"
"[theorem type] [mathematical object] theory paper"
```

Fetch promising URLs before using them as evidence.

## Step-by-step instructions

### Step 1 — Extract the mathematical fingerprint

Do not search only for the high-level claim. Search for the mathematical objects, regimes, assumptions, and conclusions.

From `discovery.json` and `theorem_state.json` if available, extract:

* mathematical objects;
* notation and key symbols;
* definitions;
* assumptions;
* theorem or lemma conclusions;
* proof techniques;
* known dependencies or acknowledged prior families;
* `novelty_hypothesis.search_queries`, if available;
* `novelty_hypothesis.suspected_gap`, if available;
* `novelty_hypothesis.likely_related_areas`, if available;
* `novelty_hypothesis.closest_known` or user-provided closest prior work, if available.

If `closest_known` exists, search it directly first. If it does not exist, do not invent one.

Illustrative example for a kernel regression project:

```text
effective dimension, source condition, RKHS, kernel integral operator,
ridgeless interpolation, spectral alignment, residual misspecification,
minimum-norm interpolation, eigenvalue decay
```

This example is illustrative only. Use the actual paper's mathematical fingerprint.

### Step 2 — Generate targeted queries

Generate 7–10 targeted queries when the topic is broad or mature. For a narrow topic, fewer may be enough if the summary explains why.

Cover different angles:

* mathematical object queries;
* assumption/regime queries;
* theorem-conclusion queries;
* proof-technique queries;
* closest-known or user-provided prior work, if available;
* recent-work queries;
* classic/foundational queries.

Use `novelty_hypothesis.search_queries` when available, but add your own query variants if needed.

Do not generate several cosmetic variants of the same query.

### Step 3 — Search sources using tiered coverage

Use thorough but non-wasteful source coverage.

For the core mathematical fingerprint and highest-value queries, search the main sources:

1. arXiv relevance search;
2. arXiv date-sorted recent search;
3. Semantic Scholar;
4. OpenReview;
5. JMLR/PMLR.

For the core fingerprint and highest-value theorem targets, also run independent web searches using
different wording from the adapter queries. At minimum, include one theorem/conclusion query and one
alternative-terminology or venue/author query unless web search is unavailable. Search more when the
area is mature or the first two lanes disagree.

For lower-value or redundant queries, stop once results become repetitive. Do not spend the whole budget on near-duplicate searches.

At minimum, for the overall topic, ensure that arXiv, Semantic Scholar, OpenReview, and JMLR/PMLR have each been checked at least once unless the corresponding script/tool is unavailable.

Do not conclude that no close prior work exists from structured adapters or web search alone. Merge
and deduplicate both candidate pools before triage. If one lane is unavailable or both return shallow
coverage, state that novelty remains unverified.

Deduplicate by arXiv ID, DOI, URL, or normalized title + year.

### Step 4 — Fetch candidate papers before judging

A search result is not enough to establish a conflict.

For each promising candidate, fetch at least the abstract or landing page. For close candidates, fetch the theorem/results section or enough of the paper to compare:

* assumptions;
* theorem statement;
* conclusion;
* regime;
* proof technique;
* whether the result is upper bound, lower bound, separation, characterization, impossibility, or construction.

For arXiv papers, use `fetch_paper.py` when available. Its `fulltext_extracted` status means only
that readable text was acquired; it does not verify a theorem. For non-arXiv papers, use the fetched
venue/publisher/OpenReview/JMLR/PMLR page or PDF landing page. If extraction reports
`extraction_failed`, retain the metadata lead but do not treat its theorem as checked.

Do not score overlap from title alone.

### Step 5 — Abstract triage

For every paper in the candidate pool, read the abstract or available summary.

Keep papers for deeper reading if they appear to prove a result about the same mathematical object, regime, or theorem type.

Discard papers that only share broad topic, keywords, or generic methods.

Target 5–20 papers passing triage, depending on the maturity of the area. Do not pad with topic-overlap papers just to hit a number. If fewer than five genuinely relevant papers exist after broad search, explain this in the summary.

### Step 6 — Deep reading of surviving papers

For every paper passing triage, fetch the theorem/results section when possible.

Extract:

* formal or informal assumption set;
* theorem statement and quantifiers;
* regime;
* conclusion;
* proof technique;
* whether it covers, partially overlaps with, or differs from the current theorem candidate.

Compare against the current theorem candidates, assumptions, and controlling statement forms in `theorem_state`.

If `theorem_state` is unavailable, compare against the theorem candidates and assumptions in `discovery.json`.

### Step 7 — Citation chasing for the most relevant papers

For the most relevant fetched papers, follow citation trails when tooling is available.

Default: chase citations for up to the top 3 most relevant papers.

If no paper is close enough to justify citation chasing, skip and explain why.

Add relevant cited or citing papers to the candidate pool, then triage and deep-read them as needed.

### Step 8 — Check lemmas as known results

For each planned lemma or supporting claim, search for whether it is already a standard result.

If a lemma is known, this is not necessarily a novelty conflict. It may simply need citation.

Flag only when the manuscript appears to claim a known lemma as a new contribution.

### Step 9 — Score idea-level overlap

Score overlap only after reading enough of the paper to compare the statement.

Use:

| Overlap score     | Meaning                                                              |
| ----------------- | -------------------------------------------------------------------- |
| `identical`       | Same assumptions and same conclusion after notation translation      |
| `subsumes`        | Prior work has weaker assumptions and same or stronger conclusion    |
| `partial-overlap` | Overlaps in regime, conclusion, or assumptions but leaves a real gap |
| `same-technique`  | Same proof tools but different result; not a conflict                |
| `weaker-version`  | Prior work proves a weaker version; current claim may still be novel |

Conservative scoring rules:

* unsure between low and medium → choose low;
* unsure between medium and high → choose medium;
* mark high or fatal only when the theorem statement genuinely covers the same ground after reading it.

### Step 10 — Call `flag_novelty_conflict`

Call `flag_novelty_conflict` for every medium, high, major, or fatal overlap according to the tool's accepted severity schema.

Each flag must include:

* paper title;
* URL;
* overlap score;
* exact overlapping theorem/result, if identified;
* comparison of assumptions;
* comparison of conclusion;
* `gap_remaining` in one clear sentence;
* recommended action: cite, reposition, weaken, abandon, or distinguish.

If you cannot state the remaining gap in one sentence, the gap may not be real.

Do not flag `same-technique` alone as a conflict.

### Step 11 — Summary

Report:

* sources searched and queries run;
* sources unavailable or failed;
* papers found, triaged, and deep-read;
* citation chasing performed or skipped;
* conflicts flagged by severity;
* whether the novelty hypothesis survives as stated;
* recommended repositioning if conflicts exist.

## Quality checklist

* No paper named without a fetched URL or trusted pipeline URL.
* Mathematical objects and theorem forms were searched, not only the high-level claim.
* `novelty_hypothesis.search_queries` were used when available.
* `closest_known` was searched directly only if it existed.
* Multiple source types were checked, or unavailable sources were explicitly recorded.
* Independent web queries used different terminology or retrieval paths from the adapter queries, or web unavailability was recorded.
* Structured and web candidate pools were merged and deduplicated before novelty conclusions.
* arXiv date-sorted search was used for at least the core/recent queries unless unavailable.
* JMLR/PMLR was checked for foundational or proceedings results unless unavailable.
* Search results were fetched before being used as evidence.
* Topic overlap was not flagged as conflict.
* Theorem-level overlap was scored only after reading enough of the result.
* All genuinely relevant papers found by the search were triaged.
* Citation chasing was done for the most relevant papers when useful and available.
* Lemmas were checked as potential known results when they are claimed as contributions.
* Every novelty flag has `gap_remaining` in one sentence.
* Summary states whether the novelty hypothesis survives.

## What NOT to do

* Do not name or cite any paper without fetching it or having a trusted pipeline URL.
* Do not flag topic overlap as a conflict.
* Do not score overlap from title alone.
* Do not skip date-sorted recent search for core queries unless unavailable.
* Do not skip JMLR/PMLR for foundational searches unless unavailable.
* Do not pretend unavailable or failed sources were searched.
* Do not mark overlap fatal if a clear gap remains.
* Do not flag `same-technique` as a conflict.
* Do not conclude "no conflict" from a shallow search.
* Do not treat web search as optional merely because an adapter returned results.
* Do not treat an adapter result list as comprehensive merely because it is nonempty.
* Do not fabricate closest prior work, citation keys, titles, authors, venues, years, or URLs.
