#!/usr/bin/env python3
"""Run-level canonical literature registry and paper-usage ledger."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from citations import bibtex_entries, citation_key_base, dedupe_with_report
from literature.record_schema import canonical_json_sha256, normalize_legacy_record, validate_record
from state_store import file_sha256, read_json, update_json, utc_now, write_json


REGISTRY_SCHEMA_VERSION = 1
PURPOSES = {
    "application_evidence", "citation", "closest_work", "contextual_related_work",
    "discovery_candidate", "empirical_baseline", "method_source", "novelty_neighbor",
    "theorem_provenance",
}
USAGE_STATUSES = {"active", "reclassified", "withdrawn"}
THEOREM_LEVEL_PURPOSES = {"theorem_provenance", "closest_work", "novelty_neighbor"}
SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def registry_path(run_dir: Path) -> Path:
    return run_dir / "literature" / "registry.json"


def empty_registry(run_id: str) -> dict:
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "artifact": "literature_registry",
        "run_id": run_id,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "records": [],
        "aliases": {},
        "citation_keys": {},
        "merge_decisions": [],
        "conflicts": [],
        "usage": [],
        "queries": [],
        "raw_artifacts": [],
    }


def validate_registry(value: dict, run_id: str | None = None) -> dict:
    if not isinstance(value, dict) or value.get("schema_version") != REGISTRY_SCHEMA_VERSION or value.get("artifact") != "literature_registry":
        raise ValueError("unsupported literature registry schema")
    if run_id and value.get("run_id") != run_id:
        raise ValueError("literature registry belongs to another run")
    records = value.get("records")
    if not isinstance(records, list):
        raise ValueError("literature registry records must be a list")
    ids = set()
    for record in records:
        validate_record(record)
        if record["record_id"] in ids:
            raise ValueError(f"duplicate registry record: {record['record_id']}")
        ids.add(record["record_id"])
    aliases = value.get("aliases")
    if not isinstance(aliases, dict) or any(target not in ids for target in aliases.values()):
        raise ValueError("registry aliases must resolve to canonical records")
    keys = value.get("citation_keys")
    if not isinstance(keys, dict) or set(keys) != ids or len(set(keys.values())) != len(keys):
        raise ValueError("registry requires one unique citation key per canonical record")
    for key in keys.values():
        if not re.fullmatch(r"[a-z0-9]+", key):
            raise ValueError(f"invalid citation key: {key}")
    for field in ("merge_decisions", "conflicts", "usage", "queries", "raw_artifacts"):
        if not isinstance(value.get(field), list):
            raise ValueError(f"registry {field} must be a list")
    records_by_id = {item["record_id"]: item for item in records}
    usage_ids = set()
    for usage in value["usage"]:
        if usage.get("record_id") not in ids or usage.get("purpose") not in PURPOSES:
            raise ValueError("registry usage has an invalid record or purpose")
        status = usage.get("status", "active")
        if status not in USAGE_STATUSES:
            raise ValueError("registry usage has an invalid status")
        if status == "reclassified" and not usage.get("reclassified_to"):
            raise ValueError("reclassified registry usage must identify its replacement")
        if usage.get("usage_id") in usage_ids:
            raise ValueError("registry contains duplicate usage IDs")
        usage_ids.add(usage.get("usage_id"))
        if usage.get("record_sha256") != canonical_json_sha256(records_by_id[usage["record_id"]]):
            raise ValueError(f"registry usage is not bound to current record metadata: {usage.get('usage_id')}")
    for raw in value["raw_artifacts"]:
        if not isinstance(raw, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(raw.get("sha256") or "")):
            raise ValueError("registry raw artifacts require a SHA-256 digest")
        path = Path(str(raw.get("path") or ""))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("registry raw artifact path must stay inside the run")
    return value


def load_registry(run_dir: Path, *, create: bool = False) -> dict:
    path = registry_path(run_dir)
    if not path.exists():
        if not create:
            raise ValueError("literature registry does not exist")
        value = empty_registry(run_dir.name)
        # Empty registries have a valid empty citation-key map.
        write_json(path, value)
        return value
    value = validate_registry(read_json(path), run_dir.name)
    for raw in value["raw_artifacts"]:
        candidate = (run_dir / raw["path"]).resolve()
        try:
            candidate.relative_to(run_dir.resolve())
        except ValueError as exc:
            raise ValueError("registry raw artifact escapes the run") from exc
        if not candidate.is_file() or file_sha256(candidate) != raw["sha256"]:
            raise ValueError(f"registry raw artifact is missing or modified: {raw['path']}")
    return value


def resolve_record_id(registry: dict, record_id: str) -> str:
    aliases = registry.get("aliases", {})
    seen = set()
    while record_id in aliases and aliases[record_id] != record_id:
        if record_id in seen:
            raise ValueError("cyclic literature alias")
        seen.add(record_id)
        record_id = aliases[record_id]
    if record_id not in {item["record_id"] for item in registry["records"]}:
        raise ValueError(f"unknown literature record: {record_id}")
    return record_id


def ingest_records(run_dir: Path, records: Iterable[dict], *, stage: str = "literature_audit", purpose: str | None = None,
                   claim_ids: Iterable[str] = (), section_ids: Iterable[str] = (), source_artifact: str = "",
                   evidence_locator: str = "", actor: str = "codex") -> dict:
    incoming = [normalize_legacy_record(item) for item in records]
    claim_ids, section_ids = list(claim_ids), list(section_ids)
    if not incoming:
        return load_registry(run_dir, create=True)
    if purpose and purpose not in PURPOSES:
        raise ValueError(f"unsupported literature purpose: {purpose}")
    if not SAFE_LABEL.fullmatch(stage) or not SAFE_LABEL.fullmatch(actor):
        raise ValueError("stage and actor must be safe identifiers")

    def transform(value):
        if value.get("artifact") != "literature_registry":
            raise ValueError("invalid literature registry")
        report = dedupe_with_report([*value.get("records", []), *incoming])
        previous_aliases = value.get("aliases", {})
        previous_keys = value.get("citation_keys", {})
        aliases = dict(report["aliases"])
        for alias, target in previous_aliases.items():
            aliases[alias] = aliases.get(target, target)
        value["records"] = report["references"]
        value["aliases"] = dict(sorted(aliases.items()))
        for usage in value["usage"]:
            usage["record_id"] = value["aliases"].get(usage["record_id"], usage["record_id"])
            canonical_record = next(item for item in value["records"] if item["record_id"] == usage["record_id"])
            usage["record_sha256"] = canonical_json_sha256(canonical_record)
        value["merge_decisions"].extend(report["merge_decisions"])
        value["conflicts"].extend(report["conflicts"])
        stable_keys, occupied = {}, set()
        for old_id, old_key in sorted(previous_keys.items()):
            canonical = value["aliases"].get(old_id, old_id)
            if canonical in {item["record_id"] for item in value["records"]} and canonical not in stable_keys and old_key not in occupied:
                stable_keys[canonical] = old_key
                occupied.add(old_key)
        for record in value["records"]:
            if record["record_id"] in stable_keys:
                continue
            base, candidate, suffix = citation_key_base(record), citation_key_base(record), 0
            while candidate in occupied:
                suffix += 1
                disambiguator = chr(ord("a") + suffix - 1) if suffix <= 26 else str(suffix)
                candidate = f"{base}{disambiguator}"
            stable_keys[record["record_id"]] = candidate
            occupied.add(candidate)
        value["citation_keys"] = dict(sorted(stable_keys.items()))
        if purpose:
            existing = {
                (item["record_id"], item["stage"], item["purpose"], tuple(item["claim_ids"]), tuple(item["section_ids"]), item.get("source_artifact", ""))
                for item in value["usage"] if item.get("status", "active") == "active"
            }
            for original in incoming:
                canonical = value["aliases"].get(original["record_id"], original["record_id"])
                key = (canonical, stage, purpose, tuple(claim_ids), tuple(section_ids), source_artifact)
                if key in existing:
                    continue
                record = next(item for item in value["records"] if item["record_id"] == canonical)
                value["usage"].append({
                    "usage_id": f"USE-{len(value['usage']) + 1:05d}", "record_id": canonical,
                    "stage": stage, "purpose": purpose, "claim_ids": list(claim_ids),
                    "section_ids": list(section_ids), "source_artifact": source_artifact,
                    "evidence_locator": evidence_locator, "actor": actor, "recorded_at": utc_now(),
                    "record_sha256": canonical_json_sha256(record),
                    "status": "active",
                })
        value["updated_at"] = utc_now()
        return value

    path = registry_path(run_dir)
    return validate_registry(update_json(path, transform, empty_registry(run_dir.name)), run_dir.name)


def register_usage(run_dir: Path, record_ids: Iterable[str], **kwargs) -> dict:
    registry = load_registry(run_dir)
    canonical_ids = [resolve_record_id(registry, item) for item in record_ids]
    stage = kwargs.get("stage", "literature_audit")
    purpose = kwargs.get("purpose")
    actor = kwargs.get("actor", "codex")
    claim_ids = list(kwargs.get("claim_ids", ()))
    section_ids = list(kwargs.get("section_ids", ()))
    source_artifact = kwargs.get("source_artifact", "")
    evidence_locator = kwargs.get("evidence_locator", "")
    if purpose not in PURPOSES:
        raise ValueError(f"unsupported literature purpose: {purpose}")
    if not SAFE_LABEL.fullmatch(stage) or not SAFE_LABEL.fullmatch(actor):
        raise ValueError("stage and actor must be safe identifiers")

    def transform(value):
        records = {item["record_id"]: item for item in value["records"]}
        existing = {
            (item["record_id"], item["stage"], item["purpose"], tuple(item["claim_ids"]),
             tuple(item["section_ids"]), item.get("source_artifact", ""))
            for item in value["usage"] if item.get("status", "active") == "active"
        }
        for record_id in canonical_ids:
            key = (record_id, stage, purpose, tuple(claim_ids), tuple(section_ids), source_artifact)
            if key in existing:
                continue
            value["usage"].append({
                "usage_id": f"USE-{len(value['usage']) + 1:05d}", "record_id": record_id,
                "stage": stage, "purpose": purpose, "claim_ids": claim_ids,
                "section_ids": section_ids, "source_artifact": source_artifact,
                "evidence_locator": evidence_locator, "actor": actor, "recorded_at": utc_now(),
                "record_sha256": canonical_json_sha256(records[record_id]),
                "status": "active",
            })
        value["updated_at"] = utc_now()
        return value

    return validate_registry(update_json(registry_path(run_dir), transform, registry), run_dir.name)


def reclassify_usage(
    run_dir: Path,
    record_ids: Iterable[str],
    *,
    from_purposes: Iterable[str],
    to_purpose: str,
    actor: str,
    reason: str,
) -> dict:
    """Reclassify active evidence links without deleting their audit history."""
    registry = load_registry(run_dir)
    canonical_ids = {resolve_record_id(registry, item) for item in record_ids}
    source_purposes = set(from_purposes)
    if not canonical_ids:
        raise ValueError("reclassification requires at least one literature record")
    if not source_purposes or not source_purposes <= PURPOSES:
        raise ValueError("reclassification has an unsupported source purpose")
    if to_purpose not in PURPOSES:
        raise ValueError(f"unsupported literature purpose: {to_purpose}")
    if to_purpose in source_purposes:
        raise ValueError("replacement purpose must differ from every source purpose")
    if not SAFE_LABEL.fullmatch(actor):
        raise ValueError("actor must be a safe identifier")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 4_000:
        raise ValueError("reclassification reason must contain 1-4000 characters")

    def transform(value):
        records = {item["record_id"]: item for item in value["records"]}
        active_replacements = {
            (item["record_id"], item["stage"], item["purpose"], tuple(item["claim_ids"]),
             tuple(item["section_ids"]), item.get("source_artifact", "")): item["usage_id"]
            for item in value["usage"] if item.get("status", "active") == "active"
        }
        matched = []
        for item in value["usage"]:
            if (
                item.get("status", "active") == "active"
                and item["record_id"] in canonical_ids
                and item["purpose"] in source_purposes
            ):
                matched.append(item)
        if not matched:
            raise ValueError("no active literature uses matched the requested reclassification")
        changed_at = utc_now()
        for item in matched:
            replacement_key = (
                item["record_id"], item["stage"], to_purpose, tuple(item["claim_ids"]),
                tuple(item["section_ids"]), item.get("source_artifact", ""),
            )
            replacement_id = active_replacements.get(replacement_key)
            if replacement_id is None:
                replacement_id = f"USE-{len(value['usage']) + 1:05d}"
                replacement = {
                    "usage_id": replacement_id,
                    "record_id": item["record_id"],
                    "stage": item["stage"],
                    "purpose": to_purpose,
                    "claim_ids": list(item["claim_ids"]),
                    "section_ids": list(item["section_ids"]),
                    "source_artifact": item.get("source_artifact", ""),
                    "evidence_locator": item.get("evidence_locator", ""),
                    "actor": actor,
                    "recorded_at": changed_at,
                    "record_sha256": canonical_json_sha256(records[item["record_id"]]),
                    "status": "active",
                    "reclassified_from": item["usage_id"],
                    "reclassification_reason": reason.strip(),
                }
                value["usage"].append(replacement)
                active_replacements[replacement_key] = replacement_id
            item["status"] = "reclassified"
            item["reclassified_to"] = replacement_id
            item["reclassified_at"] = changed_at
            item["reclassified_by"] = actor
            item["reclassification_reason"] = reason.strip()
        value["updated_at"] = changed_at
        return value

    return validate_registry(
        update_json(registry_path(run_dir), transform, registry), run_dir.name
    )


def record_query(run_dir: Path, *, source: str, arguments: list[str], raw_path: str, raw_sha256: str,
                 status: str, record_count: int) -> dict:
    def transform(value):
        value["queries"].append({
            "query_id": f"QUERY-{len(value['queries']) + 1:05d}", "source": source,
            "arguments": arguments, "executed_at": utc_now(), "status": status,
            "record_count": record_count, "raw_artifact": raw_path, "raw_sha256": raw_sha256,
        })
        if raw_path:
            value["raw_artifacts"].append({"path": raw_path, "sha256": raw_sha256, "scope": "adapter_output"})
        value["updated_at"] = utc_now()
        return value
    return validate_registry(update_json(registry_path(run_dir), transform, empty_registry(run_dir.name)), run_dir.name)


def export_bibtex(run_dir: Path, output: Path, *, selected_record_ids=None) -> dict:
    registry = load_registry(run_dir)
    selected = [resolve_record_id(registry, item) for item in (selected_record_ids or [])]
    content, keys = bibtex_entries(
        registry["records"], selected_record_ids=selected, citation_keys=registry["citation_keys"]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return {"output": str(output), "entries": len(keys), "citation_keys": keys}


def coverage_report(registry: dict) -> dict:
    validate_registry(registry, registry.get("run_id"))
    active_usage = [
        item for item in registry["usage"] if item.get("status", "active") == "active"
    ]
    used = {item["record_id"] for item in active_usage}
    statuses = {item["record_id"]: item["verification"]["status"] for item in registry["records"]}
    insufficient = []
    for usage in active_usage:
        status = statuses[usage["record_id"]]
        if usage["purpose"] == "discovery_candidate":
            continue
        requires_theorem = usage["purpose"] in THEOREM_LEVEL_PURPOSES
        if requires_theorem and status != "primary_source_verified":
            insufficient.append({"record_id": usage["record_id"], "purpose": usage["purpose"], "status": status})
        elif not requires_theorem and status in {"lead", "extraction_failed"}:
            insufficient.append({"record_id": usage["record_id"], "purpose": usage["purpose"], "status": status})
    return {
        "complete": not insufficient,
        "used_records": len(used),
        "active_usage": len(active_usage),
        "inactive_usage": len(registry["usage"]) - len(active_usage),
        "insufficient_verification": insufficient,
        "registered_but_unused": sorted({item["record_id"] for item in registry["records"]} - used),
    }


def seed_from_theory_bundle(run_dir: Path) -> dict:
    """Register every canonical paper embedded in the immutable theory handoff."""
    bundle_path = run_dir / "artifacts" / "theory_bundle.json"
    load_registry(run_dir, create=True)
    if not bundle_path.is_file():
        return load_registry(run_dir)
    bundle = read_json(bundle_path)
    found = []

    def visit(value):
        if isinstance(value, dict):
            if value.get("record_type") == "literature_record":
                found.append(value)
                return
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(bundle)
    if not found:
        return load_registry(run_dir)
    ingest_records(run_dir, found, stage="theory_handoff", purpose=None, actor="system")
    purpose_for_role = {
        "theorem_provenance": "theorem_provenance",
        "novelty_neighbor": "novelty_neighbor",
        "closest_work": "closest_work",
        "contextual_related_work": "contextual_related_work",
        "method_source": "method_source",
        "empirical_baseline": "empirical_baseline",
        "application_evidence": "application_evidence",
    }
    groups = {}
    for record in found:
        role = record.get("metadata", {}).get("role", "")
        purpose = purpose_for_role.get(role, "discovery_candidate")
        groups.setdefault(purpose, []).append(record["record_id"])
    for purpose, record_ids in groups.items():
        register_usage(
            run_dir, record_ids, stage="theory_handoff", purpose=purpose,
            source_artifact="artifacts/theory_bundle.json", actor="system",
        )
    return load_registry(run_dir)


def raw_output_path(run_dir: Path, source: str, payload: str) -> tuple[Path, str]:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    path = run_dir / "literature" / "raw" / f"{source}-{digest[:16]}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path, digest
