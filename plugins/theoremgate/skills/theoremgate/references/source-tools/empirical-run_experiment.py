"""
run_experiment — executes experiment code in a Docker container.
Returns stdout, stderr, figures, metrics, and exit code.
"""

import json
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from runtime.workspace import log_event

SCHEMA = {
    "name": "run_experiment",
    "description": (
        "Execute experiment code in an isolated Docker container. "
        "Returns results including stdout, figures, metrics, and whether it succeeded. "
        "Use this for any empirical check — synthetic or real data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "experiment_id": {
                "type": "string",
                "description": "ID of the empirical check e.g. 'EC1'",
            },
            "code": {
                "type": "string",
                "description": (
                    "Complete self-contained Python experiment code. "
                    "Must import everything it needs. "
                    "Save figures with plt.savefig('/experiment/outputs/figures/EC1.pdf'). "
                    "Export a METRICS dict at module level with key results."
                ),
            },
            "description": {
                "type": "string",
                "description": "What this experiment tests",
            },
            "timeout": {
                "type": "integer",
                "description": "Max seconds to run (default 300)",
                "default": 300,
            },
        },
        "required": ["experiment_id", "code", "description"],
    },
}

PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCKER_DIR = PROJECT_ROOT / "docker" / "empirical"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "empirical"
IMAGE_NAME = "theoremgate-empirical"


def _ensure_docker_image():
    """Build Docker image if not already built."""
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE_NAME],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"[run_experiment] Building Docker image {IMAGE_NAME}...")
        build = subprocess.run(
            ["docker", "build", "-t", IMAGE_NAME, str(DOCKER_DIR)],
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            raise RuntimeError(f"Docker build failed:\n{build.stderr}")
        print(f"[run_experiment] Image built ✓")


def _docker_available():
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _run_in_subprocess(code, experiment_id, timeout):
    """Fallback: run in restricted subprocess if Docker not available."""
    import sys
    import io
    import traceback

    print(f"[run_experiment] Docker not available — running in subprocess (less safe)")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    result = {
        "success": False,
        "figures": [],
        "metrics": {},
        "stdout": "",
        "stderr": "",
        "error": None,
        "runtime_sec": None,
        "ran_in": "subprocess",
    }

    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result["success"] = proc.returncode == 0
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        if proc.returncode != 0:
            result["error"] = proc.stderr
    except subprocess.TimeoutExpired:
        result["error"] = f"Experiment timed out after {timeout}s"
    except Exception as e:
        result["error"] = str(e)
    finally:
        os.unlink(tmp_path)

    return result


def run(experiment_id, code, description, timeout=300):
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    figures_dir = OUTPUTS_DIR / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    code_dir = OUTPUTS_DIR / "code"
    code_dir.mkdir(parents=True, exist_ok=True)

    # Save experiment code
    code_path = code_dir / f"{experiment_id}.py"
    code_path.write_text(code)

    log_event("run_experiment_start", {
        "experiment_id": experiment_id,
        "description": description,
    })

    # Try Docker first, fallback to subprocess
    if _docker_available():
        result = _run_in_docker(code, experiment_id, timeout, figures_dir)
    else:
        result = _run_in_subprocess(code, experiment_id, timeout)

    result["experiment_id"] = experiment_id
    result["description"] = description
    result["ran_at"] = datetime.utcnow().isoformat()

    # Save results
    results_path = OUTPUTS_DIR / f"{experiment_id}_result.json"
    with open(results_path, "w") as f:
        json.dump(result, f, indent=2)

    log_event("run_experiment_complete", {
        "experiment_id": experiment_id,
        "success": result["success"],
        "figures": result.get("figures", []),
    })

    # Return summary for LLM
    summary = {
        "experiment_id": experiment_id,
        "success": result["success"],
        "metrics": result.get("metrics", {}),
        "figures": result.get("figures", []),
        "stdout_preview": result.get("stdout", "")[:500],
        "error": result.get("error"),
        "runtime_sec": result.get("runtime_sec"),
    }
    return json.dumps(summary, indent=2)


def _run_in_docker(code, experiment_id, timeout, figures_dir):
    """Run experiment in isolated Docker container."""
    _ensure_docker_image()

    # Create temp workspace
    workspace = tempfile.mkdtemp(prefix="theoremgate_exp_")
    try:
        # Write experiment code
        exp_path = os.path.join(workspace, "experiment.py")
        with open(exp_path, "w") as f:
            f.write(code)

        # Copy runner
        runner_src = DOCKER_DIR / "runner.py"
        shutil.copy(str(runner_src), os.path.join(workspace, "runner.py"))

        outputs_in_container = os.path.join(workspace, "outputs")
        os.makedirs(outputs_in_container, exist_ok=True)

        proc = subprocess.run(
            [
                "docker", "run",
                "--rm",
                "--network", "none",          # no network access
                "--memory", "4g",             # memory limit
                "--cpus", "2",                # CPU limit
                f"--volume={workspace}:/experiment",
                "--env", f"EXPERIMENT_FILE=/experiment/experiment.py",
                "--env", f"OUTPUT_DIR=/experiment/outputs",
                IMAGE_NAME,
                "python", "/experiment/runner.py",
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 30,
        )

        # Parse result from stdout
        result = {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "figures": [],
            "metrics": {},
            "error": None if proc.returncode == 0 else proc.stderr,
            "ran_in": "docker",
        }

        # Try to parse JSON result from runner
        try:
            result_json = json.loads(proc.stdout)
            result.update(result_json)
        except Exception:
            pass

        # Copy figures out of container workspace
        fig_src = os.path.join(outputs_in_container, "figures")
        if os.path.exists(fig_src):
            for fig in os.listdir(fig_src):
                shutil.copy(
                    os.path.join(fig_src, fig),
                    str(figures_dir / fig)
                )
                result["figures"].append(str(figures_dir / fig))

        return result

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Experiment timed out after {timeout}s",
            "figures": [],
            "metrics": {},
            "stdout": "",
            "stderr": "",
            "ran_in": "docker",
        }
    finally:
        shutil.rmtree(workspace, ignore_errors=True)