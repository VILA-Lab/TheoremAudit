#!/usr/bin/env python3
"""Canonical, auditable literature records shared by every TheoremAudit adapter."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse


SCHEMA_VERSION = 1
RECORD_TYPE = "literature_record"
VERIFICATION_STATUSES = {
    "lead",
    "metadata_fetched",
    "fulltext_extracted",
    "primary_source_verified",
    "extraction_failed",
}
STATUS_RANK = {
    "lead": 0,
    "extraction_failed": 0,
    "metadata_fetched": 1,
    "fulltext_extracted": 2,
    "primary_source_verified": 3,
}
NON_TECHNICAL_LOCATORS = {
    "abstract", "abstract page", "landing page", "paper page", "publication page",
    "proceedings page", "metadata page", "google research publication abstract",
}
ARXIV_RE = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(v\d+)?(?!\d)", re.IGNORECASE)
OLD_ARXIV_RE = re.compile(r"\b([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?\b", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_arxiv_id(value: Any) -> str:
    text = str(value or "")
    match = ARXIV_RE.search(text) or OLD_ARXIV_RE.search(text)
    return match.group(1) if match else ""


def arxiv_version(value: Any) -> str:
    text = str(value or "")
    match = ARXIV_RE.search(text) or OLD_ARXIV_RE.search(text)
    return match.group(2) or "" if match else ""


def normalize_doi(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^doi:\s*", "", text, flags=re.IGNORECASE)
    return text.lower()


def normalize_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def stable_record_id(ids: Dict[str, str], title: str, year: Any = None) -> str:
    for namespace in ("doi", "arxiv", "openreview", "semantic_scholar"):
        if ids.get(namespace):
            return f"{namespace}:{ids[namespace]}"
    fingerprint = canonical_json_sha256({"title": normalize_title(title), "year": year})[:20]
    return f"title:{fingerprint}"


def retrieval_event(adapter: str, provider: str, query: str = "", raw_response: Any = None,
                    result_url: str = "", retrieved_at: Optional[str] = None,
                    query_variant: str = "", retrieval_queries: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    return {
        "adapter": adapter,
        "provider": provider,
        "query": str(query or ""),
        "query_variant": str(query_variant or ""),
        "retrieval_queries": [str(item) for item in (retrieval_queries or []) if str(item).strip()],
        "retrieved_at": retrieved_at or utc_now(),
        "result_url": str(result_url or ""),
        "raw_response_sha256": canonical_json_sha256(raw_response) if raw_response is not None else "",
    }


def make_record(*, adapter: str, provider: str, source_type: str, title: str,
                authors: Optional[Iterable[str]] = None, year: Any = None, venue: str = "",
                version: str = "", abstract: str = "", landing_url: str = "", pdf_url: str = "",
                arxiv_id: str = "", doi: str = "", openreview_id: str = "",
                semantic_scholar_id: str = "", query: str = "", raw_response: Any = None,
                verification_status: str = "lead", evidence: Optional[List[Dict[str, Any]]] = None,
                verified_at: str = "", is_primary: bool = False, query_variant: str = "",
                retrieval_queries: Optional[Iterable[str]] = None,
                metrics: Optional[Dict[str, Any]] = None,
                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    canonical_arxiv = canonical_arxiv_id(arxiv_id or landing_url)
    ids = {
        "arxiv": canonical_arxiv,
        "doi": normalize_doi(doi),
        "openreview": str(openreview_id or "").strip(),
        "semantic_scholar": str(semantic_scholar_id or "").strip(),
    }
    status = verification_status if verification_status in VERIFICATION_STATUSES else "lead"
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "record_id": stable_record_id(ids, title, year),
        "canonical_ids": ids,
        "source": {
            "provider": provider,
            "source_type": source_type,
            "landing_url": str(landing_url or ""),
            "pdf_url": str(pdf_url or ""),
            "is_primary": bool(is_primary),
        },
        "bibliographic": {
            "title": re.sub(r"\s+", " ", str(title or "")).strip(),
            "authors": [str(author).strip() for author in (authors or []) if str(author).strip()],
            "year": year if isinstance(year, int) else None,
            "venue": re.sub(r"\s+", " ", str(venue or "")).strip(),
            "version": str(version or arxiv_version(arxiv_id)).strip(),
            "abstract": re.sub(r"\s+", " ", str(abstract or "")).strip(),
        },
        "retrieval": [retrieval_event(
            adapter=adapter,
            provider=provider,
            query=query,
            raw_response=raw_response,
            result_url=landing_url,
            query_variant=query_variant,
            retrieval_queries=retrieval_queries,
        )],
        "verification": {
            "status": status,
            "verified_at": str(verified_at or ""),
            "evidence": list(evidence or []),
        },
        "metrics": dict(metrics or {}),
        "metadata": dict(metadata or {}),
    }
    validate_record(record)
    return record


def validate_record(record: Dict[str, Any], require_verified_evidence: bool = True) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("literature record must be an object")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("record_type") != RECORD_TYPE:
        raise ValueError("unsupported literature record schema")
    if not isinstance(record.get("record_id"), str) or not record["record_id"].strip():
        raise ValueError("literature record requires record_id")
    ids = record.get("canonical_ids")
    if not isinstance(ids, dict) or any(key not in ids for key in ("arxiv", "doi", "openreview", "semantic_scholar")):
        raise ValueError("literature record requires canonical identifier fields")
    source = record.get("source")
    if not isinstance(source, dict) or not source.get("provider") or not source.get("source_type"):
        raise ValueError("literature record requires source provider and type")
    for url_field in ("landing_url", "pdf_url"):
        url = source.get(url_field) or ""
        if url and urlparse(url).scheme not in {"http", "https"}:
            raise ValueError(f"{url_field} must be HTTP(S)")
    bib = record.get("bibliographic")
    if not isinstance(bib, dict) or not str(bib.get("title") or "").strip():
        raise ValueError("literature record requires a title")
    if not isinstance(bib.get("authors"), list):
        raise ValueError("bibliographic.authors must be a list")
    retrieval = record.get("retrieval")
    if not isinstance(retrieval, list) or not retrieval:
        raise ValueError("literature record requires retrieval provenance")
    for event in retrieval:
        if (
            not isinstance(event, dict) or not event.get("adapter")
            or not event.get("provider") or not event.get("retrieved_at")
        ):
            raise ValueError("each retrieval event requires adapter, provider, and timestamp")
        digest = event.get("raw_response_sha256") or ""
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("each retrieval event requires a raw-response SHA-256 digest")
    verification = record.get("verification")
    if not isinstance(verification, dict) or verification.get("status") not in VERIFICATION_STATUSES:
        raise ValueError("invalid literature verification status")
    evidence = verification.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("verification.evidence must be a list")
    if require_verified_evidence and verification["status"] == "primary_source_verified":
        if not source.get("is_primary"):
            raise ValueError("primary_source_verified requires a primary source")
        if not verification.get("verified_at") or not evidence:
            raise ValueError("primary_source_verified requires verified_at and exact evidence")
        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError("verification evidence must be objects")
            locators = {
                field: str(item.get(field) or "").strip()
                for field in ("theorem", "section", "pages")
            }
            if not any(locators.values()):
                raise ValueError("verified evidence requires theorem, section, or pages")
            normalized_locators = {
                value.lower().rstrip(".") for value in locators.values() if value
            }
            if normalized_locators and normalized_locators <= NON_TECHNICAL_LOCATORS:
                raise ValueError(
                    "primary_source_verified requires theorem-level or full-text evidence; "
                    "an abstract or landing page is not sufficient"
                )
            if not str(item.get("conclusion") or "").strip():
                raise ValueError("verified evidence requires the supported conclusion")
            assumptions = item.get("assumptions")
            if not isinstance(assumptions, list) or not assumptions or any(
                not isinstance(value, str) or not value.strip() for value in assumptions
            ):
                raise ValueError("verified theorem evidence requires explicit assumptions")
            claim_ids = item.get("supports_claim_ids")
            if not isinstance(claim_ids, list) or any(
                not isinstance(value, str) or not value.strip() for value in claim_ids
            ):
                raise ValueError("verified evidence supports_claim_ids must be a list of claim IDs")
    return record


def is_record(value: Any) -> bool:
    return isinstance(value, dict) and value.get("record_type") == RECORD_TYPE


def normalize_legacy_record(value: Dict[str, Any], adapter: str = "legacy_import",
                            provider: str = "legacy") -> Dict[str, Any]:
    if is_record(value):
        return validate_record(value)
    source_url = value.get("source_url") or value.get("url") or value.get("arxiv_url") or value.get("ss_url") or ""
    verified = value.get("verified") is True
    evidence = []
    if verified:
        evidence.append({
            "theorem": value.get("theorem_location") or value.get("theorem") or "",
            "section": value.get("section") or "",
            "pages": value.get("pages") or "",
            "assumptions": value.get("assumptions") or [],
            "conclusion": value.get("prior_result") or value.get("conclusion") or value.get("supports") or "",
            "supports_claim_ids": value.get("supports_claim_ids") or [],
        })
    status = "primary_source_verified" if verified else "lead"
    # Old boolean verification records without exact evidence remain leads rather than
    # being silently promoted into the stricter schema.
    if verified and (not evidence[0]["conclusion"] or not any(evidence[0][key] for key in ("theorem", "section", "pages"))):
        status = "lead"
        evidence = []
    record = make_record(
        adapter=adapter,
        provider=provider,
        source_type=value.get("source_type") or "legacy_record",
        title=value.get("title") or value.get("paper_title") or "Untitled literature record",
        authors=value.get("authors") or [],
        year=value.get("year"),
        venue=value.get("venue") or "",
        version=value.get("version") or "",
        abstract=value.get("abstract") or "",
        landing_url=source_url,
        pdf_url=value.get("pdf_url") or "",
        arxiv_id=value.get("arxiv_id") or source_url,
        doi=value.get("doi") or "",
        openreview_id=value.get("openreview_id") or "",
        semantic_scholar_id=value.get("paper_id") or "",
        query=value.get("query") or "",
        raw_response=value,
        verification_status=status,
        evidence=evidence,
        verified_at=value.get("verified_at") or (utc_now() if status == "primary_source_verified" else ""),
        is_primary=bool(value.get("is_primary", verified)),
        metadata={"legacy_id": value.get("id") or value.get("cite_key") or "", "legacy_role": value.get("role") or ""},
    )
    return record


def merge_records(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    values = [normalize_legacy_record(item) for item in records]
    if not values:
        raise ValueError("cannot merge an empty literature-record group")
    merged = json.loads(json.dumps(values[0]))
    for item in values[1:]:
        for key, identifier in item["canonical_ids"].items():
            if identifier and not merged["canonical_ids"].get(key):
                merged["canonical_ids"][key] = identifier
        merged["retrieval"].extend(
            event for event in item["retrieval"] if event not in merged["retrieval"]
        )
        if STATUS_RANK[item["verification"]["status"]] > STATUS_RANK[merged["verification"]["status"]]:
            merged["verification"] = item["verification"]
        for field in ("authors", "venue", "version", "abstract"):
            if not merged["bibliographic"].get(field) and item["bibliographic"].get(field):
                merged["bibliographic"][field] = item["bibliographic"][field]
        if not merged["bibliographic"].get("year") and item["bibliographic"].get("year"):
            merged["bibliographic"]["year"] = item["bibliographic"]["year"]
        if item["source"].get("is_primary") and not merged["source"].get("is_primary"):
            merged["source"] = item["source"]
        merged["metrics"].update({key: value for key, value in item["metrics"].items() if value is not None})
        merged["metadata"].update({key: value for key, value in item["metadata"].items() if value not in (None, "", [])})
    merged["record_id"] = stable_record_id(merged["canonical_ids"], merged["bibliographic"]["title"], merged["bibliographic"]["year"])
    return validate_record(merged)


def dedupe_key(record: Dict[str, Any]) -> str:
    value = normalize_legacy_record(record)
    ids = value["canonical_ids"]
    for namespace in ("doi", "arxiv", "openreview", "semantic_scholar"):
        if ids.get(namespace):
            return f"{namespace}:{ids[namespace]}"
    return f"title:{normalize_title(value['bibliographic']['title'])}:{value['bibliographic'].get('year') or ''}"
