#!/usr/bin/env python3
"""
chase_citations.py
Given a paper (by arXiv ID or Semantic Scholar ID), extract the papers
it cites that are relevant to a given topic.

This is the citation chasing step — the most important papers are often
not the ones you find directly but the ones that paper cites.

Usage:
    python chase_citations.py --arxiv_id 2301.13812 --topic "kernel regression generalization"
    python chase_citations.py --ss_id 204e3073870fae3d05bcbc2f6a8e263d9b72e776 --topic "benign overfitting"
    python chase_citations.py --arxiv_id 2301.13812 --topic "spectral methods" --max_results 10

Output JSON:
    {
        "source_paper": "2301.13812",
        "topic": "kernel regression generalization",
        "relevant_citations": [
            {
                "title": "...",
                "authors": ["..."],
                "year": 2020,
                "arxiv_id": "...",
                "arxiv_url": "...",
                "relevance_reason": "cited in related work section on kernel interpolation"
            }
        ]
    }
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from record_schema import make_record


SS_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"
HEADERS = {
    "User-Agent": "TheoremAudit/1.0 (research agent)",
    "Accept": "application/json",
}

REFERENCE_FIELDS = "title,year,authors,externalIds,abstract,citationCount"


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 10 * (attempt + 1)  # SS is aggressive with rate limiting
                print(f"[chase_citations] Rate limited. Waiting {wait}s...", file=sys.stderr)
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


def arxiv_to_ss_id(arxiv_id):
    """Resolve an arXiv ID to a Semantic Scholar paper ID."""
    url = f"{SS_PAPER_URL}/arXiv:{arxiv_id}?fields=paperId,title"
    data = fetch_json(url)
    if data and data.get("paperId"):
        return data["paperId"], data.get("title", "")
    return None, ""


def is_relevant(paper, topic_tokens):
    """Simple relevance check: does the paper's title+abstract contain topic keywords?"""
    text = (
        (paper.get("title") or "") + " " +
        (paper.get("abstract") or "")
    ).lower()

    # Count how many topic tokens appear
    matches = sum(1 for t in topic_tokens if t.lower() in text)
    return matches >= max(1, len(topic_tokens) // 3)


def tokenize_topic(topic):
    """Break topic into meaningful tokens."""
    # Remove common words
    stopwords = {"a", "an", "the", "in", "of", "for", "to", "and", "or", "with", "under", "via"}
    tokens = re.findall(r"[a-zA-Z0-9\-]{3,}", topic)
    return [t for t in tokens if t.lower() not in stopwords]


def chase_citations(ss_id, topic, max_results=15):
    """Fetch references of a paper and filter by topic relevance."""
    url = (
        f"{SS_PAPER_URL}/{ss_id}/references"
        f"?fields={REFERENCE_FIELDS}&limit=100"
    )
    data = fetch_json(url)
    if not data:
        return []

    topic_tokens = tokenize_topic(topic)
    references = data.get("data", [])

    relevant = []
    for ref in references:
        cited = ref.get("citedPaper") or {}
        if not cited.get("title"):
            continue

        ext = cited.get("externalIds") or {}
        arxiv_id = ext.get("ArXiv") or ext.get("arxiv") or ""

        paper = {
            "paper_id": cited.get("paperId", ""),
            "title": cited.get("title", "").strip(),
            "authors": [a.get("name", "") for a in (cited.get("authors") or [])],
            "year": cited.get("year"),
            "abstract": (cited.get("abstract") or "").strip(),
            "citation_count": cited.get("citationCount", 0),
            "arxiv_id": arxiv_id,
            "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
            "ss_url": f"https://www.semanticscholar.org/paper/{cited.get('paperId', '')}",
            "_raw_response": cited,
        }

        if is_relevant(paper, topic_tokens):
            # Add a brief relevance note
            matched_tokens = [t for t in topic_tokens if t.lower() in (paper["title"] + " " + paper["abstract"]).lower()]
            paper["relevance_reason"] = f"Matches topic tokens: {', '.join(matched_tokens[:5])}"
            relevant.append(paper)

        if len(relevant) >= max_results:
            break

    # Sort by citation count — more cited = more foundational
    relevant.sort(key=lambda x: x.get("citation_count", 0), reverse=True)
    records = []
    for paper in relevant[:max_results]:
        records.append(make_record(
            adapter="chase_citations",
            provider="semantic_scholar",
            source_type="citation_graph",
            title=paper["title"],
            authors=paper["authors"],
            year=paper["year"],
            abstract=paper["abstract"],
            landing_url=paper["arxiv_url"] or paper["ss_url"],
            arxiv_id=paper["arxiv_id"],
            semantic_scholar_id=paper["paper_id"],
            query=topic,
            raw_response=paper.pop("_raw_response"),
            verification_status="lead",
            is_primary=False,
            metrics={"citation_count": paper["citation_count"]},
            metadata={"relevance_reason": paper["relevance_reason"], "citation_source_id": ss_id},
        ))
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Chase citations from a paper and filter by topic relevance."
    )
    parser.add_argument("--arxiv_id", type=str, help="arXiv ID of the source paper")
    parser.add_argument("--ss_id", type=str, help="Semantic Scholar paper ID")
    parser.add_argument("--topic", type=str, required=True, help="Topic to filter citations by")
    parser.add_argument("--max_results", type=int, default=15, help="Max relevant citations to return")
    parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args()

    if not args.arxiv_id and not args.ss_id:
        parser.error("Provide --arxiv_id or --ss_id")

    try:
        ss_id = args.ss_id
        source_title = ""

        if args.arxiv_id and not ss_id:
            print(f"[chase_citations] Resolving arXiv ID {args.arxiv_id} to SS ID...", file=sys.stderr)
            ss_id, source_title = arxiv_to_ss_id(args.arxiv_id)
            if not ss_id:
                raise RuntimeError(f"Could not resolve arXiv ID {args.arxiv_id} to Semantic Scholar")

        relevant = chase_citations(ss_id, args.topic, args.max_results)

        result = {
            "source_paper": args.arxiv_id or args.ss_id,
            "source_title": source_title,
            "topic": args.topic,
            "relevant_citations": relevant,
            "total_found": len(relevant),
        }

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
