#!/usr/bin/env python3
"""
search_semantic.py
Search Semantic Scholar using the free public API.
No API key required for basic search (rate limited to ~100 req/5min).

Usage:
    python search_semantic.py --query "kernel regression generalization bound" --max_results 10
    python search_semantic.py --query "benign overfitting interpolation" --year_from 2020
    python search_semantic.py --paper_id "204e3073870fae3d05bcbc2f6a8e263d9b72e776"

Output JSON:
    [
        {
            "paper_id": "...",
            "title": "...",
            "authors": ["..."],
            "year": 2023,
            "abstract": "...",
            "venue": "...",
            "citation_count": 42,
            "url": "https://www.semanticscholar.org/paper/...",
            "arxiv_id": "2301.13812",
            "arxiv_url": "https://arxiv.org/abs/2301.13812"
        }
    ]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from record_schema import make_record


SS_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SS_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"

FIELDS = "title,abstract,year,venue,authors,externalIds,citationCount,url"

HEADERS = {
    "User-Agent": "TheoremAudit/1.0 (research agent)",
    "Accept": "application/json",
}


def fetch_json(url, retries=3):
    """Fetch JSON from a URL with retry logic."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 10 * (attempt + 1)  # SS is aggressive with rate limiting
                print(f"[search_semantic] Rate limited. Waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"Request failed: {e}")


def parse_paper(item, query=""):
    """Parse a Semantic Scholar paper object into a structured dict."""
    if not item:
        return None

    authors = [
        a.get("name", "").strip()
        for a in (item.get("authors") or [])
        if a.get("name")
    ]

    ext = item.get("externalIds") or {}
    arxiv_id = ext.get("ArXiv") or ext.get("arxiv") or ""
    doi = ext.get("DOI") or ""

    landing_url = item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}"
    return make_record(
        adapter="search_semantic",
        provider="semantic_scholar",
        source_type="scholarly_index",
        title=(item.get("title") or "").strip(),
        authors=authors,
        year=item.get("year"),
        venue=(item.get("venue") or "").strip(),
        abstract=(item.get("abstract") or "").strip(),
        landing_url=landing_url,
        arxiv_id=arxiv_id,
        doi=doi,
        semantic_scholar_id=item.get("paperId", ""),
        query=query,
        raw_response=item,
        verification_status="lead",
        is_primary=False,
        metrics={"citation_count": item.get("citationCount", 0)},
        metadata={"arxiv_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""},
    )


def search_semantic(query, max_results=10, year_from=None, year_to=None):
    time.sleep(1.0)  # Be polite to SS API
    """Search Semantic Scholar by keyword."""
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": FIELDS,
    }

    if year_from or year_to:
        y_from = str(year_from) if year_from else ""
        y_to = str(year_to) if year_to else ""
        params["year"] = f"{y_from}-{y_to}"

    url = f"{SS_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    data = fetch_json(url)

    if not data:
        return []

    results = []
    for item in data.get("data", []):
        parsed = parse_paper(item, query)
        if parsed and parsed["bibliographic"]["title"]:
            results.append(parsed)

    return results


def fetch_paper_by_id(paper_id):
    """Fetch a specific paper by Semantic Scholar paper ID."""
    url = f"{SS_PAPER_URL}/{paper_id}?fields={FIELDS}"
    data = fetch_json(url)
    if not data:
        return None
    return parse_paper(data)


def main():
    parser = argparse.ArgumentParser(
        description="Search Semantic Scholar and return structured JSON results."
    )
    parser.add_argument("--query", "-q", type=str, help="Search query")
    parser.add_argument("--paper_id", type=str, help="Fetch specific paper by Semantic Scholar ID")
    parser.add_argument("--max_results", "-n", type=int, default=10)
    parser.add_argument("--year_from", type=int, help="Filter papers from this year")
    parser.add_argument("--year_to", type=int, help="Filter papers up to this year")
    parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args()

    if not args.query and not args.paper_id:
        parser.error("Provide --query or --paper_id")

    try:
        if args.paper_id:
            result = fetch_paper_by_id(args.paper_id)
            results = [result] if result else []
        else:
            results = search_semantic(
                query=args.query,
                max_results=args.max_results,
                year_from=args.year_from,
                year_to=args.year_to,
            )
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
