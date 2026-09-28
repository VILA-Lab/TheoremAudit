#!/usr/bin/env python3
"""Normalize TheoremAudit evidence into a research graph and compiler diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from state_store import file_sha256, read_json


def optional_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return read_json(path)
    except ValueError:
        return default


def artifact_health(run_dir: Path) -> List[Dict[str, str]]:
    """Report unreadable run JSON without making the visualizer itself unavailable."""
    issues: List[Dict[str, str]] = []
    for path in sorted(run_dir.rglob("*.json")):
        relative = str(path.relative_to(run_dir))
        if path.is_symlink():
            issues.append({"path": relative, "problem": "JSON evidence is a symbolic link"})
            continue
        try:
            if path.stat().st_size > 20 * 1024 * 1024:
                issues.append({"path": relative, "problem": "JSON evidence exceeds the 20 MiB inspection limit"})
                continue
            value = read_json(path)
            if not isinstance(value, (dict, list)):
                issues.append({"path": relative, "problem": "JSON evidence must contain an object or array"})
        except (OSError, ValueError) as exc:
            issues.append({"path": relative, "problem": str(exc)})
    return issues


def _text(value: Any) -> str:
    return "" if value is None else str(value)


class ResearchGraph:
    def __init__(self) -> None:
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, str]] = []
        self._node_ids: Set[str] = set()
        self._edge_keys: Set[Tuple[str, str, str]] = set()
        self.integrity_issues: List[Dict[str, str]] = []

    def add_node(
        self,
        node_id: str,
        kind: str,
        title: str,
        summary: str = "",
        *,
        status: str = "recorded",
        severity: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        source_path: Optional[str] = None,
    ) -> None:
        if not node_id:
            return
        if node_id in self._node_ids:
            self.integrity_issues.append({
                "kind": "duplicate_node", "source": source_path or "unknown", "node_id": node_id,
            })
            return
        self._node_ids.add(node_id)
        self.nodes.append({
            "id": node_id,
            "kind": kind,
            "title": title,
            "summary": summary,
            "status": status,
            "severity": severity,
            "details": details or {},
            "source_path": source_path,
        })

    def add_edge(self, source: str, target: str, relation: str) -> None:
        key = (source, target, relation)
        if key in self._edge_keys:
            return
        if source not in self._node_ids or target not in self._node_ids:
            self.integrity_issues.append({
                "kind": "dangling_edge", "source": source, "target": target, "relation": relation,
            })
            return
        self._edge_keys.add(key)
        self.edges.append({"source": source, "target": target, "relation": relation})


def _add_discovery(graph: ResearchGraph, run_dir: Path) -> Dict[str, Any]:
    discovery = optional_json(run_dir / "artifacts" / "discovery.json", {})
    for item in discovery.get("assumptions", []):
        item_id = _text(item.get("id"))
        graph.add_node(
            item_id, "assumption", item_id, _text(item.get("statement")),
            status="active", source_path="artifacts/discovery.json",
        )
    for item in discovery.get("theorem_targets", []):
        item_id = _text(item.get("id"))
        graph.add_node(
            item_id, "target", item_id, _text(item.get("statement")),
            status="target", source_path="artifacts/discovery.json",
        )
    for item in discovery.get("proof_obligations", []):
        item_id = _text(item.get("id"))
        graph.add_node(
            item_id,
            "proof",
            item_id,
            _text(item.get("description")),
            status="planned",
            details={
                "supports": item.get("supports"),
                "depends_on": item.get("depends_on", []),
                "assumptions_expected": item.get("assumptions_expected", []),
            },
            source_path="artifacts/discovery.json",
        )
    return discovery


def _merge_proofs(graph: ResearchGraph, run_dir: Path, discovery: Dict[str, Any]) -> Dict[str, Any]:
    proof_index = optional_json(run_dir / "proofs" / "index.json", {})
    by_id = {item.get("id"): item for item in proof_index.get("proofs", [])}
    for node in graph.nodes:
        if node["kind"] != "proof" or node["id"] not in by_id:
            continue
        proof = by_id[node["id"]]
        node["status"] = _text(proof.get("status") or "planned")
        node["details"].update({
            "proved_scope": proof.get("proved_scope", ""),
            "gaps": proof.get("gaps", []),
            "assumptions_used": proof.get("assumptions_used", []),
            "draft_path": proof.get("draft_path"),
        })
        if proof.get("proved_scope"):
            node["summary"] = _text(proof["proved_scope"])
        node["source_path"] = proof.get("draft_path") or "proofs/index.json"

    obligations = {item.get("id"): item for item in discovery.get("proof_obligations", [])}
    for proof_id, proof in by_id.items():
        if not proof_id or proof_id in graph._node_ids:
            continue
        graph.add_node(
            _text(proof_id), "proof", _text(proof_id), _text(proof.get("proved_scope")),
            status=_text(proof.get("status") or "recorded"), details=proof,
            source_path=proof.get("draft_path") or "proofs/index.json",
        )
    for proof_id, item in obligations.items():
        for assumption_id in item.get("assumptions_expected", []):
            graph.add_edge(_text(assumption_id), _text(proof_id), "required by")
        for dependency_id in item.get("depends_on", []):
            graph.add_edge(_text(dependency_id), _text(proof_id), "supports")
        graph.add_edge(_text(proof_id), _text(item.get("supports")), "proves target")
    return proof_index


def _add_theorems(graph: ResearchGraph, run_dir: Path) -> Dict[str, Any]:
    synthesis = optional_json(run_dir / "artifacts" / "synthesized_theorems.json", {})
    bundle = optional_json(run_dir / "artifacts" / "theory_bundle.json", {})
    decisions = {}
    dispositions = {}
    for collection in ("accepted_statements", "retained_nonfinal_statements", "excluded_statements"):
        for record in bundle.get(collection, []):
            statement_id = record.get("effective_statement", {}).get("id")
            if statement_id:
                decisions[statement_id] = record.get("decision", {})
                dispositions[statement_id] = record.get("disposition", collection)
    statements = list(synthesis.get("statements", []))
    seen = {item.get("id") for item in statements if isinstance(item, dict)}
    # A completed bundle remains the authoritative handoff even if an older run did
    # not retain the intermediate synthesis artifact.
    for collection in ("accepted_statements", "retained_nonfinal_statements", "excluded_statements"):
        for record in bundle.get(collection, []):
            item = record.get("effective_statement", {})
            if item.get("id") and item.get("id") not in seen:
                statements.append(item)
                seen.add(item["id"])
    for item in statements:
        item_id = _text(item.get("id"))
        decision = decisions.get(item_id, {})
        graph.add_node(
            item_id,
            "theorem",
            item_id,
            _text(item.get("informal") or item.get("formal")),
            status=_text(decision.get("status") or "synthesized"),
            details={
                "formal": item.get("formal", ""),
                "proven_scope": item.get("proven_scope", ""),
                "honest_caveats": item.get("honest_caveats", ""),
                "assumptions_used": item.get("assumptions_used", []),
                "synthesized_from": item.get("synthesized_from", []),
                "based_on": item.get("based_on", []),
                "decision_reason": decision.get("reason", ""),
                "disposition": dispositions.get(item_id, "not_yet_governed"),
            },
            source_path=("artifacts/synthesized_theorems.json" if item in synthesis.get("statements", [])
                         else "artifacts/theory_bundle.json"),
        )
    for item in statements:
        theorem_id = _text(item.get("id"))
        for assumption_id in item.get("assumptions_used", []):
            graph.add_edge(_text(assumption_id), theorem_id, "assumed by")
        for proof_id in item.get("synthesized_from", []):
            graph.add_edge(_text(proof_id), theorem_id, "establishes")
        for target_id in item.get("based_on", []):
            graph.add_edge(_text(target_id), theorem_id, "refined into")
    return bundle


def _add_findings(graph: ResearchGraph, run_dir: Path) -> List[Dict[str, Any]]:
    all_findings: List[Dict[str, Any]] = []
    for filename, label in (("local_audit.json", "Local audit"), ("final_audit.json", "Final audit")):
        artifact = optional_json(run_dir / "artifacts" / filename, {})
        effective = {item.get("id"): dict(item) for item in artifact.get("findings", [])}
        for event in artifact.get("events", []):
            item = effective.get(event.get("finding_id"))
            if item is None:
                continue
            if event.get("event_type") == "amendment":
                for field, change in event.get("changes", {}).items():
                    if isinstance(change, dict) and "to" in change:
                        item[field] = change["to"]
            elif event.get("event_type") == "resolution_verification":
                item["resolved"] = event.get("outcome") == "resolved"
                item["resolution"] = event.get("resolution")
        for item in effective.values():
            finding = dict(item)
            finding["audit"] = label
            all_findings.append(finding)
            finding_id = _text(item.get("id"))
            graph.add_node(
                finding_id,
                "finding",
                finding_id,
                _text(item.get("description")),
                status="resolved" if item.get("resolved") else "open",
                severity=_text(item.get("severity") or "minor"),
                details={
                    "kind": item.get("kind"),
                    "target_id": item.get("target_id"),
                    "resolution": item.get("resolution", ""),
                    "audit": label,
                },
                source_path=f"artifacts/{filename}",
            )
            graph.add_edge(_text(item.get("target_id")), finding_id, "challenged by")
    return all_findings


def _add_prior_work(graph: ResearchGraph, run_dir: Path) -> Dict[str, Any]:
    novelty = optional_json(run_dir / "artifacts" / "novelty_audit.json", {})
    for item in novelty.get("closest_work_comparisons", []):
        item_id = _text(item.get("id"))
        graph.add_node(
            item_id,
            "prior_work",
            _text(item.get("title") or item_id),
            _text(item.get("delta") or item.get("comparison")),
            status="verified" if item.get("verified") else "unverified",
            details={
                "source_url": item.get("source_url"),
                "theorem_location": item.get("theorem_location"),
                "prior_result": item.get("prior_result", ""),
                "current_result": item.get("current_result", ""),
                "overlap": item.get("overlap", ""),
            },
            source_path="artifacts/novelty_audit.json",
        )
        graph.add_edge(item_id, _text(item.get("statement_id")), "positions")
    return novelty


def _add_paper(graph: ResearchGraph, run_dir: Path) -> Dict[str, Any]:
    index = optional_json(run_dir / "paper" / "sections" / "index.json", {})
    for item in index.get("sections", []):
        node_id = f"SEC:{_text(item.get('name'))}"
        graph.add_node(
            node_id,
            "section",
            _text(item.get("title") or item.get("name")),
            f"{len(item.get('claims_used', []))} traced claim(s), {len(item.get('citations_used', []))} citation(s).",
            status="written",
            details={
                "name": item.get("name"),
                "location": item.get("location"),
                "claims_used": item.get("claims_used", []),
                "citations_used": item.get("citations_used", []),
            },
            source_path=f"paper/{item.get('path')}" if item.get("path") else "paper/sections/index.json",
        )
        for theorem_id in item.get("claims_used", []):
            graph.add_edge(_text(theorem_id), node_id, "claimed in")
    return index


def _add_development_actions(graph: ResearchGraph, run_dir: Path) -> Dict[str, Any]:
    contribution = optional_json(run_dir / "artifacts" / "contribution_assessment.json", {})
    primary = [_text(item) for item in contribution.get("primary_statement_ids", [])]
    for item in contribution.get("development_obligations", []):
        item_id = _text(item.get("id"))
        graph.add_node(
            item_id,
            "action",
            item_id,
            _text(item.get("description")),
            status="recommended",
            severity=_text(item.get("priority") or "medium"),
            details={"priority": item.get("priority")},
            source_path="artifacts/contribution_assessment.json",
        )
        for theorem_id in primary:
            graph.add_edge(theorem_id, item_id, "strengthened by")
    return contribution


def compiler_diagnostics(
    run_dir: Path,
    graph: ResearchGraph,
    findings: Iterable[Dict[str, Any]],
    bundle: Dict[str, Any],
    contribution: Dict[str, Any],
    section_index: Dict[str, Any],
    route: Optional[Dict[str, Any]] = None,
    artifact_issues: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    diagnostics: List[Dict[str, Any]] = []

    def add(
        item_id: str,
        severity: str,
        category: str,
        title: str,
        message: str,
        action: str,
        targets: Optional[List[str]] = None,
        source: str = "",
        repair_class: str = "",
    ) -> None:
        identifier = item_id or f"COMP-{category.upper()}-{len(diagnostics) + 1:04d}"
        diagnostics.append({
            "id": identifier,
            "severity": severity,
            "category": category,
            "title": title,
            "message": message,
            "action": action,
            "target_ids": targets or [],
            "source": source,
            "repair_class": repair_class,
        })

    for index, issue in enumerate(artifact_issues or [], start=1):
        archived = Path(issue["path"]).parts[0] in {"corrections", "strengthening"}
        add(
            f"COMP-ARTIFACT-{index:04d}", "error", "artifact_integrity",
            "Archived evidence file check failed" if archived else "Evidence file check failed",
            f"{issue['path']}: {issue['problem']}",
            "Inspect the file format and whether current results depend on it. "
            "Use an explicit revision to correct affected evidence; preserve earlier versions.",
            source=issue["path"],
        )
        diagnostics[-1]["evidence_scope"] = "archived" if archived else "current"

    for item in findings:
        if item.get("resolved"):
            continue
        raw = _text(item.get("severity") or "minor")
        severity = "error" if raw == "fatal" else "warning" if raw == "major" else "info"
        add(
            _text(item.get("id")), severity, _text(item.get("kind") or "audit"),
            f"{item.get('audit', 'Audit')} finding on {item.get('target_id', 'evidence')}",
            _text(item.get("description")),
            "Open a governed repair branch or preserve the limitation explicitly.",
            [_text(item.get("target_id"))], _text(item.get("audit")),
        )

    for index, issue in enumerate(graph.integrity_issues, start=1):
        add(
            f"COMP-GRAPH-{index:04d}", "warning", "traceability", "Incomplete research-graph link",
            (f"Duplicate object {issue.get('node_id')} was ignored." if issue.get("kind") == "duplicate_node"
             else f"Could not connect {issue.get('source')} to {issue.get('target')} ({issue.get('relation')})."),
            "Inspect the cited artifacts and repair identifiers or dependency links through the governed workflow.",
            [value for value in (issue.get("node_id"), issue.get("source"), issue.get("target")) if value],
            issue.get("source", "research_graph"),
        )

    significance = optional_json(run_dir / "artifacts" / "significance_audit.json", {})
    for item in significance.get("blocking_findings", []):
        raw = _text(item.get("severity") or "minor")
        severity = "error" if raw == "fatal" else "warning" if raw == "major" else "info"
        add(
            _text(item.get("id")), severity, _text(item.get("category") or "significance"),
            "Significance constraint", _text(item.get("description")),
            _text(item.get("required_action")), source="significance_audit",
        )

    accepted = {
        item.get("effective_statement", {}).get("id")
        for item in bundle.get("accepted_statements", [])
    }
    for item in bundle.get("accepted_statements", []):
        statement_id = _text(item.get("effective_statement", {}).get("id"))
        supporting = item.get("supporting_proofs", [])
        if not supporting:
            add(
                f"COMP-{statement_id}-PROOF", "error", "traceability",
                f"{statement_id} has no supporting proof records",
                "The accepted statement cannot be traced to a persisted proof record.",
                "Repair the theory bundle through the governed synthesis and arbiter stages.",
                [statement_id], "theory_bundle",
            )

    known_claims = {item for item in accepted if item}
    for section in section_index.get("sections", []):
        for claim_id in section.get("claims_used", []):
            if claim_id not in known_claims:
                add(
                    f"COMP-SEC-{section.get('name')}-{claim_id}", "error", "manuscript",
                    f"Unsupported manuscript claim {claim_id}",
                    f"Section {section.get('title') or section.get('name')} references a claim absent from the accepted theory bundle.",
                    "Remove the claim or repair and re-accept it before compiling the manuscript.",
                    [_text(claim_id), f"SEC:{section.get('name')}"], "paper/sections/index.json",
                )

    for item in contribution.get("development_obligations", []):
        priority = _text(item.get("priority") or "medium")
        add(
            _text(item.get("id")), "warning" if priority == "high" else "info", "development",
            f"{priority.title()}-priority development opportunity",
            _text(item.get("description")),
            "Create a scoped research branch and evaluate whether completing it changes the paper route.",
            [_text(item.get("id"))], "contribution_assessment",
        )

    review_path = run_dir / "paper" / "review.json"
    review = optional_json(review_path, {})
    revision = optional_json(run_dir / "paper" / "revision.json", {})
    addressed_review = {
        item.get("finding_id") for item in revision.get("finding_responses", [])
        if item.get("disposition") == "addressed"
    }
    for item in review.get("findings", []):
        if item.get("id") in addressed_review:
            continue
        raw = _text(item.get("severity") or "minor")
        severity = "error" if raw == "fatal" else "warning" if raw == "major" else "info"
        add(
            _text(item.get("id")), severity, _text(item.get("criterion") or "review"),
            "Independent review finding", _text(item.get("description") or item.get("summary")),
            _text(item.get("required_action")), source="paper/review.json",
            repair_class=_text(item.get("repair_class")),
        )

    comments = optional_json(run_dir / "paper" / "user_comments.json", {})
    for item in comments.get("comments", []):
        if item.get("status") == "addressed":
            continue
        severity = "warning" if item.get("priority") == "required" else "info"
        add(
            _text(item.get("id")), severity, "researcher_feedback", "Open researcher comment",
            _text(item.get("text")), "Address or explicitly decline this comment in the next manuscript revision.",
            source="paper/user_comments.json",
        )

    route = route or bundle.get("paper_route", {})
    if route and route.get("publication_goal_satisfied") is False:
        add(
            "COMP-PUBLICATION-GOAL", "warning", "routing", "Publication goal is not supported",
            " ".join(route.get("unmet_publication_goal_reasons", [])) or
            "The current evidence does not support the requested publication goal.",
            "Strengthen the missing evidence while continuing the strongest evidence-consistent manuscript.",
            source="theory_bundle",
        )
    gate_labels = {
        "novelty_supported": "Novelty evidence", "significance_sufficient_for_conference": "Conference-level significance",
        "application_evidence_ready": "Application evidence", "parameter_sensitivity_ready": "Sensitivity evidence",
        "baseline_evidence_ready": "Baseline evidence", "theoretical_depth_ready": "Theoretical depth",
        "no_major_or_fatal_significance_blocker": "Significance audit",
    }
    for gate, passed in route.get("routing_gates", {}).items():
        if passed is False:
            add(
                f"COMP-GATE-{gate.upper()}", "info", "routing", f"{gate_labels.get(gate, gate)} gate is not met",
                "This evidence gate currently limits the route; it is not a mathematical correctness failure.",
                "Inspect the routing rationale before deciding whether a scoped strengthening run is worthwhile.",
                source="theory_bundle",
            )

    compile_report = optional_json(run_dir / "paper" / "compile_report.json", {})
    tex_path = run_dir / "paper" / "paper.tex"
    pdf_path = run_dir / "paper" / "paper.pdf"
    if compile_report and tex_path.is_file() and compile_report.get("tex_sha256"):
        if compile_report["tex_sha256"] != file_sha256(tex_path):
            add(
                "COMP-STALE-COMPILE", "error", "manuscript", "Compilation report is stale",
                "paper.tex changed after the recorded compilation.", "Recompile before review or packaging.",
                source="paper/compile_report.json",
            )
    if compile_report.get("pdf_built") and pdf_path.is_file() and compile_report.get("pdf_sha256"):
        if compile_report["pdf_sha256"] != file_sha256(pdf_path):
            add(
                "COMP-STALE-PDF", "error", "manuscript", "Compiled PDF is stale",
                "paper.pdf changed after its compile report was recorded.", "Recompile and repeat independent review.",
                source="paper/compile_report.json",
            )
    if review and review.get("compile_report_sha256") and (run_dir / "paper" / "compile_report.json").is_file():
        if review["compile_report_sha256"] != file_sha256(run_dir / "paper" / "compile_report.json"):
            add(
                "COMP-STALE-REVIEW", "warning", "review", "Independent review is stale",
                "The compile report changed after the recorded review.", "Run independent paper review on the current PDF.",
                source="paper/review.json",
            )

    experiments = optional_json(run_dir / "paper" / "experiments" / "index.json", {})
    for figure in experiments.get("figures", []):
        if figure.get("role") == "main" and figure.get("status") != "publication_ready":
            add(
                f"COMP-{_text(figure.get('figure_id'))}-QUALITY", "warning", "figure",
                f"Main figure {_text(figure.get('figure_id'))} is not publication-ready",
                f"Current figure state: {_text(figure.get('status') or 'unknown')}.",
                "Complete structural and visual review at manuscript size.", source="paper/experiments/index.json",
            )

    def diagnostic_group(item: Dict[str, Any]) -> str:
        category = item.get("category")
        source = item.get("source")
        if category == "routing" or source == "significance_audit":
            return "publication"
        if category == "development":
            return "development"
        # Review criteria are intentionally free-form (for example,
        # "venue-bound page layout").  Their source, not that prose label,
        # determines that they are manuscript findings.  Falling through to
        # mathematics here makes presentation warnings look like proof gaps.
        if source == "paper/review.json":
            repair_class = item.get("repair_class")
            if repair_class and repair_class not in {
                "layout", "exposition", "figure_presentation", "table_presentation",
                "citation_presentation", "latex_presentation",
            }:
                return "mathematics"
            return "manuscript"
        if category in {"manuscript", "review", "figure", "researcher_feedback"}:
            return "manuscript"
        if category in {"artifact_integrity", "traceability"}:
            return "integrity"
        return "mathematics"

    for item in diagnostics:
        item["group"] = diagnostic_group(item)

    order = {"error": 0, "warning": 1, "info": 2}
    diagnostics.sort(key=lambda item: (order.get(item["severity"], 9), item["id"]))
    counts = {key: sum(1 for item in diagnostics if item["severity"] == key) for key in order}
    mathematical_findings = [
        item for item in diagnostics
        if item["group"] == "mathematics"
        and item["severity"] in {"error", "warning"}
    ]
    integrity_findings = [
        item for item in diagnostics
        if item["group"] == "integrity"
        and item["severity"] in {"error", "warning"}
    ]
    evidence_findings = mathematical_findings + integrity_findings
    manuscript_findings = [
        item for item in diagnostics
        if item["group"] == "manuscript"
    ]
    blocking_findings = evidence_findings + [
        item for item in manuscript_findings
        if item["severity"] in {"error", "warning"}
    ]
    status = (
        "blocked"
        if any(item["severity"] == "error" for item in blocking_findings)
        else "needs_attention"
        if any(item["severity"] == "warning" for item in blocking_findings)
        else "clean"
    )
    publication = [item for item in diagnostics if item["group"] == "publication"]
    development = [item for item in diagnostics if item["group"] == "development"]
    accepted_count = len(bundle.get("accepted_statements", []))
    manifest = optional_json(run_dir / "run.json", {})
    theory_complete = manifest.get("status") == "completed"
    paper_manifest = optional_json(run_dir / "paper" / "paper_run.json", {})
    paper_started = bool(paper_manifest)
    paper_completed = paper_manifest.get("status") == "completed"
    manuscript_kind = _text(route.get("manuscript_kind") or (
        "evidence_report" if route.get("publication_tier") == "research_report" else "full_paper"
    ))
    submission_readiness = _text(route.get("submission_readiness") or (
        "ready" if route.get("submission_framing_allowed") else "evidence incomplete"
    ))

    # Findings describe saved evidence, not whether an execution worker is running.
    if mathematical_findings:
        decision = {
            "state": "repair_required",
            "headline": (
                "Completed manuscript has unresolved mathematical findings"
                if paper_completed else "Mathematical findings require review"
            ),
            "explanation": (
                f"{len(mathematical_findings)} unresolved mathematical finding"
                f"{'s' if len(mathematical_findings) != 1 else ''} affect the claims or proofs identified below. "
                "Inspect their dependencies before relying on the affected results. "
                "This summary does not indicate that a repair is running."
            ),
            "next_action": "Inspect the findings, then explicitly resume or request a revision for correction and renewed review.",
            "action": "repair",
        }
    elif integrity_findings:
        decision = {
            "state": "evidence_attention",
            "headline": (
                "Completed manuscript; evidence checks need attention"
                if paper_completed else "Evidence checks need attention"
            ),
            "explanation": (
                f"{len(integrity_findings)} evidence-file or reference check"
                f"{'s' if len(integrity_findings) != 1 else ''} failed. "
                "These checks do not establish a mathematical error or start a repair. "
                "Saved claim decisions are unchanged; inspect the affected evidence before relying on it."
            ),
            "next_action": "Inspect the evidence findings and any linked claims. Request a revision if a correction is needed.",
            "action": "inspect",
        }
    elif not theory_complete and not bundle and not paper_completed:
        decision = {
            "state": "research_in_progress",
            "headline": "Research assessment is not yet complete",
            "explanation": "A paper decision will be made only after proof, audit, novelty, and significance evidence is complete.",
            "next_action": "Continue the current governed stage.",
            "action": "continue",
        }
    elif accepted_count == 0 and not paper_completed:
        decision = {
            "state": "no_accepted_result",
            "headline": "No result is currently accepted for manuscript use",
            "explanation": (
                "The Arbiter accepted no statement into the governed theory bundle. The paper pipeline therefore "
                "documents the attempted claims, proof failures, audits, salvage analysis, and limitations without "
                "presenting any theorem as established."
            ),
            "next_action": "Review the findings and use the evidence-report workflow if no result can be accepted.",
            "action": "write",
        }
    elif paper_completed:
        if manuscript_findings:
            decision = {
                "state": "package_with_warnings",
                "headline": "Manuscript completed with review findings",
                "explanation": (
                    f"The governed mathematical results remain accepted. {len(manuscript_findings)} "
                    f"unresolved manuscript or review finding"
                    f"{'s' if len(manuscript_findings) != 1 else ''} "
                    f"{'remain' if len(manuscript_findings) != 1 else 'remains'} in the draft. "
                    "These findings are separate from mathematical review."
                ),
                "next_action": "Inspect the remaining findings and request a manuscript revision as needed.",
                "action": "revise",
            }
        else:
            decision = {
                "state": "package_completed",
                "headline": "Manuscript is complete",
                "explanation": (
                    "The manuscript workflow is complete. Any novelty and significance limitations "
                    "remain listed below; completion does not imply submission readiness."
                ),
                "next_action": "Inspect the manuscript and its supporting evidence, or request a revision.",
                "action": "inspect",
            }
    elif paper_started and manuscript_findings:
        decision = {
            "state": "manuscript_repair_required",
            "headline": "Manuscript revision is required before packaging",
            "explanation": (
                f"{len(manuscript_findings)} unresolved manuscript or review finding"
                f"{'s' if len(manuscript_findings) != 1 else ''} require paper-stage repair. "
                "The governed theorem decisions are unchanged."
            ),
            "next_action": "Continue the bounded manuscript revision, compilation, and fresh review cycle.",
            "action": "revise",
        }
    elif paper_started:
        decision = {
            "state": "paper_in_progress",
            "headline": "The manuscript workflow is not yet complete",
            "explanation": "The saved manuscript stages show outstanding work. See Research for execution status.",
            "next_action": "Resolve the current manuscript, experiment, or review-stage findings.",
            "action": "revise",
        }
    elif route.get("writing_allowed"):
        decision = {
            "state": "paper_ready",
            "headline": "The reviewed results are eligible for manuscript development",
            "explanation": (
                "The theory bundle permits writing. A full run continues automatically, aiming for "
                "submission readiness while preserving every evidence and correctness constraint."
            ),
            "next_action": "Continue automatically with the strongest supported manuscript route.",
            "action": "write",
        }
    else:
        decision = {
            "state": "route_limited",
            "headline": "Acceptance evidence is incomplete, so manuscript development remains neutral",
            "explanation": (
                "The current novelty and significance evidence does not yet support submission framing. "
                "The controller still writes the strongest evidence-consistent research draft and records "
                "the exact work needed for acceptance readiness."
            ),
            "next_action": "Continue automatically with the full-length provisional-venue paper or evidence report.",
            "action": "write",
        }
    target_ids = [target for item in evidence_findings for target in item.get("target_ids", []) if target]
    decision.update({
        "primary_count": len(evidence_findings),
        "mathematical_count": len(mathematical_findings),
        "integrity_count": len(integrity_findings),
        "manuscript_count": len(manuscript_findings),
        "publication_count": len(publication),
        "development_count": len(development),
        "accepted_count": accepted_count,
        "target_id": target_ids[0] if target_ids else None,
        "manuscript_kind": manuscript_kind,
        "submission_readiness": submission_readiness,
    })
    return {
        "status": status,
        "counts": counts,
        "diagnostics": diagnostics,
        "decision_summary": decision,
    }


def claim_impact(
    run_dir: Path, findings: Optional[Iterable[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Explain which findings actually reach each synthesized result.

    Research targets in ``based_on`` are displayed as provenance but never treated as
    logical dependencies. Impact follows the transitive proof closure instead.
    """
    synthesis = optional_json(run_dir / "artifacts" / "synthesized_theorems.json", {})
    bundle = optional_json(run_dir / "artifacts" / "theory_bundle.json", {})
    statements = [item for item in synthesis.get("statements", []) if isinstance(item, dict)]
    if not statements:
        for collection in (
            "accepted_statements", "retained_nonfinal_statements", "excluded_statements"
        ):
            statements.extend(
                record.get("effective_statement", {})
                for record in bundle.get(collection, [])
                if isinstance(record, dict) and record.get("effective_statement", {}).get("id")
            )
    proof_artifact = optional_json(run_dir / "proofs" / "index.json", {})
    proofs = {
        item.get("id"): item for item in proof_artifact.get("proofs", [])
        if isinstance(item, dict) and item.get("id")
    }
    decision_by_id: Dict[str, Dict[str, Any]] = {}
    for collection in (
        "accepted_statements", "retained_nonfinal_statements", "excluded_statements"
    ):
        for record in bundle.get(collection, []):
            statement_id = record.get("effective_statement", {}).get("id")
            if statement_id:
                decision_by_id[statement_id] = record.get("decision", {})
    arbiter = optional_json(run_dir / "artifacts" / "arbiter.json", {})
    for decision in arbiter.get("decisions", []):
        if isinstance(decision, dict) and decision.get("statement_id"):
            decision_by_id.setdefault(decision["statement_id"], decision)

    effective_findings = list(findings or [])
    impacts: List[Dict[str, Any]] = []
    for statement in statements:
        statement_id = _text(statement.get("id"))
        pending = list(statement.get("synthesized_from", []))
        proof_closure: Set[str] = set()
        while pending:
            proof_id = _text(pending.pop())
            if not proof_id or proof_id in proof_closure:
                continue
            proof_closure.add(proof_id)
            pending.extend(proofs.get(proof_id, {}).get("depends_on", []))
        assumptions = set(_text(item) for item in statement.get("assumptions_used", []))
        for proof_id in proof_closure:
            assumptions.update(
                _text(item) for item in proofs.get(proof_id, {}).get("assumptions_used", [])
            )
        dependency_targets = {"RUN", statement_id, *proof_closure, *assumptions}
        relevant = []
        for finding in effective_findings:
            if finding.get("resolved"):
                continue
            scope = {_text(item) for item in finding.get("scope_affected", [])}
            if _text(finding.get("target_id")) in dependency_targets or dependency_targets & scope:
                relevant.append(finding)
        hard = [item for item in relevant if item.get("severity") in {"major", "fatal"}]
        minor = [item for item in relevant if item.get("severity") == "minor"]
        decision = decision_by_id.get(statement_id, {})
        accepted = decision.get("status") in {"theorem_ready", "proposition_ready"}
        if hard:
            status = "blocked_by_proof"
            recommendation = "Repair the affected proof closure, then repeat independent audit."
        elif accepted:
            status = "accepted"
            recommendation = "Accepted in the saved review; no unresolved mathematical blocker is linked to these dependencies."
        elif minor:
            status = "salvage_after_minor_repair"
            recommendation = "Repair the local definition or endpoint issue, then re-audit this result independently."
        else:
            status = "salvage_candidate"
            recommendation = "Re-run Arbiter review using only this result's proof closure."
        impacts.append({
            "statement_id": statement_id,
            "status": status,
            "current_arbiter_status": decision.get("status", "not_decided"),
            "proof_closure": sorted(proof_closure),
            "assumptions": sorted(item for item in assumptions if item),
            "research_origin": list(statement.get("based_on", [])),
            "blocking_findings": [item.get("id") for item in hard],
            "minor_findings": [item.get("id") for item in minor],
            "recommendation": recommendation,
        })
    return impacts


def research_model(run_dir: Path) -> Dict[str, Any]:
    evidence_issues = artifact_health(run_dir)
    graph = ResearchGraph()
    discovery = _add_discovery(graph, run_dir)
    _merge_proofs(graph, run_dir, discovery)
    bundle = _add_theorems(graph, run_dir)
    findings = _add_findings(graph, run_dir)
    _add_prior_work(graph, run_dir)
    section_index = _add_paper(graph, run_dir)
    contribution = _add_development_actions(graph, run_dir)
    compiler = compiler_diagnostics(
        run_dir, graph, findings, bundle, contribution, section_index, bundle.get("paper_route", {}),
        evidence_issues,
    )
    kinds: Dict[str, int] = {}
    for node in graph.nodes:
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
    return {
        "graph": {"nodes": graph.nodes, "edges": graph.edges, "kind_counts": kinds},
        "compiler": compiler,
        "claim_impact": claim_impact(run_dir, findings),
        "artifact_health": {"status": "invalid" if evidence_issues else "valid", "issues": evidence_issues},
    }
