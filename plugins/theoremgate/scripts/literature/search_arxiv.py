#!/usr/bin/env python3
"""
search_arxiv.py
Search arXiv using the free REST API and return structured JSON results.

Usage:
    python search_arxiv.py --query "effective dimension kernel regression" --max_results 10
    python search_arxiv.py --query "benign overfitting" --sort_by date --recent 24
    python search_arxiv.py --id 2301.13812
    python search_arxiv.py --query "kernel ridge" --theory --max_results 10
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from math import ceil

from record_schema import arxiv_version, make_record


ARXIV_API = "https://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

THEORY_CATEGORIES = ["cs.LG", "stat.ML", "math.ST", "cs.IT", "cs.CC", "stat.TH"]

QUERY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "for", "from", "how",
    "in", "is", "of", "on", "or", "the", "to", "under", "via", "when", "with",
}


def query_terms(query):
    """Return stable, meaningful terms used for query expansion and local reranking."""
    terms = re.findall(r"[a-z0-9][a-z0-9.\-]*", (query or "").lower())
    result = []
    for term in terms:
        if len(term) < 3 or term in QUERY_STOPWORDS or term in result:
            continue
        result.append(term)
    return result


def _quote_phrase(value):
    clean = re.sub(r'["\']', "", (value or "").strip())
    clean = re.sub(r"\s+", " ", clean)
    return f'"{clean}"' if clean else ""


def build_query_variants(query):
    """Build complementary arXiv queries dynamically from the supplied research query."""
    phrase = _quote_phrase(query)
    terms = query_terms(query)
    if not terms:
        return []

    variants = []
    if phrase:
        variants.append(("exact_phrase", f"all:{phrase}"))

    # Preserve recall with all meaningful terms while avoiding arXiv's ambiguous
    # interpretation of `all:term one term two`.
    variants.append(("all_terms", " AND ".join(f"all:{term}" for term in terms[:10])))

    # A smaller, high-signal variant rewards papers whose title or abstract contains
    # the mathematical fingerprint instead of matching incidental full-text metadata.
    focused = terms[:6]
    variants.append((
        "title_abstract",
        " AND ".join(f"(ti:{term} OR abs:{term})" for term in focused),
    ))

    # Deduplicate variants for very short queries.
    deduped = []
    seen = set()
    for name, value in variants:
        if value and value not in seen:
            seen.add(value)
            deduped.append((name, value))
    return deduped


def build_search_query(query=None, categories=None, date_from=None, date_to=None):
    """Build arXiv search_query string — NOT URL encoded (urlencode handles that)."""
    parts = []

    if query:
        variants = dict(build_query_variants(query))
        structured = variants.get("all_terms") or variants.get("exact_phrase")
        if structured:
            parts.append(structured)

    if categories:
        cat_query = " OR ".join([f"cat:{c}" for c in categories])
        parts.append(f"({cat_query})")

    if date_from or date_to:
        d_from = date_from or "19000101"
        d_to = date_to or datetime.now().strftime("%Y%m%d")
        parts.append(f"submittedDate:[{d_from}000000 TO {d_to}235959]")

    return " AND ".join(parts) if parts else "*:*"


def add_query_filters(search_query, categories=None, date_from=None, date_to=None):
    """Attach category and date filters to an already structured arXiv query."""
    parts = [search_query] if search_query else []
    if categories:
        parts.append("(" + " OR ".join(f"cat:{category}" for category in categories) + ")")
    if date_from or date_to:
        d_from = date_from or "19000101"
        d_to = date_to or datetime.now().strftime("%Y%m%d")
        parts.append(f"submittedDate:[{d_from}000000 TO {d_to}235959]")
    return " AND ".join(parts) if parts else "*:*"


def parse_entry(entry):
    """Parse a single Atom entry."""
    def text(tag, ns="atom"):
        el = entry.find(f"{ns}:{tag}", NS)
        return el.text.strip() if el is not None and el.text else ""

    raw_id = text("id")
    arxiv_id = raw_id.split("/abs/")[-1].strip() if "/abs/" in raw_id else raw_id

    authors = []
    for author in entry.findall("atom:author", NS):
        name_el = author.find("atom:name", NS)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    categories = []
    for cat in entry.findall("arxiv:primary_category", NS):
        term = cat.get("term", "")
        if term:
            categories.append(term)
    for cat in entry.findall("atom:category", NS):
        term = cat.get("term", "")
        if term and term not in categories:
            categories.append(term)

    published_raw = text("published")
    year = month = None
    published_clean = ""
    if published_raw:
        try:
            dt = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            year = dt.year
            month = dt.month
            published_clean = dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    pdf_url = ""
    for link in entry.findall("atom:link", NS):
        if link.get("type") == "application/pdf":
            pdf_url = link.get("href", "")
            break

    abstract = re.sub(r"\s+", " ", text("summary").replace("\n", " ")).strip()

    return {
        "arxiv_id": arxiv_id,
        "title": re.sub(r"\s+", " ", text("title").replace("\n", " ")),
        "authors": authors,
        "year": year,
        "month": month,
        "published": published_clean,
        "abstract": abstract,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
        "categories": categories,
    }


def score_result(result, terms, original_query=""):
    """Score transparent lexical relevance without treating it as novelty evidence."""
    title = (result.get("title") or "").lower()
    abstract = (result.get("abstract") or "").lower()
    title_tokens = set(re.findall(r"[a-z0-9][a-z0-9.\-]*", title))
    abstract_tokens = set(re.findall(r"[a-z0-9][a-z0-9.\-]*", abstract))
    matched_title = [term for term in terms if term in title_tokens]
    matched_abstract = [term for term in terms if term in abstract_tokens]
    matched = [term for term in terms if term in title_tokens or term in abstract_tokens]

    denominator = max(1, len(terms))
    score = 5.0 * len(matched_title) / denominator
    score += 2.0 * len(matched_abstract) / denominator
    phrase = re.sub(r"\s+", " ", (original_query or "").strip().lower())
    if phrase and phrase in title:
        score += 5.0
    elif phrase and phrase in abstract:
        score += 2.5
    score += min(1.0, (result.get("year") or 0) / 10000.0)
    return round(score, 4), matched, matched_title


def rank_results(results, query, max_results):
    """Deduplicate, reject weak lexical matches, and expose why each result ranked."""
    terms = query_terms(query)
    minimum_matches = min(4, max(1, ceil(len(terms) * 0.6)))
    deduped = {}
    for result in results:
        canonical_id = re.sub(r"v\d+$", "", result.get("arxiv_id", ""))
        key = canonical_id or re.sub(r"[^a-z0-9]+", " ", result.get("title", "").lower()).strip()
        if not key:
            continue
        score, matched, matched_title = score_result(result, terms, query)
        if len(matched) < minimum_matches:
            continue
        enriched = dict(result)
        enriched["relevance_score"] = score
        enriched["matched_query_terms"] = matched
        enriched["matched_title_terms"] = matched_title
        previous = deduped.get(key)
        if previous is None:
            enriched["matched_query_variants"] = [enriched.get("matched_query_variant", "")]
            enriched["retrieval_queries"] = [enriched.get("retrieval_query", "")]
            deduped[key] = enriched
        elif score > previous["relevance_score"]:
            enriched["matched_query_variants"] = list(previous["matched_query_variants"])
            enriched["retrieval_queries"] = list(previous["retrieval_queries"])
            variant = enriched.get("matched_query_variant", "")
            retrieval_query = enriched.get("retrieval_query", "")
            if variant and variant not in enriched["matched_query_variants"]:
                enriched["matched_query_variants"].append(variant)
            if retrieval_query and retrieval_query not in enriched["retrieval_queries"]:
                enriched["retrieval_queries"].append(retrieval_query)
            deduped[key] = enriched
        else:
            variant = enriched.get("matched_query_variant", "")
            retrieval_query = enriched.get("retrieval_query", "")
            if variant and variant not in previous["matched_query_variants"]:
                previous["matched_query_variants"].append(variant)
            if retrieval_query and retrieval_query not in previous["retrieval_queries"]:
                previous["retrieval_queries"].append(retrieval_query)
    ranked = sorted(
        deduped.values(),
        key=lambda item: (item["relevance_score"], len(item["matched_title_terms"]), item.get("year") or 0),
        reverse=True,
    )
    return ranked[:max_results]


def to_literature_record(item, query=""):
    return make_record(
        adapter="search_arxiv",
        provider="arxiv",
        source_type="preprint",
        title=item.get("title", ""),
        authors=item.get("authors", []),
        year=item.get("year"),
        version=arxiv_version(item.get("arxiv_id", "")),
        abstract=item.get("abstract", ""),
        landing_url=item.get("url", ""),
        pdf_url=item.get("pdf_url", ""),
        arxiv_id=item.get("arxiv_id", ""),
        query=query,
        raw_response=item,
        verification_status="metadata_fetched",
        is_primary=True,
        query_variant=item.get("matched_query_variant", ""),
        retrieval_queries=item.get("retrieval_queries", []),
        metadata={
            "categories": item.get("categories", []),
            "published": item.get("published", ""),
            "relevance_score": item.get("relevance_score"),
            "matched_query_terms": item.get("matched_query_terms", []),
            "matched_title_terms": item.get("matched_title_terms", []),
            "matched_query_variants": item.get("matched_query_variants", []),
        },
    )


def fetch_feed(search_query=None, arxiv_id=None, max_results=10,
               sort_by="relevance", retries=3):
    """Fetch and parse one arXiv Atom feed."""
    sort_map = {
        "relevance": "relevance",
        "date": "submittedDate",
        "lastUpdated": "lastUpdatedDate",
    }

    if arxiv_id:
        params = [("id_list", arxiv_id), ("max_results", "1")]
    else:
        params = [
            ("search_query", search_query or "*:*"),
            ("max_results", str(max_results)),
            ("sortBy", sort_map.get(sort_by, "relevance")),
            ("sortOrder", "descending"),
            ("start", "0"),
        ]

    param_str = "&".join(f"{key}={urllib.parse.quote(str(value), safe=':()[]*')}" for key, value in params)
    url = f"{ARXIV_API}?{param_str}"
    headers = {
        "User-Agent": "TheoremAudit/1.0 (research agent; contact@theoremgate.ai)",
        "Accept": "application/atom+xml",
    }

    raw = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"[search_arxiv] Rate limited. Waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"arXiv API HTTP {exc.code}: {exc.reason}")
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"arXiv API request failed: {exc}")

    try:
        root = ET.fromstring(raw or "")
    except ET.ParseError as exc:
        raise RuntimeError(f"Failed to parse arXiv XML: {exc}")

    results = []
    for entry in root.findall("atom:entry", NS):
        try:
            parsed = parse_entry(entry)
            if parsed["title"] and parsed["arxiv_id"]:
                results.append(parsed)
        except Exception:
            continue
    return results


def search_arxiv(query=None, arxiv_id=None, categories=None,
                 max_results=10, sort_by="relevance",
                 date_from=None, date_to=None, retries=3):
    if arxiv_id:
        return [to_literature_record(item) for item in fetch_feed(arxiv_id=arxiv_id, retries=retries)]

    variants = build_query_variants(query)
    if not variants:
        return []
    candidate_limit = min(100, max(20, max_results * 4))
    candidates = []
    for index, (variant_name, structured_query) in enumerate(variants):
        filtered_query = add_query_filters(structured_query, categories, date_from, date_to)
        found = fetch_feed(
            search_query=filtered_query,
            max_results=candidate_limit,
            sort_by=sort_by,
            retries=retries,
        )
        for item in found:
            enriched = dict(item)
            enriched["matched_query_variant"] = variant_name
            enriched["retrieval_query"] = filtered_query
            candidates.append(enriched)
        if index < len(variants) - 1:
            time.sleep(1.0)
    return [to_literature_record(item, query) for item in rank_results(candidates, query, max_results)]


def main():
    parser = argparse.ArgumentParser(description="Search arXiv and return structured JSON.")
    parser.add_argument("--query", "-q", type=str)
    parser.add_argument("--id", dest="arxiv_id", type=str)
    parser.add_argument("--max_results", "-n", type=int, default=10)
    parser.add_argument("--sort_by", choices=["relevance", "date", "lastUpdated"], default="relevance")
    parser.add_argument("--categories", nargs="+", default=None)
    parser.add_argument("--date_from", type=str)
    parser.add_argument("--date_to", type=str)
    parser.add_argument("--theory", action="store_true",
                        help="Filter to cs.LG stat.ML math.ST cs.IT")
    parser.add_argument("--recent", type=int, default=None, metavar="MONTHS")
    parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args()

    if not args.query and not args.arxiv_id:
        parser.error("Provide --query or --id")

    date_from = args.date_from
    if args.recent:
        cutoff = datetime.now() - timedelta(days=args.recent * 30)
        date_from = cutoff.strftime("%Y%m%d")

    categories = args.categories
    if args.theory and not categories:
        categories = THEORY_CATEGORIES

    try:
        results = search_arxiv(
            query=args.query,
            arxiv_id=args.arxiv_id,
            categories=categories,
            max_results=args.max_results,
            sort_by=args.sort_by,
            date_from=date_from,
            date_to=args.date_to,
        )
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    print(json.dumps(results, indent=2 if args.pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    main()
