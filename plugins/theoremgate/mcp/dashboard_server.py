#!/usr/bin/env python3
"""Minimal local MCP server for TheoremAudit evidence-view data and rendering."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from dashboard import HTML, dashboard_data, safe_output  # noqa: E402


SERVER_INFO = {"name": "TheoremAudit Evidence View", "version": "0.1.0"}
UI_URI = "ui://theoremgate/dashboard-v1.html"
UI_MIME = "text/html;profile=mcp-app"


TOOLS = [
    {
        "name": "theoremgate_render_dashboard",
        "title": "Open TheoremAudit Evidence View",
        "description": "Open the interactive TheoremAudit evidence view. Use when the user asks to open, show, view, or interact with persisted run evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspacePath": {"type": "string", "description": "Absolute TheoremAudit workspace path."},
                "runId": {"type": "string", "description": "Optional run to select initially."},
            },
            "required": ["workspacePath"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "_meta": {
            "ui": {"resourceUri": UI_URI},
            "openai/outputTemplate": UI_URI,
            "openai/widgetAccessible": True,
            "openai/toolInvocation/invoking": "Loading TheoremAudit evidence view...",
            "openai/toolInvocation/invoked": "Evidence view ready",
        },
    },
    {
        "name": "theoremgate_dashboard_data",
        "title": "Read TheoremAudit Evidence Data",
        "description": "Read normalized run, stage, result, blocker, routing, and empirical status from a TheoremAudit workspace without modifying it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspacePath": {"type": "string", "description": "Absolute TheoremAudit workspace path."},
                "runId": {"type": "string", "description": "Optional run to select initially."},
            },
            "required": ["workspacePath"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "theoremgate_build_dashboard",
        "title": "Build TheoremAudit Evidence View",
        "description": "Build a self-contained offline HTML evidence view inside the selected workspace from persisted TheoremAudit artifacts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspacePath": {"type": "string", "description": "Absolute TheoremAudit workspace path."},
                "runId": {"type": "string", "description": "Optional run to select initially."},
                "outputPath": {"type": "string", "description": "Optional workspace-relative HTML output path."},
            },
            "required": ["workspacePath"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
]


def send(message: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def result(message_id: Any, value: Dict[str, Any]) -> None:
    send({"jsonrpc": "2.0", "id": message_id, "result": value})


def error(message_id: Any, code: int, message: str) -> None:
    send({"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}})


def require_workspace(args: Dict[str, Any]) -> Path:
    value = args.get("workspacePath")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("workspacePath must be a non-empty absolute path")
    workspace = Path(value).expanduser()
    if not workspace.is_absolute() or not workspace.is_dir():
        raise ValueError("workspacePath must identify an existing absolute directory")
    return workspace.resolve()


def call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    workspace = require_workspace(args)
    run_id = args.get("runId")
    if run_id is not None and (not isinstance(run_id, str) or not run_id.strip()):
        raise ValueError("runId must be non-empty text when provided")
    data = dashboard_data(workspace, run_id)
    if name == "theoremgate_render_dashboard":
        data["ui"] = {"resource_uri": UI_URI, "mime_type": UI_MIME}
        return {
            "content": [{
                "type": "text",
                "text": (
                    f"Evidence-view data is ready for {data['selected_run_id']}. "
                    f"The associated MCP Apps resource is {UI_URI}. "
                    "A compatible host may render it; if no component is visible, report that the host returned structured data without rendering UI."
                ),
            }],
            "structuredContent": data,
        }
    if name == "theoremgate_dashboard_data":
        return {
            "content": [{"type": "text", "text": f"Loaded {len(data['runs'])} TheoremAudit run(s); selected {data['selected_run_id']}."}],
            "structuredContent": data,
        }
    if name == "theoremgate_build_dashboard":
        requested = args.get("outputPath")
        if requested is not None and not isinstance(requested, str):
            raise ValueError("outputPath must be text when provided")
        output = safe_output(workspace, requested)
        output.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        output.write_text(HTML.replace("__DATA__", encoded), encoding="utf-8")
        structured = {
            "dashboardPath": str(output),
            "selectedRunId": data["selected_run_id"],
            "runCount": len(data["runs"]),
        }
        return {
            "content": [{"type": "text", "text": f"Built TheoremAudit evidence view at {output}"}],
            "structuredContent": structured,
        }
    raise ValueError(f"unknown tool: {name}")


def handle(message: Dict[str, Any]) -> None:
    message_id = message.get("id")
    method = message.get("method")
    if method == "initialize":
        params = message.get("params") or {}
        result(message_id, {
            "protocolVersion": params.get("protocolVersion", "2025-11-25"),
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": SERVER_INFO,
            "instructions": "Call theoremgate_render_dashboard when the user asks to show the embedded evidence view. A successful tool call means data and a UI resource are available, not that the host rendered it; claim it opened only when a component is visibly rendered. Use build_dashboard for an offline file. Never bypass TheoremAudit controllers.",
        })
    elif method == "ping":
        result(message_id, {})
    elif method == "tools/list":
        result(message_id, {"tools": TOOLS})
    elif method == "resources/list":
        result(message_id, {"resources": [{
            "uri": UI_URI,
            "name": "theoremgate-dashboard",
            "title": "TheoremAudit Interactive Evidence View",
            "description": "Interactive governed-research evidence view.",
            "mimeType": UI_MIME,
        }]})
    elif method == "resources/read":
        params = message.get("params") or {}
        if params.get("uri") != UI_URI:
            error(message_id, -32602, "unknown evidence-view resource URI")
        else:
            widget = (PLUGIN_ROOT / "mcp" / "dashboard_widget.html").read_text(encoding="utf-8")
            result(message_id, {"contents": [{
                "uri": UI_URI,
                "mimeType": UI_MIME,
                "text": widget,
                "_meta": {
                    "ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}},
                    "openai/widgetPrefersBorder": True,
                },
            }]})
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            result(message_id, call_tool(params.get("name", ""), params.get("arguments") or {}))
        except ValueError as exc:
            error(message_id, -32602, str(exc))
    elif message_id is not None:
        error(message_id, -32601, f"method not found: {method}")


def main() -> None:
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict):
                handle(message)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
