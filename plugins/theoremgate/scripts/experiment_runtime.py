"""Bounded local CPU execution of an already inspected experiment, not arbitrary commands."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

from experiment_resources import (activity, check_feasibility, digest, load_store,
                                  operation_lock, verify_assets)
from state_store import file_sha256, read_json, utc_now, write_json
from tool_utils import contained


BOOTSTRAP = """
import os, runpy, socket, sys
def deny(*args, **kwargs):
    raise RuntimeError('Experiment network access is disabled; acquire resources first')
socket.create_connection = deny
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.socket.sendto = deny
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(script))
runpy.run_path(script, run_name='__main__')
"""


def cpu_findings(path):
    findings = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name in {"cuda", "mps", "xpu"}:
                findings.append("accelerator calls are not permitted in the CPU resource profile")
            options = {kw.arg: kw.value for kw in node.keywords}
            if "device_map" in options:
                findings.append("use explicit CPU placement, not device_map")
            if "device" in options and not (isinstance(options["device"], ast.Constant) and options["device"].value == "cpu"):
                findings.append("device must be the literal 'cpu' in the CPU profile")
            if "trust_remote_code" in options and not (isinstance(options["trust_remote_code"], ast.Constant) and options["trust_remote_code"].value is False):
                findings.append("remote model code is not permitted")
            if name == "from_pretrained" and not (isinstance(options.get("local_files_only"), ast.Constant) and options["local_files_only"].value is True):
                findings.append("from_pretrained requires local_files_only=True and a registered local model directory")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith(("cuda", "mps", "xpu", "http://", "https://")):
                findings.append("runtime accelerator/remote asset references are not permitted")
    return sorted(set(findings))


def available_memory_mb():
    if sys.platform == "linux":
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    if sys.platform == "darwin":
        output = subprocess.check_output(["/usr/bin/vm_stat"], text=True)
        import re
        size = int(re.search(r"page size of (\d+) bytes", output)[1])
        pages = sum(int(match[1]) for match in re.finditer(
            r"(?:Pages free|Pages inactive|Pages speculative):\s+(\d+)", output))
        return pages * size // 1_048_576
    raise ValueError("bounded experiment execution currently supports macOS and Linux")


def group_memory_mb(pgid):
    output = subprocess.check_output(["ps", "-axo", "pgid=,rss="], text=True)
    return sum(int(rss) for group, rss in (line.split() for line in output.splitlines())
               if int(group) == pgid) / 1024


def stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def receipts(root):
    directory = contained(root, "experiments/executions")
    return [read_json(path) for path in sorted(directory.glob("*/receipt.json"))] if directory.exists() else []


def verify_receipt(root, evidence, inspection):
    relative = evidence.get("managed_receipt_path")
    if not isinstance(relative, str):
        raise ValueError("strategy-v2 executions must use run-inspected, not manual execution reports")
    path = contained(root, relative)
    record = read_json(path)
    if evidence.get("managed_receipt_sha256") != file_sha256(path):
        raise ValueError("managed execution receipt changed")
    if record.get("receipt_sha256") != digest({k: v for k, v in record.items() if k != "receipt_sha256"}):
        raise ValueError("managed execution receipt is inconsistent")
    if record["script_sha256"] != inspection["script_sha256"] or record["inspection_id"] != inspection["inspection_id"]:
        raise ValueError("managed execution does not match the current inspection")
    for field in ("command", "exit_code", "output_paths", "stdout_path", "stderr_path", "started_at", "finished_at", "environment", "pilot", "resource_sha256"):
        if evidence.get(field) != record[field]:
            raise ValueError(f"managed execution report differs from receipt: {field}")
    for relative, checksum in {**record["resource_sha256"], **record["output_sha256"]}.items():
        path = contained(root, relative)
        if not path.is_file() or file_sha256(path) != checksum:
            raise ValueError(f"managed execution asset/output changed: {relative}")
    return record


def execute(root, experiment_id, specification, *, workspace, run_id):
    from experiment_tools import command_record_execution, inspect_code, load_index, _require_stage
    root = root.resolve()
    _require_stage(root, "experimenter")
    with operation_lock(root):
        activity(root, "checking_resources", f"Checking resources and CPU budget for {experiment_id}.")
        try:
            index = load_index(root)
            strategy = index.get("strategy") or {}
            if strategy.get("schema_version") != 2:
                raise ValueError("run-inspected requires a version-2 strategy with resource preflight")
            candidate = next(c for c in strategy["candidate_experiments"] if c["id"] == experiment_id)
            if not candidate["selected"] or candidate["preflight"]["status"] != "ready":
                raise ValueError("experiment has not passed resource feasibility checks")
            if not any(e["id"] == experiment_id for e in index["experiments"]):
                raise ValueError("propose the experiment before execution")
            check_feasibility(root, candidate)
            inspections = [i for i in index["inspections"] if i["experiment_id"] == experiment_id]
            if not inspections or not inspections[-1]["safe_for_manual_execution"]:
                raise ValueError("a latest safe inspection is required")
            inspection = inspections[-1]
            sources = {inspection["script_path"]: inspection["script_sha256"], **inspection.get("dependency_sha256", {})}
            for relative, checksum in sources.items():
                path = contained(root, relative)
                if not path.is_file() or file_sha256(path) != checksum:
                    raise ValueError("script/dependency changed; inspect again")
                if path.suffix == ".py":
                    findings = inspect_code(path) + cpu_findings(path)
                    if findings:
                        raise ValueError("; ".join(findings))
            assets = verify_assets(root, candidate["preflight"]["resource_ids"])
            policy = load_store(root)["policy"]
            pilot = specification.get("pilot", False)
            if type(pilot) is not bool:
                raise ValueError("pilot must be Boolean")
            arguments = specification.get("arguments", [])
            outputs = specification.get("output_paths", [])
            if not isinstance(arguments, list) or any(not isinstance(a, str) for a in arguments):
                raise ValueError("arguments must be a JSON list of strings")
            if not isinstance(outputs, list) or not outputs or any(not isinstance(p, str) for p in outputs) or len(set(outputs)) != len(outputs):
                raise ValueError("declare unique output_paths before execution")
            for relative in outputs:
                path = contained(root, relative)
                if not relative.startswith("experiments/results/") or path.exists():
                    raise ValueError("outputs must use fresh paths under experiments/results; preserve earlier results")
                path.parent.mkdir(parents=True, exist_ok=True)
            history = receipts(root)
            prior = [r for r in history if r["experiment_id"] == experiment_id]
            matching_pilot = [r for r in prior if r["pilot"] and r["exit_code"] == 0 and
                              r["script_sha256"] == inspection["script_sha256"] and
                              r["dependency_sha256"] == inspection.get("dependency_sha256", {}) and
                              r["resource_sha256"] == assets]
            if not pilot and not matching_pilot:
                raise ValueError("run a successful pilot with the same script, dependencies, and assets first")
            available = available_memory_mb()
            memory_limit = min(policy["memory_mb"], int(available * 0.6))
            if candidate["preflight"]["estimated_memory_mb"] > memory_limit:
                raise PermissionError(f"insufficient available memory; safe current budget is {memory_limit} MB")
            timeout = min(policy["experiment_seconds"] - sum(r["elapsed_seconds"] for r in prior),
                          policy["run_seconds"] - sum(r["elapsed_seconds"] for r in history))
            if pilot:
                timeout = min(timeout, policy["pilot_seconds"])
            if timeout < 0.1:
                raise PermissionError("cumulative execution budget exhausted; obtain approval for additional time")
            sequence = len(history) + 1
            folder = contained(root, f"experiments/executions/CPU-{sequence:05d}")
            folder.mkdir(parents=True, exist_ok=False)
            stdout_path, stderr_path = folder / "stdout.log", folder / "stderr.log"
            script = contained(root, inspection["script_path"])
            command = [sys.executable, "-I", "-c", BOOTSTRAP, str(script), *arguments]
            env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "TMPDIR", "TEMP", "LANG", "SYSTEMROOT"}}
            env.update({"CUDA_VISIBLE_DEVICES": "", "HIP_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1",
                        "NVIDIA_VISIBLE_DEVICES": "none", "JAX_PLATFORMS": "cpu",
                        "HF_DATASETS_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "THEOREMGATE_DEVICE": "cpu",
                        "OMP_NUM_THREADS": str(policy["cpu_threads"]), "MKL_NUM_THREADS": str(policy["cpu_threads"]),
                        "OPENBLAS_NUM_THREADS": str(policy["cpu_threads"]), "TOKENIZERS_PARALLELISM": "false"})
            started_at, start = utc_now(), time.monotonic()
            peak, failure = 0.0, ""
            activity(root, "running", f"{'Pilot' if pilot else 'Experiment'} {experiment_id} running on CPU.", experiment_id=experiment_id)
            with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
                process = subprocess.Popen(command, cwd=root, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    while process.poll() is None:
                        elapsed = time.monotonic() - start
                        peak = max(peak, group_memory_mb(process.pid))
                        size = sum(p.stat().st_size for p in [stdout_path, stderr_path, *(contained(root, p) for p in outputs)] if p.is_file())
                        if elapsed >= timeout:
                            failure = "wall-clock budget exceeded"
                        elif peak > memory_limit:
                            failure = "memory budget exceeded"
                        elif size > policy["output_bytes"]:
                            failure = "output/log size budget exceeded"
                        if failure:
                            stop_group(process)
                            break
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    failure = "execution interrupted"
                    stop_group(process)
                except (OSError, subprocess.SubprocessError) as exc:
                    failure = f"execution monitoring failed: {exc}"
                    stop_group(process)
                finally:
                    # Inspected code must not leave background descendants alive.
                    stop_group(process)
            if time.monotonic() - start > timeout and not failure:
                failure = "wall-clock budget exceeded"
            size = sum(p.stat().st_size for p in [stdout_path, stderr_path, *(contained(root, p) for p in outputs)] if p.is_file())
            if size > policy["output_bytes"] and not failure:
                failure = "output/log size budget exceeded"
            if process.returncode == 0 and any(not contained(root, p).is_file() for p in outputs):
                failure = "declared experiment output missing"
            recorded_outputs = [p for p in outputs if contained(root, p).is_file()]
            recorded_outputs += [str(stdout_path.relative_to(root)), str(stderr_path.relative_to(root))]
            receipt = {
                "experiment_id": experiment_id, "pilot": pilot, "inspection_id": inspection["inspection_id"],
                "script_sha256": inspection["script_sha256"], "dependency_sha256": inspection.get("dependency_sha256", {}),
                "resource_sha256": assets, "policy": policy, "memory_limit_mb": memory_limit,
                "peak_memory_mb": peak, "elapsed_seconds": time.monotonic() - start,
                "command": command, "exit_code": 124 if failure else process.returncode, "failure": failure,
                "started_at": started_at, "finished_at": utc_now(), "output_paths": recorded_outputs,
                "output_sha256": {p: file_sha256(contained(root, p)) for p in recorded_outputs},
                "stdout_path": str(stdout_path.relative_to(root)), "stderr_path": str(stderr_path.relative_to(root)),
                "environment": {"python": sys.version, "platform": platform.platform(), "device": "cpu",
                                "network": "offline library settings and Python socket guard; not an OS security sandbox",
                                "cpu_threads": policy["cpu_threads"]},
            }
            receipt["receipt_sha256"] = digest(receipt)
            receipt_path = folder / "receipt.json"
            write_json(receipt_path, receipt)
            evidence = {**receipt, "managed_receipt_path": str(receipt_path.relative_to(root)),
                        "managed_receipt_sha256": file_sha256(receipt_path)}
            input_path = folder / "record-input.json"
            write_json(input_path, evidence)
            command_record_execution(SimpleNamespace(workspace=workspace, run=run_id, actor="experimenter",
                                                     id=experiment_id, input=str(input_path)))
            state = "ready" if receipt["exit_code"] == 0 else "blocked"
            activity(root, state, f"{'Pilot' if pilot else 'Experiment'} {experiment_id}: {failure or ('completed' if state == 'ready' else 'failed; inspect stderr')}.")
            return receipt
        except PermissionError as exc:
            activity(root, "awaiting_approval", str(exc))
            raise
        except Exception as exc:
            activity(root, "blocked", str(exc))
            raise
