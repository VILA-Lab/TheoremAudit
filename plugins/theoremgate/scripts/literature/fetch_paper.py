#!/usr/bin/env python3
"""
fetch_paper.py
Fetch a paper from arXiv and extract theorem-relevant content.
Uses the arXiv Atom API for metadata (reliable), HTML scraping as fallback,
and optionally fetches the PDF for theorem section extraction.

Usage:
    python fetch_paper.py --id 2301.13812
    python fetch_paper.py --id 2301.13812 --full
    python fetch_paper.py --url https://arxiv.org/abs/2301.13812
"""

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from record_schema import make_record


HEADERS = {
    "User-Agent": "TheoremAudit/1.0 (research agent; contact@theoremgate.ai)",
    "Accept": "text/html,application/xhtml+xml,application/atom+xml,text/plain",
}

NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

THEOREM_KEYWORDS = ["theorem", "lemma", "proposition", "assumption", "setting", "main result"]
ALLOWED_ARXIV_HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
ARXIV_ID_RE = re.compile(
    r"^(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?$",
    re.IGNORECASE,
)


class ArxivHTMLTextExtractor(HTMLParser):
    """Extract readable block text from arXiv HTML without external dependencies."""

    BLOCK_TAGS = {
        "article", "blockquote", "br", "div", "figcaption", "h1", "h2", "h3", "h4",
        "li", "main", "p", "section", "table", "td", "th", "tr",
    }
    SKIP_TAGS = {"script", "style", "svg"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.theorem_depth = 0
        self.current_theorem = []
        self.theorem_blocks = []

    def handle_starttag(self, tag, attrs):
        classes = set((dict(attrs).get("class") or "").split())
        if self.theorem_depth:
            if tag not in self.VOID_TAGS:
                self.theorem_depth += 1
            if tag in self.BLOCK_TAGS:
                self.current_theorem.append("\n")
        elif "ltx_theorem" in classes:
            self.theorem_depth = 1
            self.current_theorem = []
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        elif not self.skip_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.theorem_depth:
            if tag in self.BLOCK_TAGS:
                self.current_theorem.append("\n")
            self.theorem_depth -= 1
            if not self.theorem_depth:
                value = " ".join(self.current_theorem)
                value = re.sub(r"\s+", " ", value).strip()
                if len(value) >= 40:
                    self.theorem_blocks.append(value)
                self.current_theorem = []
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth and data.strip():
            self.parts.append(data)
            if self.theorem_depth:
                self.current_theorem.append(data)

    def text(self):
        value = " ".join(self.parts)
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r" *\n *", "\n", value)
        return re.sub(r"\n{3,}", "\n\n", value).strip()


def validate_arxiv_id(arxiv_id):
    value = (arxiv_id or "").strip().removesuffix(".pdf")
    if not ARXIV_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid arXiv identifier: {arxiv_id}")
    return value


def validate_arxiv_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_ARXIV_HOSTS:
        raise ValueError("--url must be an HTTPS URL on arxiv.org")
    match = re.fullmatch(r"/(?:abs|pdf|html)/(.+?)(?:\.pdf)?", parsed.path)
    if not match:
        raise ValueError("--url must identify an arXiv abs, html, or PDF page")
    return validate_arxiv_id(urllib.parse.unquote(match.group(1)))


def fetch_url(url, timeout=30, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
                if "pdf" in content_type.lower():
                    return raw, "pdf"
                return raw.decode("utf-8", errors="replace"), "text"
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"Fetch failed: {e}")


def fetch_via_api(arxiv_id):
    """Fetch paper metadata using arXiv Atom API — most reliable method."""
    api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
    api_headers = {
        "User-Agent": "TheoremAudit/1.0 (research agent; contact@theoremgate.ai)",
        "Accept": "application/atom+xml",  # Must request atom+xml for arXiv API
    }
    req = urllib.request.Request(api_url, headers=api_headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    root = ET.fromstring(raw)
    entries = root.findall("atom:entry", NS)
    if not entries:
        return None, None, []

    entry = entries[0]

    def text(tag, ns="atom"):
        el = entry.find(f"{ns}:{tag}", NS)
        return el.text.strip() if el is not None and el.text else ""

    title = re.sub(r"\s+", " ", text("title").replace("\n", " ")).strip()
    abstract = re.sub(r"\s+", " ", text("summary").replace("\n", " ")).strip()
    authors = []
    for a in entry.findall("atom:author", NS):
        name_el = a.find("atom:name", NS)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    return title, abstract, authors


def extract_from_abs_page(html):
    """Extract title, abstract, authors from arXiv HTML abs page — fallback."""
    title = abstract = ""
    authors = []

    for pattern in [
        r'<meta name="citation_title" content="([^"]+)"',
        r'<h1 class="title mathjax"[^>]*>(?:<span[^>]*>[^<]*</span>)?\s*([\s\S]+?)</h1>',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1))
            title = re.sub(r"\s+", " ", title).strip().replace("Title:", "").strip()
            if title and "arXiv" not in title:
                break

    for pattern in [
        r'<meta name="citation_abstract" content="([^"]+)"',
        r'<blockquote class="abstract mathjax"[^>]*>([\s\S]+?)</blockquote>',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            abstract = re.sub(r"<[^>]+>", " ", m.group(1))
            abstract = re.sub(r"\s+", " ", abstract).strip().replace("Abstract:", "").strip()
            if len(abstract) > 50:
                break

    for pattern in [r'<meta name="citation_author" content="([^"]+)"']:
        matches = re.findall(pattern, html)
        if matches:
            authors = [m.strip() for m in matches if len(m.strip()) > 2][:15]
            break

    return title, abstract, authors


def extract_theorem_section(text, max_chars=8000):
    """Extract theorem/setting sections from raw text."""
    extracted = []
    patterns = [
        r"(?:Setting|Setup|Preliminaries|Problem\s+Formulation)[^\n]*\n([\s\S]{200,3000}?)(?=\n\d+[\.\s]|\Z)",
        r"(?:Main\s+)?(?:Results?|Theorems?|Contributions?)[^\n]*\n([\s\S]{200,3000}?)(?=\n\d+[\.\s]|\Z)",
        r"Theorem\s+\d+[^\n]*\n([\s\S]{50,1000}?)(?=Theorem\s+\d+|Lemma\s+\d+|Proof|\n\n\n)",
        r"Assumption\s+\d+[^\n]*\n([\s\S]{50,500}?)(?=Assumption\s+\d+|Theorem\s+\d+|\n\n\n)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for m in matches[:2]:
            clean = re.sub(r"\s+", " ", m).strip()
            if len(clean) > 100:
                extracted.append(clean[:2000])

    if extracted:
        return "\n\n---\n\n".join(extracted)[:max_chars]
    return ""


def extract_html_text(html):
    parser = ArxivHTMLTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text()


def extract_html_content(html):
    parser = ArxivHTMLTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.text(), parser.theorem_blocks


def extract_pdf_text(pdf_content):
    """Use a real PDF parser when available; never decode raw PDF bytes as text."""
    try:
        import fitz  # PyMuPDF is optional; HTML extraction remains dependency-free.
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is unavailable for PDF fallback extraction") from exc

    pages = []
    try:
        with fitz.open(stream=io.BytesIO(pdf_content), filetype="pdf") as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                if page_text:
                    pages.append(f"[Page {page_number}]\n{page_text}")
    except Exception as exc:
        raise RuntimeError(f"PDF parser failed: {exc}") from exc
    return "\n\n".join(pages)


def validate_extracted_text(text, title=""):
    """Reject empty, binary-like, or obviously unrelated extraction results."""
    if len(text) < 1000:
        return False, "extracted text is too short"
    printable = sum(1 for char in text if char.isprintable() or char in "\n\t")
    letters = sum(1 for char in text if char.isalpha())
    if printable / max(1, len(text)) < 0.95 or letters / max(1, len(text)) < 0.45:
        return False, "extracted text does not look like scholarly prose"
    title_terms = {
        term for term in re.findall(r"[a-z0-9\-]{4,}", (title or "").lower())
        if term not in {"with", "from", "under", "using", "based"}
    }
    if title_terms:
        document_terms = set(re.findall(r"[a-z0-9\-]{4,}", text[:20000].lower()))
        if len(title_terms & document_terms) < min(2, len(title_terms)):
            return False, "extracted text does not match the paper title"
    return True, ""


def fetch_paper(arxiv_id=None, url=None, fetch_full=False, max_chars=12000):
    if arxiv_id:
        arxiv_id = validate_arxiv_id(arxiv_id)
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    elif url:
        arxiv_id = validate_arxiv_url(url)
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    else:
        raise ValueError("Provide arxiv_id or url")

    result = {
        "arxiv_id": arxiv_id,
        "title": "",
        "authors": [],
        "abstract": "",
        "theorem_section": "",
        "fulltext_excerpt": "",
        "url": abs_url,
        "pdf_url": pdf_url,
        "fetch_mode": "metadata_only",
        "extraction_status": "metadata_only",
        "fulltext_source": "",
        "source_sha256": "",
        "error": None,
    }

    # Method 1 — arXiv Atom API (most reliable)
    if arxiv_id:
        try:
            title, abstract, authors = fetch_via_api(arxiv_id)
            if title:
                result["title"] = title
                result["abstract"] = abstract
                result["authors"] = authors
        except Exception as e:
            result["error"] = f"API fetch failed: {type(e).__name__}: {e}"

    # Method 2 — HTML scraping fallback
    if not result["title"]:
        try:
            html, _ = fetch_url(abs_url)
            if html:
                title, abstract, authors = extract_from_abs_page(html)
                result["title"] = title
                result["abstract"] = abstract
                result["authors"] = authors
                result["error"] = None
        except Exception as e:
            if not result["error"]:
                result["error"] = f"HTML fetch failed: {type(e).__name__}: {e}"

    if not result["title"] and not result["error"]:
        result["error"] = f"Could not extract metadata for {arxiv_id or url}"

    # Prefer semantic arXiv HTML; fall back to a real PDF parser. Extraction is
    # evidence acquisition only and never implies theorem-level verification.
    if fetch_full:
        extraction_errors = []
        fulltext = ""
        semantic_theorems = []
        try:
            html_url = f"https://arxiv.org/html/{arxiv_id}"
            html, content_type = fetch_url(html_url, timeout=40)
            if content_type != "text" or not isinstance(html, str):
                raise RuntimeError("arXiv HTML endpoint did not return text")
            candidate, semantic_theorems = extract_html_content(html)
            valid, reason = validate_extracted_text(candidate, result["title"])
            if not valid:
                raise RuntimeError(reason)
            fulltext = candidate
            result["fetch_mode"] = "html_fulltext"
            result["fulltext_source"] = html_url
            result["source_sha256"] = hashlib.sha256(html.encode("utf-8")).hexdigest()
        except Exception as exc:
            extraction_errors.append(f"HTML: {type(exc).__name__}: {exc}")

        if not fulltext:
            try:
                pdf_content, content_type = fetch_url(pdf_url, timeout=40)
                if content_type != "pdf" or not isinstance(pdf_content, bytes):
                    raise RuntimeError("arXiv PDF endpoint did not return PDF bytes")
                candidate = extract_pdf_text(pdf_content)
                valid, reason = validate_extracted_text(candidate, result["title"])
                if not valid:
                    raise RuntimeError(reason)
                fulltext = candidate
                result["fetch_mode"] = "pdf_fulltext"
                result["fulltext_source"] = pdf_url
                result["source_sha256"] = hashlib.sha256(pdf_content).hexdigest()
            except Exception as exc:
                extraction_errors.append(f"PDF: {type(exc).__name__}: {exc}")

        if fulltext:
            result["extraction_status"] = "fulltext_extracted"
            if semantic_theorems:
                result["theorem_section"] = "\n\n---\n\n".join(semantic_theorems)[:max_chars]
            else:
                result["theorem_section"] = extract_theorem_section(fulltext, max_chars)
            result["fulltext_excerpt"] = fulltext[:max_chars]
        else:
            result["fetch_mode"] = "metadata_only"
            result["extraction_status"] = "extraction_failed"
            result["error"] = "; ".join(extraction_errors)

    status = result["extraction_status"]
    if status == "metadata_only":
        status = "metadata_fetched" if result["title"] else "lead"
    evidence = []
    if result["extraction_status"] == "fulltext_extracted":
        evidence.append({
            "kind": "fulltext_extraction",
            "locator": result["fulltext_source"],
            "source_sha256": result["source_sha256"],
            "theorem_candidates": result["theorem_section"],
            "theorem": "",
            "section": "",
            "pages": "",
            "assumptions": [],
            "conclusion": "",
            "supports_claim_ids": [],
        })
    return make_record(
        adapter="fetch_paper",
        provider="arxiv",
        source_type="preprint",
        title=result["title"] or f"arXiv {arxiv_id}",
        authors=result["authors"],
        abstract=result["abstract"],
        landing_url=result["url"],
        pdf_url=result["pdf_url"],
        arxiv_id=arxiv_id,
        raw_response=result,
        verification_status=status,
        evidence=evidence,
        is_primary=True,
        metadata={
            "fetch_mode": result["fetch_mode"],
            "extraction_error": result["error"],
            "fulltext_excerpt": result["fulltext_excerpt"],
            "theorem_candidates": result["theorem_section"],
            "fulltext_source": result["fulltext_source"],
            "source_sha256": result["source_sha256"],
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", dest="arxiv_id", type=str)
    parser.add_argument("--url", type=str)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--max_chars", type=int, default=12000)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    if not args.arxiv_id and not args.url:
        parser.error("Provide --id or --url")

    try:
        result = fetch_paper(
            arxiv_id=args.arxiv_id,
            url=args.url,
            fetch_full=args.full,
            max_chars=args.max_chars,
        )
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    main()
