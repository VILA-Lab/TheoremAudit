#!/usr/bin/env python3
"""
search_jmlr.py
Search JMLR and PMLR for theory papers.

Usage:
    python search_jmlr.py --query "kernel regression generalization bound" --max_results 10
    python search_jmlr.py --query "Rademacher complexity" --include_pmlr --max_results 10
    python search_jmlr.py --query "benign overfitting" --year_from 2000 --year_to 2015
"""

import argparse
import html as html_lib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from record_schema import make_record


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

JMLR_BASE = "https://jmlr.org"
PMLR_BASE = "https://proceedings.mlr.press"
PMLR_TARGET_VENUES = (
    "aistats", "algorithmic learning theory", "colt", "conference on learning theory",
    "icml", "international conference on machine learning", "uai",
)


class LinkCollector(HTMLParser):
    """Collect anchor URLs and their visible text using the standard HTML parser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []

    def handle_data(self, data):
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_href is not None:
            text = re.sub(r"\s+", " ", " ".join(self.current_text)).strip()
            self.links.append((self.current_href, text))
            self.current_href = None
            self.current_text = []


class MetadataCollector(HTMLParser):
    """Collect standard scholarly citation metadata from a paper landing page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        values = dict(attrs)
        name = (values.get("name") or values.get("property") or "").lower()
        content = values.get("content", "").strip()
        if name and content:
            self.values.setdefault(name, []).append(content)


class PMLRPaperCollector(HTMLParser):
    """Associate PMLR title paragraphs with their following official abstract links."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_title = False
        self.title_parts = []
        self.latest_title = ""
        self.anchor_href = None
        self.anchor_parts = []
        self.records = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "p" and "title" in (values.get("class") or "").split():
            self.in_title = True
            self.title_parts = []
        elif tag == "a":
            self.anchor_href = values.get("href")
            self.anchor_parts = []

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.anchor_href is not None:
            self.anchor_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.in_title:
            self.latest_title = re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()
            self.in_title = False
            self.title_parts = []
        elif tag == "a" and self.anchor_href is not None:
            anchor_text = re.sub(r"\s+", " ", " ".join(self.anchor_parts)).strip().lower()
            url = urllib.parse.urljoin(self.base_url, self.anchor_href)
            path = urllib.parse.urlparse(url).path
            if self.latest_title and anchor_text == "abs" and re.fullmatch(r"/v\d+/[^/]+\.html", path):
                self.records.append((url, self.latest_title))
            self.anchor_href = None
            self.anchor_parts = []


class JMLRPaperCollector(HTMLParser):
    """Associate JMLR definition-list titles with their official abstract links."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_title = False
        self.title_parts = []
        self.latest_title = ""
        self.anchor_href = None
        self.anchor_parts = []
        self.records = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "dt":
            self.in_title = True
            self.title_parts = []
        elif tag == "a":
            self.anchor_href = values.get("href")
            self.anchor_parts = []

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.anchor_href is not None:
            self.anchor_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "dt" and self.in_title:
            self.latest_title = re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()
            self.in_title = False
            self.title_parts = []
        elif tag == "a" and self.anchor_href is not None:
            anchor_text = re.sub(r"\s+", " ", " ".join(self.anchor_parts)).strip().lower()
            url = urllib.parse.urljoin(self.base_url, self.anchor_href)
            path = urllib.parse.urlparse(url).path
            if self.latest_title and anchor_text == "abs" and re.fullmatch(r"/papers/v\d+/[^/]+\.html", path):
                self.records.append((url, self.latest_title))
            self.anchor_href = None
            self.anchor_parts = []


def collect_links(html):
    parser = LinkCollector()
    parser.feed(html)
    parser.close()
    return parser.links


def collect_metadata(html):
    parser = MetadataCollector()
    parser.feed(html)
    parser.close()
    return parser.values


def first_metadata(metadata, *names):
    for name in names:
        values = metadata.get(name.lower()) or []
        if values:
            return values[0]
    return ""


def enrich_paper_record(record, html, page_url):
    metadata = collect_metadata(html)
    title = first_metadata(metadata, "citation_title", "dc.title") or record["title"]
    authors = metadata.get("citation_author", []) or metadata.get("dc.creator", [])
    abstract = first_metadata(metadata, "citation_abstract", "description", "dc.description")
    pdf_url = first_metadata(metadata, "citation_pdf_url") or record.get("pdf_url", "")
    if pdf_url:
        pdf_url = urllib.parse.urljoin(page_url, pdf_url)
        parsed_pdf = urllib.parse.urlparse(pdf_url)
        if parsed_pdf.scheme == "http" and (parsed_pdf.hostname or "").lower() in {
            "jmlr.org", "www.jmlr.org", "proceedings.mlr.press",
        }:
            pdf_url = parsed_pdf._replace(scheme="https").geturl()
    date_value = first_metadata(metadata, "citation_publication_date", "citation_date", "dc.date")
    year_match = re.search(r"\b(19|20)\d{2}\b", date_value)
    result = dict(record)
    result.update({
        "title": re.sub(r"\s+", " ", title).strip(),
        "authors": [re.sub(r"\s+", " ", author).strip() for author in authors if author.strip()],
        "abstract": re.sub(r"\s+", " ", abstract).strip(),
        "pdf_url": pdf_url,
    })
    if year_match:
        result["year"] = int(year_match.group(0))
    return result


def to_literature_record(item, query):
    provider = item.get("source") or "proceedings"
    source_type = "journal" if provider == "jmlr" else "proceedings"
    return make_record(
        adapter="search_jmlr",
        provider=provider,
        source_type=source_type,
        title=item.get("title", ""),
        authors=item.get("authors", []),
        year=item.get("year"),
        venue=item.get("venue") or ("Journal of Machine Learning Research" if provider == "jmlr" else ""),
        abstract=item.get("abstract", ""),
        landing_url=item.get("url", ""),
        pdf_url=item.get("pdf_url", ""),
        query=query,
        raw_response=item,
        verification_status="metadata_fetched",
        is_primary=True,
        metadata={"volume": item.get("volume", "")},
    )


def paper_links_from_page(html, base_url, source):
    if source == "pmlr":
        parser = PMLRPaperCollector(base_url)
        parser.feed(html)
        parser.close()
        return list(dict.fromkeys(parser.records))
    if source == "jmlr":
        parser = JMLRPaperCollector(base_url)
        parser.feed(html)
        parser.close()
        return list(dict.fromkeys(parser.records))
    raise ValueError(f"unsupported paper page source: {source}")


def pmlr_volume_entries(html):
    """Extract official volume URLs plus their surrounding conference descriptions."""
    pattern = re.compile(
        r'<a[^>]+href=["\'](?P<href>(?:https?://proceedings\.mlr\.press/)?/?v(?P<volume>\d+)/?)["\'][^>]*>'
        r'(?:(?!</a>)[\s\S]){0,120}?Volume\s+\d+(?:(?!</a>)[\s\S]){0,120}?</a>'
        r'\s*(?P<label>[^<\r\n]{0,240})',
        re.IGNORECASE,
    )
    entries = []
    seen = set()
    for match in pattern.finditer(html):
        volume = int(match.group("volume"))
        if volume in seen:
            continue
        seen.add(volume)
        label = re.sub(r"\s+", " ", html_lib.unescape(match.group("label"))).strip(" -–—")
        entries.append({
            "volume": volume,
            "url": urllib.parse.urljoin(f"{PMLR_BASE}/", match.group("href")).rstrip("/") + "/",
            "label": label,
        })
    return entries


def fetch_html(url, retries=3, timeout=25):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            if e.code == 404:
                return None
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"Fetch failed: {e}")
    return None


def tokenize(text):
    return set(re.findall(r"[a-z0-9\-]{3,}", text.lower()))


def relevance(title, abstract, query_tokens):
    text = (title + " " + abstract).lower()
    paper_tokens = tokenize(text)
    if not query_tokens:
        return 0.0
    return len(query_tokens & paper_tokens) / max(1, len(query_tokens))


def search_jmlr_papers(query, max_results=10, year_from=None, year_to=None):
    """Search JMLR via their paper listing pages."""
    query_tokens = tokenize(query)
    index_html = fetch_html(f"{JMLR_BASE}/papers/")
    if not index_html:
        raise RuntimeError("JMLR index returned no content")
    volumes = []
    for href, text in collect_links(index_html):
        url = urllib.parse.urljoin(f"{JMLR_BASE}/papers/", href)
        match = re.fullmatch(r"/papers/v(\d+)/?", urllib.parse.urlparse(url).path)
        if match:
            volume = int(match.group(1))
            year = 1999 + volume
            if year_from and year < year_from:
                continue
            if year_to and year > year_to:
                continue
            volumes.append((volume, year, url.rstrip("/") + "/"))
    volumes = sorted(set(volumes), reverse=True)
    if not volumes:
        raise RuntimeError("JMLR volume parser found no usable volume links")

    candidates = []
    successful_pages = 0
    parsed_paper_links = 0
    for volume, year, volume_url in volumes[:20]:
        try:
            volume_html = fetch_html(volume_url)
        except Exception as exc:
            print(f"[search_jmlr] Skipping {volume_url}: {exc}", file=sys.stderr)
            continue
        if not volume_html:
            continue
        successful_pages += 1
        paper_links = paper_links_from_page(volume_html, volume_url, "jmlr")
        parsed_paper_links += len(paper_links)
        for paper_url, title in paper_links:
            score = relevance(title, "", query_tokens)
            if score >= 0.1:
                candidates.append({
                    "source": "jmlr", "title": title, "authors": [], "year": year,
                    "volume": str(volume), "abstract": "", "url": paper_url,
                    "pdf_url": paper_url.replace(".html", ".pdf"), "arxiv_id": "",
                    "_score": score,
                })
        if len(candidates) >= max_results * 3:
            break
        time.sleep(0.2)

    if not successful_pages or not parsed_paper_links:
        raise RuntimeError("JMLR paper parser could not read any volume pages")

    candidates.sort(key=lambda item: item["_score"], reverse=True)
    results = []
    for candidate in candidates[:max_results]:
        try:
            page_html = fetch_html(candidate["url"])
            enriched = enrich_paper_record(candidate, page_html or "", candidate["url"])
        except Exception as exc:
            print(f"[search_jmlr] Metadata fetch failed for {candidate['url']}: {exc}", file=sys.stderr)
            enriched = dict(candidate)
        enriched.pop("_score", None)
        results.append(to_literature_record(enriched, query))

    return results


def search_pmlr(query, max_results=10, year_from=None, year_to=None):
    """Search selected theory-heavy PMLR proceedings using official volume pages."""
    query_tokens = tokenize(query)
    index_html = fetch_html(f"{PMLR_BASE}/")
    if not index_html:
        raise RuntimeError("PMLR index returned no content")
    volumes = []
    for entry in pmlr_volume_entries(index_html):
        label_lower = entry["label"].lower()
        if not any(venue in label_lower for venue in PMLR_TARGET_VENUES):
            continue
        year_match = re.search(r"\b(19|20)\d{2}\b", entry["label"])
        year = int(year_match.group(0)) if year_match else None
        if year_from and year and year < year_from:
            continue
        if year_to and year and year > year_to:
            continue
        entry["year"] = year
        volumes.append(entry)
    volumes.sort(key=lambda item: item["volume"], reverse=True)
    if not volumes:
        raise RuntimeError("PMLR volume parser found no target proceedings")

    candidates = []
    successful_pages = 0
    parsed_paper_links = 0
    for entry in volumes[:30]:
        try:
            volume_html = fetch_html(entry["url"])
        except Exception as exc:
            print(f"[search_pmlr] Skipping {entry['url']}: {exc}", file=sys.stderr)
            continue
        if not volume_html:
            continue
        successful_pages += 1
        paper_links = paper_links_from_page(volume_html, entry["url"], "pmlr")
        parsed_paper_links += len(paper_links)
        for paper_url, title in paper_links:
            score = relevance(title, "", query_tokens)
            if score >= 0.1:
                candidates.append({
                    "source": "pmlr", "title": title, "authors": [], "year": entry["year"],
                    "venue": entry["label"] or "PMLR", "volume": str(entry["volume"]),
                    "abstract": "", "url": paper_url, "pdf_url": "", "arxiv_id": "",
                    "_score": score,
                })
        if len(candidates) >= max_results * 3:
            break
        time.sleep(0.2)

    if not successful_pages or not parsed_paper_links:
        raise RuntimeError("PMLR paper parser could not read any target volume pages")

    candidates.sort(key=lambda item: item["_score"], reverse=True)
    results = []
    for candidate in candidates[:max_results]:
        try:
            page_html = fetch_html(candidate["url"])
            enriched = enrich_paper_record(candidate, page_html or "", candidate["url"])
        except Exception as exc:
            print(f"[search_pmlr] Metadata fetch failed for {candidate['url']}: {exc}", file=sys.stderr)
            enriched = dict(candidate)
        enriched.pop("_score", None)
        results.append(to_literature_record(enriched, query))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Search JMLR and PMLR for theory papers."
    )
    parser.add_argument("--query", "-q", type=str, required=True)
    parser.add_argument("--max_results", "-n", type=int, default=10)
    parser.add_argument("--year_from", type=int)
    parser.add_argument("--year_to", type=int)
    parser.add_argument("--include_pmlr", action="store_true")
    parser.add_argument("--pmlr_only", action="store_true")
    parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args()

    try:
        results = []

        if not args.pmlr_only:
            jmlr_results = search_jmlr_papers(
                query=args.query,
                max_results=args.max_results,
                year_from=args.year_from,
                year_to=args.year_to,
            )
            results.extend(jmlr_results)

        if args.include_pmlr or args.pmlr_only:
            pmlr_results = search_pmlr(
                query=args.query,
                max_results=args.max_results,
                year_from=args.year_from,
                year_to=args.year_to,
            )
            results.extend(pmlr_results)

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
