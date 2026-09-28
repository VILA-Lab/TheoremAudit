#!/usr/bin/env python3
"""Unified TheoremAudit launcher for terminal and web-interface use."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        add_help=False,
        description=(
            "Launch TheoremAudit either in terminal mode or as the local "
            "TheoremAudit web interface."
        )
    )
    result.add_argument("-h", "--help", action="store_true", help="Show this help message and exit.")
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--terminal", action="store_true", help="Run the terminal pipeline launcher.")
    mode.add_argument("--dashboard", action="store_true", help="Open the local TheoremAudit web interface.")
    result.add_argument("--workspace", default=".", help="Workspace where .theoremgate/ state is stored.")
    result.add_argument("--host", default="127.0.0.1", help="Web-interface host; loopback only.")
    result.add_argument("--port", type=int, default=8765, help="Web-interface port.")
    result.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    result.add_argument(
        "--log-file",
        help=(
            "Write terminal output to this text file while also printing it. "
            "Relative paths are resolved inside --workspace."
        ),
    )
    return result


def run_with_optional_log(command: Sequence[str], log_file: str | None, workspace: str) -> int:
    if not log_file:
        return subprocess.call(list(command))
    log_path = Path(log_file).expanduser()
    if not log_path.is_absolute():
        log_path = Path(workspace) / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n--- TheoremAudit command: {' '.join(command)} ---\n")
        handle.flush()
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            handle.write(line)
            handle.flush()
        return process.wait()


def main() -> int:
    args, remainder = parser().parse_known_args()
    if args.help and not (args.terminal and remainder):
        parser().print_help()
        return 0
    if not args.terminal and not args.dashboard:
        parser().print_help(sys.stderr)
        return 2
    workspace = str(Path(args.workspace).expanduser().resolve())
    if args.dashboard:
        if args.help:
            parser().print_help()
            return 0
        if remainder:
            raise SystemExit("--dashboard does not accept terminal subcommands")
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            raise SystemExit("--host must be a loopback address: 127.0.0.1, localhost, or ::1")
        command = [
            sys.executable,
            str(SCRIPT_DIR / "research_studio.py"),
            "--workspace",
            workspace,
            "--host",
            args.host,
            "--port",
            str(args.port),
        ]
        if args.no_open:
            command.append("--no-open")
        try:
            return run_with_optional_log(command, args.log_file, workspace)
        except KeyboardInterrupt:
            return 130

    if not remainder:
        if args.help:
            command = [
                sys.executable,
                str(SCRIPT_DIR / "direct_pipeline.py"),
                "--help",
            ]
            return subprocess.call(command)
        raise SystemExit(
            "--terminal requires a subcommand, for example: "
            "start --question 'your theoretical ML research question'"
        )
    command = [
        sys.executable,
        str(SCRIPT_DIR / "direct_pipeline.py"),
        "--workspace",
        workspace,
        *remainder,
    ]
    if args.help:
        command.append("--help")
    try:
        return run_with_optional_log(command, args.log_file, workspace)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
