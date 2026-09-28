import re
import json
import socket
import ipaddress
import urllib.parse
import urllib.request
from typing import List, Tuple
from html.parser import HTMLParser


def html_to_text(html):
    import html as html_lib
    for pattern in (
        r"<script.*?>.*?</script>",
        r"<style.*?>.*?</style>",
        r"<noscript.*?>.*?</noscript>",
        r"<nav.*?>.*?</nav>",
        r"<footer.*?>.*?</footer>",
        r"<header.*?>.*?</header>",
    ):
        html = re.sub(pattern, " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(
        r"</?(p|div|br|li|h[1-6]|tr|td|th|article|section)(\s[^>]*)?>",
        "\n", html, flags=re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", html)
    text = html_lib.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


class DuckDuckGoResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.in_result_link = False
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs = dict(attrs)
        href = attrs.get("href", "")
        class_name = attrs.get("class", "")
        if "result__a" in class_name or "uddg=" in href:
            self.in_result_link = True
            self.current_href = href
            self.current_text = []

    def handle_data(self, data):
        if self.in_result_link:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.in_result_link:
            title = " ".join("".join(self.current_text).split())
            href = self.current_href
            if title and href:
                self.results.append((title, href))
            self.in_result_link = False
            self.current_href = None
            self.current_text = []


def normalize_duckduckgo_url(href):
    href = urllib.parse.unquote(href)
    if href.startswith("/"):
        href = urllib.parse.urljoin("https://duckduckgo.com", href)
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    if "uddg" in qs:
        href = qs["uddg"][0]
    return href


_SEARXNG_INSTANCES = [
    "https://searx.be",
    "https://search.bus-hit.me",
    "https://opnxng.com",
]


def _searxng_search(query, max_results):
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "categories": "general",
    })
    for base_url in _SEARXNG_INSTANCES:
        url = f"{base_url}/search?{params}"
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read())
            results = [
                (item.get("title", "").strip(), item.get("url", "").strip())
                for item in data.get("results", [])
                if item.get("title") and item.get("url")
            ]
            if results:
                return results[:max_results]
        except Exception:
            continue
    return []


def run_web_search(query, max_results=5):
    max_results = max(1, min(int(max_results or 5), 10))
    ddg_results = []
    try:
        params = urllib.parse.urlencode({"q": query})
        url = f"https://duckduckgo.com/html/?{params}"
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read(1_000_000).decode("utf-8", errors="replace")
        parser = DuckDuckGoResultParser()
        parser.feed(html)
        seen = set()
        for title, href in parser.results:
            href = normalize_duckduckgo_url(href)
            if not href.startswith(("http://", "https://")):
                continue
            if href in seen:
                continue
            seen.add(href)
            ddg_results.append((title, href))
            if len(ddg_results) >= max_results:
                break
    except Exception:
        pass

    if ddg_results:
        return "\n".join(f"{i}. {t}\n   {u}" for i, (t, u) in enumerate(ddg_results, 1))

    searx_results = _searxng_search(query, max_results)
    if searx_results:
        return "\n".join(f"{i}. {t}\n   {u}" for i, (t, u) in enumerate(searx_results, 1))

    # Final fallback: arXiv API — reliable for ML/theory papers and not rate-limited like
    # DuckDuckGo HTML scraping. Returns real titles + abstract-page URLs the agent can fetch.
    arxiv_results = _arxiv_search(query, max_results)
    if arxiv_results:
        return "\n".join(f"{i}. {t}\n   {u}" for i, (t, u) in enumerate(arxiv_results, 1))

    return ""


def _arxiv_search(query, max_results=5):
    """Query the arXiv Atom API. Returns list of (title, abs_url)."""
    import re as _re
    try:
        params = urllib.parse.urlencode({
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max(1, min(int(max_results or 5), 10)),
            "sortBy": "relevance",
        })
        url = f"http://export.arxiv.org/api/query?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            feed = response.read(1_000_000).decode("utf-8", errors="replace")
    except Exception:
        return []
    results = []
    for entry in _re.findall(r"<entry>(.*?)</entry>", feed, _re.DOTALL):
        m_id = _re.search(r"<id>(.*?)</id>", entry)
        m_title = _re.search(r"<title>(.*?)</title>", entry, _re.DOTALL)
        if not (m_id and m_title):
            continue
        title = _re.sub(r"\s+", " ", m_title.group(1)).strip()
        abs_url = m_id.group(1).strip()  # e.g. http://arxiv.org/abs/1906.11300v1
        results.append((title, abs_url))
        if len(results) >= max_results:
            break
    return results


def is_private_or_local_host(hostname):
    if not hostname:
        return True
    hostname = hostname.lower()
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return True
    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return True
        return False
    except OSError:
        return False


def run_web_fetch(url, max_chars=12000):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Error: only http and https URLs are allowed."
    if is_private_or_local_host(parsed.hostname or ""):
        return "Error: blocked — URL resolves to a private or local network address."
    max_chars = max(1000, min(int(max_chars or 12000), 50000))
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,text/plain,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(1_000_000)
    except urllib.error.HTTPError as e:
        return f"Error: HTTP {e.code} {e.reason} — {url}"
    except urllib.error.URLError as e:
        return f"Error: could not reach {url} — {e.reason}"
    except Exception as e:
        return f"Error: {e}"
    text = raw.decode("utf-8", errors="replace")
    if "html" in content_type.lower():
        text = html_to_text(text)
    text = text.strip()
    if not text:
        return "(no readable text found — the page may be JavaScript-rendered or require authentication)"
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n[truncated: showing first {max_chars:,} of {len(text):,} characters]"
    return text