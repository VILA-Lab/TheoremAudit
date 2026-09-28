#!/usr/bin/env python3
"""Audit packaged venue snapshots for integrity, provenance, and safe local staging."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse


SCHEMA_VERSION = 2
METADATA_SCHEMA_VERSION = 2
PACKAGED_SUFFIXES = {".sty", ".cls", ".bst", ".tex"}
ASSET_ROLES = {"style", "bibliography", "main_tex", "checklist", "support"}
REDISTRIBUTION_STATUSES = {"verified", "restricted", "unverified"}
BLOCKING_SEVERITIES = {"error", "fatal"}
MAX_ASSET_BYTES = 5 * 1024 * 1024
ROLE_SUFFIXES = {
    "style": {".sty", ".cls"},
    "bibliography": {".bst"},
    "main_tex": {".tex"},
    "checklist": {".tex"},
    "support": {".sty", ".cls", ".tex", ".bst"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finding(severity: str, code: str, message: str, path: Optional[str] = None) -> dict:
    value = {"severity": severity, "code": code, "message": message}
    if path:
        value["path"] = path
    return value


def safe_asset_path(directory: Path, supplied: Any) -> Path:
    if not isinstance(supplied, str) or not supplied.strip():
        raise ValueError("asset path must be non-empty text")
    relative = Path(supplied)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
        raise ValueError("asset path must be one contained filename")
    root = directory.resolve()
    candidate = directory / relative
    if candidate.is_symlink():
        raise ValueError("asset cannot be a symbolic link")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("asset path escapes its template directory") from exc
    return resolved


def required_text(metadata: dict, field: str, findings: List[dict]) -> Optional[str]:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        findings.append(finding("error", "invalid_metadata_field", f"{field} must be non-empty text"))
        return None
    return value.strip()


def audit_assets(directory: Path, metadata: dict, findings: List[dict]) -> List[dict]:
    raw_assets = metadata.get("assets")
    if not isinstance(raw_assets, list) or not raw_assets:
        findings.append(finding("error", "missing_asset_manifest", "assets must be a non-empty list"))
        return []
    audited: List[dict] = []
    seen_paths: Set[str] = set()
    seen_roles: Dict[str, int] = {}
    for position, raw in enumerate(raw_assets):
        label = f"assets[{position}]"
        if not isinstance(raw, dict):
            findings.append(finding("error", "invalid_asset_record", f"{label} must be an object"))
            continue
        supplied = raw.get("path")
        role = raw.get("role")
        required = raw.get("required")
        stage = raw.get("stage", True)
        if role not in ASSET_ROLES:
            findings.append(finding("error", "invalid_asset_role", f"{label}.role is invalid"))
        if not isinstance(required, bool):
            findings.append(finding("error", "invalid_asset_required", f"{label}.required must be boolean"))
            required = True
        if not isinstance(stage, bool):
            findings.append(finding("error", "invalid_asset_stage", f"{label}.stage must be boolean"))
            stage = True
        try:
            path = safe_asset_path(directory, supplied)
        except ValueError as exc:
            findings.append(finding("fatal", "unsafe_asset_path", f"{label}: {exc}", str(supplied)))
            continue
        filename = path.name
        if filename in seen_paths:
            findings.append(finding("error", "duplicate_asset", f"asset is declared more than once: {filename}", filename))
            continue
        seen_paths.add(filename)
        if isinstance(role, str):
            seen_roles[role] = seen_roles.get(role, 0) + 1
        if stage and path.suffix.lower() not in PACKAGED_SUFFIXES:
            findings.append(finding("error", "unstageable_asset", f"staged asset type is not allowed: {filename}", filename))
        if stage and role in ROLE_SUFFIXES and path.suffix.lower() not in ROLE_SUFFIXES[role]:
            findings.append(finding(
                "error", "asset_role_suffix_mismatch",
                f"{role} asset has an incompatible suffix: {filename}", filename,
            ))
        exists = path.is_file()
        if required and not exists:
            findings.append(finding("error", "missing_required_asset", f"required asset is missing: {filename}", filename))
        elif not required and not exists:
            findings.append(finding("warning", "missing_optional_asset", f"optional asset is missing: {filename}", filename))
        size = path.stat().st_size if exists else None
        if size is not None and size > MAX_ASSET_BYTES:
            findings.append(finding("error", "asset_too_large", f"asset exceeds {MAX_ASSET_BYTES} bytes", filename))
        if exists and path.suffix.lower() in {".sty", ".cls", ".tex"}:
            try:
                source = path.read_text(encoding="utf-8")
            except UnicodeError:
                findings.append(finding("error", "non_utf8_latex_asset", "LaTeX asset is not UTF-8", filename))
            else:
                if "\\write18" in source or "\\immediate\\write18" in source:
                    findings.append(finding("fatal", "shell_escape_in_asset", "LaTeX asset invokes shell escape", filename))
        audited.append({
            "path": filename,
            "role": role,
            "required": required,
            "stage": stage,
            "exists": exists,
            "sha256": sha256(path) if exists else None,
            "size_bytes": size,
        })
    if seen_roles.get("style", 0) != 1:
        findings.append(finding("error", "style_role_count", "assets must declare exactly one style asset"))
    for role in ("bibliography", "main_tex", "checklist"):
        if seen_roles.get(role, 0) > 1:
            findings.append(finding("error", "asset_role_count", f"assets may declare at most one {role} asset"))

    declared_hashes = metadata.get("asset_sha256")
    if declared_hashes is not None:
        if not isinstance(declared_hashes, dict) or set(declared_hashes) != seen_paths:
            findings.append(finding("error", "invalid_asset_hash_manifest", "asset_sha256 must map every declared asset exactly"))
        else:
            for item in audited:
                expected = declared_hashes.get(item["path"])
                if not isinstance(expected, str) or len(expected) != 64:
                    findings.append(finding("error", "invalid_declared_asset_hash", "declared asset hash must be SHA-256", item["path"]))
                elif item["sha256"] and expected.lower() != item["sha256"]:
                    findings.append(finding("fatal", "asset_hash_mismatch", "asset differs from its declared SHA-256", item["path"]))

    declared = set(seen_paths)
    actual = {
        item.name for item in directory.iterdir()
        if item.is_file() and not item.is_symlink() and item.suffix.lower() in PACKAGED_SUFFIXES
    }
    for filename in sorted(actual - declared):
        findings.append(finding("warning", "undeclared_packaged_asset", f"packaged asset is not declared: {filename}", filename))
    return audited


def cross_validate_metadata(metadata: dict, assets: List[dict], findings: List[dict]) -> None:
    role_paths = {item["role"]: item["path"] for item in assets if isinstance(item.get("role"), str)}
    style_file = metadata.get("style_file")
    if style_file != role_paths.get("style"):
        findings.append(finding("error", "style_mismatch", "style_file must match the declared style asset"))
    mappings = (("main_tex", "main_tex"), ("checklist_file", "checklist"))
    for field, role in mappings:
        value = metadata.get(field)
        if value is not None and value != role_paths.get(role):
            findings.append(finding("error", "asset_role_mismatch", f"{field} must match the {role} asset"))
        if role in role_paths and value is None:
            findings.append(finding("error", "missing_asset_mapping", f"{field} is required when a {role} asset is declared"))
    bibstyle = metadata.get("bibstyle")
    if bibstyle:
        expected = bibstyle if str(bibstyle).endswith(".bst") else f"{bibstyle}.bst"
        bibliography = role_paths.get("bibliography")
        # Standard TeX styles such as plainnat need not be packaged.
        if bibliography is not None and bibliography != expected:
            findings.append(finding("error", "bibliography_mismatch", "bibstyle does not match the bibliography asset"))
    if role_paths.get("bibliography") and not bibstyle:
        findings.append(finding("error", "missing_bibstyle", "bibstyle is required when a bibliography asset is declared"))
    files = metadata.get("files")
    if files is not None:
        if not isinstance(files, list) or len(files) != len(set(files)) or set(files) != {
            item["path"] for item in assets if item["stage"]
        }:
            findings.append(finding("error", "files_manifest_mismatch", "files must list every staged asset exactly"))
    class_options = metadata.get("class_options")
    if class_options is not None and (
        not isinstance(class_options, list)
        or len(class_options) != len(set(class_options))
        or any(not isinstance(item, str) or not item.strip() for item in class_options)
    ):
        findings.append(finding("error", "invalid_class_options", "class_options must contain unique non-empty strings"))
    for field in (
        "page_limit", "page_limit_scope", "publication_format",
        "blind_review", "empirical_expected", "theory_track",
    ):
        if field not in metadata:
            findings.append(finding("error", "missing_metadata_field", f"required metadata field is missing: {field}"))
    if metadata.get("page_limit") is not None and (
        not isinstance(metadata.get("page_limit"), int) or metadata["page_limit"] <= 0
    ):
        findings.append(finding("error", "invalid_page_limit", "page_limit must be null or a positive integer"))
    scope = metadata.get("page_limit_scope")
    if scope not in {"main_text", "main_plus_references", "total_manuscript", "none"}:
        findings.append(finding("error", "invalid_page_limit_scope", "page_limit_scope is invalid"))
    elif metadata.get("page_limit") is None and scope != "none":
        findings.append(finding(
            "error", "page_limit_scope_mismatch",
            "page_limit_scope must be none when page_limit is null",
        ))
    elif metadata.get("page_limit") is not None and scope == "none":
        findings.append(finding(
            "error", "page_limit_scope_mismatch",
            "a positive page_limit requires an applicable page_limit_scope",
        ))
    if metadata.get("publication_format") not in {"conference", "journal", "neutral"}:
        findings.append(finding(
            "error", "invalid_publication_format",
            "publication_format must be conference, journal, or neutral",
        ))
    for field in ("blind_review", "empirical_expected", "theory_track"):
        if field in metadata and not isinstance(metadata[field], bool):
            findings.append(finding("error", "invalid_metadata_field", f"{field} must be boolean"))
    if (
        "references_start_new_page" in metadata
        and not isinstance(metadata["references_start_new_page"], bool)
    ):
        findings.append(finding(
            "error", "invalid_metadata_field",
            "references_start_new_page must be boolean when declared",
        ))


def audit_metadata(metadata_path: Path) -> dict:
    directory = metadata_path.parent
    findings: List[dict] = []
    if directory.is_symlink() or metadata_path.is_symlink():
        findings.append(finding(
            "fatal", "symlink_template", "template directories and metadata files cannot be symbolic links"
        ))
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "venue": directory.name,
            "path": str(directory),
            "metadata_path": str(metadata_path),
            "metadata_sha256": sha256(metadata_path) if metadata_path.is_file() else None,
            "metadata_schema_version": None,
            "assets": [],
            "findings": [finding("fatal", "invalid_metadata_json", str(exc), metadata_path.name)],
            "integrity_valid": False,
            "local_staging_allowed": False,
            "official_rules_verified": False,
            "submission_ready": False,
            "redistribution_status": "unverified",
            "redistribution_allowed": False,
        }
    if not isinstance(metadata, dict):
        findings.append(finding("fatal", "invalid_metadata_root", "metadata root must be an object"))
        metadata = {}
    venue = required_text(metadata, "venue", findings) or directory.name
    if venue.casefold() != directory.name.casefold():
        findings.append(finding("error", "venue_directory_mismatch", "venue must match its directory name"))
    required_text(metadata, "full_name", findings)
    required_text(metadata, "format", findings)
    schema = metadata.get("schema_version")
    if schema != METADATA_SCHEMA_VERSION:
        findings.append(finding(
            "error", "unsupported_metadata_schema",
            f"schema_version must be {METADATA_SCHEMA_VERSION}; received {schema!r}",
        ))
    assets = audit_assets(directory, metadata, findings)
    cross_validate_metadata(metadata, assets, findings)

    provenance = metadata.get("snapshot_provenance")
    if not isinstance(provenance, dict):
        findings.append(finding("error", "missing_snapshot_provenance", "snapshot_provenance must be an object"))
        provenance = {}
    source_url = provenance.get("source_url")
    if source_url is not None:
        parsed = urlparse(source_url) if isinstance(source_url, str) else None
        if (
            parsed is None or parsed.scheme != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
        ):
            findings.append(finding("error", "invalid_source_url", "source_url must be a credential-free HTTPS URL"))
    captured_at = provenance.get("captured_at")
    if captured_at is None:
        findings.append(finding("warning", "snapshot_date_unknown", "snapshot capture date is unknown"))
    elif not isinstance(captured_at, str) or not captured_at.strip():
        findings.append(finding("error", "invalid_snapshot_date", "captured_at must be null or non-empty text"))
    official = provenance.get("official_rules_verified") is True
    rules_fresh = False
    if not official:
        findings.append(finding("warning", "official_rules_unverified", "current official venue rules have not been verified"))
    elif (
        not source_url
        or not isinstance(provenance.get("official_rules_verified_at"), str)
        or not provenance["official_rules_verified_at"].strip()
    ):
        findings.append(finding(
            "error", "incomplete_official_verification",
            "official verification requires source_url and official_rules_verified_at",
        ))
    else:
        try:
            verified_at = datetime.fromisoformat(provenance["official_rules_verified_at"].replace("Z", "+00:00"))
            if verified_at.tzinfo is None:
                raise ValueError
            age_days = (datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)).days
            rules_fresh = 0 <= age_days <= 400
            if not rules_fresh:
                findings.append(finding("warning", "official_rules_stale", "official venue verification is older than 400 days"))
        except (TypeError, ValueError):
            findings.append(finding("error", "invalid_official_verification_date", "official_rules_verified_at must be an ISO-8601 timestamp"))
    redistribution = provenance.get("redistribution_status", "unverified")
    if redistribution not in REDISTRIBUTION_STATUSES:
        findings.append(finding("error", "invalid_redistribution_status", "invalid redistribution_status"))
        redistribution = "unverified"
    redistribution_evidence_valid = (
        isinstance(provenance.get("redistribution_evidence"), str)
        and bool(provenance["redistribution_evidence"].strip())
    )
    if redistribution != "verified":
        findings.append(finding("warning", "redistribution_unverified", "redistribution authorization is not verified"))
    elif not redistribution_evidence_valid:
        findings.append(finding(
            "error", "missing_redistribution_evidence",
            "verified redistribution status requires non-empty redistribution_evidence",
        ))

    integrity_valid = not any(item["severity"] in BLOCKING_SEVERITIES for item in findings)
    local_staging = integrity_valid
    return {
        "venue": venue,
        "path": str(directory),
        "metadata_path": str(metadata_path),
        "metadata_sha256": sha256(metadata_path),
        "metadata_schema_version": schema,
        "assets": assets,
        "findings": findings,
        "integrity_valid": integrity_valid,
        "local_staging_allowed": local_staging,
        "official_rules_verified": official,
        "official_rules_fresh": rules_fresh,
        "submission_ready": bool(local_staging and official and rules_fresh),
        "redistribution_status": redistribution,
        "redistribution_allowed": redistribution == "verified" and redistribution_evidence_valid,
        "development_snapshot": True,
    }


def audit(root: Path) -> dict:
    resolved = root.resolve()
    root_findings: List[dict] = []
    if root.is_symlink():
        root_findings.append(finding("fatal", "symlink_root", "template root cannot be a symbolic link"))
    if not resolved.is_dir():
        root_findings.append(finding("fatal", "missing_template_root", "template root does not exist", str(root)))
        metadata_paths: List[Path] = []
    else:
        metadata_paths = []
        for directory in sorted(item for item in resolved.iterdir() if item.is_dir()):
            candidates = sorted(directory.glob("*_template.json"))
            if len(candidates) != 1:
                root_findings.append(finding(
                    "error", "metadata_file_count",
                    f"template directory must contain exactly one *_template.json: {directory.name}",
                    directory.name,
                ))
            metadata_paths.extend(candidates)
    venues = [audit_metadata(path) for path in metadata_paths]
    names: Dict[str, List[dict]] = {}
    for venue in venues:
        names.setdefault(str(venue["venue"]).casefold(), []).append(venue)
    for records in names.values():
        if len(records) > 1:
            label = records[0]["venue"]
            root_findings.append(finding("error", "duplicate_venue", f"venue is declared more than once: {label}"))
            for record in records:
                record["integrity_valid"] = False
                record["local_staging_allowed"] = False
                record["submission_ready"] = False
    if not venues:
        root_findings.append(finding("error", "no_templates", "no venue metadata files were found"))
    blocking = sum(
        1 for item in root_findings if item["severity"] in BLOCKING_SEVERITIES
    ) + sum(
        1 for venue in venues for item in venue["findings"]
        if item["severity"] in BLOCKING_SEVERITIES
    )
    warnings = sum(1 for item in root_findings if item["severity"] == "warning") + sum(
        1 for venue in venues for item in venue["findings"] if item["severity"] == "warning"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": "venue_template_audit",
        "root": str(resolved),
        "venues": venues,
        "findings": root_findings,
        "summary": {
            "venue_count": len(venues),
            "integrity_valid_count": sum(1 for venue in venues if venue["integrity_valid"]),
            "locally_stageable_count": sum(1 for venue in venues if venue["local_staging_allowed"]),
            "submission_ready_count": sum(1 for venue in venues if venue["submission_ready"]),
            "blocking_finding_count": blocking,
            "warning_count": warnings,
        },
        "notice": (
            "Package integrity does not establish current venue compliance or redistribution rights. "
            "Verify both independently before submission or public release."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2))


if __name__ == "__main__":
    main()
