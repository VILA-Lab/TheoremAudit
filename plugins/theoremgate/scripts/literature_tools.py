#!/usr/bin/env python3
"""Search, normalize, register, audit, and export TheoremAudit literature."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from citations import dedupe_with_report
from literature.record_schema import is_record, normalize_legacy_record, validate_record
from literature.registry import (
    PURPOSES, coverage_report, export_bibtex, ingest_records, load_registry, raw_output_path, record_query,
    reclassify_usage, register_usage, resolve_record_id, seed_from_theory_bundle, validate_registry,
)
from state_store import artifact_path, read_json, resolve_run, write_json
from tool_utils import workspace_path


HERE = Path(__file__).resolve().parent
ADAPTERS = {
    "arxiv": "search_arxiv.py", "semantic": "search_semantic.py",
    "openreview": "search_openreview.py", "jmlr": "search_jmlr.py",
    "fetch-paper": "fetch_paper.py", "chase-citations": "chase_citations.py",
}


def _workspace(args) -> Path:
    return Path(getattr(args, "workspace", ".")).resolve()


def _run(args) -> Path:
    return resolve_run(_workspace(args), getattr(args, "run", None))


def _path(args, supplied: str) -> Path:
    # Direct Python callers from older integrations remain compatible; CLI calls are contained.
    return workspace_path(_workspace(args), supplied) if hasattr(args, "workspace") else Path(supplied)


def _records(value, key="references") -> list[dict]:
    if isinstance(value, dict) and is_record(value):
        return [value]
    if isinstance(value, dict):
        value = value.get(key)
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        raise ValueError("input must be a literature record, list, or object containing the selected key")
    return [item for item in value if isinstance(item, dict)]


def _json_list(value: str, label: str) -> list[str]:
    try:
        result = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be a JSON list") from exc
    if not isinstance(result, list) or any(not isinstance(item, str) for item in result):
        raise ValueError(f"{label} must be a JSON list of strings")
    return result


def _adapter_arguments(args) -> list[str]:
    try:
        values = json.loads(args.arguments_json)
    except json.JSONDecodeError as exc:
        raise ValueError("--arguments-json must be a JSON list") from exc
    if not isinstance(values, list) or any(not isinstance(item, str) or "\x00" in item for item in values):
        raise ValueError("adapter arguments must be a JSON list of strings")
    if len(values) > 32 or any(len(item) > 4096 for item in values) or sum(map(len, values)) > 16384:
        raise ValueError("adapter arguments exceed the safe size limit")
    if not 1 <= args.timeout <= 300:
        raise ValueError("--timeout must be between 1 and 300 seconds")
    return values


def _invoke_adapter(source: str, values: list[str], timeout: int) -> str:
    script = HERE / "literature" / ADAPTERS[source]
    completed = subprocess.run(
        [sys.executable, str(script), *values], capture_output=True, text=True,
        timeout=timeout, check=False,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or f"adapter exited {completed.returncode}")
    return completed.stdout


def command_dedupe(args):
    report = dedupe_with_report(_records(read_json(_path(args, args.input)), args.key))
    if args.output:
        write_json(_path(args, args.output), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def command_run(args):
    print(_invoke_adapter(args.source, _adapter_arguments(args), args.timeout), end="")


def command_search_and_save(args):
    run_dir = _run(args)
    values = _adapter_arguments(args)
    load_registry(run_dir, create=True)
    try:
        payload = _invoke_adapter(args.source, values, args.timeout)
    except (ValueError, subprocess.TimeoutExpired):
        record_query(run_dir, source=args.source, arguments=values, raw_path="", raw_sha256="",
                     status="failed", record_count=0)
        raise
    raw_path, digest = raw_output_path(run_dir, args.source, payload)
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        record_query(run_dir, source=args.source, arguments=values,
                     raw_path=str(raw_path.relative_to(run_dir)), raw_sha256=digest,
                     status="malformed", record_count=0)
        raise ValueError("adapter returned malformed JSON") from exc
    if args.source == "chase-citations" and isinstance(decoded, dict):
        records = decoded.get("relevant_citations", [])
    else:
        records = decoded if isinstance(decoded, list) else [decoded]
    if any(not isinstance(item, dict) or not is_record(item) for item in records):
        record_query(run_dir, source=args.source, arguments=values,
                     raw_path=str(raw_path.relative_to(run_dir)), raw_sha256=digest,
                     status="invalid_records", record_count=0)
        raise ValueError("adapter output contains a non-canonical literature record")
    for index, record in enumerate(records):
        try:
            validate_record(record)
        except ValueError as exc:
            record_query(run_dir, source=args.source, arguments=values,
                         raw_path=str(raw_path.relative_to(run_dir)), raw_sha256=digest,
                         status="invalid_records", record_count=0)
            raise ValueError(f"adapter record[{index}] is invalid: {exc}") from exc
    registry = ingest_records(
        run_dir, records, stage=args.stage, purpose=args.purpose,
        claim_ids=_json_list(args.claims_json, "claims-json"),
        section_ids=_json_list(args.sections_json, "sections-json"),
        source_artifact=str(raw_path.relative_to(run_dir)), actor=args.actor,
    )
    registry = record_query(
        run_dir, source=args.source, arguments=values,
        raw_path=str(raw_path.relative_to(run_dir)), raw_sha256=digest,
        status="completed", record_count=len(records),
    )
    print(json.dumps({"saved": len(records), "registry_records": len(registry["records"]),
                      "raw_artifact": str(raw_path)}, indent=2))


def command_validate(args):
    records = _records(read_json(_path(args, args.input)), args.key)
    for index, record in enumerate(records):
        try:
            validate_record(record)
        except ValueError as exc:
            raise ValueError(f"record[{index}] is invalid: {exc}") from exc
    print(json.dumps({"valid": True, "count": len(records)}, indent=2))


def command_normalize(args):
    normalized = [normalize_legacy_record(record) for record in _records(read_json(_path(args, args.input)), args.key)]
    result = {"references": normalized}
    if args.output:
        write_json(_path(args, args.output), result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def command_ingest(args):
    run_dir = _run(args)
    records = _records(read_json(_path(args, args.input)), args.key)
    registry = ingest_records(
        run_dir, records, stage=args.stage, purpose=args.purpose,
        claim_ids=_json_list(args.claims_json, "claims-json"),
        section_ids=_json_list(args.sections_json, "sections-json"),
        source_artifact=args.source_artifact, evidence_locator=args.evidence_locator, actor=args.actor,
    )
    print(json.dumps({"registry": str(run_dir / 'literature' / 'registry.json'),
                      "records": len(registry["records"]), "usage": len(registry["usage"])}, indent=2))


def command_register_use(args):
    registry = register_usage(
        _run(args), _json_list(args.record_ids_json, "record-ids-json"), stage=args.stage,
        purpose=args.purpose, claim_ids=_json_list(args.claims_json, "claims-json"),
        section_ids=_json_list(args.sections_json, "sections-json"),
        source_artifact=args.source_artifact, evidence_locator=args.evidence_locator, actor=args.actor,
    )
    print(json.dumps({"registered": True, "usage": len(registry["usage"])}, indent=2))


def command_reclassify_use(args):
    registry = reclassify_usage(
        _run(args),
        _json_list(args.record_ids_json, "record-ids-json"),
        from_purposes=_json_list(args.from_purposes_json, "from-purposes-json"),
        to_purpose=args.to_purpose,
        actor=args.actor,
        reason=args.reason,
    )
    report = coverage_report(registry)
    print(json.dumps({
        "reclassified": True,
        "active_usage": report["active_usage"],
        "inactive_usage": report["inactive_usage"],
        "coverage_complete": report["complete"],
    }, indent=2))


def command_curate_novelty(args):
    """Keep a deliberate theorem-level shortlist and demote broad retrieval leads."""
    run_dir = _run(args)
    registry = load_registry(run_dir)
    keep = {
        resolve_record_id(registry, item)
        for item in _json_list(args.keep_record_ids_json, "keep-record-ids-json")
    }
    theorem_purposes = {"closest_work", "novelty_neighbor"}
    demote = sorted({
        item["record_id"]
        for item in registry["usage"]
        if item.get("status", "active") == "active"
        and item["purpose"] in theorem_purposes
        and item["record_id"] not in keep
    })
    if demote:
        registry = reclassify_usage(
            run_dir,
            demote,
            from_purposes=theorem_purposes,
            to_purpose="discovery_candidate",
            actor=args.actor,
            reason=args.reason,
        )
    report = coverage_report(registry)
    print(json.dumps({
        "curated": True,
        "kept_theorem_level_records": sorted(keep),
        "demoted_to_discovery_candidate": demote,
        "coverage": report,
    }, indent=2))


def command_registry(args):
    value = load_registry(_run(args), create=args.create)
    print(json.dumps(value, indent=2, ensure_ascii=False))


def command_seed_theory(args):
    registry = seed_from_theory_bundle(_run(args))
    print(json.dumps({"seeded": True, "records": len(registry["records"]),
                      "usage": len(registry["usage"])}, indent=2))


def command_validate_registry(args):
    value = validate_registry(load_registry(_run(args)), _run(args).name)
    print(json.dumps({"valid": True, "records": len(value["records"]),
                      "usage": len(value["usage"]), "queries": len(value["queries"])}, indent=2))


def command_export_bib(args):
    run_dir = _run(args)
    if args.output:
        supplied = Path(args.output)
        if supplied.is_absolute():
            output = supplied.resolve()
            try:
                output.relative_to(run_dir.resolve())
            except ValueError as exc:
                raise ValueError("BibTeX output must stay inside the selected run") from exc
        else:
            output = artifact_path(run_dir, args.output)
    else:
        output = run_dir / "paper" / "references.bib"
    result = export_bibtex(run_dir, output, selected_record_ids=_json_list(args.record_ids_json, "record-ids-json"))
    print(json.dumps(result, indent=2))


def command_coverage(args):
    print(json.dumps(coverage_report(load_registry(_run(args))), indent=2))


def _common_usage(parser, *, required: bool = True, default: str | None = None):
    parser.add_argument("--stage", default="literature_audit")
    parser.add_argument("--purpose", required=required, default=default, choices=sorted(PURPOSES))
    parser.add_argument("--claims-json", default="[]")
    parser.add_argument("--sections-json", default="[]")
    parser.add_argument("--source-artifact", default="")
    parser.add_argument("--evidence-locator", default="")
    parser.add_argument("--actor", default="codex")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    commands = result.add_subparsers(dest="command", required=True)
    dedupe = commands.add_parser("dedupe")
    dedupe.add_argument("--input", required=True); dedupe.add_argument("--output"); dedupe.add_argument("--key", default="references")
    dedupe.set_defaults(function=command_dedupe)
    run = commands.add_parser("run")
    run.add_argument("--source", required=True, choices=sorted(ADAPTERS)); run.add_argument("--arguments-json", required=True); run.add_argument("--timeout", type=int, default=120)
    run.set_defaults(function=command_run)
    search = commands.add_parser("search-and-save")
    search.add_argument("--source", required=True, choices=sorted(ADAPTERS)); search.add_argument("--arguments-json", required=True); search.add_argument("--timeout", type=int, default=120)
    _common_usage(search, required=False, default="discovery_candidate")
    search.set_defaults(function=command_search_and_save)
    validate = commands.add_parser("validate")
    validate.add_argument("--input", required=True); validate.add_argument("--key", default="references"); validate.set_defaults(function=command_validate)
    normalize = commands.add_parser("normalize")
    normalize.add_argument("--input", required=True); normalize.add_argument("--output"); normalize.add_argument("--key", default="references"); normalize.set_defaults(function=command_normalize)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--input", required=True); ingest.add_argument("--key", default="references"); _common_usage(ingest); ingest.set_defaults(function=command_ingest)
    use = commands.add_parser("register-use")
    use.add_argument("--record-ids-json", required=True); _common_usage(use); use.set_defaults(function=command_register_use)
    reclassify = commands.add_parser("reclassify-use")
    reclassify.add_argument("--record-ids-json", required=True)
    reclassify.add_argument("--from-purposes-json", required=True)
    reclassify.add_argument("--to-purpose", required=True, choices=sorted(PURPOSES))
    reclassify.add_argument("--reason", required=True)
    reclassify.add_argument("--actor", default="literature_auditor")
    reclassify.set_defaults(function=command_reclassify_use)
    curate = commands.add_parser("curate-novelty")
    curate.add_argument("--keep-record-ids-json", default="[]")
    curate.add_argument("--reason", required=True)
    curate.add_argument("--actor", default="literature_auditor")
    curate.set_defaults(function=command_curate_novelty)
    show = commands.add_parser("registry"); show.add_argument("--create", action="store_true"); show.set_defaults(function=command_registry)
    seed = commands.add_parser("seed-theory"); seed.set_defaults(function=command_seed_theory)
    valid_registry = commands.add_parser("validate-registry"); valid_registry.set_defaults(function=command_validate_registry)
    export = commands.add_parser("export-bib")
    export.add_argument("--output"); export.add_argument("--record-ids-json", default="[]"); export.set_defaults(function=command_export_bib)
    coverage = commands.add_parser("coverage"); coverage.set_defaults(function=command_coverage)
    return result


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, PermissionError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
