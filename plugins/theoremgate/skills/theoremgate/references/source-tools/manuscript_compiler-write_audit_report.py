"""
write_audit_report.py
Write audit_report.json tracing every claim in the paper back to theorem_state.
This is the key traceability artifact for TheoremAudit.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from runtime.workspace import get_project_root, load_theorem_state, log_event

SCHEMA = {
    "name": "write_audit_report",
    "description": "Write audit_report.json tracing every compiled claim to its governed source in theorem_state.json.",
    "input_schema": {
        "type": "object",
        "properties": {
            "compiled_statements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "statement_id": {"type": "string"},
                        "paper_location": {"type": "string"},
                        "environment": {"type": "string"},
                        "label": {"type": "string"}
                    }
                },
                "description": "List of statements compiled into the paper"
            },
            "omitted_statements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Statement IDs omitted and why"
            }
        },
        "required": ["compiled_statements"]
    }
}


def run(compiled_statements, omitted_statements=None):
    state = load_theorem_state()
    decisions = state.get("decisions", {})
    project_root = get_project_root()

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_compiled": len(compiled_statements),
        "total_omitted": len(omitted_statements or []),
        "compiled": [],
        "omitted": [],
        "governance_chain": {}
    }

    for entry in compiled_statements:
        sid = entry.get("statement_id", "")
        decision = decisions.get(sid, {})
        audit["compiled"].append({
            "statement_id": sid,
            "paper_location": entry.get("paper_location", ""),
            "environment": entry.get("environment", ""),
            "label": entry.get("label", ""),
            "arbiter_action": decision.get("action", "unknown"),
            "arbiter_status": decision.get("new_status", "unknown"),
            "arbiter_reason": decision.get("reason", ""),
        })

    for sid in (omitted_statements or []):
        decision = decisions.get(sid, {})
        audit["omitted"].append({
            "statement_id": sid,
            "reason": decision.get("action", "unknown"),
            "arbiter_reason": decision.get("reason", ""),
        })

    # Write audit report
    output_dir = project_root / "outputs" / "paper"
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / "audit_report.json"

    with open(audit_path, "w") as f:
        json.dump(audit, f, indent=2)

    log_event("write_audit_report", {
        "compiled": len(compiled_statements),
        "omitted": len(omitted_statements or [])
    })

    return f"Audit report written: {audit_path} ({len(compiled_statements)} compiled, {len(omitted_statements or [])} omitted)"