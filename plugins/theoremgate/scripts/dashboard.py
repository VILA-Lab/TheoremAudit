#!/usr/bin/env python3
"""Build a self-contained evidence view from immutable TheoremAudit artifacts."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from research_model import research_model
from state_store import data_root, read_json, resolve_run, utc_now


THEORY_LABELS = {
    "direction_generation": "Directions",
    "direction_selection": "Selection",
    "discovery": "Discovery",
    "exploration": "Exploration",
    "proof_development": "Proofs",
    "local_adversarial_audit": "Local audit",
    "governance_review": "Governance",
    "theorem_synthesis": "Synthesis",
    "final_adversarial_audit": "Final audit",
    "arbiter": "Arbiter",
    "novelty_audit": "Novelty",
    "significance_audit": "Significance",
    "contribution_assessment": "Contribution",
    "theory_bundle": "Theory bundle",
}

PAPER_LABELS = {
    "literature_audit": "Literature",
    "content_architecture": "Architecture",
    "exemplar_study": "Writing exemplars",
    "venue_selection": "Venue",
    "empirical_validation": "Experiments",
    "section_writing": "Writing",
    "compilation": "Compilation",
    "independent_review": "Review",
    "revision": "Revision",
    "final_package": "Final package",
}


def optional_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return read_json(path)
    except ValueError:
        return default


def stages(manifest: Dict[str, Any], labels: Dict[str, str]) -> List[Dict[str, Any]]:
    records = []
    for name, record in manifest.get("stages", {}).items():
        history = [item for item in record.get("history", []) if isinstance(item, dict)]
        completed_cycles = sorted({item.get("cycle") for item in history if item.get("cycle") is not None})
        status = record.get("status", "pending")
        # Revision is conditional.  A clean review or an exhausted, explicitly
        # packaged presentation-repair path can proceed directly to the final
        # package.  Once that package is complete, leaving Revision as pending
        # makes a finished workflow look unfinished in the evidence view.
        if (
            name == "revision"
            and status == "pending"
            and manifest.get("status") == "completed"
            and manifest.get("stages", {}).get("final_package", {}).get("status") == "completed"
        ):
            status = "skipped"
        records.append({
            "id": name,
            "label": labels.get(name, name.replace("_", " ").title()),
            "status": status,
            "actor": record.get("actor"),
            "artifact": record.get("artifact"),
            "completed_cycles": completed_cycles,
            "ever_completed": status == "completed" or bool(completed_cycles),
            "reopened": bool(completed_cycles) and status in {"pending", "in_progress"},
            "last_completed_cycle": completed_cycles[-1] if completed_cycles else None,
        })
    return records


def findings(run_dir: Path, route: Dict[str, Any]) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    for item in route.get("review_blockers", []):
        records.append({
            "id": str(item.get("id", "blocker")),
            "severity": str(item.get("severity", "major")),
            "category": str(item.get("category", "significance")),
            "description": str(item.get("description", "")),
            "action": str(item.get("required_action", "")),
        })
    for filename in ("local_audit.json", "final_audit.json"):
        audit = optional_json(run_dir / "artifacts" / filename, {})
        effective = {item.get("id"): dict(item) for item in audit.get("findings", [])}
        for event in audit.get("events", []):
            item = effective.get(event.get("finding_id"))
            if item is not None and event.get("event_type") == "resolution_verification":
                item["resolved"] = event.get("outcome") == "resolved"
        for item in effective.values():
            if item.get("resolved") or item.get("severity") not in {"major", "fatal"}:
                continue
            records.append({
                "id": str(item.get("id", "finding")),
                "severity": str(item.get("severity", "major")),
                "category": str(item.get("kind", "audit")),
                "description": str(item.get("description", "")),
                "action": "Resolve through the governed repair workflow.",
            })
    return records


def summarize_run(run_dir: Path) -> Dict[str, Any]:
    manifest = optional_json(run_dir / "run.json", {})
    bundle = optional_json(run_dir / "artifacts" / "theory_bundle.json", {})
    route = bundle.get("paper_route", {})
    paper = optional_json(run_dir / "paper" / "paper_run.json", {})
    empirical = optional_json(run_dir / "paper" / "empirical_validation.json", {})
    section_index = optional_json(run_dir / "paper" / "sections" / "index.json", {})
    paper_review = optional_json(run_dir / "paper" / "review.json", {})
    revision = optional_json(run_dir / "paper" / "revision.json", {})
    comments = optional_json(run_dir / "paper" / "user_comments.json", {})
    compile_report = optional_json(run_dir / "paper" / "compile_report.json", {})
    experiment_index = optional_json(run_dir / "paper" / "experiments" / "index.json", {})
    from experiment_resources import activity_snapshot, load_store
    try:
        experiment_activity = activity_snapshot(run_dir / "paper")
        resource_store = load_store(run_dir / "paper")
    except (ValueError, OSError, TypeError):
        experiment_activity = {"state": "unavailable", "detail": "Resource status could not be read."}
        resource_store = {}
    venue_selection = optional_json(run_dir / "paper" / "venue_selection.json", {})
    selected_direction = optional_json(run_dir / "artifacts" / "selected_direction.json", {})
    directions = optional_json(run_dir / "artifacts" / "directions.json", {})
    direction_candidates = directions.get("candidates", []) if isinstance(directions, dict) else []
    if not isinstance(direction_candidates, list):
        direction_candidates = []
    selected_candidate = next(
        (
            item for item in direction_candidates
            if isinstance(item, dict)
            if item.get("id") == selected_direction.get("selected_id")
        ),
        {},
    )
    selected_direction = {**selected_direction, "candidate": selected_candidate}
    pdf_exists = (run_dir / "paper" / "paper.pdf").is_file()
    reviewed_paper_is_current = (
        paper.get("status") == "completed"
        or paper.get("current_stage") == "final_package"
    )
    automatic_repair = paper.get("manuscript_repair", {
        "maximum_rounds": 2,
        "rounds_used": 0,
        "status": "not_started",
        "history": [],
    })
    if (
        reviewed_paper_is_current
        and paper_review.get("recommendation") == "accept"
        and not paper_review.get("findings")
        and automatic_repair.get("status") == "in_progress"
    ):
        automatic_repair = {
            **automatic_repair,
            "status": "completed",
            "resolved_by_final_review": True,
        }
    legacy_checkpoints = optional_json(run_dir / "artifacts" / "human_checkpoints.json", {})
    governance = optional_json(run_dir / "artifacts" / "governance_review.json", {})
    governance_decisions = [
        item for item in governance.get("decisions", [])
        if isinstance(item, dict)
    ]
    serious_governance = [
        item for item in governance_decisions
        if item.get("action") in {"repair_requested", "invalidated", "deferred", "excluded"}
    ]
    refinement = bundle.get("refinement", {})
    accepted = []
    for record in bundle.get("accepted_statements", []):
        statement = record.get("effective_statement", {})
        accepted.append({
            "id": statement.get("id", "statement"),
            "informal": statement.get("informal") or statement.get("formal", ""),
            "scope": statement.get("proven_scope", ""),
            "caveats": statement.get("honest_caveats", ""),
            "decision": record.get("decision", {}).get("status", "accepted"),
        })
    retained = []
    for record in bundle.get("retained_nonfinal_statements", []):
        statement = record.get("effective_statement", {})
        retained.append({
            "id": statement.get("id", "statement"),
            "informal": statement.get("informal") or statement.get("formal", ""),
            "decision": record.get("decision", {}).get("status", "nonfinal"),
            "disposition": record.get("disposition", "retained_nonfinal"),
            "reason": record.get("decision", {}).get("reason", ""),
        })
    excluded = []
    for record in bundle.get("excluded_statements", []):
        statement = record.get("effective_statement", {})
        excluded.append({
            "id": statement.get("id", "statement"),
            "informal": statement.get("informal") or statement.get("formal", ""),
            "decision": record.get("decision", {}).get("status", "invalid"),
            "disposition": record.get("disposition", "invalid_excluded"),
            "reason": record.get("decision", {}).get("reason", ""),
        })
    normalized = {
        "run_id": manifest.get("run_id", run_dir.name),
        "question": manifest.get("research_question", "Research question unavailable"),
        "created_at": manifest.get("created_at"),
        "parent_run_id": manifest.get("parent_run_id"),
        "revision_state": manifest.get("revision_state", {}),
        "correction_state": manifest.get("correction_state", {}),
        "strengthening_state": manifest.get("strengthening_state", {}),
        "lineage": {
            "parent_run_id": manifest.get("parent_run_id"),
            "revision_cycle": refinement.get("lineage_depth", 0),
            "protocol": refinement.get("protocol"),
            "next_action": refinement.get("next_action"),
            "progress_vector": refinement.get("progress_vector", {}),
            "stopping_rule": refinement.get("stopping_rule", ""),
        },
        "research_decisions": {
            "selected_direction": selected_direction,
            "governance_outcome": {
                "serious_decisions": serious_governance,
                "all_decisions": governance_decisions,
            },
        },
        "legacy_decision_history": {
            "active": False,
            "decisions": legacy_checkpoints.get("decisions", []),
        },
        "interaction_state": manifest.get("status", "unknown"),
        "execution_contract": manifest.get("execution_contract", {}),
        "theory_status": manifest.get("status", "unknown"),
        "current_theory_stage": manifest.get("current_stage"),
        "theory_stages": stages(manifest, THEORY_LABELS),
        "paper_status": paper.get("status", "not_started"),
        "current_paper_stage": paper.get("current_stage"),
        "paper_stages": stages(paper, PAPER_LABELS),
        "venue_templates": {
            "selection_mode": venue_selection.get(
                "selection_method", "agent_comparative_judgment_pending"
            ),
            "required": "agent_selected_evidence_compatible_template",
            "provisional_target": None,
            "selected": venue_selection.get("venue"),
        },
        "route": {
            "manuscript_kind": route.get("manuscript_kind") or (
                "evidence_report"
                if route.get("publication_tier") == "research_report"
                else "full_paper"
            ),
            "submission_readiness": route.get("submission_readiness") or (
                "ready" if route.get("submission_framing_allowed") else "evidence_incomplete"
            ),
            "significance": route.get("significance_level", "not_audited"),
            "novelty": route.get("novelty_verdict", "not_audited"),
            "novelty_positioning": route.get("novelty_positioning", "not_routed"),
            "writing_allowed": bool(route.get("writing_allowed")),
            "full_length_allowed": bool(route.get("full_length_allowed")),
            "submission_framing_allowed": bool(route.get("submission_framing_allowed")),
            "venue_selection_required": route.get("venue_selection_required", True),
            "venue_selection_context": route.get("venue_selection_context", {}),
            "publication_goal": route.get("publication_goal", "no_preference"),
            "publication_goal_satisfied": route.get("publication_goal_satisfied"),
            "unmet_publication_goal_reasons": route.get("unmet_publication_goal_reasons", []),
            "routing_gates": route.get("routing_gates", {}),
            "reasons": route.get("routing_reasons", []),
        },
        "accepted_statements": accepted,
        "retained_nonfinal_statements": retained,
        "excluded_statements": excluded,
        "blockers": findings(run_dir, route),
        "empirical": {
            "status": empirical.get("status", "not_started"),
            "coverage": {tag: True for tag in empirical.get("coverage_tags", [])},
            "strategy": experiment_index.get("strategy") or empirical.get("strategy", {}),
            "experiments": experiment_index.get("experiments") or empirical.get("experiments", []),
            "limitations": empirical.get("limitations", []),
            "activity": experiment_activity,
            "resource_policy": resource_store.get("policy", {}),
            "resources": [{"id": r["id"], "kind": r["kind"], "status": r["status"],
                           "license": r["license"], "revision": r["revision"]}
                          for r in resource_store.get("resources", [])],
        },
        "manuscript": {
            "pdf_available": pdf_exists and reviewed_paper_is_current,
            "draft_pdf_available": pdf_exists,
            "tex_available": (run_dir / "paper" / "paper.tex").is_file(),
            "pdf_built": bool(compile_report.get("pdf_built")),
            "compile_warnings": compile_report.get("warnings", []),
            "sections": section_index.get("sections", []),
            "review_cycle": paper.get("review_cycle", 0),
            "automatic_repair": automatic_repair,
            "revision": {
                "available": bool(revision),
                "theory_changes_required": bool(revision.get("theory_changes_required")),
                "unresolved_findings": revision.get("unresolved_findings", []),
                "changes": revision.get("changes", []),
            },
            "user_comments": comments.get("comments", []),
            "open_user_comments": [
                item for item in comments.get("comments", []) if item.get("status") != "addressed"
            ],
            "figures": experiment_index.get("figures", []),
            "review": {
                "recommendation": paper_review.get("recommendation", "not_reviewed"),
                "summary": paper_review.get("summary", ""),
                "confidence": paper_review.get("confidence"),
                "criterion_scores": paper_review.get("criterion_scores", {}),
                "findings": paper_review.get("findings", []),
            },
        },
    }
    normalized.update(research_model(run_dir))
    return normalized


def run_listing(run_dir: Path) -> Dict[str, Any]:
    """Read only the metadata needed to select runs and navigate their lineage."""
    manifest = optional_json(run_dir / "run.json", {})
    return {
        "run_id": manifest.get("run_id", run_dir.name),
        "question": manifest.get("research_question", "Research question unavailable"),
        "created_at": manifest.get("created_at"),
        "parent_run_id": manifest.get("parent_run_id"),
        "details_loaded": False,
    }


def dashboard_data(
    workspace: Path,
    selected_run: Optional[str] = None,
    *,
    selected_only: bool = False,
    auto_select: bool = True,
) -> Dict[str, Any]:
    root = data_root(workspace)
    runs_dir = root / "runs"
    if not runs_dir.is_dir() and (auto_select or selected_run):
        raise ValueError("no .theoremgate/runs directory exists in this workspace")
    run_dirs = sorted(
        (path for path in runs_dir.iterdir() if path.is_dir() and (path / "run.json").is_file())
        if runs_dir.is_dir() else [],
        key=lambda path: path.name,
        reverse=True,
    )
    if not run_dirs and (auto_select or selected_run):
        raise ValueError("no TheoremAudit runs were found")
    selected = resolve_run(workspace, selected_run).name if selected_run or auto_select else None
    if selected is not None and not any(path.name == selected for path in run_dirs):
        raise ValueError("selected run has no run.json record")
    return {
        "schema_version": 3,
        "generated_at": utc_now(),
        "workspace": str(workspace.resolve()),
        "selected_run_id": selected,
        # Offline exports keep complete data; the live UI expands only an explicit selection.
        "runs": [
            summarize_run(path)
            if not selected_only or path.name == selected
            else run_listing(path)
            for path in run_dirs
        ],
    }


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:">
<title>TheoremAudit Evidence View</title><style>
:root{--ink:#17251f;--muted:#637069;--paper:#f6f4ed;--card:#fffdf8;--line:#d9ddd5;--green:#176b4d;--mint:#dceee5;--amber:#b66a16;--red:#ad3c36;--blue:#315a72}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.45 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{padding:28px 34px 22px;background:var(--ink);color:#fff;display:flex;gap:20px;align-items:center;justify-content:space-between}h1{font:600 29px/1.1 ui-serif,Georgia,serif;margin:0}.eyebrow{color:#a9c9b9;font-size:11px;letter-spacing:.14em;text-transform:uppercase}.stamp{color:#cbd6d0;font-size:12px}main{max-width:1440px;margin:auto;padding:24px 30px 50px}.toolbar{display:flex;gap:14px;align-items:center;margin-bottom:20px}select{max-width:760px;width:100%;padding:11px 13px;border:1px solid var(--line);border-radius:9px;background:#fff;font-weight:600}.grid{display:grid;grid-template-columns:1.3fr .7fr;gap:18px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 8px 24px rgba(23,37,31,.05)}.wide{grid-column:1/-1}h2{font:600 20px ui-serif,Georgia,serif;margin:0 0 13px}h3{margin:0 0 5px;font-size:14px}.question{font:500 23px/1.35 ui-serif,Georgia,serif;margin:5px 0 16px}.badges{display:flex;flex-wrap:wrap;gap:8px}.badge{border-radius:999px;padding:5px 9px;background:#eef0eb;color:#46534c;font-size:12px}.badge.good{background:var(--mint);color:var(--green)}.badge.warn{background:#f8e8d3;color:#8a4c08}.pipeline{display:flex;gap:7px;overflow-x:auto;padding:8px 2px 13px}.stage{min-width:112px;border-top:4px solid var(--line);padding:9px 7px;background:#f5f5ef;border-radius:4px 4px 9px 9px}.stage.completed{border-color:var(--green)}.stage.in_progress{border-color:var(--amber);background:#fff5e7}.stage.pending{color:#879089}.stage small{display:block;color:var(--muted);margin-top:4px}.statement,.finding{border-top:1px solid var(--line);padding:13px 0}.statement:first-of-type,.finding:first-of-type{border-top:0}.finding.fatal{border-left:4px solid var(--red);padding-left:10px}.finding.major{border-left:4px solid var(--amber);padding-left:10px}.meta{color:var(--muted);font-size:12px}.empty{color:var(--muted);font-style:italic;padding:8px 0}.coverage{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.coverage div{padding:8px;border-radius:8px;background:#f0f1ec}.yes{color:var(--green);font-weight:700}.no{color:var(--muted)}.decision{border:1px solid var(--line);border-left:5px solid var(--amber);border-radius:11px;padding:15px;background:#fffaf1;margin-bottom:12px}.decision.repair_required{border-left-color:var(--red);background:#fff5f4}.decision h3{font-size:18px}.decision p{color:var(--muted)}.decision-groups{display:grid;gap:8px}.decision-groups details{border:1px solid var(--line);border-radius:9px;background:#fff;padding:10px 12px}.decision-groups summary{font-weight:700;cursor:pointer}@media(max-width:850px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}header{align-items:flex-start;flex-direction:column}main{padding:18px}}
</style></head><body><header><div><div class="eyebrow">Governed research evidence</div><h1>TheoremAudit Evidence View</h1></div><div class="stamp" id="stamp"></div></header>
<main><div class="toolbar"><select id="runSelect" aria-label="Select research run"></select></div><div class="grid">
<section class="card wide"><div class="eyebrow">Research question</div><div class="question" id="question"></div><div class="badges" id="badges"></div></section>
<section class="card wide"><h2>Theory pipeline</h2><div class="pipeline" id="theory"></div><h2>Paper pipeline</h2><div class="pipeline" id="paper"></div></section>
<section class="card"><h2>Accepted results</h2><div id="statements"></div></section>
<section class="card"><h2>Research results still in development</h2><div id="retained"></div></section>
<section class="card"><h2>Invalid results excluded</h2><div id="excluded"></div></section>
<section class="card"><h2>Open blockers</h2><div id="blockers"></div></section>
<section class="card"><h2>Empirical evidence</h2><div class="coverage" id="coverage"></div></section>
<section class="card"><h2>Routing rationale</h2><div id="reasons"></div></section>
<section class="card wide"><h2>Research health</h2><div id="diagnostics"></div></section>
</div></main><script>
const DATA=__DATA__; const $=id=>document.getElementById(id); const safe=v=>String(v??'').replaceAll('_',' ').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function stageHTML(s){return `<div class="stage ${s.status}"><strong>${safe(s.label)}</strong><small>${safe(s.status)}</small></div>`}
function render(run){$('question').textContent=run.question;$('stamp').textContent=`Generated ${DATA.generated_at}`;
 const b=[run.route.manuscript_kind,`submission: ${run.route.submission_readiness}`,`novelty: ${run.route.novelty}`,`significance: ${run.route.significance}`];
 $('badges').innerHTML=b.map((x,i)=>`<span class="badge ${i===0&&run.route.submission_framing_allowed?'good':i===0?'warn':''}">${safe(x)}</span>`).join('');
 $('theory').innerHTML=run.theory_stages.map(stageHTML).join('');$('paper').innerHTML=run.paper_stages.length?run.paper_stages.map(stageHTML).join(''):'<div class="empty">Paper workflow has not started.</div>';
 $('statements').innerHTML=run.accepted_statements.length?run.accepted_statements.map(s=>`<article class="statement"><h3>${safe(s.id)} · ${safe(s.decision)}</h3><div>${safe(s.informal)}</div><div class="meta">${safe(s.scope)}</div></article>`).join(''):'<div class="empty">No accepted statement yet.</div>';
 $('retained').innerHTML=run.retained_nonfinal_statements.length?run.retained_nonfinal_statements.map(s=>`<article class="statement"><h3>${safe(s.id)} · ${safe(s.disposition)}</h3><div>${safe(s.informal)}</div><div class="meta">Not established: ${safe(s.reason)}</div></article>`).join(''):'<div class="empty">No conjecture, repair candidate, or deferred result.</div>';
 $('excluded').innerHTML=run.excluded_statements.length?run.excluded_statements.map(s=>`<article class="finding fatal"><h3>${safe(s.id)} · ${safe(s.disposition)}</h3><div>${safe(s.informal)}</div><div class="meta">Reason: ${safe(s.reason)}</div></article>`).join(''):'<div class="empty">No mathematically invalid result was excluded.</div>';
 $('blockers').innerHTML=run.blockers.length?run.blockers.map(f=>`<article class="finding ${f.severity}"><h3>${safe(f.id)} · ${safe(f.severity)}</h3><div>${safe(f.description)}</div><div class="meta">Next: ${safe(f.action)}</div></article>`).join(''):'<div class="empty">No open major or fatal blocker.</div>';
 const cov=run.empirical.coverage;$('coverage').innerHTML=Object.keys(cov).length?Object.entries(cov).map(([k,v])=>`<div><span class="${v?'yes':'no'}">${v?'✓':'○'}</span> ${safe(k)}</div>`).join(''):'<div class="empty">No claim-linked empirical evidence recorded.</div>';
 $('reasons').innerHTML=run.route.reasons.length?`<ul>${run.route.reasons.map(x=>`<li>${safe(x)}</li>`).join('')}</ul>`:'<div class="empty">No route has been derived.</div>';
 const diagnostics=run.compiler?.diagnostics||[],decision=run.compiler?.decision_summary||{};const groups=[['mathematics','Required mathematical repairs'],['integrity','Evidence integrity'],['manuscript','Manuscript and review'],['publication','Publication-route limitations'],['development','Optional development opportunities']];const detail=groups.map(([key,title])=>{const entries=diagnostics.filter(d=>(d.group||'mathematics')===key);return entries.length?`<details ${key==='mathematics'||key==='integrity'?'open':''}><summary>${safe(title)} · ${entries.length}</summary>${entries.map(d=>`<article class="finding ${d.severity==='error'?'fatal':d.severity==='warning'?'major':''}"><h3>${safe(d.id)} · ${safe(d.title)}</h3><div>${safe(d.message)}</div><div class="meta">Next: ${safe(d.action)}</div></article>`).join('')}</details>`:''}).join('');$('diagnostics').innerHTML=`<div class="decision ${safe(decision.state)}"><div class="eyebrow">Current decision</div><h3>${safe(decision.headline||'Research health')}</h3><p>${safe(decision.explanation||'Review the evidence below.')}</p><div class="meta"><strong>Next:</strong> ${safe(decision.next_action||'Inspect the highest-priority finding.')}</div></div><div class="decision-groups">${detail||'<div class="empty">No modeled evidence inconsistency or open review action.</div>'}</div>`}
const select=$('runSelect');DATA.runs.forEach(r=>{const o=document.createElement('option');o.value=r.run_id;o.textContent=`${r.run_id} — ${r.question}`;select.appendChild(o)});select.value=DATA.selected_run_id;select.addEventListener('change',()=>render(DATA.runs.find(r=>r.run_id===select.value)));render(DATA.runs.find(r=>r.run_id===select.value)||DATA.runs[0]);
</script></body></html>'''


def safe_output(workspace: Path, requested: Optional[str]) -> Path:
    root = workspace.resolve()
    unresolved = root / requested if requested else data_root(root) / "dashboard" / "index.html"
    if unresolved.is_symlink():
        raise ValueError("evidence-view output cannot be a symbolic link")
    path = unresolved.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("evidence-view output must stay inside the workspace") from exc
    return path


def command_build(args: argparse.Namespace) -> None:
    workspace = Path(args.workspace)
    data = dashboard_data(workspace, args.run)
    output = safe_output(workspace, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    content = HTML.replace("__DATA__", encoded).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(output.parent), prefix=f".{output.name}.",
            suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(output))
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps({"dashboard": str(output), "selected_run_id": data["selected_run_id"],
                      "runs": len(data["runs"])}, indent=2))


def command_data(args: argparse.Namespace) -> None:
    print(json.dumps(dashboard_data(Path(args.workspace), args.run), indent=2, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    commands = result.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--output")
    build.set_defaults(function=command_build)
    data = commands.add_parser("data")
    data.set_defaults(function=command_data)
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        args.function(args)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
