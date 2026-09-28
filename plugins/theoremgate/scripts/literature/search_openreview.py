#!/usr/bin/env python3
"""
search_openreview.py
Search OpenReview for papers at NeurIPS, ICLR, ICML, COLT, AISTATS.
Uses the public OpenReview API — no key required.

Critical for theory papers because:
- NeurIPS/ICLR/ICML theory track papers appear here before arXiv
- Workshop papers that precede full submissions
- Papers under review that may conflict with novelty

Usage:
    python search_openreview.py --query "kernel regression generalization bound" --max_results 10
    python search_openreview.py --query "benign overfitting interpolation" --venue NeurIPS --max_results 10
    python search_openreview.py --query "effective dimension kernel" --year_from 2021

Output JSON:
    [
        {
            "openreview_id": "abc123",
            "title": "...",
            "authors": ["..."],
            "year": 2023,
            "venue": "NeurIPS 2023",
            "abstract": "...",
            "url": "https://openreview.net/forum?id=abc123",
            "arxiv_id": "...",
            "arxiv_url": "..."
        }
    ]
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


OR_SEARCH_URL = "https://api.openreview.net/notes/search"
OR_NOTES_URL = "https://api.openreview.net/notes"

HEADERS = {
    "User-Agent": "TheoremAudit/1.0 (research agent)",
    "Accept": "application/json",
}

# Top theory venues on OpenReview
THEORY_VENUES = [
    "NeurIPS",
    "ICLR",
    "ICML",
    "COLT",
    "AISTATS",
    "TMLR",
]


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"[search_openreview] Rate limited. Waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code in (404, 400):
                return None
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"Request failed: {e}")


def extract_arxiv_id(content):
    """Try to find arXiv ID in paper content fields."""
    for field in ["code", "pdf", "html", "_bibtex"]:
        val = content.get(field, "") or ""
        if isinstance(val, dict):
            val = str(val)
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([\w.\-]+)", str(val))
        if m:
            return m.group(1)
    return ""


def parse_note(note, query=""):
    """Parse an OpenReview note into a structured dict."""
    content = note.get("content") or {}

    # Handle both old API (values directly) and new API (values in dicts)
    def get_field(key):
        val = content.get(key, "")
        if isinstance(val, dict):
            return val.get("value", "")
        return val or ""

    title = get_field("title")
    abstract = get_field("abstract")
    venue = get_field("venue") or note.get("venue", "")

    # Authors
    authors_raw = content.get("authors", [])
    if isinstance(authors_raw, dict):
        authors_raw = authors_raw.get("value", [])
    authors = [str(a).strip() for a in authors_raw if a]

    # Year from venue or cdate
    year = None
    year_match = re.search(r"\b(20\d{2})\b", str(venue))
    if year_match:
        year = int(year_match.group(1))
    elif note.get("cdate"):
        try:
            import datetime
            year = datetime.datetime.fromtimestamp(note["cdate"] / 1000).year
        except Exception:
            pass

    note_id = note.get("id", "")
    arxiv_id = extract_arxiv_id(content)

    landing_url = f"https://openreview.net/forum?id={note_id}"
    return make_record(
        adapter="search_openreview",
        provider="openreview",
        source_type="review_platform",
        title=title.strip(),
        authors=authors,
        year=year,
        venue=str(venue).strip(),
        abstract=str(abstract).strip(),
        landing_url=landing_url,
        arxiv_id=arxiv_id,
        openreview_id=note_id,
        query=query,
        raw_response=note,
        verification_status="metadata_fetched",
        is_primary=True,
        metadata={"arxiv_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""},
    )


def search_openreview(query, max_results=10, venue=None, year_from=None):
    """Search OpenReview by keyword, optionally filtering by venue."""

    params = {
        "term": query,
        "content": "all",
        "source": "forum",
        "offset": 0,
        "limit": min(max_results * 2, 50),  # fetch extra to allow filtering
    }

    if venue:
        params["venue"] = venue

    url = f"{OR_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    data = fetch_json(url)

    if not data:
        # Try alternate endpoint
        params2 = {
            "content.title": query,
            "limit": min(max_results, 25),
            "offset": 0,
        }
        url2 = f"{OR_NOTES_URL}?{urllib.parse.urlencode(params2)}"
        data = fetch_json(url2)

    if not data:
        return []

    notes = data.get("notes", []) or data.get("data", []) or []

    results = []
    for note in notes:
        try:
            parsed = parse_note(note, query)
            bibliography = parsed["bibliographic"]
            if not bibliography["title"]:
                continue

            # Filter by year if specified
            if year_from and bibliography["year"] and bibliography["year"] < year_from:
                continue

            # Filter to theory venues if no specific venue given
            if not venue:
                note_venue = bibliography["venue"].lower()
                is_theory_venue = any(v.lower() in note_venue for v in THEORY_VENUES)
                if not is_theory_venue:
                    continue

            results.append(parsed)
            if len(results) >= max_results:
                break

        except Exception as e:
            print(f"[search_openreview] Warning: failed to parse note: {e}", file=sys.stderr)
            continue

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Search OpenReview for theory papers at top ML venues."
    )
    parser.add_argument("--query", "-q", type=str, required=True, help="Search query")
    parser.add_argument("--max_results", "-n", type=int, default=10)
    parser.add_argument(
        "--venue",
        type=str,
        default=None,
        help="Filter by venue e.g. NeurIPS, ICLR, ICML, COLT"
    )
    parser.add_argument("--year_from", type=int, help="Only return papers from this year onward")
    parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args()

    try:
        results = search_openreview(
            query=args.query,
            max_results=args.max_results,
            venue=args.venue,
            year_from=args.year_from,
        )
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
