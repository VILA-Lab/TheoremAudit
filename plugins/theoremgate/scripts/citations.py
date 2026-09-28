"""Deterministic citation identity, deduplication, LaTeX, and BibTeX helpers."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from literature.record_schema import is_record, merge_records, normalize_legacy_record, normalize_title


_ARXIV_RE = re.compile(r"(\d{4}\.\d{4,5})")
_LATEX_CITE_RE = re.compile(
    r"\\cite(?:alp|alt|author|num|p|p\*|t|t\*|year|yearpar)?\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}"
)
_STOPWORDS = {"a", "an", "and", "for", "from", "in", "of", "on", "the", "to", "with"}


def arxiv_id(ref) -> str:
    """Return a version-free modern arXiv identifier when available."""
    if not isinstance(ref, dict):
        return ""
    if is_record(ref):
        return ref.get("canonical_ids", {}).get("arxiv", "")
    for field in ("url", "paper_url", "arxiv_id", "arxiv", "note"):
        match = _ARXIV_RE.search(str(ref.get(field, "") or ""))
        if match:
            return match.group(1)
    return ""


def norm_title(ref) -> str:
    if not isinstance(ref, dict):
        return ""
    if is_record(ref):
        return normalize_title(ref.get("bibliographic", {}).get("title", ""))
    return normalize_title(ref.get("title") or ref.get("paper_title") or "")


def _author_tokens(record: dict) -> set[str]:
    authors = record.get("bibliographic", {}).get("authors") or []
    return {
        re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", author).encode("ascii", "ignore").decode().lower().split()[-1])
        for author in authors if isinstance(author, str) and author.strip()
    }


def _identifier_pairs(record: dict) -> set[tuple[str, str]]:
    return {(key, value) for key, value in record["canonical_ids"].items() if value}


def _same_work(left: dict, right: dict) -> tuple[bool, str]:
    shared = _identifier_pairs(left) & _identifier_pairs(right)
    if shared:
        return True, "shared_identifier"
    if not norm_title(left) or norm_title(left) != norm_title(right):
        return False, ""
    left_year = left["bibliographic"].get("year")
    right_year = right["bibliographic"].get("year")
    if left_year and right_year and left_year != right_year:
        return False, "title_year_conflict"
    left_authors, right_authors = _author_tokens(left), _author_tokens(right)
    if left_authors and right_authors and not (left_authors & right_authors):
        return False, "title_author_conflict"
    return True, "normalized_title"


def dedupe_with_report(refs):
    """Cluster references transitively and return canonical records plus an audit report."""
    normalized = [normalize_legacy_record(item) for item in (refs or []) if isinstance(item, dict)]
    parent = list(range(len(normalized)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[max(left, right)] = min(left, right)

    decisions, conflicts = [], []
    for left in range(len(normalized)):
        for right in range(left + 1, len(normalized)):
            same, reason = _same_work(normalized[left], normalized[right])
            entry = {
                "left_record_id": normalized[left]["record_id"],
                "right_record_id": normalized[right]["record_id"],
                "reason": reason,
            }
            if same:
                union(left, right)
                entry["decision"] = "merge"
                decisions.append(entry)
            elif reason:
                entry["decision"] = "keep_separate"
                conflicts.append(entry)

    groups = defaultdict(list)
    for index, record in enumerate(normalized):
        groups[find(index)].append(record)

    records, duplicates, aliases = [], [], {}
    for group in groups.values():
        merged = merge_records(sorted(group, key=lambda item: item["record_id"]))
        records.append(merged)
        for item in group:
            aliases[item["record_id"]] = merged["record_id"]
            if item is not group[0] or item["record_id"] != merged["record_id"]:
                duplicates.append(item)
    records.sort(key=lambda item: item["record_id"])
    return {
        "references": records,
        "duplicates": duplicates,
        "aliases": dict(sorted(aliases.items())),
        "merge_decisions": decisions,
        "conflicts": conflicts,
    }


def dedupe_references(refs):
    report = dedupe_with_report(refs)
    return report["references"], report["duplicates"]


def _ascii_token(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", value)


def citation_key_base(record: dict) -> str:
    record = normalize_legacy_record(record)
    authors = record["bibliographic"].get("authors") or []
    surname = _ascii_token(authors[0].split()[-1]) if authors else "anonymous"
    year = str(record["bibliographic"].get("year") or "nd")
    words = [_ascii_token(word) for word in record["bibliographic"]["title"].split()]
    keyword = next((word for word in words if word and word not in _STOPWORDS), "work")
    return f"{surname}{year}{keyword}"


def citation_key_map(records) -> dict[str, str]:
    """Map record IDs to stable readable keys, deterministically resolving collisions."""
    groups = defaultdict(list)
    for record in (normalize_legacy_record(item) for item in records):
        groups[citation_key_base(record)].append(record)
    result = {}
    for base, group in sorted(groups.items()):
        for index, record in enumerate(sorted(group, key=lambda item: item["record_id"])):
            suffix = "" if index == 0 else (chr(ord("a") + index - 1) if index <= 26 else str(index))
            result[record["record_id"]] = f"{base}{suffix}"
    return result


def latex_citation_keys(content: str) -> set[str]:
    return {
        key.strip()
        for match in _LATEX_CITE_RE.finditer(content or "")
        for key in match.group(1).split(",")
        if key.strip()
    }


def _bibtex_escape(value: object) -> str:
    text = str(value or "")
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_"}
    return "".join(replacements.get(char, char) for char in text)


def bibtex_entries(records, *, selected_record_ids=None, citation_keys=None) -> tuple[str, dict[str, str]]:
    normalized = [normalize_legacy_record(item) for item in records]
    selected = set(selected_record_ids or [])
    if selected:
        normalized = [item for item in normalized if item["record_id"] in selected]
    generated = citation_key_map(normalized)
    keys = {item["record_id"]: (citation_keys or {}).get(item["record_id"], generated[item["record_id"]])
            for item in normalized}
    entries = []
    for record in sorted(normalized, key=lambda item: keys[item["record_id"]]):
        bib, source, ids = record["bibliographic"], record["source"], record["canonical_ids"]
        source_type = str(source.get("source_type") or "").lower()
        if any(token in source_type for token in ("conference", "proceeding")):
            entry_type, venue_field = "inproceedings", "booktitle"
        elif "journal" in source_type:
            entry_type, venue_field = "article", "journal"
        else:
            entry_type, venue_field = "misc", "note"
        fields = [("title", bib["title"])]
        if bib.get("authors"):
            fields.append(("author", " and ".join(bib["authors"])))
        if bib.get("year"):
            fields.append(("year", bib["year"]))
        if bib.get("venue"):
            fields.append((venue_field, bib["venue"]))
        if ids.get("doi"):
            fields.append(("doi", ids["doi"]))
        if ids.get("arxiv"):
            fields.extend((("eprint", ids["arxiv"]), ("archivePrefix", "arXiv")))
        if source.get("landing_url"):
            fields.append(("url", source["landing_url"]))
        lines = [f"@{entry_type}{{{keys[record['record_id']]},"]
        lines.extend(f"  {name} = {{{_bibtex_escape(value)}}}," for name, value in fields)
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries) + ("\n" if entries else ""), keys
