# Literature record v1

Every packaged literature adapter emits the same auditable object. Search-index metadata is a lead;
it is never silently converted into theorem evidence.

```json
{
  "schema_version": 1,
  "record_type": "literature_record",
  "record_id": "arxiv:2401.00001",
  "canonical_ids": {
    "arxiv": "2401.00001",
    "doi": "",
    "openreview": "",
    "semantic_scholar": ""
  },
  "source": {
    "provider": "arxiv",
    "source_type": "preprint",
    "landing_url": "https://arxiv.org/abs/2401.00001",
    "pdf_url": "https://arxiv.org/pdf/2401.00001",
    "is_primary": true
  },
  "bibliographic": {
    "title": "...",
    "authors": ["..."],
    "year": 2024,
    "venue": "",
    "version": "v2",
    "abstract": "..."
  },
  "retrieval": [{
    "adapter": "search_arxiv",
    "provider": "arxiv",
    "query": "...",
    "query_variant": "title_abstract",
    "retrieval_queries": ["..."],
    "retrieved_at": "2026-01-01T00:00:00+00:00",
    "result_url": "https://arxiv.org/abs/2401.00001",
    "raw_response_sha256": "..."
  }],
  "verification": {
    "status": "primary_source_verified",
    "verified_at": "2026-01-01T00:00:00+00:00",
    "evidence": [{
      "theorem": "Theorem 3",
      "section": "4.2",
      "pages": "8--10",
      "assumptions": ["..."],
      "conclusion": "...",
      "supports_claim_ids": ["TH-1"]
    }]
  },
  "metrics": {},
  "metadata": {"role": "novelty_neighbor"}
}
```

Allowed verification states are `lead`, `metadata_fetched`, `fulltext_extracted`,
`primary_source_verified`, and `extraction_failed`. Only `primary_source_verified` may support a
verified theorem comparison. It requires a primary source, a verification timestamp, an exact
theorem/section/page locator, and the supported conclusion. `fulltext_extracted` says only that text
was acquired successfully.

Deduplication clusters records transitively when they share any canonical identifier. Exact
normalized-title matching is a conservative fallback: conflicting years or disjoint known author
sets remain separate and are reported for review. Merging preserves all retrieval events, aliases,
and the strongest valid verification state.

Each run owns `.theoremgate/runs/<run>/literature/registry.json`. Besides canonical records it stores
stable generated citation keys, merge decisions, conflicts, query executions, exact adapter-output
hashes, and a usage ledger linking papers to stages, purposes, claim IDs, section IDs, source
artifacts, and evidence locators. Manuscript `citations_used` entries refer to canonical `record_id`;
LaTeX uses the corresponding registry key, and `references.bib` is generated from those records.
