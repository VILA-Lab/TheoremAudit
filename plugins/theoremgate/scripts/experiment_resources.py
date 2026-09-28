#!/usr/bin/env python3
"""Acquire small, pinned public research assets separately from experiment execution."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import unquote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from state_store import file_sha256, read_json, utc_now, write_json
from tool_utils import contained, identifier, load_object_argument, locked_json_update, paper_dir


DEFAULT_POLICY = {
    "dataset_download_bytes": 100_000_000,
    "model_download_bytes": 500_000_000,
    "memory_mb": 2048,
    "experiment_seconds": 600,
    "run_seconds": 1800,
    "pilot_seconds": 30,
    "cpu_threads": 2,
    "output_bytes": 100_000_000,
}
FORMATS = {"dataset": {".csv", ".tsv", ".json", ".jsonl", ".parquet"},
           "model": {".json", ".txt", ".safetensors", ".model"}}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def store_path(root):
    return contained(root, "experiments/resources.json")


def empty_store():
    return {"schema_version": 1, "policy": dict(DEFAULT_POLICY), "resources": [],
            "transferred": {"dataset": 0, "model": 0}, "events": []}


def load_store(root):
    path = store_path(root)
    return read_json(path) if path.exists() else empty_store()


def event_update(root, kind, details, transform=None):
    def update(value):
        if transform:
            transform(value)
        event = {"kind": kind, "at": utc_now(), "details": details}
        event["sha256"] = digest(event)
        value["events"].append(event)
        return value
    return locked_json_update(store_path(root), update, empty_store())


def activity(root, state, detail, **extra):
    path = contained(root, "experiments/activity.json")
    write_json(path, {"state": state, "detail": detail, "updated_at": utc_now(),
                      "pid": os.getpid(), **extra})


def activity_snapshot(root):
    path = contained(root, "experiments/activity.json")
    if not path.exists():
        return {}
    value = read_json(path)
    if value.get("state") in {"checking_resources", "downloading", "running"}:
        try:
            os.kill(int(value["pid"]), 0)
        except (ProcessLookupError, ValueError, KeyError):
            return {**value, "state": "interrupted", "detail": "Experiment operation interrupted; inspect its logs before retrying."}
        except PermissionError:
            pass
    return value


@contextmanager
def operation_lock(root):
    path = contained(root, "experiments/resource-operation.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another resource or experiment operation is active in this run") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def validate_policy(policy):
    if set(policy) != set(DEFAULT_POLICY):
        raise ValueError("resource policy must contain exactly the documented limit fields")
    for key, value in policy.items():
        if type(value) is not int or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if policy["pilot_seconds"] > policy["experiment_seconds"]:
        raise ValueError("pilot limit cannot exceed the experiment limit")
    return policy


def checked_url(url, *, initial=False, revision=None, kind=None):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password or
            parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("resources require credential-free HTTPS URLs")
    if initial:
        if host != "huggingface.co" or parsed.query:
            raise ValueError("initial asset URL must be a public Hugging Face resolve URL without a query")
        prefix = "/datasets/" if kind == "dataset" else "/"
        pattern = re.escape(prefix) + r"[^/]+/[^/]+/resolve/" + re.escape(revision or "") + r"/[^?#]+"
        if not re.fullmatch(pattern, parsed.path) or ".." in Path(unquote(parsed.path)).parts:
            raise ValueError("asset URL must identify a file at the recorded commit revision")
    elif not (host == "huggingface.co" or host.endswith(".huggingface.co") or
              host == "hf.co" or host.endswith(".hf.co")):
        raise ValueError("download redirect left the approved Hugging Face hosts")
    return url


class CheckedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_resource(record):
    identifier(record.get("id", ""), "resource ID")
    kind = record.get("kind")
    if kind not in FORMATS:
        raise ValueError("resource kind must be dataset or model")
    for key in ("description", "license", "license_source", "source_description"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"resource requires {key}")
    local = record.get("access") == "local"
    if not local and not re.fullmatch(r"[a-fA-F0-9]{40}", record.get("revision", "")):
        raise ValueError("resource revision must be an immutable 40-character commit hash")
    if record.get("access") not in {"public", "local"}:
        raise ValueError("automatic acquisition supports public, ungated resources only")
    files = record.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= 100:
        raise ValueError("resource requires 1 to 100 explicitly selected files")
    paths = set()
    for item in files:
        name = item.get("path", "")
        if (not name or Path(name).is_absolute() or ".." in Path(name).parts or
                name in paths or Path(name).suffix.lower() not in FORMATS[kind]):
            raise ValueError("resource files must have unique relative paths and supported non-archive formats")
        paths.add(name)
        if type(item.get("expected_bytes")) is not int or item["expected_bytes"] <= 0:
            raise ValueError("each asset needs its positive expected_bytes from source metadata")
        if local:
            if not isinstance(item.get("source_path"), str) or not item["source_path"]:
                raise ValueError("local resource files require source_path relative to the paper directory")
        else:
            checked_url(item.get("url", ""), initial=True, revision=record["revision"], kind=kind)
        if item.get("expected_sha256") and not re.fullmatch(r"[a-f0-9]{64}", item["expected_sha256"]):
            raise ValueError("invalid expected_sha256")
    return record


def dataset_columns(path):
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t" if suffix == ".tsv" else ",")
            columns = reader.fieldnames
            if not columns or next(reader, None) is None:
                raise ValueError("dataset has no header or rows")
    elif suffix == ".parquet":
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise ValueError("Parquet inspection requires pyarrow; install it with permission or choose CSV/JSONL") from exc
        table = pq.ParquetFile(path)
        if not table.metadata.num_rows:
            raise ValueError("dataset has no rows")
        columns = table.schema.names
    else:
        with path.open(encoding="utf-8") as handle:
            if suffix == ".jsonl":
                row = json.loads(handle.readline())
            else:
                data = json.load(handle)
                row = data[0] if isinstance(data, list) and data else data
        if not isinstance(row, dict) or not row:
            raise ValueError("dataset must expose named fields; select a supported tabular export")
        columns = list(row)
    return sorted(set(columns))


def resource_entry(root, resource_id):
    matches = [r for r in load_store(root)["resources"] if r["id"] == resource_id]
    if len(matches) != 1:
        raise ValueError(f"unregistered resource: {resource_id}")
    validate_resource(matches[0])
    if matches[0].get("spec_sha256") != digest(resource_spec(matches[0])):
        raise ValueError("resource specification changed after registration")
    return matches[0]


def resource_spec(record):
    spec = {k: v for k, v in record.items() if k not in {
        "status", "registered_at", "acquired_at", "spec_sha256", "columns"}}
    spec["files"] = [{k: v for k, v in item.items() if k not in {"local_path", "sha256", "bytes"}}
                     for item in record["files"]]
    return spec


def register(root, record):
    validate_resource(record)
    if record.get("access") == "local":
        store = load_store(root)
        local_bytes = sum(f["expected_bytes"] for r in store["resources"]
                          if r["kind"] == record["kind"] and r["access"] == "local" for f in r["files"])
        if local_bytes + sum(f["expected_bytes"] for f in record["files"]) > store["policy"][record["kind"] + "_download_bytes"]:
            raise PermissionError("local assets exceed the small-resource size budget; obtain approval")
        columns = set()
        for item in record["files"]:
            path = contained(root, item["source_path"])
            if not path.is_file() or path.suffix.lower() not in FORMATS[record["kind"]] or path.stat().st_size != item["expected_bytes"]:
                raise ValueError("local resource is missing, unsupported, or has an unexpected size")
            checksum = file_sha256(path)
            if item.get("expected_sha256") and item["expected_sha256"] != checksum:
                raise ValueError("local resource checksum mismatch")
            item.update(local_path=item["source_path"], sha256=checksum, bytes=path.stat().st_size)
            if record["kind"] == "dataset":
                columns.update(dataset_columns(path))
        record = {**record, "revision": digest(record["files"]), "columns": sorted(columns)}
    record = {**record, "status": "registered", "registered_at": utc_now()}
    if record.get("access") == "local":
        record["status"] = "ready"
    record["spec_sha256"] = digest(resource_spec(record))
    def add(store):
        if any(r["id"] == record["id"] for r in store["resources"]):
            raise ValueError("resource ID already registered; use a new ID for a changed resource")
        store["resources"].append(record)
    event_update(root, "resource_registered", {"id": record["id"]}, add)
    activity(root, "ready" if record["status"] == "ready" else "awaiting_resources", f"Registered resource {record['id']} ({record['status']}).")
    return record


def verify_assets(root, resource_ids):
    result = {}
    for resource_id in resource_ids:
        record = resource_entry(root, resource_id)
        if record.get("status") != "ready":
            raise ValueError(f"resource {resource_id} is not ready")
        for item in record["files"]:
            path = contained(root, item["local_path"])
            if not path.is_file() or file_sha256(path) != item["sha256"]:
                raise ValueError(f"resource file missing or modified: {item['local_path']}")
            result[item["local_path"]] = item["sha256"]
    return result


def acquire(root, resource_id, opener=None):
    record = resource_entry(root, resource_id)
    if record["status"] == "ready":
        verify_assets(root, [resource_id])
        activity(root, "ready", f"Using verified cached resource {resource_id}.")
        return record
    opener = opener or build_opener(CheckedRedirect())
    store = load_store(root)
    limit = store["policy"][record["kind"] + "_download_bytes"]
    remaining = limit - store["transferred"][record["kind"]]
    needed = sum(f["expected_bytes"] for f in record["files"] if not f.get("sha256"))
    if needed > remaining:
        activity(root, "awaiting_approval", f"{resource_id} needs {needed} bytes; {remaining} bytes remain in its download budget.")
        raise PermissionError("download budget exceeded; obtain explicit approval before changing limits")
    try:
        for number, item in enumerate(record["files"]):
            if item.get("sha256"):
                path = contained(root, item["local_path"])
                if not path.is_file() or file_sha256(path) != item["sha256"]:
                    raise ValueError("previously acquired asset changed; register a fresh resource")
                continue
            activity(root, "downloading", f"Downloading {resource_id}: {item['path']}")
            relative = f"experiments/assets/{resource_id}/{item['path']}"
            destination = contained(root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise ValueError("asset destination exists without a receipt; refusing to overwrite")
            transferred = 0
            transfer_started = time.monotonic()
            temp_path = None
            try:
                request = Request(item["url"], headers={"Accept-Encoding": "identity", "User-Agent": "TheoremAudit-resource-acquisition"})
                with opener.open(request, timeout=30) as response:
                    checked_url(response.geturl())
                    if response.headers.get("Content-Encoding", "identity") != "identity":
                        raise ValueError("compressed transfer rejected; use an explicit uncompressed asset")
                    length = response.headers.get("Content-Length")
                    if length and int(length) != item["expected_bytes"]:
                        raise ValueError("remote size differs from the registered source metadata")
                    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".acquire-", delete=False) as output:
                        temp_path = Path(output.name)
                        while True:
                            if time.monotonic() - transfer_started > 120:
                                raise TimeoutError("asset transfer exceeded the two-minute time limit")
                            chunk = response.read(min(65536, item["expected_bytes"] - transferred + 1))
                            if not chunk:
                                break
                            transferred += len(chunk)
                            if transferred > item["expected_bytes"]:
                                raise ValueError("remote body exceeded the declared file size")
                            output.write(chunk)
                if transferred != item["expected_bytes"]:
                    raise ValueError("incomplete download")
                checksum = file_sha256(temp_path)
                if item.get("expected_sha256") and checksum != item["expected_sha256"]:
                    raise ValueError("download checksum mismatch")
                temp_path.replace(destination)
                saved = {**item, "local_path": relative, "bytes": transferred, "sha256": checksum}
                def save(store):
                    target = next(r for r in store["resources"] if r["id"] == resource_id)
                    target["files"][number] = saved
                event_update(root, "file_acquired", {"id": resource_id, "path": relative, "sha256": checksum}, save)
                record["files"][number] = saved
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink()
                # Failed transfers count too, so retrying cannot bypass the per-run budget.
                def charge(store):
                    store["transferred"][record["kind"]] += transferred
                event_update(root, "transfer_accounted", {"id": resource_id, "bytes": transferred}, charge)
        columns = set()
        for item in record["files"]:
            if record["kind"] == "dataset":
                columns.update(dataset_columns(contained(root, item["local_path"])))
        def ready(store):
            target = next(r for r in store["resources"] if r["id"] == resource_id)
            target.update(status="ready", columns=sorted(columns), acquired_at=utc_now())
        event_update(root, "resource_ready", {"id": resource_id}, ready)
        activity(root, "ready", f"Resource {resource_id} is cached and file-verified.")
        return resource_entry(root, resource_id)
    except Exception as exc:
        activity(root, "blocked", f"Resource {resource_id}: {exc}")
        event_update(root, "acquisition_failed", {"id": resource_id, "reason": str(exc)})
        raise


def validate_preflight(check):
    if not isinstance(check, dict):
        raise ValueError("strategy-v2 candidates require a preflight object")
    if check.get("status") not in {"ready", "blocked", "awaiting_approval"}:
        raise ValueError("preflight status must be ready, blocked, or awaiting_approval")
    if check.get("evidence_kind") not in {"synthetic", "semi_synthetic", "real_data"}:
        raise ValueError("declare synthetic, semi_synthetic, or real_data evidence")
    if check.get("operation") not in {"simulation", "inference", "classical_fit"}:
        raise ValueError("CPU program supports simulation, inference, or classical_fit; no neural training")
    for field in ("resource_ids", "required_columns"):
        values = check.get(field)
        if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values) or len(values) != len(set(values)):
            raise ValueError(f"preflight.{field} must be a unique list of strings")
    for field in ("rationale", "annotation_evidence", "sampling_plan"):
        if not isinstance(check.get(field), str) or not check[field].strip():
            raise ValueError(f"preflight requires {field}")
    if type(check.get("new_human_annotation")) is not bool:
        raise ValueError("preflight must declare new_human_annotation")
    for field in ("estimated_seconds", "estimated_memory_mb"):
        if type(check.get(field)) not in (int, float) or not 0 < check[field] < float("inf"):
            raise ValueError(f"preflight requires positive finite {field}")
    if check["status"] == "ready" and check["new_human_annotation"]:
        raise ValueError("new human annotation cannot be marked automatically runnable")
    if check["evidence_kind"] != "synthetic" and not check["resource_ids"] and check["status"] == "ready":
        raise ValueError("real-data and semi-synthetic experiments require registered resources")


def check_feasibility(root, candidate):
    check = candidate["preflight"]
    validate_preflight(check)
    if check["status"] != "ready":
        return
    assets = verify_assets(root, check["resource_ids"])
    columns = set()
    for resource_id in check["resource_ids"]:
        record = resource_entry(root, resource_id)
        if record["kind"] == "dataset":
            for item in record["files"]:
                columns.update(dataset_columns(contained(root, item["local_path"])))
    missing = set(check["required_columns"]) - columns
    if missing:
        raise ValueError(f"{candidate['id']}: required annotation/data columns unavailable: {sorted(missing)}")
    policy = load_store(root)["policy"]
    if check["estimated_seconds"] > policy["experiment_seconds"] or check["estimated_memory_mb"] > policy["memory_mb"]:
        raise PermissionError("experiment estimate exceeds resource limits; record awaiting_approval")
    return assets


def validate_resource_evidence(root, artifact):
    """Bind new empirical reports to asset receipts without migrating historical runs."""
    if artifact["strategy"].get("schema_version") != 2:
        return
    store = load_store(root)
    path = store_path(root)
    expected = file_sha256(path) if path.exists() else None
    if artifact.get("resource_registry_sha256") != expected or artifact.get("resource_evidence") != store:
        raise ValueError("empirical resource evidence does not match the current resource registry")
    candidates = {c["id"]: c for c in artifact["strategy"]["candidate_experiments"]}
    for experiment in artifact["experiments"]:
        check = candidates[experiment["id"]]["preflight"]
        if experiment.get("preflight") != check:
            raise ValueError("experiment preflight differs from its selected strategy")
        if "real_system" in experiment["tags"] and check["evidence_kind"] != "real_data":
            raise ValueError("real_system support cannot come from synthetic or semi-synthetic evidence")
        if experiment.get("evaluation"):
            if check["status"] != "ready":
                raise ValueError("evaluated experiment has unresolved resource requirements")
            verify_assets(root, check["resource_ids"])
    inspections = {i["inspection_id"]: i for i in artifact.get("inspections", [])}
    executions = {e["execution_id"]: e for e in artifact.get("executions", [])}
    from experiment_runtime import verify_receipt
    for execution in executions.values():
        if execution.get("inspection_id") not in inspections:
            raise ValueError("managed execution has no corresponding inspection")
        verify_receipt(root, execution, inspections[execution["inspection_id"]])
    for experiment in artifact["experiments"]:
        evaluation = experiment.get("evaluation")
        if evaluation and executions.get(evaluation["execution_id"], {}).get("pilot"):
            raise ValueError("pilot-only evidence cannot support a completed experiment")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--run", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    register_parser = commands.add_parser("register")
    register_parser.add_argument("--input", required=True)
    fetch = commands.add_parser("acquire")
    fetch.add_argument("--id", required=True)
    config = commands.add_parser("configure")
    config.add_argument("--input", required=True)
    config.add_argument("--approval-note", required=True)
    args = parser.parse_args()
    try:
        root = paper_dir(args.workspace, args.run)
        if args.command == "status":
            print(json.dumps({**load_store(root), "activity": activity_snapshot(root)}, indent=2))
            return
        from experiment_tools import _require_stage
        _require_stage(root, "experimenter")
        with operation_lock(root):
            if args.command == "register":
                result = register(root, load_object_argument(args.input, Path(args.workspace)))
            elif args.command == "acquire":
                result = acquire(root, identifier(args.id))
            else:
                policy = validate_policy(load_object_argument(args.input, Path(args.workspace)))
                if not args.approval_note.strip():
                    raise ValueError("record the researcher's explicit approval; this note does not grant OS/network permission")
                def configure(store):
                    store["policy"] = policy
                result = event_update(root, "policy_changed", {"approval_note": args.approval_note, "policy": policy}, configure)
                activity(root, "ready", "Resource policy updated; retry the pending operation.")
            print(json.dumps(result, indent=2))
    except (ValueError, OSError, PermissionError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
