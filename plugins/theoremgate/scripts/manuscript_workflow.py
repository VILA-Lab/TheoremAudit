#!/usr/bin/env python3
"""Deterministic post-theory controller for a TheoremAudit paper package."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

from experiment_schema import FINAL_STATUSES, validate_experiment, validate_strategy
from literature.record_schema import validate_record
from state_store import (
    file_sha256, load_manifest, read_json, resolve_run, update_json, utc_now, write_json,
)
from venue_tools import venue_candidates


STAGES: Dict[str, Dict[str, str]] = {
    "literature_audit": {"actor": "literature_auditor", "artifact": "literature_audit.json"},
    "exemplar_study": {"actor": "manuscript_architect", "artifact": "writing_exemplars.json"},
    "venue_selection": {"actor": "venue_formatter", "artifact": "venue_selection.json"},
    "content_architecture": {"actor": "manuscript_architect", "artifact": "content_architecture.json"},
    "empirical_validation": {"actor": "experimenter", "artifact": "empirical_validation.json"},
    "section_writing": {"actor": "manuscript_writer", "artifact": "sections/index.json"},
    "compilation": {"actor": "manuscript_compiler", "artifact": "compile_report.json"},
    "independent_review": {"actor": "paper_reviewer", "artifact": "review.json"},
    "revision": {"actor": "manuscript_writer", "artifact": "revision.json"},
    "final_package": {"actor": "paper_reviewer", "artifact": "final_package.json"},
}

MAX_MANUSCRIPT_REPAIR_ROUNDS = 2
PRESENTATION_REPAIR_CLASSES = {
    "layout", "exposition", "figure_presentation", "table_presentation",
    "citation_presentation", "latex_presentation",
}
RECOVERABLE_SECTION_MESSAGES = (
    "lacks its planned formal statement",
    "lacks planned main-text derivation",
    "lacks planned supporting result",
    "manuscript proof section must contain a complete proof environment",
    "proof-bearing sections contain a proof that is too short",
    "manuscript is missing its dedicated full-proof appendix",
    "selected results lack written proof coverage",
    "selected results lack written appendix proofs",
    "every selected result requires its own complete proof environment",
    "selected result lacks its labeled main formal statement",
    "selected result lacks its labeled complete appendix proof",
    "selected result requires exactly one labeled appendix proof",
    "every selected result requires exact two-way main-to-appendix cross-references",
    "appendix proof for",
    "lacks the planned empirical figure",
)

REQUIRED_CORE_SECTIONS = {"abstract", "introduction", "related_work", "conclusion"}
# Optional limitations still cannot substitute for a substantive contribution section.
CORE_SECTIONS = REQUIRED_CORE_SECTIONS | {"limitations"}

CONVENTIONAL_SECTION_TITLES = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related_work": "related work",
    "limitations": "limitations",
    "conclusion": "conclusion",
}
CONVENTIONAL_CONTRIBUTION_TITLES = {
    "analysis", "approach", "discussion", "empirical results", "experiments", "main result",
    "main results", "method", "methods", "our approach", "our method", "proof", "proofs",
    "results", "setting", "theory",
}
INFORMAL_TITLE_WORDS = {
    "buys", "breaks", "ignored", "matters", "recipe", "story", "takeaway", "journey", "puzzle",
}
MANUSCRIPT_META_TERMS = re.compile(
    r"\b(?:story|TheoremAudit|proof obligation|governance|arbiter|method team|attack team|"
    r"submission readiness|novelty audit|significance audit|paper route|claim policy|"
    r"content architecture|development obligations?)\b",
    re.IGNORECASE,
)
FORBIDDEN_SECTION_PAGE_BREAKS = re.compile(
    r"\\(?:clearpage|newpage|pagebreak)(?:\[[^\]]*\])?"
)
RHETORICAL_TITLE_PREFIXES = ("how ", "what ", "when ", "where ", "why ", "who ")
EVASIVE_PROOF_PHRASES = (
    "details are omitted", "details omitted", "left to the reader", "omitted for brevity",
    "proof sketch", "routine calculation", "standard argument", "straightforward calculation",
)


def require_dict(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def require_fields(value: dict, fields: Iterable[str], label: str) -> None:
    missing = [name for name in fields if name not in value]
    if missing:
        raise ValueError(f"{label} is missing required fields: {missing}")


def route_manuscript_kind(route: dict) -> str:
    """Read the unified manuscript kind while preserving old completed runs."""
    kind = route.get("manuscript_kind")
    if kind in {"full_paper", "evidence_report"}:
        return kind
    if route.get("publication_tier") == "research_report" and route.get("paper_type") == "research_report":
        return "evidence_report"
    return "full_paper"


def _positive_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive number")
    return float(value)


def _nonnegative_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a nonnegative number")
    return float(value)


PAGE_LIMIT_SCOPES = {"main_text", "main_plus_references", "total_manuscript", "none"}


def uses_component_page_contract(venue_metadata: dict | None) -> bool:
    """New venue snapshots opt in without invalidating persisted legacy runs."""
    return isinstance(venue_metadata, dict) and "page_limit_scope" in venue_metadata


def validate_length_plan(
    value: dict,
    sections: list,
    *,
    venue_metadata: dict | None = None,
    writing_exemplars: dict | None = None,
) -> None:
    """Validate the page plan used by both first drafts and full rewrites."""
    plan = require_dict(value.get("length_plan"), "length_plan")
    if plan.get("planning_basis") not in {
        "verified_venue_rules", "provisional_venue_target", "matched_exemplars",
    }:
        raise ValueError("length_plan.planning_basis is invalid")
    component_contract = uses_component_page_contract(venue_metadata)
    selected_scope = venue_metadata.get("page_limit_scope") if component_contract else None
    journal_without_limit = (
        selected_scope == "none"
        and venue_metadata.get("publication_format") == "journal"
    )
    neutral_draft = (
        selected_scope == "none"
        and venue_metadata.get("neutral_draft") is True
    )
    minimum_value = plan.get("minimum_total_pages")
    if journal_without_limit or neutral_draft:
        if minimum_value is not None:
            raise ValueError(
                "no-limit journals and neutral evidence reports must not declare "
                "minimum_total_pages"
            )
        minimum = None
    else:
        minimum = _positive_number(minimum_value, "length_plan.minimum_total_pages")
    target = _positive_number(plan.get("target_total_pages"), "length_plan.target_total_pages")
    maximum = _positive_number(plan.get("maximum_total_pages"), "length_plan.maximum_total_pages")
    target_main = _positive_number(plan.get("target_main_pages"), "length_plan.target_main_pages")
    maximum_main = _positive_number(plan.get("maximum_main_pages"), "length_plan.maximum_main_pages")
    reference_pages = _positive_number(plan.get("target_reference_pages"), "length_plan.target_reference_pages")
    if minimum is not None and not minimum <= target <= maximum:
        raise ValueError("length_plan total pages must satisfy minimum <= target <= maximum")
    if minimum is None and target > maximum:
        raise ValueError("length_plan total pages must satisfy target <= maximum")
    if target_main > maximum_main or maximum_main > maximum:
        raise ValueError("length_plan main-page targets are inconsistent with the total-page plan")
    if plan.get("references_before_appendix") is not True:
        raise ValueError("length_plan must place references before the appendix")
    if require_text(plan.get("appendix_heading"), "length_plan.appendix_heading").casefold() != "appendix":
        raise ValueError("length_plan.appendix_heading must be Appendix")
    hard_limit = plan.get("hard_page_limit")
    if hard_limit is not None:
        hard_limit = _positive_number(hard_limit, "length_plan.hard_page_limit")
        if maximum_main > hard_limit:
            raise ValueError("length_plan maximum_main_pages exceeds the venue hard page limit")

    if uses_component_page_contract(venue_metadata):
        page_limit_scope = venue_metadata.get("page_limit_scope")
        if page_limit_scope not in PAGE_LIMIT_SCOPES:
            raise ValueError("selected venue page_limit_scope is invalid")
        if plan.get("page_limit_scope") != page_limit_scope:
            raise ValueError("length_plan.page_limit_scope must match the selected venue snapshot")
        minimum_main_value = plan.get("minimum_main_pages")
        minimum_appendix_value = plan.get("minimum_appendix_pages")
        if neutral_draft:
            if minimum_main_value is not None or minimum_appendix_value is not None:
                raise ValueError(
                    "neutral evidence reports must set minimum_main_pages and "
                    "minimum_appendix_pages to null"
                )
            minimum_main = None
            minimum_appendix = None
        else:
            minimum_main = _positive_number(
                minimum_main_value, "length_plan.minimum_main_pages"
            )
            minimum_appendix = _positive_number(
                minimum_appendix_value, "length_plan.minimum_appendix_pages"
            )
        target_appendix = _positive_number(
            plan.get("target_appendix_pages"), "length_plan.target_appendix_pages"
        )
        if minimum_main is not None and not minimum_main <= target_main <= maximum_main:
            raise ValueError(
                "length_plan main pages must satisfy minimum_main_pages <= "
                "target_main_pages <= maximum_main_pages"
            )
        if minimum_appendix is not None and minimum_appendix > target_appendix:
            raise ValueError(
                "length_plan minimum_appendix_pages cannot exceed target_appendix_pages"
            )
        maximum_references = plan.get("maximum_reference_pages")
        if maximum_references is not None:
            maximum_references = _positive_number(
                maximum_references, "length_plan.maximum_reference_pages"
            )
            if maximum_references < reference_pages:
                raise ValueError(
                    "length_plan.maximum_reference_pages cannot be below target_reference_pages"
                )

        venue_limit = venue_metadata.get("page_limit")
        if page_limit_scope == "none":
            if venue_limit is not None or hard_limit is not None:
                raise ValueError("a no-limit venue cannot declare a hard page limit")
            if neutral_draft and plan.get("planning_basis") != "provisional_venue_target":
                raise ValueError(
                    "neutral evidence reports require an evidence-scoped provisional page target, "
                    "not an exemplar-derived minimum"
                )
            if not neutral_draft and plan.get("planning_basis") != "matched_exemplars":
                raise ValueError(
                    "no-limit venues require length planning from matched full-text exemplars"
                )
            basis = plan.get("exemplar_page_basis", [])
            if plan.get("planning_basis") == "matched_exemplars":
                basis = require_list(basis, "length_plan.exemplar_page_basis")
                if not 3 <= len(basis) <= 6:
                    raise ValueError(
                        "no-limit venue planning requires page profiles for three to six exemplars"
                    )
            elif basis:
                raise ValueError("neutral draft planning cannot declare unused exemplar_page_basis")
            expected_ids = {
                str(item.get("record_id", "")).strip()
                for item in (writing_exemplars or {}).get("exemplars", [])
                if isinstance(item, dict) and str(item.get("record_id", "")).strip()
            }
            recorded_profiles = {
                str(item.get("record_id", "")).strip(): item.get("page_profile")
                for item in (writing_exemplars or {}).get("exemplars", [])
                if isinstance(item, dict) and isinstance(item.get("page_profile"), dict)
            }
            seen_ids = set()
            observed_main_pages = []
            for index, profile in enumerate(basis):
                profile = require_dict(profile, f"exemplar_page_basis[{index}]")
                record_id = require_text(
                    profile.get("record_id"), f"exemplar_page_basis[{index}].record_id"
                )
                if record_id in seen_ids:
                    raise ValueError("exemplar_page_basis contains a duplicate record")
                seen_ids.add(record_id)
                page_parts = [
                    _positive_number(profile.get(field), f"{record_id}.{field}")
                    for field in ("main_pages", "reference_pages", "appendix_pages", "total_pages")
                ]
                if abs(sum(page_parts[:3]) - page_parts[3]) > 0.51:
                    raise ValueError(
                        f"{record_id} exemplar page components do not match total_pages"
                    )
                require_text(profile.get("source_locator"), f"{record_id}.source_locator")
                recorded = recorded_profiles.get(record_id)
                if recorded is not None and any(
                    profile.get(field) != recorded.get(field)
                    for field in (
                        "main_pages", "reference_pages", "appendix_pages",
                        "total_pages", "source_locator",
                    )
                ):
                    raise ValueError(
                        f"{record_id} exemplar_page_basis does not match the inspected exemplar profile"
                    )
                observed_main_pages.append(page_parts[0])
            if expected_ids and seen_ids != expected_ids:
                raise ValueError(
                    "exemplar_page_basis must cover every matched writing exemplar exactly once"
                )
            if observed_main_pages:
                observed_maximum = max(observed_main_pages)
                expected_target = max(10.0, observed_maximum) if journal_without_limit else observed_maximum
                if abs(target_main - expected_target) > 0.01:
                    raise ValueError(
                        "no-limit venue target_main_pages must equal the journal floor or the "
                        "largest observed main-text length, whichever is greater"
                    )
            if journal_without_limit and abs(minimum_main - 10.0) > 0.01:
                raise ValueError(
                    "no-limit journal minimum_main_pages must equal 10, excluding references and appendices"
                )
            if not journal_without_limit and not neutral_draft and minimum_main < max(1.0, target_main - 1.0):
                raise ValueError(
                    "no-limit venue minimum_main_pages must stay within one page of the "
                    "exemplar-derived target"
                )
            if maximum_main > target_main + 2.0:
                raise ValueError(
                    "no-limit venue maximum_main_pages may exceed the exemplar-derived target "
                    "by at most two layout pages"
                )
        else:
            if venue_limit is None:
                raise ValueError("a scoped venue page limit requires page_limit metadata")
            venue_limit = _positive_number(venue_limit, "selected venue page_limit")
            if hard_limit != venue_limit:
                raise ValueError("length_plan hard_page_limit must match the selected venue limit")
            if page_limit_scope == "main_text":
                if target_main != venue_limit or maximum_main != venue_limit:
                    raise ValueError(
                        "hard-limit venues must target and cap the main text at the full venue allowance"
                    )
                if minimum_main < max(1.0, venue_limit - 1.0):
                    raise ValueError(
                        "hard-limit venue minimum_main_pages must be within one page of the allowance"
                    )
    allocations = require_list(plan.get("section_page_targets"), "length_plan.section_page_targets")
    expected = {str(section.get("name", "")).lower() for section in sections}
    seen = set()
    allocated_main = 0.0
    allocated_appendix = 0.0
    for index, allocation in enumerate(allocations):
        allocation = require_dict(allocation, f"length_plan.section_page_targets[{index}]")
        name = require_text(allocation.get("section"), f"section_page_targets[{index}].section").lower()
        if name not in expected or name in seen:
            raise ValueError("length_plan section targets contain an unknown or duplicate section")
        seen.add(name)
        pages = _positive_number(allocation.get("target_pages"), f"{name}.target_pages")
        planned = next(item for item in sections if str(item.get("name", "")).lower() == name)
        if planned.get("location", "main") == "appendix":
            allocated_appendix += pages
        else:
            allocated_main += pages
    if seen != expected:
        raise ValueError("length_plan must allocate pages to every planned section")
    if abs(allocated_main - target_main) > 0.51:
        raise ValueError("length_plan main section allocations do not match target_main_pages")
    if abs(allocated_main + allocated_appendix + reference_pages - target) > 0.51:
        raise ValueError("length_plan section and reference allocations do not match target_total_pages")
    if uses_component_page_contract(venue_metadata):
        if abs(allocated_appendix - float(plan["target_appendix_pages"])) > 0.51:
            raise ValueError(
                "length_plan appendix allocations do not match target_appendix_pages"
            )


def validate_section_title(section: dict, *, schema_version: int) -> None:
    """Reject unclear or unprofessional headings without prescribing a title style."""
    if schema_version != 3:
        return
    name = str(section.get("name", "")).strip().casefold()
    title = require_text(section.get("title"), f"section {name}.title").strip()
    normalized = " ".join(title.casefold().split())
    if name in CONVENTIONAL_SECTION_TITLES:
        if name == "conclusion" and normalized == "conclusion and limitations":
            return
        if normalized != CONVENTIONAL_SECTION_TITLES[name]:
            raise ValueError(
                f"universal section {name} must use the conventional scholarly title "
                f"{CONVENTIONAL_SECTION_TITLES[name].title()}"
            )
        return
    if title.endswith("?") or normalized.startswith(RHETORICAL_TITLE_PREFIXES):
        raise ValueError(f"section {name} title must be a scholarly noun phrase, not a rhetorical question")
    words = re.findall(r"[A-Za-z][A-Za-z0-9+-]*", title)
    if INFORMAL_TITLE_WORDS & {word.casefold() for word in words}:
        raise ValueError(f"section {name} title uses informal or promotional wording")
    if normalized in CONVENTIONAL_CONTRIBUTION_TITLES:
        return
    if len(words) < 2:
        raise ValueError(
            f"section {name} title is unclear; use a conventional heading or name the scientific topic"
        )


def validate_detailed_appendix_proof(body: str, *, claim_id: str) -> None:
    """Enforce substantive detail for each selected claim's schema-v3 appendix proof."""
    normalized = " ".join(body.casefold().split())
    evasive = [phrase for phrase in EVASIVE_PROOF_PHRASES if phrase in normalized]
    if evasive:
        raise ValueError(
            f"appendix proof for {claim_id} uses an omission or sketch phrase: {evasive[0]}"
        )
    meaningful = re.sub(r"%.*?$|\\[A-Za-z@]+\*?|[^A-Za-z0-9]+", "", body, flags=re.MULTILINE)
    if len(meaningful) < 1200:
        raise ValueError(
            f"appendix proof for {claim_id} is too compressed; include the full detailed derivation"
        )
    display_units = len(re.findall(
        r"\\\[|\\begin\{(?:align\*?|equation\*?|gather\*?|multline\*?)\}", body
    ))
    paragraph_units = len(re.findall(r"\n\s*\n|\\paragraph\{|\\subsubsection\{", body))
    reference_units = len(re.findall(r"\\(?:eqref|ref|autoref|cref|Cref)\{", body))
    if display_units + paragraph_units + reference_units < 5:
        raise ValueError(
            f"appendix proof for {claim_id} lacks enough explicit intermediate structure"
        )
    if not re.search(r"\b(?:therefore|thus|hence|consequently|as claimed|this proves)\b", normalized):
        raise ValueError(f"appendix proof for {claim_id} lacks an explicit concluding inference")


def safe_paper_path(run_dir: Path, relative: str) -> Path:
    candidate = (run_dir / "paper" / relative).resolve()
    root = (run_dir / "paper").resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("paper artifact escapes the paper directory") from exc
    return candidate


def paper_manifest_path(run_dir: Path) -> Path:
    return run_dir / "paper" / "paper_run.json"


def manuscript_authorization_path(run_dir: Path) -> Path:
    return run_dir / "paper" / "manuscript_authorization.json"


def load_paper_manifest(run_dir: Path) -> dict:
    return require_dict(read_json(paper_manifest_path(run_dir)), "paper manifest")


def save_paper_manifest(run_dir: Path, manifest: dict) -> None:
    path = paper_manifest_path(run_dir)
    expected = manifest.get("state_revision", 0)

    def replace(current: Any) -> dict:
        current_revision = current.get("state_revision", 0) if isinstance(current, dict) else 0
        if current and current_revision != expected:
            raise ValueError("paper manifest changed concurrently; reload before updating it")
        updated = dict(manifest)
        updated["state_revision"] = current_revision + 1
        return updated

    updated = update_json(path, replace, {})
    manifest.clear()
    manifest.update(updated)


def user_comments_path(run_dir: Path) -> Path:
    return run_dir / "paper" / "user_comments.json"


def load_user_comments(run_dir: Path) -> dict:
    path = user_comments_path(run_dir)
    if not path.is_file():
        return {"schema_version": 1, "artifact": "user_comment_registry", "comments": []}
    value = require_dict(read_json(path), "user comment registry")
    require_list(value.get("comments"), "user comments")
    return value


def unresolved_user_comments(run_dir: Path) -> list:
    return [
        item for item in load_user_comments(run_dir)["comments"]
        if item.get("status", "open") in {"open", "reopened"}
    ]


def _archive_stage(run_dir: Path, manifest: dict, stage_name: str) -> None:
    stage = manifest["stages"][stage_name]
    snapshot = {
        key: value for key, value in stage.items()
        if key not in {"history", "status", "completed_at", "completed_by", "evidence_sha256"}
    }
    if stage.get("status") == "completed":
        source = safe_paper_path(run_dir, stage["artifact"])
        archive_relative = f"history/cycle-{manifest.get('review_cycle', 1)}/{stage_name}-{source.name}"
        archive = safe_paper_path(run_dir, archive_relative)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, archive)
        snapshot.update({
            "status": "completed",
            "completed_at": stage.get("completed_at"),
            "completed_by": stage.get("completed_by"),
            "evidence_sha256": stage.get("evidence_sha256"),
            "cycle": manifest.get("review_cycle", 1),
            "archived_artifact": archive_relative,
            "archived_sha256": file_sha256(archive),
        })
        stage.setdefault("history", []).append(snapshot)
    for key in ("completed_at", "completed_by", "evidence_sha256"):
        stage.pop(key, None)
    stage["status"] = "pending"


def manuscript_repair_state(manifest: dict) -> dict:
    state = manifest.setdefault("manuscript_repair", {
        "maximum_rounds": MAX_MANUSCRIPT_REPAIR_ROUNDS,
        "rounds_used": 0,
        "status": "available",
        "history": [],
    })
    state.setdefault("maximum_rounds", MAX_MANUSCRIPT_REPAIR_ROUNDS)
    state.setdefault("rounds_used", 0)
    state.setdefault("status", "available")
    state.setdefault("history", [])
    return state


def manuscript_repair_budget_exhausted(manifest: dict) -> bool:
    state = manuscript_repair_state(manifest)
    return int(state["rounds_used"]) >= int(state["maximum_rounds"])


def recoverable_section_validation(error: Exception) -> bool:
    message = str(error).casefold()
    return any(fragment.casefold() in message for fragment in RECOVERABLE_SECTION_MESSAGES)


def compile_repair_findings(report: dict) -> list:
    """Normalize repairable compile/layout defects without hiding hard claim validation."""
    findings = []
    if report.get("pdf_built") is not True:
        findings.append({
            "id": "COMPILE-PDF", "repair_class": "latex_presentation",
            "description": "The current manuscript did not produce a clean PDF.",
        })
    for index, warning in enumerate(report.get("warnings", []), start=1):
        findings.append({
            "id": f"COMPILE-W{index}", "repair_class": "latex_presentation",
            "description": str(warning),
        })
    for index, finding in enumerate(report.get("source_lint_findings", []), start=1):
        if isinstance(finding, dict) and finding.get("severity") == "error":
            findings.append({
                "id": f"COMPILE-L{index}", "repair_class": "latex_presentation",
                "description": str(finding.get("message") or finding.get("code") or "LaTeX source error"),
            })
    for index, finding in enumerate(report.get("page_budget_findings", []), start=1):
        if isinstance(finding, dict):
            findings.append({
                "id": f"COMPILE-P{index}", "repair_class": "layout",
                "description": (
                    f"{finding.get('component', 'manuscript')} page budget: "
                    f"{finding.get('code', 'outside planned range')}"
                ),
                "evidence": finding,
            })
    if report.get("page_budget_status") not in {None, "within_budget"} and not any(
        item["repair_class"] == "layout" for item in findings
    ):
        findings.append({
            "id": "COMPILE-PAGE", "repair_class": "layout",
            "description": "The rendered manuscript is outside its component page plan.",
        })
    return findings


def automatic_manuscript_repair_enabled(run_dir: Path) -> bool:
    architecture_path = run_dir / "paper" / "content_architecture.json"
    if not architecture_path.is_file():
        return False
    architecture = read_json(architecture_path)
    return (
        architecture.get("schema_version") == 3
        and architecture.get("length_plan", {}).get("page_limit_scope") in PAGE_LIMIT_SCOPES
    )


def _repair_quality_penalty(report: dict) -> float:
    penalty = 0.0 if report.get("pdf_built") is True else 10000.0
    penalty += 100.0 * len(report.get("warnings", []))
    penalty += 100.0 * sum(
        1 for item in report.get("source_lint_findings", [])
        if isinstance(item, dict) and item.get("severity") == "error"
    )
    for finding in report.get("page_budget_findings", []):
        if not isinstance(finding, dict):
            continue
        actual = finding.get("actual")
        required = finding.get("required")
        if isinstance(actual, (int, float)) and isinstance(required, (int, float)):
            penalty += abs(float(actual) - float(required))
        else:
            penalty += 10.0
    return penalty


def archive_manuscript_attempt(run_dir: Path, manifest: dict, report: dict, findings: list) -> dict:
    state = manuscript_repair_state(manifest)
    attempt = len(state["history"]) + 1
    relative = f"history/manuscript-repair/attempt-{attempt:02d}"
    archive = safe_paper_path(run_dir, relative)
    archive.mkdir(parents=True, exist_ok=True)
    paper_root = run_dir / "paper"
    files = []
    # Keep the assembled source and its generated bibliography/assembly metadata
    # together.  Restoring only paper.tex and paper.pdf could leave a later
    # attempt's references.bib behind, making the preserved package internally
    # inconsistent even though the PDF itself is the selected best attempt.
    for name in (
        "compile_report.json",
        "assembly_report.json",
        "paper.tex",
        "paper.pdf",
        "references.bib",
    ):
        source = paper_root / name
        if source.is_file():
            destination = archive / name
            shutil.copy2(source, destination)
            files.append({
                "path": str(destination.relative_to(paper_root)),
                "sha256": file_sha256(destination),
            })
    sections_archive = archive / "sections"
    sections_archive.mkdir(parents=True, exist_ok=True)
    section_root = paper_root / "sections"
    if section_root.is_dir():
        for source in section_root.iterdir():
            if source.is_file() and not source.name.startswith("."):
                destination = sections_archive / source.name
                shutil.copy2(source, destination)
                files.append({
                    "path": str(destination.relative_to(paper_root)),
                    "sha256": file_sha256(destination),
                })
    record = {
        "attempt": attempt,
        "repair_round": state["rounds_used"],
        "recorded_at": utc_now(),
        "archive": relative,
        "quality_penalty": _repair_quality_penalty(report),
        "pdf_built": report.get("pdf_built") is True,
        "pdf_sha256": report.get("pdf_sha256"),
        "findings": findings,
        "files": files,
    }
    state["history"].append(record)
    return record


def restore_best_manuscript_attempt(run_dir: Path, manifest: dict) -> dict:
    state = manuscript_repair_state(manifest)
    candidates = [item for item in state["history"] if isinstance(item, dict)]
    if not candidates:
        raise ValueError("cannot restore a manuscript repair attempt because no attempt was archived")
    best = min(
        candidates,
        key=lambda item: (
            0 if item.get("pdf_built") else 1,
            float(item.get("quality_penalty", 1e12)),
            -int(item.get("attempt", 0)),
        ),
    )
    paper_root = run_dir / "paper"
    archive = safe_paper_path(run_dir, best["archive"])
    for name in (
        "compile_report.json",
        "assembly_report.json",
        "paper.tex",
        "paper.pdf",
        "references.bib",
    ):
        source = archive / name
        if source.is_file():
            shutil.copy2(source, paper_root / name)
    archived_sections = archive / "sections"
    if archived_sections.is_dir():
        target = paper_root / "sections"
        target.mkdir(parents=True, exist_ok=True)
        for source in archived_sections.iterdir():
            if source.is_file():
                shutil.copy2(source, target / source.name)
    state["best_attempt"] = best["attempt"]
    state["best_attempt_archive"] = best["archive"]
    return best


def reopen_for_manuscript_repair(run_dir: Path, manifest: dict, findings: list) -> None:
    state = manuscript_repair_state(manifest)
    state["rounds_used"] = int(state["rounds_used"]) + 1
    state["status"] = "in_progress"
    state["last_findings"] = findings
    for stage_name in ("section_writing", "compilation", "independent_review", "revision", "final_package"):
        stage = manifest["stages"][stage_name]
        for key in ("completed_at", "completed_by", "evidence_sha256"):
            stage.pop(key, None)
        stage["status"] = "pending"
    manifest["status"] = "active"
    manifest["current_stage"] = "section_writing"
    manifest["stages"]["section_writing"]["status"] = "in_progress"
    manifest.setdefault("events", []).append({
        "event": "automatic_manuscript_repair_started",
        "round": state["rounds_used"],
        "maximum_rounds": state["maximum_rounds"],
        "findings": findings,
        "recorded_at": utc_now(),
    })


def review_findings_are_packagable(findings: list) -> bool:
    return bool(findings) and all(
        isinstance(item, dict)
        and item.get("severity") != "fatal"
        and item.get("repair_class") in PRESENTATION_REPAIR_CLASSES
        for item in findings
    )


def _reset_sections_for_full_rewrite(run_dir: Path, manifest: dict) -> str | None:
    """Archive registered section sources, then clear only the active generated section set."""
    index_path = run_dir / "paper" / "sections" / "index.json"
    if not index_path.is_file():
        return None
    index = require_dict(read_json(index_path), "section index")
    archive_relative = f"history/cycle-{manifest.get('review_cycle', 1)}/rewrite-sections"
    archive_root = safe_paper_path(run_dir, archive_relative)
    archive_root.mkdir(parents=True, exist_ok=True)
    for record in require_list(index.get("sections"), "sections"):
        if not isinstance(record, dict) or not record.get("path"):
            continue
        source = safe_paper_path(run_dir, record["path"])
        if source.is_file():
            shutil.copy2(source, archive_root / source.name)
            source.unlink()
    write_json(index_path, {
        "schema_version": 2,
        "artifact": "manuscript_section_registry",
        "revision": 0,
        "sections": [],
        "history": [],
    })
    return archive_relative


def open_revision_cycle(run_dir: Path, manifest: dict, reason: str) -> None:
    """Preserve accepted evidence and open editable manuscript state."""
    for stage_name in ("section_writing", "compilation", "independent_review", "revision", "final_package"):
        _archive_stage(run_dir, manifest, stage_name)
    manifest["status"] = "active"
    manifest["current_stage"] = "revision"
    manifest["stages"]["revision"]["status"] = "in_progress"
    manifest.setdefault("events", []).append({
        "event": "revision_requested", "reason": reason,
        "cycle": manifest.get("review_cycle", 1), "recorded_at": utc_now(),
    })


def open_paper_revision(
    run_dir: Path,
    manifest: dict,
    *,
    start_stage: str,
    reason: str,
    plan_id: str,
    revision_action: str = "revise_manuscript",
) -> None:
    """Archive and reopen a same-run paper from an explicitly routed stage."""
    names = list(STAGES)
    if start_stage not in STAGES:
        raise ValueError(f"unknown paper revision stage: {start_stage}")
    if revision_action == "rewrite_manuscript":
        architecture_path = run_dir / "paper" / "content_architecture.json"
        section_index_path = run_dir / "paper" / "sections" / "index.json"
        baseline_sections = {}
        if section_index_path.is_file():
            section_index = require_dict(read_json(section_index_path), "section index")
            for record in require_list(section_index.get("sections"), "sections"):
                if isinstance(record, dict) and record.get("name") and record.get("content_sha256"):
                    baseline_sections[str(record["name"]).lower()] = record["content_sha256"]
        manifest["manuscript_rewrite"] = {
            "status": "in_progress",
            "plan_id": plan_id,
            "baseline_content_architecture_sha256": (
                file_sha256(architecture_path) if architecture_path.is_file() else None
            ),
            "baseline_section_hashes": baseline_sections,
            "required_fresh_sections": sorted(baseline_sections),
            "started_at": utc_now(),
        }
    start = names.index(start_stage)
    for stage_name in names[start:]:
        _archive_stage(run_dir, manifest, stage_name)
    if revision_action == "rewrite_manuscript":
        manifest["manuscript_rewrite"]["archived_sections"] = _reset_sections_for_full_rewrite(
            run_dir, manifest
        )
    manifest["status"] = "active"
    manifest["review_cycle"] = manifest.get("review_cycle", 1) + 1
    manifest["current_stage"] = start_stage
    manifest["stages"][start_stage]["status"] = "in_progress"
    manifest.setdefault("events", []).append({
        "event": "paper_revision_started",
        "reason": reason,
        "plan_id": plan_id,
        "action": revision_action,
        "resume_stage": start_stage,
        "cycle": manifest["review_cycle"],
        "recorded_at": utc_now(),
    })


def start_paper_revision(
    run_dir: Path,
    *,
    start_stage: str,
    reason: str,
    plan_id: str,
    revision_action: str = "revise_manuscript",
) -> dict:
    """Validate the immutable theory handoff and persist a paper revision transition."""
    verify_theory_handoff(run_dir)
    if not paper_manifest_path(run_dir).is_file():
        raise ValueError("paper workflow has not been initialized")
    manifest = load_paper_manifest(run_dir)
    open_paper_revision(
        run_dir,
        manifest,
        start_stage=start_stage,
        reason=require_text(reason, "paper revision reason"),
        plan_id=require_text(plan_id, "paper revision plan ID"),
        revision_action=require_text(revision_action, "paper revision action"),
    )
    save_paper_manifest(run_dir, manifest)
    return manifest


def open_venue_revision(run_dir: Path, manifest: dict, reason: str) -> None:
    """Reopen formatting and every downstream paper gate after a template change."""
    names = list(STAGES)
    start = names.index("venue_selection")
    for stage_name in names[start:]:
        _archive_stage(run_dir, manifest, stage_name)
    manifest["status"] = "active"
    manifest["review_cycle"] = manifest.get("review_cycle", 1) + 1
    manifest["current_stage"] = "venue_selection"
    manifest["stages"]["venue_selection"]["status"] = "in_progress"
    manifest.setdefault("events", []).append({
        "event": "venue_revision_requested", "reason": reason,
        "cycle": manifest.get("review_cycle", 1), "recorded_at": utc_now(),
    })


def reopen_for_user_feedback(run_dir: Path, comment_id: str) -> None:
    """Reopen a reviewed/final paper when new user feedback arrives."""
    path = paper_manifest_path(run_dir)
    if not path.is_file():
        return
    manifest = load_paper_manifest(run_dir)
    reviewed = manifest.get("status") == "completed" or manifest.get("current_stage") in {
        "final_package", "independent_review", "revision"
    }
    if reviewed and manifest.get("current_stage") != "revision":
        open_revision_cycle(run_dir, manifest, f"user comment {comment_id}")
        save_paper_manifest(run_dir, manifest)


def verify_theory_handoff(run_dir: Path) -> dict:
    manifest = load_manifest(run_dir)
    stage = manifest.get("stages", {}).get("theory_bundle", {})
    if manifest.get("status") != "completed" or stage.get("status") != "completed":
        raise ValueError("the governed theory workflow must be completed first")
    bundle_path = run_dir / stage["artifact"]
    if file_sha256(bundle_path) != stage.get("evidence_sha256"):
        raise ValueError("the completed theory bundle was modified")
    bundle = require_dict(read_json(bundle_path), "theory bundle")
    if not bundle.get("writing_eligible"):
        raise ValueError("the contribution gate does not permit manuscript writing")
    route = require_dict(bundle.get("paper_route"), "paper_route")
    if not route.get("writing_allowed"):
        raise ValueError("paper route does not permit writing")
    accepted = bundle.get("accepted_statements")
    if not isinstance(accepted, list):
        raise ValueError("theory bundle accepted_statements must be a list")
    if not accepted:
        if route_manuscript_kind(route) != "evidence_report":
            raise ValueError("a theory bundle without accepted statements must use the evidence-report route")
        if route.get("selected_statement_ids"):
            raise ValueError("an evidence report cannot select established statements")
    return bundle


def verify_paper_evidence(run_dir: Path, manifest: dict) -> None:
    authorization_path = manuscript_authorization_path(run_dir)
    if not authorization_path.is_file():
        raise ValueError("governed manuscript authorization is missing")
    authorization = require_dict(read_json(authorization_path), "manuscript authorization")
    if authorization.get("artifact") != "manuscript_authorization":
        raise ValueError("invalid governed manuscript authorization")
    if authorization.get("run_id") != run_dir.name:
        raise ValueError("manuscript authorization targets a different run")
    expected_authorization_hash = manifest.get("manuscript_authorization_sha256")
    if not expected_authorization_hash or file_sha256(authorization_path) != expected_authorization_hash:
        raise ValueError("manuscript authorization was modified or is not bound to the paper run")
    bundle_path = run_dir / "artifacts" / "theory_bundle.json"
    if authorization.get("theory_bundle_sha256") != file_sha256(bundle_path):
        raise ValueError("manuscript authorization does not match the current theory bundle")
    if authorization.get("authorized_output_root") != "paper":
        raise ValueError("manuscript authorization has an invalid output root")
    for stage_name, stage in manifest["stages"].items():
        if stage["status"] != "completed":
            continue
        path = safe_paper_path(run_dir, stage["artifact"])
        # Compilation may expose recoverable layout or length findings after the
        # section-writing gate has completed.  Those repairs still go through
        # manuscript_tools.py, whose section index binds every current section
        # hash and is revalidated by validate_compile.  Permit that governed
        # index to advance while compilation is active; command_complete then
        # atomically refreshes the completed-stage evidence hash.
        if stage_name in {"section_writing", "revision"} and manifest.get("current_stage") == "compilation":
            if not path.is_file():
                raise ValueError(f"completed paper artifact for {stage_name} is missing")
            continue
        if not path.is_file() or file_sha256(path) != stage.get("evidence_sha256"):
            raise ValueError(f"completed paper artifact for {stage_name} was modified")


def current_artifact(run_dir: Path, manifest: dict) -> dict:
    stage = manifest["stages"][manifest["current_stage"]]
    return require_dict(read_json(safe_paper_path(run_dir, stage["artifact"])), stage["artifact"])


def validate_literature(run_dir: Path, value: dict) -> None:
    from literature.registry import load_registry, resolve_record_id

    require_text(value.get("scope"), "scope")
    refs = require_list(value.get("references"), "references")
    seen = set()
    for index, ref in enumerate(refs):
        ref = require_dict(ref, f"references[{index}]")
        try:
            validate_record(ref)
        except ValueError as exc:
            raise ValueError(f"references[{index}] is not a valid literature_record.v1: {exc}") from exc
        ref_id = require_text(ref["record_id"], f"references[{index}].record_id")
        if ref_id in seen:
            raise ValueError(f"duplicate reference ID: {ref_id}")
        seen.add(ref_id)
    registry = None
    registry_path = run_dir / "literature" / "registry.json"
    if registry_path.is_file():
        registry = load_registry(run_dir)
        registered = {item["record_id"]: item for item in registry["records"]}
        active_usage = {
            item.get("record_id")
            for item in registry.get("usage", [])
            if isinstance(item, dict) and item.get("status", "active") == "active"
            and isinstance(item.get("purpose"), str) and item.get("purpose")
        }
        for ref in refs:
            ref_id = ref["record_id"]
            canonical_id = resolve_record_id(registry, ref_id)
            if canonical_id != ref_id:
                raise ValueError(f"literature audit must use canonical record ID {canonical_id}, not alias {ref_id}")
            if registered[canonical_id] != ref:
                raise ValueError(f"literature audit record differs from canonical registry metadata: {ref_id}")
            metadata = ref.get("metadata", {})
            role = metadata.get("role") or metadata.get("legacy_role")
            if not role and canonical_id not in active_usage:
                raise ValueError(
                    f"{ref_id} requires metadata.role, legacy_role, or an active governed usage"
                )
    require_list(value.get("novelty_findings"), "novelty_findings")
    require_list(value.get("citation_risks"), "citation_risks")
    if value.get("schema_version") == 2:
        coverage = require_dict(value.get("coverage_assessment"), "coverage_assessment")
        maturity = coverage.get("area_maturity")
        if maturity not in {"mature", "narrow", "emerging"}:
            raise ValueError("coverage_assessment.area_maturity must be mature, narrow, or emerging")
        publication_goal = (
            load_manifest(run_dir).get("execution_contract", {}).get("publication_goal", "no_preference")
        )
        original_conference_goal = publication_goal == "original_research"
        minimum = 20 if maturity == "mature" or original_conference_goal else 15
        target = coverage.get("target_reference_count")
        if not isinstance(target, int) or isinstance(target, bool) or target < minimum:
            raise ValueError(f"{maturity} literature requires a target of at least {minimum} references")
        themes = require_list(coverage.get("search_themes"), "coverage_assessment.search_themes")
        if len(themes) < 3 or any(not isinstance(item, str) or not item.strip() for item in themes):
            raise ValueError("literature coverage requires at least three non-empty search themes")
        closest = require_list(
            coverage.get("closest_work_record_ids"),
            "coverage_assessment.closest_work_record_ids",
        )
        if len(closest) < 3 or len(closest) != len(set(closest)) or any(item not in seen for item in closest):
            raise ValueError("literature coverage requires at least three distinct closest-work records")
        actual = len(refs)
        if coverage.get("reference_count") != actual:
            raise ValueError("coverage_assessment.reference_count must equal the audited reference count")
        status = coverage.get("status")
        if actual < target:
            raise ValueError(
                f"literature audit contains {actual} relevant references; this paper requires "
                f"at least {target}. Continue searching, triaging, and verifying sources instead "
                "of downgrading the paper or claiming search saturation"
            )
        if status != "adequate":
            raise ValueError("literature coverage at or above target must be marked adequate")

        maturity_basis = require_text(
            coverage.get("area_maturity_rationale"),
            "coverage_assessment.area_maturity_rationale",
        )
        if "surviving theorem" in maturity_basis.casefold() or "accepted theorem is narrow" in maturity_basis.casefold():
            raise ValueError(
                "area maturity must describe the surrounding research literature, not the breadth "
                "of the surviving theorem or the routed document"
            )

        if registry is None:
            raise ValueError("literature coverage requires a canonical search registry")
        query_by_id = {item.get("query_id"): item for item in registry.get("queries", [])}
        protocol = require_dict(coverage.get("search_protocol"), "coverage_assessment.search_protocol")
        structured_ids = require_list(
            protocol.get("structured_query_ids"),
            "coverage_assessment.search_protocol.structured_query_ids",
        )
        if len(set(structured_ids)) < 3 or any(query_id not in query_by_id for query_id in structured_ids):
            raise ValueError("literature coverage requires at least three recorded structured queries")
        structured_queries = [query_by_id[query_id] for query_id in set(structured_ids)]
        if len({item.get("source") for item in structured_queries}) < 2:
            raise ValueError("literature coverage requires structured searches across at least two sources")
        if len([item for item in structured_queries if item.get("status") == "completed"]) < 2:
            raise ValueError("literature coverage requires at least two completed structured searches")
        web_queries = require_list(
            protocol.get("independent_web_queries"),
            "coverage_assessment.search_protocol.independent_web_queries",
        )
        declared_web_queries = {str(item).strip() for item in web_queries if str(item).strip()}
        if len(declared_web_queries) < 2:
            raise ValueError("literature coverage requires at least two independent web-search queries")
        recorded_web_queries = {
            str(event.get("query") or "").strip()
            for record in refs
            for event in record.get("retrieval", [])
            if event.get("adapter") == "web_search" and str(event.get("query") or "").strip()
        }
        if not declared_web_queries <= recorded_web_queries:
            raise ValueError("independent web queries must be preserved in audited reference retrieval events")
        require_text(protocol.get("triage_summary"), "coverage_assessment.search_protocol.triage_summary")

        registered = {item["record_id"]: item for item in registry["records"]}
        for record_id in closest:
            if registered[record_id].get("verification", {}).get("status") != "primary_source_verified":
                raise ValueError(
                    f"closest-work record {record_id} requires primary-source theorem verification"
                )
        comparisons = require_list(value.get("closest_work_comparisons"), "closest_work_comparisons")
        compared = set()
        for index, comparison in enumerate(comparisons):
            comparison = require_dict(comparison, f"closest_work_comparisons[{index}]")
            record_id = require_text(comparison.get("record_id"), f"closest_work_comparisons[{index}].record_id")
            if record_id not in closest or record_id in compared:
                raise ValueError("closest-work comparisons must map each closest record exactly once")
            compared.add(record_id)
            for field in ("prior_result", "prior_assumptions", "our_difference", "remaining_overlap"):
                require_text(comparison.get(field), f"closest_work_comparisons[{index}].{field}")
        if compared != set(closest):
            raise ValueError("every closest-work record requires a technical comparison")


def validate_exemplar_study(run_dir: Path, value: dict) -> None:
    from literature.registry import load_registry, resolve_record_id

    bundle = verify_theory_handoff(run_dir)
    schema_version = value.get("schema_version", 1)
    if schema_version not in {1, 2}:
        raise ValueError("writing exemplar schema_version must be 1 or 2")
    status = value.get("status")
    if status not in {"completed", "limited", "not_applicable"}:
        raise ValueError("writing exemplar status must be completed, limited, or not_applicable")
    require_text(value.get("purpose"), "writing exemplar purpose")
    require_text(value.get("selection_policy"), "writing exemplar selection_policy")
    exemplars = require_list(value.get("exemplars"), "writing exemplars")
    submission_candidate = bundle["paper_route"].get("submission_framing_allowed") is True
    if submission_candidate and (status != "completed" or not 3 <= len(exemplars) <= 6):
        raise ValueError("submission-framed papers require three to six completed writing exemplars")
    if status == "completed" and not 3 <= len(exemplars) <= 6:
        raise ValueError("a completed writing exemplar study requires three to six papers")
    if status == "limited" and not 1 <= len(exemplars) <= 2:
        raise ValueError("a limited writing exemplar study requires one or two papers")
    if status == "not_applicable":
        if exemplars:
            raise ValueError("not_applicable writing exemplar study cannot contain exemplars")
        require_text(value.get("limitation"), "writing exemplar limitation")

    literature = require_dict(read_json(run_dir / "paper" / "literature_audit.json"), "literature audit")
    literature_ids = {item["record_id"] for item in literature.get("references", [])}
    registry = load_registry(run_dir)
    registered = {item["record_id"]: item for item in registry["records"]}
    seen = set()
    required_sections = {"abstract", "introduction", "related_work", "result_exposition"}
    for index, exemplar in enumerate(exemplars):
        exemplar = require_dict(exemplar, f"exemplars[{index}]")
        record_id = resolve_record_id(
            registry, require_text(exemplar.get("record_id"), f"exemplars[{index}].record_id")
        )
        if record_id in seen or record_id not in literature_ids:
            raise ValueError("writing exemplars must be distinct audited literature records")
        seen.add(record_id)
        verification = registered[record_id].get("verification", {}).get("status")
        if verification not in {"fulltext_extracted", "primary_source_verified"}:
            raise ValueError("writing exemplars require inspected full text")
        require_text(exemplar.get("selection_reason"), f"exemplars[{index}].selection_reason")
        sections = set(require_list(exemplar.get("sections_analyzed"), f"exemplars[{index}].sections_analyzed"))
        if not required_sections <= sections:
            raise ValueError("each exemplar must analyze abstract, introduction, related work, and result exposition")
        observations = require_list(exemplar.get("structural_observations"), f"exemplars[{index}].structural_observations")
        if len(observations) < 3 or any(not isinstance(item, str) or not item.strip() for item in observations):
            raise ValueError("each exemplar requires at least three structural observations")
        if schema_version == 2:
            profile = require_dict(
                exemplar.get("page_profile"), f"exemplars[{index}].page_profile"
            )
            parts = [
                _nonnegative_number(profile.get(field), f"exemplars[{index}].page_profile.{field}")
                for field in ("main_pages", "reference_pages", "appendix_pages")
            ]
            parts.append(
                _positive_number(
                    profile.get("total_pages"),
                    f"exemplars[{index}].page_profile.total_pages",
                )
            )
            if abs(sum(parts[:3]) - parts[3]) > 0.51:
                raise ValueError("writing exemplar page components do not match total_pages")
            require_text(
                profile.get("source_locator"),
                f"exemplars[{index}].page_profile.source_locator",
            )

    if exemplars:
        patterns = require_dict(value.get("cross_paper_patterns"), "cross_paper_patterns")
        for section in required_sections | {"transitions", "visual_presentation"}:
            observations = require_list(patterns.get(section), f"cross_paper_patterns.{section}")
            if not observations or any(not isinstance(item, str) or not item.strip() for item in observations):
                raise ValueError(f"cross_paper_patterns.{section} must contain observations")
        principles = require_list(value.get("adopted_principles"), "adopted_principles")
        if len(principles) < 4:
            raise ValueError("writing exemplar study requires at least four adopted principles")
    safeguards = require_list(value.get("originality_safeguards"), "originality_safeguards")
    if not {"no_sentence_copying", "no_author_style_imitation", "cite_borrowed_technical_ideas"} <= set(safeguards):
        raise ValueError("writing exemplar study lacks originality safeguards")


def validate_main_text_math_plan(
    value: dict,
    *,
    accepted: set[str],
    primary: set[str],
    sections: list,
    proof_map: list,
) -> None:
    """Require auditable mathematical exposition in the main paper for every result."""
    plan = require_list(value.get("main_text_math_plan"), "main_text_math_plan")
    main_sections = {
        str(section.get("name", "")).lower(): section
        for section in sections
        if section.get("location", "main") == "main"
    }
    statement_labels = {
        str(item.get("claim_id")): str(item.get("statement_label"))
        for item in proof_map if isinstance(item, dict)
    }
    seen_claims = set()
    seen_derivation_labels = set()
    seen_supporting_labels = set()
    for index, item in enumerate(plan):
        item = require_dict(item, f"main_text_math_plan[{index}]")
        require_fields(
            item,
            (
                "claim_id", "section", "statement_label", "setup_objects",
                "key_derivations", "supporting_lemmas", "proof_roadmap",
                "technical_interpretation", "appendix_connection",
            ),
            f"main_text_math_plan[{index}]",
        )
        claim_id = require_text(item["claim_id"], f"main_text_math_plan[{index}].claim_id")
        if claim_id not in accepted or claim_id in seen_claims:
            raise ValueError("main_text_math_plan has an unknown or duplicate selected claim")
        seen_claims.add(claim_id)
        section_name = require_text(item["section"], f"{claim_id}.section").lower()
        section = main_sections.get(section_name)
        if section is None or claim_id not in section.get("claims_planned", []):
            raise ValueError(
                f"{claim_id} main-text mathematics must be assigned to a main contribution section"
            )
        statement_label = require_text(item["statement_label"], f"{claim_id}.statement_label")
        if statement_label != statement_labels.get(claim_id):
            raise ValueError(
                f"{claim_id} main-text statement label must match proof_appendix_map"
            )
        setup_objects = require_list(item["setup_objects"], f"{claim_id}.setup_objects")
        if not setup_objects or any(not isinstance(entry, str) or not entry.strip() for entry in setup_objects):
            raise ValueError(f"{claim_id} needs explicit main-text setup objects")
        derivations = require_list(item["key_derivations"], f"{claim_id}.key_derivations")
        required_derivations = 2 if claim_id in primary else 1
        if len(derivations) < required_derivations:
            raise ValueError(
                f"{claim_id} requires at least {required_derivations} labeled main-text derivations"
            )
        for derivation in derivations:
            derivation = require_dict(derivation, f"{claim_id}.key_derivations item")
            label = require_text(derivation.get("label"), f"{claim_id}.derivation label")
            if label in seen_derivation_labels:
                raise ValueError("main-text derivation labels must be globally unique")
            seen_derivation_labels.add(label)
            require_text(derivation.get("role"), f"{claim_id}.derivation role")
            sources = require_list(
                derivation.get("source_support"), f"{claim_id}.derivation source_support"
            )
            if not sources or any(not isinstance(source, str) or not source.strip() for source in sources):
                raise ValueError(f"{claim_id} derivations require proof-source support")
        supporting = require_list(item["supporting_lemmas"], f"{claim_id}.supporting_lemmas")
        for lemma in supporting:
            lemma = require_dict(lemma, f"{claim_id}.supporting_lemmas item")
            label = require_text(lemma.get("label"), f"{claim_id}.supporting lemma label")
            if label in seen_supporting_labels:
                raise ValueError("main-text supporting-result labels must be globally unique")
            seen_supporting_labels.add(label)
            require_text(lemma.get("role"), f"{claim_id}.supporting lemma role")
            sources = require_list(
                lemma.get("source_support"), f"{claim_id}.supporting lemma source_support"
            )
            if not sources or any(not isinstance(source, str) or not source.strip() for source in sources):
                raise ValueError(f"{claim_id} supporting results require proof-source support")
        if not supporting:
            require_text(
                item.get("supporting_lemma_rationale"),
                f"{claim_id}.supporting_lemma_rationale",
            )
        roadmap = require_list(item["proof_roadmap"], f"{claim_id}.proof_roadmap")
        if len(roadmap) < 3:
            raise ValueError(f"{claim_id} needs a main-text proof roadmap with at least three steps")
        for step in roadmap:
            step = require_dict(step, f"{claim_id}.proof_roadmap item")
            require_text(step.get("step"), f"{claim_id}.proof roadmap step")
            require_text(step.get("justification"), f"{claim_id}.proof roadmap justification")
        require_text(item["technical_interpretation"], f"{claim_id}.technical_interpretation")
        require_text(item["appendix_connection"], f"{claim_id}.appendix_connection")
    if seen_claims != accepted:
        missing = sorted(accepted - seen_claims)
        raise ValueError(f"main_text_math_plan is missing selected results: {missing}")


def validate_visual_evidence_plan(
    run_dir: Path,
    value: dict,
    *,
    accepted: set,
    sections: list,
    route: dict,
) -> dict:
    """Validate the claim-linked empirical visual plan."""
    plan = require_dict(value.get("visual_evidence_plan"), "visual_evidence_plan")
    require_fields(
        plan,
        ("empirical_claim_ids", "empirical_section", "empirical_question"),
        "visual_evidence_plan",
    )
    empirical_claim_ids = require_list(
        plan["empirical_claim_ids"], "visual_evidence_plan.empirical_claim_ids"
    )
    if len(empirical_claim_ids) != len(set(empirical_claim_ids)) or any(
        claim not in accepted for claim in empirical_claim_ids
    ):
        raise ValueError("visual_evidence_plan empirical claims must be unique selected results")

    section_map = {str(item["name"]).lower(): item for item in sections}
    empirical_section = plan.get("empirical_section")
    empirical_question = plan.get("empirical_question")
    if empirical_claim_ids:
        empirical_section = require_text(
            empirical_section, "visual_evidence_plan.empirical_section"
        ).lower()
        require_text(empirical_question, "visual_evidence_plan.empirical_question")
        section = section_map.get(empirical_section)
        if section is None or section.get("location") != "main":
            raise ValueError("the empirical visual must be assigned to a planned main-text section")
        evidence_types = set(section.get("evidence_types", []))
        if not {"empirical", "visual"} <= evidence_types:
            raise ValueError(
                "the empirical visual section requires evidence_types empirical and visual"
            )
    elif empirical_section is not None or empirical_question is not None:
        raise ValueError(
            "non-testable visual plans must set empirical_section and empirical_question to null"
        )
    if (
        route.get("empirical_requirements", {}).get("status") == "required"
        and not empirical_claim_ids
    ):
        raise ValueError("required empirical routes must identify empirically testable selected claims")

    return plan


def validate_architecture(run_dir: Path, value: dict) -> None:
    bundle = verify_theory_handoff(run_dir)
    route = bundle["paper_route"]
    schema_version = value.get("schema_version")
    paper_manifest = load_paper_manifest(run_dir) if paper_manifest_path(run_dir).is_file() else {}
    rewrite_in_progress = paper_manifest.get("manuscript_rewrite", {}).get("status") == "in_progress"
    if ("manuscript_kind" in route or rewrite_in_progress) and schema_version != 3:
        raise ValueError("first-run and rewritten manuscripts require page-aware content architecture schema v3")
    if schema_version not in {2, 3}:
        raise ValueError("content architecture schema_version must be 2 or 3")
    require_text(value.get("title"), "title")
    require_text(value.get("narrative_arc"), "narrative_arc")
    exemplar_path = run_dir / "paper" / "writing_exemplars.json"
    if exemplar_path.is_file():
        if value.get("writing_exemplars_sha256") != file_sha256(exemplar_path):
            raise ValueError("content architecture must bind to the completed writing exemplar study")
        if not require_list(value.get("adopted_writing_principles"), "adopted_writing_principles"):
            raise ValueError("content architecture must apply writing principles from the exemplar study")
    if schema_version == 3:
        if value.get("manuscript_kind") != route_manuscript_kind(route):
            raise ValueError("content architecture manuscript_kind must match the deterministic paper route")
        venue_path = run_dir / "paper" / "venue_selection.json"
        if not venue_path.is_file():
            raise ValueError("page-aware content architecture requires completed venue selection first")
        if paper_manifest_path(run_dir).is_file():
            venue_stage = load_paper_manifest(run_dir).get("stages", {}).get("venue_selection", {})
            if venue_stage.get("status") != "completed":
                raise ValueError("page-aware content architecture requires completed venue selection first")
        if value.get("venue_selection_sha256") != file_sha256(venue_path):
            raise ValueError("content architecture must bind to the selected venue artifact")
        venue_selection = require_dict(read_json(venue_path), "venue selection")
        venue_snapshot = require_dict(venue_selection.get("venue_snapshot"), "venue selection snapshot")
        venue_metadata = require_dict(
            venue_snapshot.get("source_metadata"), "venue selection snapshot source_metadata"
        )
    else:
        # Completed schema-v2 runs retain their original architecture contract.
        if value.get("publication_tier") != route["publication_tier"]:
            raise ValueError("content architecture publication_tier must match the legacy paper route")
        if value.get("paper_type") != route["paper_type"]:
            raise ValueError("content architecture paper_type must match the legacy paper route")
    if value.get("claim_policy_acknowledged") is not True:
        raise ValueError("content architecture must acknowledge the routed claim policy")
    primary = require_list(value.get("primary_statement_ids"), "primary_statement_ids")
    if set(primary) != set(route["primary_statement_ids"]):
        raise ValueError("content architecture primary statements must match the paper route")
    claim_map = require_list(value.get("claim_evidence_map"), "claim_evidence_map")
    accepted = set(route.get("selected_statement_ids") or [
        item["effective_statement"]["id"] for item in bundle["accepted_statements"]
    ])
    mapped = set()
    for index, item in enumerate(claim_map):
        item = require_dict(item, f"claim_evidence_map[{index}]")
        require_fields(item, ("claim_id", "evidence"), f"claim_evidence_map[{index}]")
        claim_id = require_text(item["claim_id"], f"claim_evidence_map[{index}].claim_id")
        if claim_id not in accepted or claim_id in mapped:
            raise ValueError(f"claim evidence map has unknown or duplicate claim: {claim_id}")
        mapped.add(claim_id)
        if not require_list(item["evidence"], f"{claim_id}.evidence"):
            raise ValueError(f"{claim_id} must have manuscript evidence")
    if not set(primary) <= mapped:
        raise ValueError("every routed primary statement needs a claim-evidence entry")
    if not accepted <= mapped:
        raise ValueError("every selected established statement needs a claim-evidence entry")
    sections = require_list(value.get("sections"), "sections")
    normalized = set()
    for index, section in enumerate(sections):
        section = require_dict(section, f"sections[{index}]")
        require_fields(section, ("name", "title", "purpose", "claims_planned"), f"sections[{index}]")
        name = require_text(section["name"], f"sections[{index}].name").lower()
        if name in normalized:
            raise ValueError(f"duplicate planned section: {name}")
        normalized.add(name)
        require_text(section["title"], f"sections[{index}].title")
        validate_section_title(section, schema_version=schema_version)
        require_text(section["purpose"], f"sections[{index}].purpose")
        claims = require_list(section["claims_planned"], f"sections[{index}].claims_planned")
        if any(claim not in accepted for claim in claims):
            raise ValueError(f"planned section {name} uses a claim outside the accepted bundle")
        evidence_types = section.get("evidence_types", [])
        if not isinstance(evidence_types, list) or any(
            not isinstance(item, str) or not item.strip() for item in evidence_types
        ):
            raise ValueError(f"sections[{index}].evidence_types must be a list of non-empty labels")
        if schema_version in {2, 3}:
            if section.get("location") not in {"main", "appendix"}:
                raise ValueError(f"sections[{index}].location must be main or appendix")
            if "proof" in evidence_types:
                if section.get("proof_mode") not in {"complete_inline", "appendix_full"}:
                    raise ValueError(
                        f"proof section {name} must declare proof_mode complete_inline or appendix_full"
                    )
                if section.get("complete_proof") is not True:
                    raise ValueError(f"proof section {name} must commit to a complete proof")
    if not sections or sections[0]["name"].lower() != "abstract":
        raise ValueError("content architecture must begin with the abstract")
    missing = REQUIRED_CORE_SECTIONS - normalized
    if missing:
        raise ValueError(f"content architecture is missing universal scholarly sections: {sorted(missing)}")
    # Existing plans imply a standalone section; integrated plans must name their destination.
    limitations_section = value.get(
        "limitations_section", "limitations" if "limitations" in normalized else None
    )
    if limitations_section not in ("limitations", "conclusion", "discussion"):
        raise ValueError("limitations_section must identify limitations, conclusion, or discussion")
    section_map = {section["name"].lower(): section for section in sections}
    if limitations_section not in section_map:
        raise ValueError("limitations_section must identify a planned section")
    if limitations_section != "limitations":
        if "limitations" in normalized:
            raise ValueError("integrated limitations must not also plan a standalone limitations section")
        if section_map[limitations_section].get("location") != "main":
            raise ValueError("integrated limitations must appear in the main text")
    conclusion_title = " ".join(section_map["conclusion"]["title"].casefold().split())
    if conclusion_title == "conclusion and limitations" and limitations_section != "conclusion":
        raise ValueError("a combined conclusion title requires limitations_section conclusion")
    if schema_version == 3:
        writing_exemplars = read_json(exemplar_path) if exemplar_path.is_file() else None
        validate_length_plan(
            value,
            sections,
            venue_metadata=venue_metadata,
            writing_exemplars=writing_exemplars,
        )
        length_plan = require_dict(value.get("length_plan"), "length_plan")
        venue_limit = venue_metadata.get("page_limit")
        planned_limit = length_plan.get("hard_page_limit")
        if venue_limit is not None and planned_limit != venue_limit:
            raise ValueError("content architecture hard_page_limit must match the selected venue snapshot")
        if venue_limit is None and planned_limit is not None:
            raise ValueError("content architecture declares a hard page limit absent from the selected venue snapshot")
    contribution_claims = {
        claim
        for section in sections if section["name"].lower() not in CORE_SECTIONS
        for claim in section["claims_planned"]
    }
    if not set(primary) <= contribution_claims:
        raise ValueError(
            "every primary statement must appear in a model-designed contribution section"
        )
    if route["empirical_requirements"]["status"] == "required" and not any(
        "empirical" in section.get("evidence_types", []) for section in sections
    ):
        raise ValueError(
            "required empirical evidence must appear in a model-designed section with evidence_types including empirical"
        )
    if accepted:
        if schema_version not in {2, 3}:
            raise ValueError("papers containing established statements require structured content architecture")
        proof_sections = [
            section for section in sections
            if "proof" in section.get("evidence_types", [])
        ]
        if not proof_sections:
            raise ValueError(
                "papers containing established statements require a proof section with evidence_types including proof"
            )
        proved_claims = {
            claim for section in proof_sections for claim in section.get("claims_planned", [])
        }
        if not accepted <= proved_claims:
            raise ValueError("every selected established claim must be planned in a proof section")
        appendix_proof_sections = [
            section for section in proof_sections
            if section.get("location") == "appendix"
            and section.get("proof_mode") == "appendix_full"
            and section.get("complete_proof") is True
        ]
        if not appendix_proof_sections:
            raise ValueError(
                "every paper with established claims requires a dedicated complete appendix proof section"
            )
        if schema_version == 3:
            detail_plan = require_list(value.get("proof_detail_plan"), "proof_detail_plan")
            planned_detail_claims = set()
            for index, item in enumerate(detail_plan):
                item = require_dict(item, f"proof_detail_plan[{index}]")
                require_fields(
                    item,
                    (
                        "claim_id", "proof_strategy", "assumption_uses", "supporting_results",
                        "critical_steps", "boundary_checks", "conclusion",
                    ),
                    f"proof_detail_plan[{index}]",
                )
                claim_id = require_text(item["claim_id"], f"proof_detail_plan[{index}].claim_id")
                if claim_id not in accepted or claim_id in planned_detail_claims:
                    raise ValueError("proof_detail_plan has an unknown or duplicate selected claim")
                planned_detail_claims.add(claim_id)
                require_text(item["proof_strategy"], f"{claim_id}.proof_strategy")
                require_text(item["conclusion"], f"{claim_id}.conclusion")
                require_list(item["supporting_results"], f"{claim_id}.supporting_results")
                assumption_uses = require_list(item["assumption_uses"], f"{claim_id}.assumption_uses")
                if not assumption_uses:
                    raise ValueError(f"{claim_id} proof detail plan must explain its assumption use")
                for assumption in assumption_uses:
                    assumption = require_dict(assumption, f"{claim_id}.assumption_uses item")
                    require_text(assumption.get("assumption"), f"{claim_id}.assumption")
                    require_text(assumption.get("use"), f"{claim_id}.assumption use")
                critical_steps = require_list(item["critical_steps"], f"{claim_id}.critical_steps")
                if len(critical_steps) < 3:
                    raise ValueError(f"{claim_id} proof detail plan requires at least three critical steps")
                for step in critical_steps:
                    step = require_dict(step, f"{claim_id}.critical_steps item")
                    require_text(step.get("step"), f"{claim_id}.critical step")
                    require_text(step.get("justification"), f"{claim_id}.critical step justification")
                boundary_checks = require_list(item["boundary_checks"], f"{claim_id}.boundary_checks")
                if not boundary_checks:
                    raise ValueError(f"{claim_id} proof detail plan requires a boundary or edge-case check")
                for check in boundary_checks:
                    check = require_dict(check, f"{claim_id}.boundary_checks item")
                    require_text(check.get("case"), f"{claim_id}.boundary case")
                    require_text(check.get("resolution"), f"{claim_id}.boundary resolution")
            if planned_detail_claims != accepted:
                missing = sorted(accepted - planned_detail_claims)
                raise ValueError(f"proof_detail_plan is missing selected results: {missing}")
            proof_section_names = {str(section["name"]).lower() for section in appendix_proof_sections}
            proof_page_target = sum(
                float(allocation["target_pages"])
                for allocation in value["length_plan"]["section_page_targets"]
                if str(allocation["section"]).lower() in proof_section_names
            )
            minimum_proof_pages = max(3.0, 1.5 * len(accepted))
            if proof_page_target < minimum_proof_pages:
                raise ValueError(
                    "the page plan underallocates the detailed proof appendix: "
                    f"target at least {minimum_proof_pages:g} pages"
                )
        appendix_proved_claims = {
            claim for section in appendix_proof_sections
            for claim in section.get("claims_planned", [])
        }
        if not accepted <= appendix_proved_claims:
            missing = sorted(accepted - appendix_proved_claims)
            raise ValueError(f"selected results lack complete appendix proof coverage: {missing}")
        proof_map = require_list(value.get("proof_appendix_map"), "proof_appendix_map")
        mapped_claims = set()
        statement_labels = set()
        appendix_labels = set()
        for index, mapping in enumerate(proof_map):
            mapping = require_dict(mapping, f"proof_appendix_map[{index}]")
            require_fields(
                mapping,
                ("claim_id", "statement_label", "appendix_proof_label"),
                f"proof_appendix_map[{index}]",
            )
            claim_id = require_text(mapping["claim_id"], f"proof_appendix_map[{index}].claim_id")
            statement_label = require_text(
                mapping["statement_label"], f"proof_appendix_map[{index}].statement_label"
            )
            appendix_label = require_text(
                mapping["appendix_proof_label"],
                f"proof_appendix_map[{index}].appendix_proof_label",
            )
            if claim_id not in accepted or claim_id in mapped_claims:
                raise ValueError("proof_appendix_map has an unknown or duplicate selected claim")
            if statement_label in statement_labels or appendix_label in appendix_labels:
                raise ValueError("proof_appendix_map labels must be unique")
            mapped_claims.add(claim_id)
            statement_labels.add(statement_label)
            appendix_labels.add(appendix_label)
        if mapped_claims != accepted:
            missing = sorted(accepted - mapped_claims)
            raise ValueError(f"proof_appendix_map is missing selected results: {missing}")
        if schema_version == 3 and uses_component_page_contract(venue_metadata):
            validate_main_text_math_plan(
                value,
                accepted=accepted,
                primary=set(primary),
                sections=sections,
                proof_map=proof_map,
            )
        if schema_version == 3:
            validate_visual_evidence_plan(
                run_dir,
                value,
                accepted=accepted,
                sections=sections,
                route=route,
            )
    else:
        if schema_version not in {2, 3}:
            raise ValueError("evidence reports require structured content architecture")
        evidence_sections = [
            section for section in sections
            if section.get("location") == "appendix"
            and "audit" in section.get("evidence_types", [])
            and section.get("complete_evidence") is True
        ]
        if not evidence_sections:
            raise ValueError(
                "an evidence report requires a complete appendix evidence section"
            )
        for section in evidence_sections:
            sources = require_list(
                section.get("source_artifacts"),
                f"{section['name']}.source_artifacts",
            )
            if not sources or any(not isinstance(item, str) or not item.strip() for item in sources):
                raise ValueError("the evidence appendix must name the persisted audit and proof artifacts it explains")
    if schema_version in {2, 3}:
        appendix_claims = {
            item.get("statement_id") for item in route.get("result_roles", [])
            if isinstance(item, dict) and item.get("paper_placement") == "appendix"
        }
        planned_appendix_claims = {
            claim for section in sections if section.get("location") == "appendix"
            for claim in section.get("claims_planned", [])
        }
        if not appendix_claims <= planned_appendix_claims:
            missing = sorted(appendix_claims - planned_appendix_claims)
            raise ValueError(f"routed appendix results lack appendix sections: {missing}")
    if "related_work" in normalized:
        related = require_dict(value.get("related_work_strategy"), "related_work_strategy")
        require_text(related.get("placement_rationale"), "related_work_strategy.placement_rationale")
        if related.get("mode") not in {"standalone", "hybrid"}:
            raise ValueError("related_work_strategy.mode must be standalone or hybrid")
        if not isinstance(related.get("nonstandard_placement"), bool):
            raise ValueError("related_work_strategy.nonstandard_placement must be boolean")
        section_order = [item["name"].lower() for item in sections]
        immediately_after_intro = (
            "introduction" in normalized
            and section_order.index("related_work") == section_order.index("introduction") + 1
        )
        if not immediately_after_intro and not related["nonstandard_placement"]:
            raise ValueError(
                "Related Work defaults to immediately after Introduction; later placement must be explicit"
            )
        if immediately_after_intro and related["nonstandard_placement"]:
            raise ValueError("nonstandard_placement cannot be true for the default Related Work position")
        comparison_ids = require_list(
            related.get("comparison_record_ids", []), "related_work_strategy.comparison_record_ids"
        )
        literature_path = run_dir / "paper" / "literature_audit.json"
        if literature_path.is_file():
            literature = require_dict(read_json(literature_path), "literature audit")
            coverage = literature.get("coverage_assessment", {})
            closest = set(coverage.get("closest_work_record_ids", []))
            if closest and not closest <= set(comparison_ids):
                raise ValueError("Related Work strategy must compare every audited closest work")


def validate_venue_selection(run_dir: Path, value: dict) -> None:
    venue = require_text(value.get("venue"), "venue")
    legacy_architecture_binding = value.get("content_architecture_sha256")
    if legacy_architecture_binding is not None:
        architecture_path = run_dir / "paper" / "content_architecture.json"
        if not architecture_path.is_file() or legacy_architecture_binding != file_sha256(architecture_path):
            raise ValueError("legacy venue selection must bind to the immutable content architecture")
    else:
        if value.get("schema_version") != 3:
            raise ValueError("pre-architecture venue selection requires schema_version 3")
        bundle_path = run_dir / "artifacts" / "theory_bundle.json"
        if value.get("theory_bundle_sha256") != file_sha256(bundle_path):
            raise ValueError("venue selection must bind to the immutable theory bundle")
        exemplars_path = run_dir / "paper" / "writing_exemplars.json"
        if not exemplars_path.is_file() or value.get("writing_exemplars_sha256") != file_sha256(exemplars_path):
            raise ValueError("venue selection must bind to the completed exemplar study")
        require_text(value.get("selection_rationale"), "venue selection rationale")
        if value.get("selection_method") != "agent_comparative_judgment":
            raise ValueError("venue selection must use agent_comparative_judgment")
        candidate_set = venue_candidates(run_dir)
        if value.get("candidate_set_sha256") != candidate_set["candidate_set_sha256"]:
            raise ValueError("venue selection must bind to the current evidence-compatible candidate set")
        candidate_names = {
            str(item.get("venue", "")).casefold(): item
            for item in candidate_set.get("candidates", [])
            if isinstance(item, dict)
        }
        selected_candidate = candidate_names.get(venue.casefold())
        if selected_candidate is None:
            raise ValueError("selected venue is not in the current evidence-compatible candidate set")
        considered = require_list(value.get("considered_venues"), "considered_venues")
        required_count = min(3, len(candidate_names))
        if len(considered) < required_count:
            raise ValueError(f"venue selection must compare at least {required_count} candidates")
        considered_names = set()
        selected_names = []
        for index, comparison in enumerate(considered):
            comparison = require_dict(comparison, f"considered_venues[{index}]")
            name = require_text(comparison.get("venue"), f"considered_venues[{index}].venue")
            folded = name.casefold()
            if folded not in candidate_names:
                raise ValueError(f"considered venue is not in the candidate set: {name}")
            if folded in considered_names:
                raise ValueError(f"duplicate considered venue: {name}")
            considered_names.add(folded)
            if not isinstance(comparison.get("compatible"), bool):
                raise ValueError(f"considered_venues[{index}].compatible must be boolean")
            if not isinstance(comparison.get("selected"), bool):
                raise ValueError(f"considered_venues[{index}].selected must be boolean")
            require_text(comparison.get("fit_summary"), f"considered_venues[{index}].fit_summary")
            for field in ("strengths", "limitations", "evidence_refs"):
                entries = require_list(comparison.get(field), f"considered_venues[{index}].{field}")
                if field in {"strengths", "evidence_refs"} and not entries:
                    raise ValueError(f"considered_venues[{index}].{field} cannot be empty")
                if any(not isinstance(entry, str) or not entry.strip() for entry in entries):
                    raise ValueError(f"considered_venues[{index}].{field} must contain nonempty strings")
            if comparison["selected"]:
                selected_names.append(folded)
                if comparison["compatible"] is not True:
                    raise ValueError("the selected venue must be marked compatible")
        if selected_names != [venue.casefold()]:
            raise ValueError("exactly one considered venue must be selected and match venue")
        factors = require_dict(value.get("decision_factors"), "decision_factors")
        for factor in candidate_set["selection_requirements"]["comparison_axes"]:
            require_text(factors.get(factor), f"decision_factors.{factor}")
        if value.get("order_invariance_attestation") is not True:
            raise ValueError("venue selection must attest that candidate order carried no preference")
    require_dict(value.get("venue_snapshot"), "venue_snapshot")
    require_list(value.get("formatting_adaptations"), "formatting_adaptations")
    if legacy_architecture_binding is not None:
        if value.get("title_changed") is not False:
            raise ValueError("venue formatting cannot change the scientific title")
        if require_list(value.get("sections_removed"), "sections_removed"):
            raise ValueError("venue formatting cannot silently remove scientific sections")
    bundle = verify_theory_handoff(run_dir)
    route = bundle["paper_route"]
    snapshot = require_dict(value.get("venue_snapshot"), "venue_snapshot")
    metadata = require_dict(snapshot.get("source_metadata"), "venue_snapshot.source_metadata")
    if str(snapshot.get("venue", venue)).casefold() != venue.casefold():
        raise ValueError("venue selection does not match its staged template snapshot")
    if snapshot.get("package_integrity_verified") is not True:
        raise ValueError("selected venue requires a package-integrity-verified snapshot")
    if any(
        item.get("severity") in {"error", "fatal"}
        for item in require_list(snapshot.get("audit_findings", []), "venue_snapshot.audit_findings")
        if isinstance(item, dict)
    ):
        raise ValueError("selected venue snapshot has blocking integrity findings")
    if legacy_architecture_binding is None:
        neutral = metadata.get("neutral_draft") is True
        manuscript_kind = route.get("manuscript_kind")
        if manuscript_kind == "full_paper" and neutral:
            raise ValueError("full-paper routes require a named scholarly venue template")
        if manuscript_kind == "evidence_report" and not neutral:
            raise ValueError("evidence-report routes require a neutral document template")
    if route.get("submission_framing_allowed") is True and snapshot.get("submission_ready") is not True:
        raise ValueError(
            "submission-eligible routes require a locally staged venue snapshot with verified, fresh official rules"
        )


def validate_empirical(run_dir: Path, value: dict) -> None:
    status = value.get("status")
    if status not in {"not_required", "planned", "completed", "contradictory", "blocked"}:
        raise ValueError(f"invalid empirical status: {status}")
    require_text(value.get("reason"), "empirical reason")
    bundle = verify_theory_handoff(run_dir)
    accepted = set(bundle["paper_route"].get("selected_statement_ids") or [
        item["effective_statement"]["id"] for item in bundle["accepted_statements"]
    ])
    accepted_assumptions = {
        assumption
        for item in bundle.get("accepted_statements", []) if isinstance(item, dict)
        for assumption in item.get("effective_statement", {}).get("assumptions_used", [])
        if isinstance(assumption, str)
    }
    strategy = require_dict(value.get("strategy"), "experiment strategy")
    validate_strategy(strategy, accepted)
    from experiment_resources import validate_resource_evidence
    validate_resource_evidence(run_dir / "paper", value)
    experiments = require_list(value.get("experiments"), "experiments")
    experiment_ids = set()
    supported_tags = set()
    for index, experiment in enumerate(experiments):
        experiment = require_dict(experiment, f"experiments[{index}]")
        experiment_id = require_text(experiment.get("id"), f"experiments[{index}].id")
        if experiment_id in experiment_ids:
            raise ValueError(f"duplicate experiment ID: {experiment_id}")
        experiment_ids.add(experiment_id)
        validate_experiment(
            experiment, accepted, run_dir / "paper",
            require_final=status in {"completed", "contradictory"},
        )
        if accepted_assumptions and any(
            assumption not in accepted_assumptions for assumption in experiment.get("assumptions_tested", [])
        ):
            raise ValueError(f"{experiment_id} tests an assumption outside the accepted theory bundle")
        if experiment.get("evaluation", {}).get("verdict") == "supports":
            supported_tags.update(experiment["tags"])
    selected = set(strategy["selected_experiment_ids"])
    if experiment_ids != selected:
        raise ValueError("experiments must exactly match the strategy's selected experiments")
    coverage_tags = require_list(value.get("coverage_tags"), "coverage_tags")
    if len(coverage_tags) != len(set(coverage_tags)) or any(
        not isinstance(tag, str) or not tag.strip() for tag in coverage_tags
    ):
        raise ValueError("coverage_tags must contain unique non-empty tags")
    if any(tag not in supported_tags for tag in coverage_tags):
        raise ValueError("coverage_tags must be derived from supporting evaluated experiments")
    limitations = require_list(value.get("limitations"), "empirical limitations")
    if status == "blocked":
        if not any(experiment.get("status") == "blocked" for experiment in experiments):
            raise ValueError("blocked empirical validation requires a documented blocked experiment")
        if any(experiment.get("status") not in FINAL_STATUSES | {"blocked"} for experiment in experiments):
            raise ValueError("blocked empirical validation requires each experiment to be evaluated or explicitly blocked")
        if not limitations or any(not isinstance(item, str) or not item.strip() for item in limitations):
            raise ValueError("blocked empirical validation requires explicit limitations")
    if status == "not_required" and (selected or experiments or coverage_tags):
        raise ValueError("not_required empirical status cannot select or claim experiment evidence")
    if status in {"completed", "contradictory"} and not experiments:
        raise ValueError(f"empirical status {status} requires selected, evaluated experiments")
    verdicts = {
        experiment.get("evaluation", {}).get("verdict") for experiment in experiments
        if experiment.get("status") in {"evaluated", "contradictory", "inconclusive", "failed"}
    }
    if status == "contradictory" and "contradicts" not in verdicts:
        raise ValueError("contradictory empirical status requires a contradicting result")
    if status in {"completed", "blocked"} and "contradicts" in verdicts:
        raise ValueError("a contradicting result must use contradictory empirical status")
    route = bundle["paper_route"]
    # Preserve unavailable evidence in an already restricted manuscript route,
    # without treating the empirical requirement as satisfied.
    blocked_draft = (
        status == "blocked"
        and value.get("schema_version") == 2
        and route.get("writing_allowed") is True
        and route.get("submission_framing_allowed") is False
        and route.get("submission_readiness") == "evidence_incomplete"
        and route.get("publication_goal_satisfied") is not True
    )
    if status == "blocked" and not blocked_draft:
        raise ValueError("blocked empirical evidence requires an explicitly non-submission, evidence-incomplete manuscript route")
    if route["empirical_requirements"]["status"] == "required" and status != "completed" and not blocked_draft:
        raise ValueError(
            "paper route requires completed empirical validation; a plan cannot substitute for evidence"
        )
    significance = route.get("significance_audit", {})
    if status == "completed" and significance:
        framing = significance.get("framing_scope")
        burden = significance.get("theory_assessment", {}).get("known_parameter_burden")
        if framing != "theory_only" and "real_system" not in coverage_tags:
            raise ValueError("completed application validation requires real-system coverage")
        if burden == "strong" and "misspecification" not in coverage_tags:
            raise ValueError("completed validation must test misspecification of required parameters")
    if value.get("schema_version") == 2:
        import hashlib
        import json

        def canonical_hash(item):
            payload = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()

        registry_path = run_dir / "paper" / "experiments" / "index.json"
        if not registry_path.is_file() or value.get("evidence_registry_sha256") != file_sha256(registry_path):
            raise ValueError("empirical validation is not bound to the current experiment evidence registry")
        inspections = require_list(value.get("inspections"), "experiment inspections")
        latest_inspection_ids = {}
        for inspection in inspections:
            if isinstance(inspection, dict):
                experiment_id = inspection.get("experiment_id")
                inspection_id = inspection.get("inspection_id")
                if isinstance(experiment_id, str) and isinstance(inspection_id, str):
                    latest_inspection_ids[experiment_id] = inspection_id
        inspection_ids = set()
        for inspection in inspections:
            inspection = require_dict(inspection, "experiment inspection")
            inspection_id = require_text(inspection.get("inspection_id"), "inspection_id")
            if inspection_id in inspection_ids:
                raise ValueError(f"duplicate experiment inspection: {inspection_id}")
            inspection_ids.add(inspection_id)
            report_hash = inspection.get("report_sha256")
            if report_hash != canonical_hash({key: item for key, item in inspection.items() if key != "report_sha256"}):
                raise ValueError(f"experiment inspection record was modified: {inspection_id}")
            if latest_inspection_ids.get(inspection.get("experiment_id")) == inspection_id:
                script = safe_paper_path(run_dir, require_text(inspection.get("script_path"), "script_path"))
                if not script.is_file() or file_sha256(script) != inspection.get("script_sha256"):
                    raise ValueError(f"latest inspected experiment script is missing or modified: {inspection_id}")
                for relative, digest in inspection.get("dependency_sha256", {}).items():
                    dependency = safe_paper_path(run_dir, relative)
                    if not dependency.is_file() or file_sha256(dependency) != digest:
                        raise ValueError(f"latest inspected experiment dependency is missing or modified: {relative}")
        executions = require_list(value.get("executions"), "experiment executions")
        latest_execution_ids = {}
        for execution in executions:
            if isinstance(execution, dict):
                experiment_id = execution.get("experiment_id")
                execution_id = execution.get("execution_id")
                if isinstance(experiment_id, str) and isinstance(execution_id, str):
                    latest_execution_ids[experiment_id] = execution_id
        execution_ids = set()
        for execution in executions:
            execution = require_dict(execution, "experiment execution")
            execution_id = require_text(execution.get("execution_id"), "execution_id")
            if execution_id in execution_ids or execution.get("inspection_id") not in inspection_ids:
                raise ValueError(f"invalid or duplicate experiment execution: {execution_id}")
            execution_ids.add(execution_id)
            if execution.get("record_sha256") != canonical_hash({key: item for key, item in execution.items() if key != "record_sha256"}):
                raise ValueError(f"experiment execution record was modified: {execution_id}")
            if latest_execution_ids.get(execution.get("experiment_id")) == execution_id:
                for relative, digest in {**execution.get("artifact_sha256", {}), **execution.get("log_sha256", {})}.items():
                    path = safe_paper_path(run_dir, relative)
                    if not path.is_file() or file_sha256(path) != digest:
                        raise ValueError(f"latest experiment execution artifact is missing or modified: {relative}")
        from experiment_tools import validate_evaluation_hashes, validate_figure_review_hash
        for experiment in experiments:
            validate_evaluation_hashes(experiment)
            for evaluation in [*experiment.get("evaluation_history", []), experiment.get("evaluation")]:
                if not evaluation:
                    continue
                evaluation = require_dict(evaluation, "experiment evaluation")
                if evaluation.get("execution_id") not in execution_ids:
                    raise ValueError(f"experiment evaluation lacks a registered execution: {experiment.get('id')}")
        figures = require_list(value.get("figures"), "empirical figures")
        figure_history = read_json(registry_path).get("figure_history", [])
        figure_ids, labels = set(), set()
        for figure in figures:
            figure = require_dict(figure, "empirical figure")
            figure_id = require_text(figure.get("figure_id"), "figure_id")
            label = require_text(figure.get("label"), "figure label")
            if figure_id in figure_ids or label in labels:
                raise ValueError("empirical figures require unique IDs and labels")
            figure_ids.add(figure_id); labels.add(label)
            path = safe_paper_path(run_dir, require_text(figure.get("path"), "figure path"))
            results = safe_paper_path(run_dir, require_text(figure.get("results_path"), "figure results path"))
            if not path.is_file() or file_sha256(path) != figure.get("figure_sha256"):
                raise ValueError(f"empirical figure is missing or modified: {figure_id}")
            if not results.is_file() or file_sha256(results) != figure.get("results_sha256"):
                raise ValueError(f"empirical figure results are missing or modified: {figure_id}")
            if figure.get("record_sha256") != canonical_hash({key: item for key, item in figure.items() if key != "record_sha256"}):
                raise ValueError(f"empirical figure record was modified: {figure_id}")
            visual_review = figure.get("visual_review")
            if status in {"completed", "contradictory"} and figure.get("role") == "main":
                visual_review = require_dict(visual_review, f"{figure_id}.visual_review")
                if visual_review.get("schema_version") != 2:
                    raise ValueError(f"completed main figure lacks professional schema-v2 review: {figure_id}")
                validate_figure_review_hash(figure, figure_history)
                scores = require_dict(visual_review.get("design_scores"), f"{figure_id}.design_scores")
                if len(scores) != 8 or any(
                    not isinstance(score, (int, float)) or isinstance(score, bool) or score < 4
                    for score in scores.values()
                ):
                    raise ValueError(f"main figure has a design score below publication quality: {figure_id}")
                if visual_review.get("computed_overall_score", 0) < 4.25:
                    raise ValueError(f"main figure design average is below publication quality: {figure_id}")
                if visual_review.get("professional_quality_passed") is not True:
                    raise ValueError(f"main figure did not pass professional visual review: {figure_id}")
            snippet = figure.get("latex_snippet_path")
            if snippet:
                snippet_path = safe_paper_path(run_dir, snippet)
                if not snippet_path.is_file() or file_sha256(snippet_path) != figure.get("latex_snippet_sha256"):
                    raise ValueError(f"empirical figure LaTeX snippet is missing or modified: {figure_id}")
            if (
                status in {"completed", "contradictory", "blocked"}
                and figure.get("role") == "main"
                and figure.get("status") != "publication_ready"
            ):
                raise ValueError(f"completed empirical validation has an unreviewed main figure: {figure_id}")

        architecture_path = run_dir / "paper" / "content_architecture.json"
        if architecture_path.is_file():
            architecture = require_dict(read_json(architecture_path), "content architecture")
            visual_plan = architecture.get("visual_evidence_plan")
            if architecture.get("schema_version") == 3 and visual_plan is not None:
                visual_plan = require_dict(visual_plan, "visual_evidence_plan")
                declared_testable = set(require_list(
                    visual_plan.get("empirical_claim_ids"),
                    "visual_evidence_plan.empirical_claim_ids",
                ))
                coverage = {
                    item["claim_id"]: item["status"]
                    for item in strategy["claim_coverage"]
                }
                deferred = sorted(
                    claim for claim, claim_status in coverage.items()
                    if claim_status == "deferred"
                )
                if deferred:
                    raise ValueError(
                        "full-paper empirical validation cannot defer accepted claims; "
                        f"classify them as selected or not empirically testable: {deferred}"
                    )
                selected_claims = {
                    claim for claim, claim_status in coverage.items()
                    if claim_status == "selected"
                }
                if selected_claims != declared_testable:
                    raise ValueError(
                        "experiment strategy testability must match visual_evidence_plan.empirical_claim_ids"
                    )
                if declared_testable:
                    if status not in {"completed", "contradictory", "blocked"}:
                        raise ValueError(
                            "empirically testable full-paper claims require completed, contradictory, "
                            "or honestly blocked experiments"
                        )
                    if status in {"completed", "contradictory", "blocked"}:
                        experiment_by_id = {
                            experiment["id"]: experiment for experiment in experiments
                        }
                        figure_claims = {
                            claim
                            for figure in figures
                            if figure.get("role") == "main"
                            and figure.get("status") == "publication_ready"
                            for claim in experiment_by_id.get(
                                figure.get("experiment_id"), {}
                            ).get("claim_ids", [])
                        }
                        required_figure_claims = declared_testable
                        if status == "blocked":
                            required_figure_claims = declared_testable & {
                                claim for experiment in experiments
                                if experiment.get("status") in FINAL_STATUSES
                                for claim in experiment.get("claim_ids", [])
                            }
                        missing = sorted(required_figure_claims - figure_claims)
                        if missing:
                            raise ValueError(
                                "each empirically testable claim requires a publication-ready main figure: "
                                f"{missing}"
                            )
                elif status != "not_required":
                    raise ValueError(
                        "a full paper with no empirically testable claims must use empirical status not_required"
                    )


def _section_includes_tex(content: str, relative: str) -> bool:
    normalized = relative[:-4] if relative.endswith(".tex") else relative
    return bool(re.search(
        rf"\\input\{{(?:{re.escape(relative)}|{re.escape(normalized)})\}}",
        content,
    ))


def validate_written_visual_evidence(
    run_dir: Path,
    *,
    architecture: dict,
    sections: list,
    section_contents: dict,
) -> None:
    plan = require_dict(architecture.get("visual_evidence_plan"), "visual_evidence_plan")
    declared_testable = set(require_list(
        plan.get("empirical_claim_ids"), "visual_evidence_plan.empirical_claim_ids"
    ))
    empirical = require_dict(
        read_json(run_dir / "paper" / "empirical_validation.json"),
        "empirical validation",
    )
    empirical_status = empirical.get("status")
    if empirical_status == "blocked":
        declared_testable &= {
            claim for experiment in empirical.get("experiments", [])
            if experiment.get("status") in FINAL_STATUSES
            for claim in experiment.get("claim_ids", [])
        }
    if declared_testable and empirical_status in {"completed", "contradictory", "blocked"}:
        section_name = require_text(
            plan.get("empirical_section"), "visual_evidence_plan.empirical_section"
        ).lower()
        content = section_contents.get(section_name, "")
        experiments = {
            item.get("id"): item
            for item in empirical.get("experiments", []) if isinstance(item, dict)
        }
        included_claims = set()
        for figure in empirical.get("figures", []):
            if not isinstance(figure, dict):
                continue
            if figure.get("role") != "main" or figure.get("status") != "publication_ready":
                continue
            snippet = figure.get("latex_snippet_path")
            if not isinstance(snippet, str) or not snippet.strip() or not _section_includes_tex(content, snippet):
                continue
            included_claims.update(
                experiments.get(figure.get("experiment_id"), {}).get("claim_ids", [])
            )
        missing = sorted(declared_testable - included_claims)
        if missing:
            raise ValueError(
                f"manuscript lacks the planned empirical figure for testable claims: {missing}"
            )
        return


def validate_sections(run_dir: Path, value: dict) -> None:
    from citations import latex_citation_keys
    from literature.registry import load_registry, resolve_record_id

    bundle = verify_theory_handoff(run_dir)
    accepted = set(bundle["paper_route"].get("selected_statement_ids") or [
        item["effective_statement"]["id"] for item in bundle["accepted_statements"]
    ])
    primary = set(bundle["paper_route"]["primary_statement_ids"])
    sections = require_list(value.get("sections"), "sections")
    literature_path = run_dir / "paper" / "literature_audit.json"
    literature_ids = set()
    if literature_path.is_file():
        literature = require_dict(read_json(literature_path), "literature audit")
        literature_ids = {
            item["record_id"] for item in require_list(literature.get("references"), "references")
            if isinstance(item, dict) and isinstance(item.get("record_id"), str)
        }
    registry_path = run_dir / "literature" / "registry.json"
    registry = load_registry(run_dir) if registry_path.is_file() else None
    if not sections:
        raise ValueError("section index cannot be empty")
    names = set()
    cited_record_ids = set()
    section_contents = {}
    for index, record in enumerate(sections):
        record = require_dict(record, f"sections[{index}]")
        require_fields(record, ("name", "path", "claims_used", "citations_used"), f"sections[{index}]")
        name = require_text(record["name"], f"sections[{index}].name").lower()
        if name in names:
            raise ValueError(f"duplicate section: {name}")
        names.add(name)
        relative = require_text(record["path"], f"sections[{index}].path")
        section_path = safe_paper_path(run_dir, relative)
        if not section_path.is_file():
            raise ValueError(f"missing section file: {relative}")
        if value.get("schema_version") == 2 and record.get("content_sha256") != file_sha256(section_path):
            raise ValueError(f"section content was modified outside the section writer: {name}")
        claims = require_list(record["claims_used"], f"{name}.claims_used")
        if any(claim not in accepted for claim in claims):
            raise ValueError(f"{name} uses a claim outside the accepted theory bundle")
        if name == "abstract" and accepted and (not claims or not set(claims) <= primary):
            raise ValueError("abstract must use at least one routed primary statement and no non-primary claim")
        if name == "abstract" and not accepted and claims:
            raise ValueError("an evidence-report abstract cannot claim an established statement")
        citations = require_list(record["citations_used"], f"{name}.citations_used")
        if len(citations) != len(set(citations)):
            raise ValueError(f"{name}.citations_used contains duplicate record IDs")
        if any(citation not in literature_ids for citation in citations):
            raise ValueError(f"{name} cites a record outside the validated literature audit")
        cited_record_ids.update(citations)
        section_content = section_path.read_text(encoding="utf-8")
        section_contents[name] = section_content
        if FORBIDDEN_SECTION_PAGE_BREAKS.search(section_content):
            raise ValueError(
                f"{name} contains a forced page break; sections must add substantive "
                "content or rely on assembler-controlled reference/appendix boundaries"
            )
        meta_terms = sorted(set(match.group(0) for match in MANUSCRIPT_META_TERMS.finditer(section_content)))
        if meta_terms:
            raise ValueError(
                f"{name} contains planning or instruction vocabulary that must be rewritten: {meta_terms}"
            )
        if name == "abstract" and latex_citation_keys(section_content):
            raise ValueError("abstract must not contain citations")
        actual_keys = latex_citation_keys(section_content)
        if citations or actual_keys:
            if registry is None:
                raise ValueError(f"{name} uses citations but the run literature registry is missing")
            canonical = [resolve_record_id(registry, citation) for citation in citations]
            expected_keys = {registry["citation_keys"][citation] for citation in canonical}
            if actual_keys != expected_keys:
                raise ValueError(
                    f"{name} LaTeX citation keys do not match its citations_used record IDs"
                )
    if "abstract" not in names:
        raise ValueError("section index must include abstract")
    if value.get("schema_version") == 2 and literature_path.is_file():
        literature = require_dict(read_json(literature_path), "literature audit")
        if literature.get("schema_version") == 2:
            maturity = literature.get("coverage_assessment", {}).get("area_maturity")
            publication_goal = load_manifest(run_dir).get("execution_contract", {}).get(
                "publication_goal", "no_preference"
            )
            floor = 20 if maturity == "mature" or publication_goal == "original_research" else 15
            target = literature.get("coverage_assessment", {}).get("target_reference_count", floor)
            required_citations = max(floor, target) if isinstance(target, int) else floor
            if len(cited_record_ids) < required_citations:
                raise ValueError(
                    f"manuscript cites {len(cited_record_ids)} audited sources; "
                    f"this route requires at least {required_citations} sources actually cited in section text"
                )
    architecture_path = run_dir / "paper" / "content_architecture.json"
    if architecture_path.is_file():
        architecture = require_dict(read_json(architecture_path), "content architecture")
        planned = architecture["sections"]
        planned_names = [item["name"].lower() for item in planned]
        if names != set(planned_names):
            raise ValueError("written sections must match the venue-independent content architecture")
        titles = {item["name"].lower(): item["title"] for item in planned}
        claims_planned = {item["name"].lower(): set(item.get("claims_planned", [])) for item in planned}
        for record in sections:
            plan = next(item for item in planned if item["name"].lower() == record["name"].lower())
            if record.get("title") != titles[record["name"].lower()]:
                raise ValueError(f"section title does not match content architecture: {record['name']}")
            if architecture.get("schema_version") in {2, 3} and record.get("location", "main") != plan.get("location"):
                raise ValueError(f"section location does not match content architecture: {record['name']}")
            if (
                value.get("schema_version") == 2
                and "claims_planned" in plan
                and not set(record["claims_used"]) <= claims_planned[record["name"].lower()]
            ):
                raise ValueError(f"section uses claims not planned by the content architecture: {record['name']}")
        rewrite = (
            load_paper_manifest(run_dir).get("manuscript_rewrite", {})
            if paper_manifest_path(run_dir).is_file()
            else {}
        )
        if rewrite.get("status") == "in_progress":
            if architecture.get("schema_version") != 3:
                raise ValueError("a full manuscript rewrite requires a fresh page-aware architecture")
            baseline = require_dict(rewrite.get("baseline_section_hashes", {}), "baseline section hashes")
            unchanged = sorted(
                record["name"] for record in sections
                if baseline.get(record["name"].lower()) == record.get("content_sha256")
            )
            if unchanged:
                raise ValueError(
                    f"full manuscript rewrite reused unchanged section content: {unchanged}"
                )
        if all("claims_planned" in item for item in planned):
            for claim in primary:
                if not any(
                    claim in record["claims_used"] and record["name"].lower() not in CORE_SECTIONS
                    for record in sections
                ):
                    raise ValueError(f"primary claim {claim} is missing from a contribution section")
        route = bundle["paper_route"]
        if accepted and architecture.get("schema_version") == 3:
            validate_written_visual_evidence(
                run_dir,
                architecture=architecture,
                sections=sections,
                section_contents=section_contents,
            )
        if accepted and architecture.get("schema_version") in {2, 3}:
            proof_names = {
                item["name"].lower() for item in planned
                if "proof" in item.get("evidence_types", [])
            }
            if not proof_names:
                raise ValueError("manuscript is missing its planned proof section")
            proof_content = "\n".join(
                (safe_paper_path(run_dir, record["path"])).read_text(encoding="utf-8")
                for record in sections if record["name"].lower() in proof_names
            )
            proof_bodies = re.findall(
                r"\\begin\{proof\}(.*?)\\end\{proof\}", proof_content, flags=re.DOTALL
            )
            if not proof_bodies:
                raise ValueError("manuscript proof section must contain a complete proof environment")
            if architecture.get("schema_version") in {2, 3}:
                thin = [body for body in proof_bodies if len(re.sub(r"\\[A-Za-z]+|\s+", "", body)) < 500]
                if thin:
                    raise ValueError(
                        "proof-bearing sections contain a proof that is too short to establish completeness; "
                        "include the detailed argument or a complete appendix proof"
                    )
                appendix_proof_names = {
                    item["name"].lower() for item in planned
                    if "proof" in item.get("evidence_types", [])
                    and item.get("location") == "appendix"
                    and item.get("proof_mode") == "appendix_full"
                    and item.get("complete_proof") is True
                }
                if not appendix_proof_names:
                    raise ValueError("manuscript is missing its dedicated full-proof appendix")
                written_proof_claims = {
                    claim for record in sections if record["name"].lower() in proof_names
                    for claim in record.get("claims_used", [])
                }
                if not accepted <= written_proof_claims:
                    missing = sorted(accepted - written_proof_claims)
                    raise ValueError(f"selected results lack written proof coverage: {missing}")
                written_appendix_proof_claims = {
                    claim for record in sections if record["name"].lower() in appendix_proof_names
                    for claim in record.get("claims_used", [])
                }
                if not accepted <= written_appendix_proof_claims:
                    missing = sorted(accepted - written_appendix_proof_claims)
                    raise ValueError(f"selected results lack written appendix proofs: {missing}")
                if len(proof_bodies) < len(accepted):
                    raise ValueError("every selected result requires its own complete proof environment")
                appendix_claims = {
                    item.get("statement_id") for item in route.get("result_roles", [])
                    if isinstance(item, dict) and item.get("paper_placement") == "appendix"
                }
                written_appendix_claims = {
                    claim for record in sections if record.get("location") == "appendix"
                    for claim in record.get("claims_used", [])
                }
                if not appendix_claims <= written_appendix_claims:
                    raise ValueError("routed appendix results were written outside the appendix")
                main_content = "\n".join(
                    (safe_paper_path(run_dir, record["path"])).read_text(encoding="utf-8")
                    for record in sections if record.get("location", "main") == "main"
                )
                appendix_content = "\n".join(
                    (safe_paper_path(run_dir, record["path"])).read_text(encoding="utf-8")
                    for record in sections if record.get("location") == "appendix"
                )
                formal_blocks = re.findall(
                    r"\\begin\{(?:theorem|proposition|lemma|corollary)\}(.*?)"
                    r"\\end\{(?:theorem|proposition|lemma|corollary)\}",
                    main_content,
                    flags=re.DOTALL,
                )
                appendix_proof_bodies = re.findall(
                    r"\\begin\{proof\}(.*?)\\end\{proof\}",
                    appendix_content,
                    flags=re.DOTALL,
                )
                proof_map = require_list(
                    architecture.get("proof_appendix_map"), "proof_appendix_map"
                )
                for mapping in proof_map:
                    statement_label = mapping["statement_label"]
                    appendix_label = mapping["appendix_proof_label"]
                    if not any(f"\\label{{{statement_label}}}" in block for block in formal_blocks):
                        raise ValueError(
                            f"selected result lacks its labeled main formal statement: {statement_label}"
                        )
                    if not any(f"\\label{{{appendix_label}}}" in body for body in appendix_proof_bodies):
                        raise ValueError(
                            f"selected result lacks its labeled complete appendix proof: {appendix_label}"
                        )
                    if architecture.get("schema_version") == 3:
                        matching_bodies = [
                            body for body in appendix_proof_bodies
                            if f"\\label{{{appendix_label}}}" in body
                        ]
                        if len(matching_bodies) != 1:
                            raise ValueError(
                                f"selected result requires exactly one labeled appendix proof: {appendix_label}"
                            )
                        validate_detailed_appendix_proof(
                            matching_bodies[0], claim_id=mapping["claim_id"]
                        )
                    main_ref = re.search(
                        rf"\\(?:auto|[cC]|eq)?ref\{{{re.escape(appendix_label)}\}}",
                        main_content,
                    )
                    appendix_ref = re.search(
                        rf"\\(?:auto|[cC]|eq)?ref\{{{re.escape(statement_label)}\}}",
                        appendix_content,
                    )
                    if main_ref is None or appendix_ref is None:
                        raise ValueError(
                            "every selected result requires exact two-way main-to-appendix cross-references"
                        )
                math_plan = architecture.get("main_text_math_plan")
                if math_plan is not None:
                    math_plan = require_list(math_plan, "main_text_math_plan")
                    for item in math_plan:
                        claim_id = item["claim_id"]
                        section_name = str(item["section"]).lower()
                        content = section_contents.get(section_name, "")
                        statement_label = item["statement_label"]
                        formal_statement = re.search(
                            r"\\begin\{(?:theorem|proposition|lemma|corollary)\}.*?"
                            rf"\\label\{{{re.escape(statement_label)}\}}.*?"
                            r"\\end\{(?:theorem|proposition|lemma|corollary)\}",
                            content,
                            flags=re.DOTALL,
                        )
                        if formal_statement is None:
                            raise ValueError(
                                f"{claim_id} lacks its planned formal statement in {section_name}"
                            )
                        display_blocks = re.findall(
                            r"\\\[(.*?)\\\]|"
                            r"\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?)\}"
                            r"(.*?)\\end\{(?:equation\*?|align\*?|gather\*?|multline\*?)\}",
                            content,
                            flags=re.DOTALL,
                        )
                        display_text = "\n".join(left or right for left, right in display_blocks)
                        for derivation in item["key_derivations"]:
                            label = derivation["label"]
                            if f"\\label{{{label}}}" not in display_text:
                                raise ValueError(
                                    f"{claim_id} lacks planned main-text derivation {label} in {section_name}"
                                )
                        for supporting in item["supporting_lemmas"]:
                            label = supporting["label"]
                            if re.search(
                                r"\\begin\{(?:lemma|proposition|corollary)\}.*?"
                                rf"\\label\{{{re.escape(label)}\}}.*?"
                                r"\\end\{(?:lemma|proposition|corollary)\}",
                                content,
                                flags=re.DOTALL,
                            ) is None:
                                raise ValueError(
                                    f"{claim_id} lacks planned supporting result {label} in {section_name}"
                                )
            formal_content = "\n".join(
                (safe_paper_path(run_dir, record["path"])).read_text(encoding="utf-8")
                for record in sections
            )
            formal_count = len(re.findall(
                r"\\begin\{(?:theorem|proposition|lemma|corollary)\}", formal_content
            ))
            if formal_count < len(accepted):
                raise ValueError(
                    "manuscript must typeset every selected result in a formal environment"
                )
        elif not accepted:
            evidence_names = {
                item["name"].lower() for item in planned
                if item.get("location") == "appendix"
                and "audit" in item.get("evidence_types", [])
                and item.get("complete_evidence") is True
            }
            if not evidence_names:
                raise ValueError("evidence report is missing its complete evidence appendix")
            evidence_content = "\n".join(
                (safe_paper_path(run_dir, record["path"])).read_text(encoding="utf-8")
                for record in sections if record["name"].lower() in evidence_names
            )
            meaningful = re.sub(r"\\[A-Za-z]+|[^A-Za-z0-9]+", "", evidence_content)
            if len(meaningful) < 500:
                raise ValueError(
                    "null-result evidence appendix is too short; explain the attempted claims, "
                    "audited failure, preserved evidence, and supported next research step"
                )
            if re.search(r"\\begin\{(?:theorem|proposition|lemma|corollary)\}", evidence_content):
                raise ValueError("a null-result evidence appendix cannot present an unaccepted theorem as established")


def validate_compile(run_dir: Path, value: dict) -> None:
    require_text(value.get("tex_path"), "tex_path")
    if not safe_paper_path(run_dir, value["tex_path"]).is_file():
        raise ValueError("compiled paper TeX file is missing")
    if not isinstance(value.get("pdf_built"), bool):
        raise ValueError("pdf_built must be boolean")
    require_list(value.get("warnings"), "compile warnings")
    if value.get("warnings"):
        raise ValueError("compiled manuscript has unresolved warnings")
    if value.get("schema_version") == 2:
        tex = safe_paper_path(run_dir, value["tex_path"])
        if value.get("tex_sha256") != file_sha256(tex):
            raise ValueError("compile report is not bound to the current paper.tex")
        if value["pdf_built"]:
            pdf = safe_paper_path(run_dir, require_text(value.get("pdf_path"), "pdf_path"))
            if not pdf.is_file() or value.get("pdf_sha256") != file_sha256(pdf):
                raise ValueError("compile report is not bound to the current PDF")
        findings = require_list(value.get("source_lint_findings"), "source_lint_findings")
        if any(isinstance(item, dict) and item.get("severity") == "error" for item in findings):
            raise ValueError("compiled manuscript has unresolved source-lint errors")
        architecture_path = run_dir / "paper" / "content_architecture.json"
        if architecture_path.is_file():
            architecture = require_dict(read_json(architecture_path), "content architecture")
            if architecture.get("schema_version") == 3 and value["pdf_built"]:
                page_count = value.get("page_count")
                if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count <= 0:
                    raise ValueError("page-aware manuscript compilation must record the PDF page count")
                plan = require_dict(architecture.get("length_plan"), "length_plan")
                minimum = plan.get("minimum_total_pages")
                maximum = plan["maximum_total_pages"]
                if minimum is not None and page_count < minimum:
                    raise ValueError(
                        f"compiled manuscript has {page_count} pages, below its planned minimum of {minimum}"
                    )
                if page_count > maximum:
                    raise ValueError(
                        f"compiled manuscript has {page_count} pages, above its planned maximum of {maximum}"
                    )
                if value.get("page_budget_status") != "within_budget":
                    raise ValueError("compiled manuscript did not satisfy its page-aware architecture")
                if plan.get("page_limit_scope") in PAGE_LIMIT_SCOPES:
                    breakdown = require_dict(value.get("page_breakdown"), "page_breakdown")
                    for field in ("main_pages", "reference_pages", "appendix_pages", "total_pages"):
                        count = breakdown.get(field)
                        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                            raise ValueError(f"page_breakdown.{field} must be a nonnegative integer")
                    if breakdown["main_pages"] <= 0 or breakdown["total_pages"] != page_count:
                        raise ValueError("rendered component page counts are inconsistent")
                    if require_list(value.get("page_budget_findings"), "page_budget_findings"):
                        raise ValueError("compiled manuscript has unresolved component page-budget findings")
                    minimum_main = plan["minimum_main_pages"]
                    maximum_main = plan["maximum_main_pages"]
                    if (
                        (minimum_main is not None and breakdown["main_pages"] < minimum_main)
                        or breakdown["main_pages"] > maximum_main
                    ):
                        raise ValueError(
                            "compiled main text is outside its venue-derived page range"
                        )
                    minimum_appendix = plan["minimum_appendix_pages"]
                    if (
                        minimum_appendix is not None
                        and breakdown["appendix_pages"] < minimum_appendix
                    ):
                        raise ValueError(
                            "compiled proof appendix is below its planned minimum length"
                        )
                    maximum_references = plan.get("maximum_reference_pages")
                    if (
                        maximum_references is not None
                        and breakdown["reference_pages"] > maximum_references
                    ):
                        raise ValueError("compiled references exceed their planned page allowance")
                    hard_limit = plan.get("hard_page_limit")
                    if hard_limit is not None:
                        scoped_pages = {
                            "main_text": breakdown["main_pages"],
                            "main_plus_references": breakdown.get(
                                "main_plus_reference_pages",
                                breakdown["main_pages"] + breakdown["reference_pages"],
                            ),
                            "total_manuscript": breakdown["total_pages"],
                        }.get(plan["page_limit_scope"])
                        if scoped_pages is not None and scoped_pages > hard_limit:
                            raise ValueError("compiled manuscript exceeds the venue page-limit scope")
                source = tex.read_text(encoding="utf-8")
                bibliography_positions = [
                    position for token in ("\\bibliographystyle", "\\bibliography{")
                    if (position := source.find(token)) >= 0
                ]
                appendix_position = source.find("\\appendix")
                if appendix_position >= 0 and bibliography_positions and max(bibliography_positions) > appendix_position:
                    raise ValueError("references must be assembled before the appendix")
                if appendix_position >= 0 and "\\section*{Appendix}" not in source[appendix_position:]:
                    raise ValueError("compiled manuscript is missing the explicit Appendix heading")


def validate_review(run_dir: Path, value: dict) -> None:
    recommendation = value.get("recommendation")
    if recommendation not in {
        "accept", "draft_ready", "package_with_warnings",
        "minor_revision", "major_revision", "reject",
    }:
        raise ValueError(f"invalid review recommendation: {recommendation}")
    findings = require_list(value.get("findings"), "review findings")
    for index, finding in enumerate(findings):
        finding = require_dict(finding, f"review findings[{index}]")
        require_fields(finding, ("id", "severity", "criterion", "description", "required_action"),
                       f"review findings[{index}]")
        if finding["severity"] not in {"minor", "major", "fatal"}:
            raise ValueError(f"invalid review finding severity: {finding['severity']}")
    scores = require_dict(value.get("criterion_scores"), "criterion_scores")
    for criterion in (
        "technical_quality", "clarity", "novelty", "significance",
        "empirical_validation", "reproducibility",
    ):
        score = scores.get(criterion)
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValueError(f"criterion_scores.{criterion} must be between 1 and 5")
    confidence = value.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 1 <= confidence <= 5:
        raise ValueError("review confidence must be between 1 and 5")
    for field in ("route_consistent", "application_evidence_sufficient"):
        if not isinstance(value.get(field), bool):
            raise ValueError(f"review {field} must be boolean")
    require_text(value.get("summary"), "review summary")
    route = verify_theory_handoff(run_dir)["paper_route"]
    empirical = require_dict(
        read_json(run_dir / "paper" / "empirical_validation.json"), "empirical validation"
    )
    if route.get("novelty_verdict") != "supported" and scores["novelty"] > 3:
        raise ValueError("review novelty score exceeds the routed novelty evidence")
    if route.get("significance_level") in {"narrow", "unclear"} and scores["significance"] > 3:
        raise ValueError("review significance score exceeds the routed significance assessment")
    if route.get("significance_level") == "insufficient" and scores["significance"] > 2:
        raise ValueError("review significance score exceeds an insufficient significance assessment")
    empirical_required = route.get("empirical_requirements", {}).get("status") == "required"
    if empirical_required and empirical.get("status") != "completed" and scores["empirical_validation"] > 2:
        raise ValueError("review empirical score exceeds the completed empirical evidence")
    if empirical_required and empirical.get("status") != "completed" and value["application_evidence_sufficient"]:
        raise ValueError("review cannot claim sufficient application evidence without completed validation")
    major_route_blockers = [
        item for item in route.get("review_blockers", [])
        if isinstance(item, dict) and item.get("severity") in {"major", "fatal"}
    ]
    if recommendation == "accept" and major_route_blockers:
        raise ValueError("accept is impossible while the paper route has major or fatal blockers")
    if recommendation == "draft_ready" and route.get("submission_framing_allowed") is True:
        raise ValueError("draft_ready is reserved for governed non-submission paper routes")
    if recommendation == "draft_ready" and findings:
        raise ValueError("draft_ready requires no actionable manuscript findings")
    if recommendation == "package_with_warnings":
        manifest = load_paper_manifest(run_dir)
        if not manuscript_repair_budget_exhausted(manifest):
            raise ValueError("package_with_warnings requires the two-round manuscript repair budget")
        if not review_findings_are_packagable(findings):
            raise ValueError(
                "package_with_warnings permits only nonfatal layout or exposition findings"
            )
    elif findings and review_findings_are_packagable(findings):
        manifest = load_paper_manifest(run_dir)
        if (
            manuscript_repair_budget_exhausted(manifest)
            and recommendation in {"minor_revision", "major_revision"}
        ):
            raise ValueError(
                "the two-round manuscript repair budget is exhausted; use package_with_warnings"
            )
    if recommendation == "accept" and empirical_required:
        if empirical.get("status") != "completed":
            raise ValueError("accept requires completed routed empirical validation")
    if value.get("schema_version") == 2:
        compile_path = run_dir / "paper" / "compile_report.json"
        if value.get("compile_report_sha256") != file_sha256(compile_path):
            raise ValueError("review is not bound to the current compile report")
        compile_report = require_dict(read_json(compile_path), "compile report")
        pdf_path = compile_report.get("pdf_path")
        if pdf_path and value.get("pdf_sha256") != compile_report.get("pdf_sha256"):
            raise ValueError("review is not bound to the reviewed PDF")
        ids = [item["id"] for item in findings]
        if len(ids) != len(set(ids)):
            raise ValueError("review finding IDs must be unique")
        section_index = require_dict(
            read_json(run_dir / "paper" / "sections" / "index.json"), "section index"
        )
        section_names = {item["name"] for item in section_index.get("sections", [])}
        assessments = require_list(value.get("section_assessments"), "section_assessments")
        assessed = set()
        for index, assessment in enumerate(assessments):
            assessment = require_dict(assessment, f"section_assessments[{index}]")
            name = require_text(assessment.get("section"), f"section_assessments[{index}].section")
            if name not in section_names or name in assessed:
                raise ValueError("section assessments must cover each written section exactly once")
            assessed.add(name)
            section_scores = require_dict(assessment.get("scores"), f"section_assessments[{index}].scores")
            for field in ("clarity", "narrative_function", "evidence_alignment", "scholarly_exposition"):
                score = section_scores.get(field)
                if not isinstance(score, (int, float)) or isinstance(score, bool) or not 1 <= score <= 5:
                    raise ValueError(f"section assessment {name}.{field} must be between 1 and 5")
            if assessment.get("status") not in {"pass", "revise"}:
                raise ValueError("section assessment status must be pass or revise")
            require_text(assessment.get("rationale"), f"section_assessments[{index}].rationale")
        if assessed != section_names:
            raise ValueError("independent review must assess every written section")
        checks = require_dict(value.get("proofreading_checks"), "proofreading_checks")
        for field in (
            "cross_references", "citations", "latex_artifacts", "figure_readability",
            "page_layout", "title_rendering",
        ):
            if not isinstance(checks.get(field), bool):
                raise ValueError(f"proofreading_checks.{field} must be boolean")
        architecture_path = run_dir / "paper" / "content_architecture.json"
        architecture = read_json(architecture_path) if architecture_path.is_file() else {}
        if isinstance(architecture, dict) and architecture.get("visual_evidence_plan") is not None:
            for field in ("visual_evidence_readability", "visual_evidence_alignment"):
                if not isinstance(checks.get(field), bool):
                    raise ValueError(f"proofreading_checks.{field} must be boolean")
        if recommendation in {"accept", "draft_ready"}:
            if compile_report.get("warnings"):
                raise ValueError("clean packaging requires a warning-free compiled manuscript")
            if compile_report.get("page_budget_status") not in {None, "within_budget"}:
                raise ValueError(
                    "clean packaging requires a compiled manuscript within its "
                    "page-aware architecture; use findings or package_with_warnings "
                    "after repair-budget exhaustion"
                )
            if compile_report.get("page_budget_findings"):
                raise ValueError("clean packaging requires resolved component page-budget findings")
            if any(
                assessment["status"] != "pass" or min(assessment["scores"].values()) < 4
                for assessment in assessments
            ):
                raise ValueError("clean packaging requires every manuscript section to score at least 4 and pass")
            if not all(checks.values()):
                raise ValueError("clean packaging requires all proofreading checks to pass")


def validate_revision(run_dir: Path, value: dict) -> None:
    changes = require_list(value.get("changes"), "revision changes")
    unresolved = require_list(value.get("unresolved_findings"), "unresolved_findings")
    if not isinstance(value.get("theory_changes_required"), bool):
        raise ValueError("theory_changes_required must be boolean")
    if value.get("schema_version") != 2:
        return
    review_path = run_dir / "paper" / "review.json"
    if value.get("source_review_sha256") != file_sha256(review_path):
        raise ValueError("revision is not bound to the current review")
    review = require_dict(read_json(review_path), "review")
    finding_ids = {item["id"] for item in review["findings"]}
    responses = require_list(value.get("finding_responses"), "finding_responses")
    response_ids = {item.get("finding_id") for item in responses if isinstance(item, dict)}
    if response_ids != finding_ids:
        raise ValueError("revision must respond exactly once to every review finding")
    all_comment_ids = {item["id"] for item in load_user_comments(run_dir)["comments"]}
    comment_ids = {item["id"] for item in unresolved_user_comments(run_dir)}
    comment_responses = require_list(value.get("user_comment_responses"), "user_comment_responses")
    responded_comments = {item.get("comment_id") for item in comment_responses if isinstance(item, dict)}
    if not comment_ids <= responded_comments or not responded_comments <= all_comment_ids:
        raise ValueError("revision must respond exactly once to every open user comment")
    for label, records, id_field in (
        ("finding response", responses, "finding_id"),
        ("user comment response", comment_responses, "comment_id"),
    ):
        for item in records:
            item = require_dict(item, label)
            require_text(item.get(id_field), f"{label}.{id_field}")
            if item.get("disposition") not in {"addressed", "declined_with_reason", "theory_change_required"}:
                raise ValueError(f"invalid {label} disposition")
            require_text(item.get("response"), f"{label}.response")
            for changed in require_list(item.get("changed_files"), f"{label}.changed_files"):
                changed = require_dict(changed, "changed file")
                path = safe_paper_path(run_dir, require_text(changed.get("path"), "changed file path"))
                if not path.is_file() or changed.get("sha256") != file_sha256(path):
                    raise ValueError(f"revision changed-file evidence is missing or modified: {path.name}")
    if set(unresolved) - finding_ids:
        raise ValueError("unresolved_findings contains an unknown finding ID")
    if any(not isinstance(item, dict) for item in changes):
        raise ValueError("schema-v2 revision changes must be objects")


def validate_final(run_dir: Path, value: dict) -> None:
    from literature.registry import coverage_report, load_registry

    if not isinstance(value.get("ready_for_submission_check"), bool):
        raise ValueError("ready_for_submission_check must be boolean")
    route = verify_theory_handoff(run_dir)["paper_route"]
    if value["ready_for_submission_check"] and not route["submission_framing_allowed"]:
        raise ValueError("non-submission paper routes cannot be marked as submission candidates")
    files = require_list(value.get("files"), "final files")
    if not files:
        raise ValueError("final package must contain at least one file")
    for item in files:
        if isinstance(item, str):
            path = safe_paper_path(run_dir, item)
            if not path.is_file():
                raise ValueError(f"final package file is missing: {item}")
        elif isinstance(item, dict):
            path = safe_paper_path(run_dir, require_text(item.get("path"), "final file path"))
            if not path.is_file() or item.get("sha256") != file_sha256(path):
                raise ValueError(f"final package file is missing or modified: {path.name}")
        else:
            raise ValueError("final files must be paths or hash-bound file records")
    require_list(value.get("remaining_warnings"), "remaining_warnings")
    require_text(value.get("theory_bundle_sha256"), "theory_bundle_sha256")
    expected = file_sha256(run_dir / "artifacts" / "theory_bundle.json")
    if value["theory_bundle_sha256"] != expected:
        raise ValueError("final package does not bind to the current theory bundle")
    review = require_dict(read_json(run_dir / "paper" / "review.json"), "review")
    validate_review(run_dir, review)
    if not value["ready_for_submission_check"]:
        warning_package = (
            review.get("recommendation") == "package_with_warnings"
            and manuscript_repair_budget_exhausted(load_paper_manifest(run_dir))
            and review_findings_are_packagable(review.get("findings", []))
        )
        if not warning_package and (
            review.get("recommendation") not in {"accept", "draft_ready"}
            or review.get("findings")
        ):
            raise ValueError(
                "non-submission final package requires a clean review or an exhausted repair warning package"
            )
        if warning_package:
            remaining = value.get("remaining_warnings", [])
            warning_ids = {
                item if isinstance(item, str) else item.get("id")
                for item in remaining if isinstance(item, (str, dict))
            }
            finding_ids = {item["id"] for item in review["findings"]}
            if not finding_ids <= warning_ids:
                raise ValueError(
                    "final package must preserve every exhausted manuscript-repair finding as a warning"
                )
        if not review.get("route_consistent"):
            raise ValueError("non-submission final package must remain consistent with its routed tier")
    if value["ready_for_submission_check"]:
        venue_selection = require_dict(
            read_json(run_dir / "paper" / "venue_selection.json"), "venue selection"
        )
        venue_snapshot = require_dict(
            venue_selection.get("venue_snapshot"), "venue selection snapshot"
        )
        if venue_snapshot.get("submission_ready") is not True:
            raise ValueError(
                "submission-ready package requires a verified, fresh, submission-ready venue snapshot"
            )
        if unresolved_user_comments(run_dir):
            raise ValueError("submission-ready package has unresolved user comments")
        literature_coverage = coverage_report(load_registry(run_dir))
        if not literature_coverage["complete"]:
            raise ValueError("submission-ready package has literature with insufficient verification")
        if review["recommendation"] != "accept" or review["findings"]:
            raise ValueError("submission-ready package requires a clean accept review")
        if not review["route_consistent"]:
            raise ValueError("submission-ready package must be consistent with its routed evidence status")
        if any(item["severity"] in {"major", "fatal"} for item in review["findings"]):
            raise ValueError("submission-ready package has unresolved major/fatal review findings")
        empirical = require_dict(read_json(run_dir / "paper" / "empirical_validation.json"),
                                 "empirical validation")
        validate_empirical(run_dir, empirical)
        if route["empirical_requirements"]["status"] == "required" and empirical["status"] != "completed":
            raise ValueError("submission-ready package has incomplete required empirical validation")
        if route["empirical_requirements"]["status"] == "required" and not any(
            item.get("evaluation", {}).get("verdict") == "supports"
            for item in empirical.get("experiments", []) if isinstance(item, dict)
        ):
            raise ValueError("required empirical validation has no supporting evaluated experiment")
        significance = route.get("significance_audit", {})
        if significance.get("framing_scope") != "theory_only" and not review["application_evidence_sufficient"]:
            raise ValueError("application-framed submission lacks sufficient application evidence")


VALIDATORS: Dict[str, Callable[[Path, dict], None]] = {
    "literature_audit": validate_literature,
    "exemplar_study": validate_exemplar_study,
    "content_architecture": validate_architecture,
    "venue_selection": validate_venue_selection,
    "empirical_validation": validate_empirical,
    "section_writing": validate_sections,
    "compilation": validate_compile,
    "independent_review": validate_review,
    "revision": validate_revision,
    "final_package": validate_final,
}


def validate_current(run_dir: Path, manifest: dict) -> None:
    verify_theory_handoff(run_dir)
    verify_paper_evidence(run_dir, manifest)
    stage = manifest["current_stage"]
    VALIDATORS[stage](run_dir, current_artifact(run_dir, manifest))


def command_init(args: argparse.Namespace) -> None:
    from literature.registry import seed_from_theory_bundle

    run_dir = resolve_run(Path(args.workspace), args.run)
    bundle = verify_theory_handoff(run_dir)
    paper_dir = run_dir / "paper"
    if paper_manifest_path(run_dir).exists():
        raise ValueError("paper workflow already exists for this run")
    (paper_dir / "sections").mkdir(parents=True, exist_ok=True)
    names = list(STAGES)
    authorization = {
        "schema_version": 1,
        "artifact": "manuscript_authorization",
        "run_id": run_dir.name,
        "theory_bundle_sha256": file_sha256(run_dir / "artifacts" / "theory_bundle.json"),
        "manuscript_kind": route_manuscript_kind(bundle["paper_route"]),
        "selected_statement_ids": bundle["paper_route"].get("selected_statement_ids") or [
            item["effective_statement"]["id"] for item in bundle["accepted_statements"]
        ],
        "authorized_output_root": "paper",
        "authorized_by": "manuscript_workflow",
        "authorized_at": utc_now(),
    }
    authorization_path = manuscript_authorization_path(run_dir)
    write_json(authorization_path, authorization)
    manifest = {
        "schema_version": 2,
        "artifact": "paper_run_manifest",
        "run_id": run_dir.name,
        "created_at": utc_now(),
        "status": "active",
        "state_revision": 0,
        "review_cycle": 1,
        "manuscript_repair": {
            "maximum_rounds": MAX_MANUSCRIPT_REPAIR_ROUNDS,
            "rounds_used": 0,
            "status": "available",
            "history": [],
        },
        "events": [],
        "current_stage": names[0],
        "theory_bundle_sha256": file_sha256(run_dir / "artifacts" / "theory_bundle.json"),
        "manuscript_authorization_sha256": file_sha256(authorization_path),
        "accepted_statement_ids": bundle["paper_route"].get("selected_statement_ids") or [
            item["effective_statement"]["id"] for item in bundle["accepted_statements"]
        ],
        "paper_route": bundle["paper_route"],
        "stages": {
            name: {"status": "in_progress" if name == names[0] else "pending", **spec}
            for name, spec in STAGES.items()
        },
    }
    save_paper_manifest(run_dir, manifest)
    verify_paper_evidence(run_dir, manifest)
    write_json(user_comments_path(run_dir), {
        "schema_version": 1, "artifact": "user_comment_registry", "comments": []
    })
    registry = seed_from_theory_bundle(run_dir)
    print(json.dumps({"run_id": run_dir.name, "paper_dir": str(paper_dir), "current_stage": names[0],
                      "registered_literature": len(registry["records"])}, indent=2))


def command_status(args: argparse.Namespace) -> None:
    run_dir = resolve_run(Path(args.workspace), args.run)
    manifest = load_paper_manifest(run_dir)
    verify_theory_handoff(run_dir)
    verify_paper_evidence(run_dir, manifest)
    stage = manifest["current_stage"]
    print(json.dumps({"run_id": run_dir.name, "status": manifest["status"], "current_stage": stage,
                      "review_cycle": manifest.get("review_cycle", 1),
                      "manuscript_repair": manuscript_repair_state(manifest),
                      "open_user_comments": len(unresolved_user_comments(run_dir)),
                      "actor": manifest["stages"][stage]["actor"],
                      "artifact": str(safe_paper_path(run_dir, manifest["stages"][stage]["artifact"]))}, indent=2))


def command_validate(args: argparse.Namespace) -> None:
    run_dir = resolve_run(Path(args.workspace), args.run)
    manifest = load_paper_manifest(run_dir)
    try:
        validate_current(run_dir, manifest)
    except ValueError as exc:
        if manifest["current_stage"] == "section_writing" and recoverable_section_validation(exc):
            print(json.dumps({
                "valid": False,
                "recoverable": True,
                "stage": "section_writing",
                "finding": {
                    "repair_class": "exposition",
                    "description": str(exc),
                },
                "next_action": "revise the affected manuscript section and validate again",
            }, indent=2))
            return
        raise
    print(json.dumps({"valid": True, "stage": manifest["current_stage"]}, indent=2))


def command_complete(args: argparse.Namespace) -> None:
    run_dir = resolve_run(Path(args.workspace), args.run)
    manifest = load_paper_manifest(run_dir)
    if manifest["status"] == "completed":
        raise ValueError("paper workflow is already completed")
    stage_name = manifest["current_stage"]
    stage = manifest["stages"][stage_name]
    if args.actor != stage["actor"]:
        raise PermissionError(f"stage {stage_name} requires actor {stage['actor']}")
    if stage_name == "compilation":
        verify_theory_handoff(run_dir)
        verify_paper_evidence(run_dir, manifest)
        report = require_dict(current_artifact(run_dir, manifest), "compile report")
        repair_findings = (
            compile_repair_findings(report)
            if automatic_manuscript_repair_enabled(run_dir)
            else []
        )
        if repair_findings:
            attempt = archive_manuscript_attempt(run_dir, manifest, report, repair_findings)
            if not manuscript_repair_budget_exhausted(manifest):
                reopen_for_manuscript_repair(run_dir, manifest, repair_findings)
                save_paper_manifest(run_dir, manifest)
                print(json.dumps({
                    "completed": "compilation_attempt",
                    "next_stage": "section_writing",
                    "status": "active",
                    "next_action": {
                        "type": "automatic_manuscript_repair",
                        "round": manifest["manuscript_repair"]["rounds_used"],
                        "maximum_rounds": manifest["manuscript_repair"]["maximum_rounds"],
                        "findings": repair_findings,
                        "archive": attempt["archive"],
                    },
                }, indent=2))
                return
            state = manuscript_repair_state(manifest)
            state["status"] = "exhausted"
            state["last_findings"] = repair_findings
            best = restore_best_manuscript_attempt(run_dir, manifest)
            section_artifact = safe_paper_path(
                run_dir, manifest["stages"]["section_writing"]["artifact"]
            )
            if section_artifact.is_file():
                manifest["stages"]["section_writing"]["evidence_sha256"] = file_sha256(
                    section_artifact
                )
            artifact = safe_paper_path(run_dir, stage["artifact"])
            stage.update({
                "status": "completed",
                "completed_at": utc_now(),
                "completed_by": args.actor,
                "evidence_sha256": file_sha256(artifact),
                "completion_mode": "repair_budget_exhausted",
            })
            manifest["current_stage"] = "independent_review"
            manifest["stages"]["independent_review"]["status"] = "in_progress"
            manifest.setdefault("events", []).append({
                "event": "manuscript_repair_budget_exhausted",
                "rounds_used": state["rounds_used"],
                "best_attempt": best["attempt"],
                "remaining_findings": repair_findings,
                "recorded_at": utc_now(),
            })
            save_paper_manifest(run_dir, manifest)
            print(json.dumps({
                "completed": "compilation",
                "next_stage": "independent_review",
                "status": "active",
                "next_action": {
                    "type": "review_best_preserved_manuscript",
                    "repair_budget_exhausted": True,
                    "best_attempt": best["attempt"],
                    "remaining_findings": repair_findings,
                },
            }, indent=2))
            return
    try:
        validate_current(run_dir, manifest)
    except ValueError as exc:
        if stage_name == "section_writing" and recoverable_section_validation(exc):
            finding = {"repair_class": "exposition", "description": str(exc)}
            state = manuscript_repair_state(manifest)
            state["last_findings"] = [finding]
            manifest.setdefault("events", []).append({
                "event": "manuscript_stage_repair_required",
                "stage": "section_writing",
                "finding": finding,
                "recorded_at": utc_now(),
            })
            save_paper_manifest(run_dir, manifest)
            print(json.dumps({
                "completed": None,
                "next_stage": "section_writing",
                "status": "active",
                "next_action": {
                    "type": "repair_current_manuscript_stage",
                    "finding": finding,
                },
            }, indent=2))
            return
        raise
    artifact = safe_paper_path(run_dir, stage["artifact"])
    stage.update({"status": "completed", "completed_at": utc_now(), "completed_by": args.actor,
                  "evidence_sha256": file_sha256(artifact)})
    if stage_name == "compilation":
        for refreshed_stage in ("section_writing", "revision"):
            refreshed = manifest["stages"][refreshed_stage]
            if refreshed["status"] != "completed":
                continue
            refreshed_artifact = safe_paper_path(run_dir, refreshed["artifact"])
            refreshed["evidence_sha256"] = file_sha256(refreshed_artifact)
    if stage_name == "section_writing" and manifest.get("manuscript_rewrite", {}).get("status") == "in_progress":
        manifest["manuscript_rewrite"].update({
            "status": "sections_rewritten",
            "completed_at": utc_now(),
            "section_index_sha256": file_sha256(artifact),
        })
    if stage_name == "independent_review":
        review = current_artifact(run_dir, manifest)
        if review["recommendation"] in {"accept", "draft_ready"} and not review["findings"] and not unresolved_user_comments(run_dir):
            manifest["current_stage"] = "final_package"
            manifest["stages"]["final_package"]["status"] = "in_progress"
        elif review["recommendation"] == "package_with_warnings":
            state = manuscript_repair_state(manifest)
            state["status"] = "exhausted"
            state["remaining_review_findings"] = review["findings"]
            manifest["current_stage"] = "final_package"
            manifest["stages"]["final_package"]["status"] = "in_progress"
        else:
            if review_findings_are_packagable(review.get("findings", [])):
                state = manuscript_repair_state(manifest)
                state["rounds_used"] = int(state["rounds_used"]) + 1
                state["status"] = "in_progress"
                state["last_findings"] = review["findings"]
                manifest.setdefault("events", []).append({
                    "event": "automatic_manuscript_repair_started",
                    "round": state["rounds_used"],
                    "maximum_rounds": state["maximum_rounds"],
                    "findings": review["findings"],
                    "source": "independent_review",
                    "recorded_at": utc_now(),
                })
            open_revision_cycle(run_dir, manifest, "independent review requires revision")
    elif stage_name == "revision":
        revision = current_artifact(run_dir, manifest)
        if revision.get("theory_changes_required"):
            manifest["status"] = "blocked"
            manifest.setdefault("events", []).append({
                "event": "theory_change_required", "recorded_at": utc_now(),
                "cycle": manifest.get("review_cycle", 1),
            })
        else:
            manifest["review_cycle"] = manifest.get("review_cycle", 1) + 1
            manifest["current_stage"] = "section_writing"
            manifest["stages"]["section_writing"]["status"] = "in_progress"
    elif stage_name == "final_package":
        manifest["status"] = "completed"
    else:
        names = list(STAGES)
        index = names.index(stage_name)
        manifest["current_stage"] = names[index + 1]
        manifest["stages"][names[index + 1]]["status"] = "in_progress"
    save_paper_manifest(run_dir, manifest)
    print(json.dumps({"completed": stage_name, "next_stage": manifest.get("current_stage"),
                      "status": manifest["status"]}, indent=2))


def command_reconcile(args: argparse.Namespace) -> None:
    """Normalize derived repair state after a clean completed review/package."""
    run_dir = resolve_run(Path(args.workspace), args.run)
    manifest = load_paper_manifest(run_dir)
    verify_theory_handoff(run_dir)
    verify_paper_evidence(run_dir, manifest)
    if manifest.get("status") != "completed":
        raise ValueError("repair-state reconciliation requires a completed paper workflow")
    review = require_dict(read_json(run_dir / "paper" / "review.json"), "review")
    validate_review(run_dir, review)
    if review.get("recommendation") not in {"accept", "draft_ready"} or review.get("findings"):
        raise ValueError("repair-state reconciliation requires a clean final review")
    state = manuscript_repair_state(manifest)
    prior = state.get("status")
    if prior == "in_progress":
        findings = list(state.get("last_findings", []))
        if findings:
            state.setdefault("history", []).append({
                "round": state.get("rounds_used", 0),
                "findings": findings,
                "resolution": "resolved_by_clean_re_review",
                "review_cycle": manifest.get("review_cycle", 1),
                "recorded_at": utc_now(),
            })
        state["status"] = "completed"
        state.pop("last_findings", None)
        manifest.setdefault("events", []).append({
            "event": "manuscript_repair_completed",
            "rounds_used": state.get("rounds_used", 0),
            "review_cycle": manifest.get("review_cycle", 1),
            "recorded_at": utc_now(),
        })
        save_paper_manifest(run_dir, manifest)
    print(json.dumps({
        "status": manifest["status"],
        "manuscript_repair": manuscript_repair_state(manifest),
        "changed": prior == "in_progress",
    }, indent=2))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init").set_defaults(function=command_init)
    commands.add_parser("status").set_defaults(function=command_status)
    commands.add_parser("validate").set_defaults(function=command_validate)
    commands.add_parser("reconcile").set_defaults(function=command_reconcile)
    complete = commands.add_parser("complete")
    complete.add_argument("--actor", required=True)
    complete.set_defaults(function=command_complete)
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, PermissionError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
