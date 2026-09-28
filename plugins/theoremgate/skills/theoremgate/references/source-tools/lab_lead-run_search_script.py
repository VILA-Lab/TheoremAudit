"""
run_search_script — lets an agent execute a whitelisted literature-search script.

Skills are instructions, not code: a `python foo.py` line in a SKILL.md never runs by
itself. This tool is the executor that makes those scripts runnable. It is deliberately
restricted to the .py files inside skills/literature-search/scripts/ (no arbitrary shell),
so agents can call the real arXiv / Semantic Scholar / OpenReview / JMLR search + fetch
scripts but cannot run anything else.
"""

import sys
import shlex
import subprocess
from pathlib import Path
from runtime.workspace import get_project_root, log_event

SCRIPTS_DIR = get_project_root() / "skills" / "literature-search" / "scripts"


def _allowed_scripts():
    """Whitelist = every .py in the scripts folder except tests/helpers."""
    if not SCRIPTS_DIR.exists():
        return []
    return sorted(
        p.stem for p in SCRIPTS_DIR.glob("*.py")
        if not p.name.startswith(("test_", "_"))
    )


SCHEMA = {
    "name": "run_search_script",
    "description": (
        "Execute a literature-search helper script (arXiv / Semantic Scholar / OpenReview / "
        "JMLR-PMLR search, paper fetch, or citation chasing) and return its output. These "
        "query official APIs and are more reliable than web_search. Only scripts in the "
        "literature-search scripts folder can be run."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "Script name without path/extension, e.g. 'search_arxiv', "
                               "'fetch_paper', 'search_semantic', 'search_openreview', "
                               "'search_jmlr', 'chase_citations'.",
            },
            "args": {
                "description": "Arguments to pass, either as a single string "
                               "(e.g. \"--query 'benign overfitting' --max_results 5\") "
                               "or a list of strings.",
            },
            "timeout": {
                "type": "integer",
                "description": "Max seconds to run (default 120).",
            },
        },
        "required": ["script"],
    },
}


def run(script, args="", timeout=120, **_ignored):
    allowed = _allowed_scripts()
    name = str(script).strip().removesuffix(".py")
    if name not in allowed:
        return (f"Error: '{script}' is not a runnable search script. "
                f"Allowed: {allowed}")

    script_path = SCRIPTS_DIR / f"{name}.py"
    if not script_path.exists():
        return f"Error: script file not found: {script_path}"

    # Normalize args to a list, without invoking a shell.
    if isinstance(args, list):
        arg_list = [str(a) for a in args]
    elif args:
        arg_list = shlex.split(str(args))
    else:
        arg_list = []

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), *arg_list],
            cwd=str(get_project_root()),
            capture_output=True, text=True,
            timeout=int(timeout or 120),
        )
    except subprocess.TimeoutExpired:
        log_event("run_search_script_timeout", {"script": name, "timeout": timeout})
        return f"Error: {name} timed out after {timeout}s. Try a narrower query or web_search."
    except Exception as e:
        return f"Error running {name}: {e}"

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    log_event("run_search_script", {"script": name, "args": arg_list,
                                     "returncode": proc.returncode, "out_len": len(out)})
    if proc.returncode != 0:
        return f"[{name} exited {proc.returncode}]\nstderr:\n{err[:1500]}\nstdout:\n{out[:2000]}"
    result = out[:8000] if out else "(no output)"
    if err:
        result += f"\n\n[stderr]\n{err[:500]}"
    return result
