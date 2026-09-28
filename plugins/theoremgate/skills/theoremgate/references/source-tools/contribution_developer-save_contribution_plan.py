"""
Save the Contribution Developer output.

This tool writes:
- state/contribution_development.json
- state/theorem_state.json["contribution_development"]

It may also store proposed extension obligations under:
- state/theorem_state.json["extension_obligations"]

The tool does not directly modify existing committed proofs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from runtime.workspace import get_project_root


SCHEMA = {
    "name": "save_contribution_plan",
    "description": (
        "Save the contribution-development assessment and proposed extension "
        "obligations for Method Team. Use this after deciding whether the "
        "current safe core is paper-ready."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "submission_evidence_status": {
                "type": "string",
                "enum": ["ready", "needs_strengthening"],
                "description": "Whether acceptance evidence is ready or needs bounded strengthening.",
            },
            "maturity_label": {
                "type": "string",
                "enum": [
                    "seed_lemma",
                    "structural_corollary",
                    "statistical_consequence",
                    "separation_or_impossibility",
                ],
                "description": "Contribution maturity of the strongest committed result.",
            },
            "current_core": {
                "type": "string",
                "description": "Strongest safe result already proved.",
            },
            "main_gap": {
                "type": "string",
                "description": "What is missing for a paper-level contribution.",
            },
            "recommended_upgrade": {
                "type": "object",
                "description": "Concrete theorem direction to make the project paper-ready.",
            },
            "new_obligations": {
                "type": "array",
                "description": "New proof obligations for Method Team.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "claim": {"type": "string"},
                        "why_nontrivial": {"type": "string"},
                        "proof_strategy": {"type": "string"},
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "difficulty": {"type": "string"},
                        "status": {"type": "string"},
                    },
                    "required": ["id", "claim", "proof_strategy"],
                },
            },
            "manuscript_kind": {
                "type": "string",
                "enum": ["full_paper"],
                "description": "Unified manuscript kind for accepted-result packages.",
            },
            "rationale": {
                "type": "string",
                "description": "Why this plan is appropriate.",
            },
        },
        "required": [
            "submission_evidence_status",
            "maturity_label",
            "current_core",
            "main_gap",
            "recommended_upgrade",
            "new_obligations",
            "manuscript_kind",
            "rationale",
        ],
    },
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _normalize_obligations(obligations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for i, item in enumerate(obligations or [], start=1):
        po_id = str(item.get("id") or f"PX-{i}")

        normalized.append(
            {
                "id": po_id,
                "claim": str(item.get("claim", "")).strip(),
                "why_nontrivial": str(item.get("why_nontrivial", "")).strip(),
                "proof_strategy": str(item.get("proof_strategy", "")).strip(),
                "dependencies": item.get("dependencies", []) or [],
                "difficulty": str(item.get("difficulty", "unknown")).strip(),
                "status": str(item.get("status", "open")).strip(),
                "source": "contribution_developer",
            }
        )

    return normalized

def _sync_discovery_obligations(
    root: Path,
    extension_obligations: List[Dict[str, Any]],
) -> List[str]:
    """
    Register Contribution Developer obligations in discovery.json so Method Team
    tools such as write_blueprint recognize them as valid proof-obligation IDs.

    TH-* dependencies are kept as seed_dependencies, not DAG dependencies.
    """
    discovery_path = root / "state" / "discovery.json"
    discovery = _load_json(discovery_path)

    if not discovery:
        return []

    proof_obligations = discovery.get("proof_obligations", [])
    if not isinstance(proof_obligations, list):
        proof_obligations = []

    existing_ids = {
        str(ob.get("id"))
        for ob in proof_obligations
        if isinstance(ob, dict) and ob.get("id")
    }

    added = []

    for ob in extension_obligations:
        if not isinstance(ob, dict):
            continue

        po_id = str(ob.get("id", "")).strip()
        if not po_id or po_id in existing_ids:
            continue

        deps = ob.get("dependencies", []) or []

        po_deps = [
            str(d)
            for d in deps
            if str(d).startswith("PO-")
        ]

        seed_deps = [
            str(d)
            for d in deps
            if str(d).startswith("TH-")
        ]

        new_ob = {
            "id": po_id,
            "claim": str(ob.get("claim", "")).strip(),
            "informal": str(ob.get("claim", "")).strip(),
            "type": "extension_obligation",
            "role": "contribution_development",
            "dependencies": po_deps,
            "seed_dependencies": seed_deps,
            "why_nontrivial": str(ob.get("why_nontrivial", "")).strip(),
            "proof_strategy_hint": str(ob.get("proof_strategy", "")).strip(),
            "difficulty": str(ob.get("difficulty", "unknown")).strip(),
            "source": "contribution_developer",
        }

        proof_obligations.append(new_ob)
        existing_ids.add(po_id)
        added.append(po_id)

    discovery["proof_obligations"] = proof_obligations

    _write_json(discovery_path, discovery)

    return added

def run(
    submission_evidence_status: str,
    maturity_label: str,
    current_core: str,
    main_gap: str,
    recommended_upgrade: Dict[str, Any],
    new_obligations: List[Dict[str, Any]],
    manuscript_kind: str,
    rationale: str,
):
    root = get_project_root()
    state_dir = root / "state"

    now = datetime.now(timezone.utc).isoformat()
    normalized_obligations = _normalize_obligations(new_obligations)
    synced_to_discovery = _sync_discovery_obligations(
    root,
    normalized_obligations,
)

    plan = {
        "submission_evidence_status": submission_evidence_status,
        "maturity_label": maturity_label,
        "current_core": current_core,
        "main_gap": main_gap,
        "recommended_upgrade": recommended_upgrade or {},
        "new_obligations": normalized_obligations,
        "manuscript_kind": manuscript_kind,
        "rationale": rationale,
        "saved_by": "contribution_developer",
        "saved_at": now,
    }

    out_path = state_dir / "contribution_development.json"
    _write_json(out_path, plan)

    theorem_state_path = state_dir / "theorem_state.json"
    theorem_state = _load_json(theorem_state_path)

    theorem_state["contribution_development"] = plan

    existing = theorem_state.get("extension_obligations", [])
    if not isinstance(existing, list):
        existing = []

    existing_ids = {str(x.get("id")) for x in existing if isinstance(x, dict)}

    merged = list(existing)
    for obligation in normalized_obligations:
        if obligation["id"] not in existing_ids:
            merged.append(obligation)
            existing_ids.add(obligation["id"])

    theorem_state["extension_obligations"] = merged

    _write_json(theorem_state_path, theorem_state)

    return {
        "ok": True,
        "path": str(out_path),
        "submission_evidence_status": submission_evidence_status,
        "maturity_label": maturity_label,
        "manuscript_kind": manuscript_kind,
        "new_obligations_count": len(normalized_obligations),
        "new_obligation_ids": [x["id"] for x in normalized_obligations],
        "synced_to_discovery": synced_to_discovery,
    }
