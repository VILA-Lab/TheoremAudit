#!/usr/bin/env python3
"""List, audit, and safely stage packaged venue assets into a paper run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from audit_templates import audit
from state_store import file_sha256, read_json, utc_now, write_json
from tool_utils import paper_dir


ASSETS = Path(__file__).resolve().parents[1] / "assets" / "conference-templates"
COPY_SUFFIXES = {".sty", ".cls", ".bst", ".tex"}
def canonical_sha256(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def venue_metadata(venue: str):
    directory = ASSETS / venue.lower()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"unknown packaged venue: {venue}")
    paths = list(directory.glob("*_template.json"))
    if len(paths) != 1:
        raise ValueError(f"venue {venue} must have exactly one metadata file")
    if paths[0].is_symlink():
        raise ValueError(f"venue {venue} metadata cannot be a symbolic link")
    try:
        metadata = json.loads(paths[0].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"venue {venue} metadata is invalid: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"venue {venue} metadata must be an object")
    return directory, metadata


def command_list(args):
    print(json.dumps(audit(ASSETS), indent=2))


def venue_candidates(run_dir: Path) -> dict:
    """Return the evidence-compatible venues without ranking or selecting one."""
    bundle = read_json(run_dir / "artifacts" / "theory_bundle.json")
    route = bundle.get("paper_route", {})
    audited = audit(ASSETS)
    manuscript_kind = route.get("manuscript_kind")
    if manuscript_kind not in {"full_paper", "evidence_report"}:
        manuscript_kind = "full_paper" if route.get("full_length_allowed") is True else "evidence_report"
    candidates = []
    for item in audited.get("venues", []):
        if item.get("local_staging_allowed") is not True:
            continue
        venue = str(item.get("venue", ""))
        _, metadata = venue_metadata(venue)
        neutral = metadata.get("neutral_draft") is True
        if manuscript_kind == "full_paper" and neutral:
            continue
        if manuscript_kind == "evidence_report" and not neutral:
            continue
        candidates.append({
            "venue": venue,
            "full_name": metadata.get("full_name"),
            "publication_format": metadata.get("publication_format"),
            "world_fit": metadata.get("world_fit", []),
            "page_limit": metadata.get("page_limit"),
            "page_limit_scope": metadata.get("page_limit_scope"),
            "references_start_new_page": metadata.get("references_start_new_page", False),
            "appendix": metadata.get("appendix"),
            "format": metadata.get("format"),
            "empirical_expected": metadata.get("empirical_expected"),
            "theory_track": metadata.get("theory_track"),
            "theory_bar": metadata.get("theory_bar"),
            "novelty_bar": metadata.get("novelty_bar"),
            "blind_review": metadata.get("blind_review"),
            "notes": metadata.get("notes"),
            "neutral_draft": neutral,
            "official_rules_verified": item.get("official_rules_verified") is True,
            "official_rules_fresh": item.get("official_rules_fresh") is True,
            "submission_ready": item.get("submission_ready") is True,
            "local_staging_allowed": True,
            "audit_findings": item.get("findings", []),
            "metadata_sha256": item.get("metadata_sha256"),
        })
    candidates.sort(key=lambda item: item["venue"].casefold())
    context = route.get("venue_selection_context")
    if not isinstance(context, dict):
        context = {
            "manuscript_kind": manuscript_kind,
            "submission_readiness": route.get("submission_readiness"),
            "novelty_verdict": route.get("novelty_verdict"),
            "significance_level": route.get("significance_level"),
            "empirical_requirement": (route.get("empirical_requirements") or {}).get("status"),
            "selected_statement_count": len(route.get("selected_statement_ids", [])),
        }
    payload = {
        "schema_version": 1,
        "artifact": "venue_candidate_set",
        "theory_bundle_sha256": file_sha256(run_dir / "artifacts" / "theory_bundle.json"),
        "selection_context": context,
        "selection_requirements": {
            "decision_owner": "venue_formatter_agent",
            "minimum_comparisons": min(3, len(candidates)),
            "comparison_axes": [
                "contribution_fit",
                "theorem_and_proof_fit",
                "empirical_fit",
                "length_and_appendix_fit",
                "template_and_rule_status",
            ],
            "order_carries_preference": False,
        },
        "candidates": candidates,
    }
    payload["candidate_set_sha256"] = canonical_sha256(payload)
    return payload


def command_candidates(args):
    root = paper_dir(args.workspace, args.run)
    print(json.dumps(venue_candidates(root.parent), indent=2))


def command_recommend(args):
    """Backward-compatible alias that no longer makes a recommendation."""
    command_candidates(args)


def command_stage(args):
    root = paper_dir(args.workspace, args.run)
    source, metadata = venue_metadata(args.venue)
    audit_result = audit(ASSETS)
    matches = [
        item for item in audit_result["venues"]
        if str(item.get("venue", "")).casefold() == str(metadata.get("venue", args.venue)).casefold()
    ]
    if len(matches) != 1:
        raise ValueError(f"venue audit could not uniquely identify {args.venue}")
    venue_audit = matches[0]
    if not venue_audit["local_staging_allowed"]:
        blocking = [
            item["code"] for item in venue_audit["findings"]
            if item["severity"] in {"error", "fatal"}
        ]
        raise ValueError(
            f"venue {args.venue} failed package-integrity audit and cannot be staged: {blocking}"
        )
    metadata_path = next(source.glob("*_template.json"))
    if file_sha256(metadata_path) != venue_audit["metadata_sha256"]:
        raise ValueError("venue metadata changed during audit; retry staging")
    selection_path = root / "venue_selection.json"
    selection_sha256 = None
    if selection_path.is_file():
        selection = read_json(selection_path)
        selected = str(selection.get("venue", ""))
        if selected and selected.casefold() != str(metadata.get("venue", args.venue)).casefold():
            raise ValueError(f"staged venue {args.venue} does not match venue_selection.json ({selected})")
        selection_sha256 = file_sha256(selection_path)
    reason = getattr(args, "reason", None)
    target = root / "venue"
    if target.is_symlink():
        raise ValueError("paper venue directory cannot be a symbolic link")
    existing = list(target.iterdir()) if target.exists() else []
    old_snapshot = target / "venue_snapshot.json"
    old_venue = ""
    if old_snapshot.exists():
        old_venue = json.loads(old_snapshot.read_text(encoding="utf-8")).get("venue", "")
        if old_venue.lower() != str(metadata.get("venue", args.venue)).lower() and not args.replace:
            raise ValueError("changing venues requires --replace and --reason")
    if existing and not args.replace:
        raise ValueError("paper venue directory is not empty; pass --replace to replace individual assets")
    if existing and args.replace and not reason:
        raise ValueError("replacing staged venue assets requires --reason")
    temporary = Path(tempfile.mkdtemp(prefix=".venue-stage-", dir=root))
    copied = []
    asset_hashes = {}
    try:
        for asset in venue_audit["assets"]:
            if not asset["stage"]:
                continue
            item = source / asset["path"]
            if item.suffix.lower() not in COPY_SUFFIXES:
                raise ValueError(f"venue audit exposed an unsupported staged asset: {item.name}")
            if file_sha256(item) != asset["sha256"]:
                raise ValueError(f"venue asset changed during audit: {item.name}")
            destination = temporary / item.name
            shutil.copy2(item, destination)
            if file_sha256(destination) != asset["sha256"]:
                raise ValueError(f"staged venue asset failed hash verification: {item.name}")
            copied.append(item.name)
            asset_hashes[item.name] = asset["sha256"]
        snapshot = {
            "schema_version": 3,
            "artifact": "venue_snapshot",
            "venue": metadata.get("venue", args.venue),
            "staged_at": utc_now(),
            "replacement_reason": reason if existing else None,
            "source_metadata": metadata,
            "source_metadata_sha256": venue_audit["metadata_sha256"],
            "venue_selection_sha256": selection_sha256,
            "copied_assets": copied,
            "asset_sha256": asset_hashes,
            "package_integrity_verified": True,
            "development_snapshot": True,
            "official_rules_verified": venue_audit["official_rules_verified"],
            "official_rules_fresh": venue_audit.get("official_rules_fresh", False),
            "submission_ready": venue_audit["submission_ready"],
            "redistribution_status": venue_audit["redistribution_status"],
            "redistribution_allowed": venue_audit["redistribution_allowed"],
            "audit_findings": venue_audit["findings"],
            "audit_record_sha256": canonical_sha256(venue_audit),
            "notice": "Verify current official rules and redistribution rights before submission or release.",
        }
        snapshot["snapshot_payload_sha256"] = canonical_sha256(snapshot)
        write_json(temporary / "venue_snapshot.json", snapshot)
        (temporary / ".venue_snapshot.json.lock").unlink(missing_ok=True)
        archive = None
        if target.exists():
            if existing:
                history = root / "venue-history"
                history.mkdir(parents=True, exist_ok=True)
                archive = history / f"{utc_now().replace(':', '-')}-{old_venue or 'venue'}"
                os.replace(target, archive)
            else:
                target.rmdir()
        try:
            os.replace(temporary, target)
        except OSError:
            if archive is not None and archive.exists() and not target.exists():
                os.replace(archive, target)
            raise
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)
    print(json.dumps(snapshot, indent=2))


def command_verify(args):
    root = paper_dir(args.workspace, args.run)
    target = root / "venue"
    snapshot = read_json(target / "venue_snapshot.json")
    if snapshot.get("schema_version") != 3 or snapshot.get("artifact") != "venue_snapshot":
        raise ValueError("staged venue snapshot has an unsupported schema")
    expected_payload_hash = snapshot.get("snapshot_payload_sha256")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_payload_sha256"}
    findings = []
    if canonical_sha256(payload) != expected_payload_hash:
        findings.append("venue snapshot payload was modified")
    expected_files = set(snapshot.get("copied_assets", []))
    if len(expected_files) != len(snapshot.get("copied_assets", [])):
        findings.append("venue snapshot contains duplicate asset names")
    if set(snapshot.get("asset_sha256", {})) != expected_files:
        findings.append("venue snapshot asset hashes do not match copied_assets")
    actual_files = {
        item.name for item in target.iterdir()
        if item.name != "venue_snapshot.json" and not item.name.startswith(".")
    }
    if actual_files != expected_files:
        findings.append("staged venue file set differs from the snapshot")
    for name, digest in snapshot.get("asset_sha256", {}).items():
        path = target / name
        if not path.is_file() or path.is_symlink() or file_sha256(path) != digest:
            findings.append(f"staged asset is missing or modified: {name}")
    result = {"valid": not findings, "venue": snapshot.get("venue"), "findings": findings}
    if findings:
        raise ValueError("; ".join(findings))
    print(json.dumps(result, indent=2))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("list").set_defaults(function=command_list)
    commands.add_parser("candidates").set_defaults(function=command_candidates)
    commands.add_parser("recommend").set_defaults(function=command_recommend)
    stage = commands.add_parser("stage")
    stage.add_argument("--venue", required=True)
    stage.add_argument("--replace", action="store_true")
    stage.add_argument("--reason")
    stage.set_defaults(function=command_stage)
    commands.add_parser("verify").set_defaults(function=command_verify)
    return result


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
