#!/usr/bin/env python3
"""Write, assemble, compile, review, and package artifacts inside a TheoremAudit run."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import manuscript_workflow
from citations import latex_citation_keys
from literature.registry import export_bibtex, load_registry, register_usage, resolve_record_id
from state_store import file_sha256, read_json, update_json, utc_now, write_json
from tool_utils import contained, load_object_argument, paper_dir, workspace_path


SECTION_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
INTERNAL_TERMS = re.compile(
    r"\b(?:story|TheoremAudit|proof obligation|governance|arbiter|method team|attack team|"
    r"submission readiness|novelty audit|significance audit|paper route|claim policy|"
    r"content architecture|development obligations?)\b",
    re.IGNORECASE,
)
FORBIDDEN_SECTION_PAGE_BREAKS = re.compile(
    r"\\(?:clearpage|newpage|pagebreak)(?:\[[^\]]*\])?"
)
USER_EDIT_TYPES = (
    "general",
    "clarity",
    "section_content",
    "citations_related_work",
    "figure_table",
    "formatting_venue",
    "full_rewrite",
    "mathematical_claim",
)


def latex_source_findings(content: str) -> list[dict]:
    """Return deterministic source-level findings that LaTeX may compile past."""
    findings = []
    labels = re.findall(r"\\label\{([^}]+)\}", content)
    label_set = set(labels)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        findings.append({
            "severity": "error", "code": "duplicate_labels",
            "message": f"duplicate LaTeX labels: {duplicates}",
        })
    referenced = set(re.findall(r"\\(?:ref|eqref|autoref|cref|Cref)\{([^}]+)\}", content))
    missing = sorted(referenced - label_set)
    if missing:
        findings.append({
            "severity": "error", "code": "missing_labels",
            "message": f"references to undefined labels: {missing}",
        })
    if re.search(r"(?<!\\)\bq?quad[A-Za-z]", content):
        findings.append({
            "severity": "error", "code": "leaked_latex_command",
            "message": "possible literal quad/qquad command leaked into manuscript prose",
        })
    if re.search(r"\b(?:TODO|TBD|CITATION NEEDED)\b|\\cite\{TODO\}", content, re.IGNORECASE):
        findings.append({
            "severity": "error", "code": "placeholder_text",
            "message": "unresolved manuscript placeholder remains",
        })
    for match in FORBIDDEN_SECTION_PAGE_BREAKS.finditer(content):
        remainder = content[match.end():]
        next_source = re.sub(r"^(?:\s|%[^\n]*(?:\n|$))*", "", remainder)
        allowed_boundary = next_source.startswith(
            r"\phantomsection\label{tg:references-start}"
        ) or next_source.startswith(
            r"\phantomsection\label{tg:appendix-start}"
        )
        if not allowed_boundary:
            findings.append({
                "severity": "error",
                "code": "forced_page_break",
                "message": (
                    "forced page breaks are allowed only at assembler-controlled "
                    "reference or appendix boundaries"
                ),
            })
            break
    return findings


def json_list(value: str, label: str):
    try:
        result = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be a JSON list") from exc
    if not isinstance(result, list) or any(not isinstance(item, str) for item in result):
        raise ValueError(f"{label} must be a JSON list of strings")
    return result


def reference_boundary_lines(venue_metadata: dict) -> list[str]:
    """Return the venue-governed boundary before the bibliography."""
    start_new_page = venue_metadata.get("references_start_new_page", False)
    if not isinstance(start_new_page, bool):
        raise ValueError("venue references_start_new_page must be boolean")
    lines = []
    if start_new_page:
        lines.append("\\clearpage")
    lines.append("\\phantomsection\\label{tg:references-start}")
    return lines


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def _sha_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def command_section(args):
    root = paper_dir(args.workspace, args.run)
    if not SECTION_NAME.fullmatch(args.name):
        raise ValueError("invalid section name")
    if bool(args.input) == bool(args.content_base64):
        raise ValueError("write-section requires exactly one of --input or --content-base64")
    if args.content_base64:
        try:
            content = base64.b64decode(args.content_base64, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("content-base64 must encode valid UTF-8 manuscript text") from exc
    else:
        source = workspace_path(Path(args.workspace), args.input)
        if not source.is_file():
            raise ValueError("section input file does not exist")
        content = source.read_text(encoding="utf-8")
    leaks = sorted(set(match.group(0) for match in INTERNAL_TERMS.finditer(content)))
    if leaks:
        raise ValueError(f"section contains internal workflow vocabulary: {leaks}")
    if FORBIDDEN_SECTION_PAGE_BREAKS.search(content):
        raise ValueError(
            "section content must not contain forced page breaks "
            r"(\\clearpage, \\newpage, or \\pagebreak); revise section substance instead"
        )
    citation_ids = json_list(args.citations_json, "citations-json")
    registry = load_registry(root.parent, create=True)
    canonical_ids = [resolve_record_id(registry, item) for item in citation_ids]
    if len(canonical_ids) != len(set(canonical_ids)):
        raise ValueError("citations-json contains duplicate canonical records")
    expected_keys = {registry["citation_keys"][item] for item in canonical_ids}
    actual_keys = latex_citation_keys(content)
    if actual_keys != expected_keys:
        raise ValueError(
            f"LaTeX citation keys {sorted(actual_keys)} do not match citations-json "
            f"{sorted(expected_keys)}"
        )
    claims = json_list(args.claims_json, "claims-json")
    architecture_path = root / "content_architecture.json"
    if architecture_path.is_file():
        planned = {item["name"].lower(): item for item in read_json(architecture_path)["sections"]}
        if args.name.lower() not in planned:
            raise ValueError("section is not present in the content architecture")
        plan = planned[args.name.lower()]
        if args.title != plan["title"]:
            raise ValueError("section title does not match the content architecture")
        if "claims_planned" in plan and not set(claims) <= set(plan["claims_planned"]):
            raise ValueError("section uses claims not planned for it")
    destination = contained(root, f"sections/{args.name}.tex")
    if destination.exists() and not args.replace:
        raise ValueError("section already exists")
    reason = getattr(args, "reason", None)
    if destination.exists() and args.replace and not reason:
        raise ValueError("replacing a section requires --reason")
    normalized = content.rstrip() + "\n"
    index_path = root / "sections" / "index.json"
    index = read_json(index_path) if index_path.exists() else {
        "schema_version": 2, "artifact": "manuscript_section_registry",
        "revision": 0, "sections": [], "history": [],
    }
    records = index.setdefault("sections", [])
    record = {"name": args.name, "title": args.title, "path": f"sections/{args.name}.tex",
              "location": args.location, "claims_used": claims, "citations_used": canonical_ids,
              "content_sha256": _sha_text(normalized), "written_at": utc_now(),
              "actor": "manuscript_writer", "reason": reason or "initial draft"}
    matches = [position for position, item in enumerate(records) if item.get("name") == args.name]
    if matches:
        previous = dict(records[matches[0]])
        previous["replaced_at"] = utc_now()
        previous["replacement_reason"] = reason
        index.setdefault("history", []).append(previous)
        records[matches[0]] = record
    else:
        records.append(record)
    index["schema_version"] = 2
    index["artifact"] = "manuscript_section_registry"
    index["revision"] = int(index.get("revision", 0)) + 1
    atomic_write_text(destination, normalized)
    write_json(index_path, index)
    if canonical_ids:
        register_usage(
            root.parent, canonical_ids, stage="section_writing", purpose="citation",
            claim_ids=record["claims_used"], section_ids=[args.name],
            source_artifact=record["path"], actor="manuscript_writer",
        )
    print(json.dumps({"written": str(destination), "workflow_terms": leaks}, indent=2))


def strip_section_header(content: str) -> str:
    return re.sub(r"(?m)^\s*\\section\*?\{[^}]*\}\s*", "", content, count=1).strip()


def command_assemble(args):
    root = paper_dir(args.workspace, args.run)
    index = read_json(root / "sections" / "index.json")
    manuscript_workflow.validate_sections(root.parent, index)
    records = index["sections"]
    cited_record_ids = sorted({citation for record in records for citation in record["citations_used"]})
    bib_result = export_bibtex(root.parent, root / "references.bib", selected_record_ids=cited_record_ids)
    architecture_path = root / "content_architecture.json"
    architecture = {}
    if architecture_path.is_file():
        architecture = read_json(architecture_path)
        planned = architecture["sections"]
        order = {item["name"].lower(): position for position, item in enumerate(planned)}
        titles = {item["name"].lower(): item["title"] for item in planned}
        records = sorted(records, key=lambda item: order[item["name"].lower()])
        for record in records:
            record["title"] = titles[record["name"].lower()]
    abstract = next((item for item in records if item["name"].lower() == "abstract"), None)
    body = [item for item in records if item is not abstract and item.get("location", "main") == "main"]
    appendix = [item for item in records if item.get("location") == "appendix"]
    venue_snapshot = root / "venue" / "venue_snapshot.json"
    package_line = ""
    bibstyle = "plainnat"
    document_class = "article"
    class_options = []
    blind_review = False
    venue_metadata = {}
    if venue_snapshot.exists():
        snapshot = read_json(venue_snapshot)
        venue_metadata = snapshot.get("source_metadata", {})
        style = venue_metadata.get("style_file")
        bibstyle = venue_metadata.get("bibstyle") or bibstyle
        class_options = venue_metadata.get("class_options") or []
        blind_review = venue_metadata.get("blind_review") is True
        if style and (root / "venue" / style).is_file():
            if style.endswith(".sty"):
                package_line = f"\\usepackage{{venue/{style[:-4]}}}"
            elif style.endswith(".cls"):
                document_class = f"venue/{style[:-4]}"
    supplied_authors = json_list(args.authors_json, "authors-json")
    if any(INTERNAL_TERMS.search(author) for author in supplied_authors):
        raise ValueError("manuscript authors cannot contain internal workflow identities")
    authors = "Anonymous" if blind_review else (" \\and ".join(supplied_authors) or "Anonymous")
    option_text = f"[{','.join(class_options)}]" if class_options else ""
    # COLT/JMLR supply their own proof environment and cannot load amsthm over it.
    lines = [f"\\documentclass{option_text}{{{document_class}}}", package_line,
             "\\usepackage{amsmath,amssymb}", "\\makeatletter",
             "\\@ifundefined{proof}{\\usepackage{amsthm}}{}", "\\makeatother",
             "\\usepackage{graphicx,booktabs,natbib,xurl,hyperref}", f"\\title{{{args.title}}}",
             f"\\author{{{authors}}}", "\\begin{document}", "\\maketitle",
             "\\phantomsection\\label{tg:main-start}"]
    if abstract:
        content = (root / abstract["path"]).read_text(encoding="utf-8").strip()
        lines.extend(["\\begin{abstract}", strip_section_header(content), "\\end{abstract}"])
    for record in body:
        content = (root / record["path"]).read_text(encoding="utf-8")
        lines.extend([f"\\section{{{record.get('title') or record['name'].replace('_', ' ').title()}}}",
                      strip_section_header(content)])
    lines.append("\\phantomsection\\label{tg:main-end}")
    if bib_result["entries"]:
        bibliography_style = f"venue/{bibstyle}" if (root / "venue" / f"{bibstyle}.bst").is_file() else bibstyle
        lines.extend(reference_boundary_lines(venue_metadata))
        # The JMLR class (including COLT) and journal style already select a BibTeX style.
        lines.extend([
            "\\makeatletter",
            "\\@ifclassloaded{jmlr}{}{\\@ifpackageloaded{jmlr2e}{}{"
            f"\\bibliographystyle{{{bibliography_style}}}" + "}}",
            "\\makeatother", "\\bibliography{references}",
        ])
    if appendix:
        appendix_heading = architecture.get("length_plan", {}).get("appendix_heading", "Appendix")
        lines.extend([
            "\\clearpage", "\\phantomsection\\label{tg:appendix-start}",
            "\\appendix", f"\\section*{{{appendix_heading}}}",
        ])
        for record in appendix:
            content = (root / record["path"]).read_text(encoding="utf-8")
            lines.extend([f"\\section{{{record.get('title') or record['name'].replace('_', ' ').title()}}}",
                          strip_section_header(content)])
    lines.append("\\end{document}")
    output = root / "paper.tex"
    atomic_write_text(output, "\n\n".join(line for line in lines if line) + "\n")
    write_json(root / "assembly_report.json", {
        "schema_version": 2, "artifact": "manuscript_assembly_report",
        "assembled_at": utc_now(), "paper_tex_sha256": file_sha256(output),
        "section_index_sha256": file_sha256(root / "sections" / "index.json"),
        "bibliography_sha256": file_sha256(root / "references.bib"),
        "document_class": document_class, "class_options": class_options,
        "blind_review": blind_review, "bibliography_style": bibstyle,
        "bibliography_entries": bib_result["entries"],
        "references_before_appendix": True,
        "references_start_new_page": venue_metadata.get("references_start_new_page", False),
        "appendix_heading": architecture.get("length_plan", {}).get("appendix_heading", "Appendix"),
    })
    print(json.dumps({"written": str(output), "sections": len(records),
                      "bibliography_entries": bib_result["entries"]}, indent=2))


def _aux_marker_page(aux_text: str, label: str) -> int | None:
    match = re.search(
        # Hyperref writes the current section counter into the first field for
        # markers placed after a numbered section (for example ``{{8}{9}}``),
        # while a marker before the first section has an empty first field.
        # Accept either form and read the second field as the rendered page.
        rf"\\newlabel\{{{re.escape(label)}\}}\{{\{{[^{{}}]*\}}\{{(\d+)\}}",
        aux_text,
    )
    return int(match.group(1)) if match else None


def rendered_page_breakdown(root: Path, page_count: int | None) -> dict | None:
    """Read assembler-inserted labels to measure rendered manuscript components."""
    aux_path = root / "paper.aux"
    if page_count is None or not aux_path.is_file():
        return None
    aux_text = aux_path.read_text(encoding="utf-8", errors="replace")
    main_start = _aux_marker_page(aux_text, "tg:main-start")
    main_end = _aux_marker_page(aux_text, "tg:main-end")
    references_start = _aux_marker_page(aux_text, "tg:references-start")
    appendix_start = _aux_marker_page(aux_text, "tg:appendix-start")
    if main_start is None or main_end is None or main_end < main_start:
        return None
    references_pages = 0
    main_plus_references_pages = main_end - main_start + 1
    shared_main_reference_page = False
    if references_start is not None:
        references_end = (appendix_start - 1) if appendix_start is not None else page_count
        if references_end < references_start:
            return None
        references_pages = references_end - references_start + 1
        main_plus_references_pages = references_end - main_start + 1
        shared_main_reference_page = references_start <= main_end
    appendix_pages = 0
    if appendix_start is not None:
        if appendix_start > page_count:
            return None
        appendix_pages = page_count - appendix_start + 1
    return {
        "main_pages": main_end - main_start + 1,
        "reference_pages": references_pages,
        "main_plus_reference_pages": main_plus_references_pages,
        "appendix_pages": appendix_pages,
        "total_pages": page_count,
        "shared_main_reference_page": shared_main_reference_page,
        "markers": {
            "main_start": main_start,
            "main_end": main_end,
            "references_start": references_start,
            "appendix_start": appendix_start,
        },
    }


def evaluate_page_budget(length_plan: dict, page_count: int | None, breakdown: dict | None):
    findings = []
    if page_count is None:
        return "unavailable", [{"code": "page_count_unavailable", "component": "total"}]

    def check_range(component: str, actual: float, minimum: float | None, maximum: float | None):
        if minimum is not None and actual < minimum:
            findings.append({
                "code": "below_planned_minimum", "component": component,
                "actual": actual, "required": minimum,
            })
        if maximum is not None and actual > maximum:
            findings.append({
                "code": "above_planned_maximum", "component": component,
                "actual": actual, "required": maximum,
            })

    check_range(
        "total", page_count,
        length_plan.get("minimum_total_pages"), length_plan.get("maximum_total_pages"),
    )
    component_contract = length_plan.get("page_limit_scope") in manuscript_workflow.PAGE_LIMIT_SCOPES
    if component_contract:
        if breakdown is None:
            findings.append({"code": "component_boundaries_unavailable", "component": "manuscript"})
        else:
            check_range(
                "main", breakdown["main_pages"],
                length_plan.get("minimum_main_pages"), length_plan.get("maximum_main_pages"),
            )
            check_range(
                "appendix", breakdown["appendix_pages"],
                length_plan.get("minimum_appendix_pages"), None,
            )
            check_range(
                "references", breakdown["reference_pages"],
                None, length_plan.get("maximum_reference_pages"),
            )
            hard_limit = length_plan.get("hard_page_limit")
            scope = length_plan.get("page_limit_scope")
            if hard_limit is not None:
                scoped_pages = {
                    "main_text": breakdown["main_pages"],
                    "main_plus_references": breakdown.get(
                        "main_plus_reference_pages",
                        breakdown["main_pages"] + breakdown["reference_pages"],
                    ),
                    "total_manuscript": breakdown["total_pages"],
                }.get(scope)
                if scoped_pages is not None and scoped_pages > hard_limit:
                    findings.append({
                        "code": "venue_page_limit_exceeded", "component": scope,
                        "actual": scoped_pages, "required": hard_limit,
                    })
    if not findings:
        return "within_budget", []
    if any(item["code"] == "component_boundaries_unavailable" for item in findings):
        return "unavailable", findings
    if any(item["code"] in {"above_planned_maximum", "venue_page_limit_exceeded"} for item in findings):
        return "over_budget", findings
    return "under_budget", findings


def command_compile(args):
    root = paper_dir(args.workspace, args.run)
    if not (root / "paper.tex").is_file():
        raise ValueError("paper.tex does not exist; assemble it first")
    engine = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if not 1 <= args.timeout <= 900:
        raise ValueError("timeout must be between 1 and 900 seconds")
    lint_source = (root / "paper.tex").read_text(encoding="utf-8")
    for relative in re.findall(r"\\input\{([^}]+)\}", lint_source):
        input_path = contained(root, relative if Path(relative).suffix else f"{relative}.tex")
        if input_path.is_file():
            lint_source += "\n" + input_path.read_text(encoding="utf-8")
    source_findings = latex_source_findings(lint_source)
    warnings = [item["message"] for item in source_findings if item["severity"] == "error"]
    log_parts = []
    built = False
    if not engine:
        warnings.append("pdflatex is unavailable")
    else:
        passes = 0
        for pass_index in range(3):
            result = subprocess.run([engine, "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                                    cwd=root, capture_output=True, text=True, timeout=args.timeout)
            passes += 1
            log_parts.append(result.stdout + "\n" + result.stderr)
            if result.returncode:
                warnings.append(result.stdout[-4000:] or result.stderr[-4000:])
                break
            if pass_index == 0 and (root / "references.bib").is_file() and (root / "references.bib").stat().st_size:
                if not bibtex:
                    warnings.append("bibtex is unavailable")
                    break
                bibliography = subprocess.run(
                    [bibtex, "paper"], cwd=root, capture_output=True, text=True, timeout=args.timeout,
                )
                log_parts.append(bibliography.stdout + "\n" + bibliography.stderr)
                if bibliography.returncode:
                    warnings.append(bibliography.stdout[-4000:] or bibliography.stderr[-4000:])
                    break
        built = (root / "paper.pdf").is_file() and not warnings
    full_log = "\n\n".join(log_parts)
    log_path = root / "build" / f"compile-{utc_now().replace(':', '-')}.log"
    atomic_write_text(log_path, full_log)
    for pattern, message in (
        (r"undefined references", "undefined references"),
        (r"undefined citations", "undefined citations"),
        (r"Overfull \\hbox", "overfull box"),
    ):
        if re.search(pattern, full_log, re.IGNORECASE) and message not in warnings:
            warnings.append(message)
    built = (root / "paper.pdf").is_file() and not warnings
    page_matches = re.findall(r"Output written on .*?\((\d+)\s+pages?[,)]", full_log)
    page_count = int(page_matches[-1]) if page_matches else None
    page_budget_status = None
    page_budget_findings = []
    page_breakdown = rendered_page_breakdown(root, page_count) if built else None
    architecture_path = root / "content_architecture.json"
    if architecture_path.is_file() and read_json(architecture_path).get("schema_version") == 3:
        length_plan = read_json(architecture_path)["length_plan"]
        page_budget_status, page_budget_findings = evaluate_page_budget(
            length_plan, page_count, page_breakdown
        )
    report = {"schema_version": 2, "artifact": "manuscript_compile_report",
              "compiled_at": utc_now(), "tex_path": "paper.tex",
              "tex_sha256": file_sha256(root / "paper.tex"), "pdf_built": built,
              "pdf_path": "paper.pdf" if built else None,
              "pdf_sha256": file_sha256(root / "paper.pdf") if built else None,
              "log_path": str(log_path.relative_to(root)), "log_sha256": file_sha256(log_path),
              "engine": engine, "passes": passes if engine else 0, "warnings": warnings,
              "source_lint_findings": source_findings, "page_count": page_count,
              "page_breakdown": page_breakdown,
              "page_budget_findings": page_budget_findings,
              "page_budget_status": page_budget_status}
    write_json(root / "compile_report.json", report)
    print(json.dumps(report, indent=2))


def command_review(args):
    root = paper_dir(args.workspace, args.run)
    value = load_object_argument(args.input, Path(args.workspace))
    compile_path = root / "compile_report.json"
    compile_report = read_json(compile_path)
    value = dict(value)
    value.update({
        "schema_version": 2,
        "artifact": "independent_manuscript_review",
        "reviewed_at": utc_now(),
        "compile_report_sha256": file_sha256(compile_path),
        "pdf_sha256": compile_report.get("pdf_sha256"),
    })
    manuscript_workflow.validate_review(root.parent, value)
    write_json(root / "review.json", value)
    print(json.dumps({"written": str(root / 'review.json'), "recommendation": value["recommendation"]}, indent=2))


def command_add_comment(args):
    root = paper_dir(args.workspace, args.run)
    text = args.text.strip()
    if not text:
        raise ValueError("comment text cannot be empty")
    comment_id = args.id or f"UC-{utc_now().replace(':', '').replace('-', '').replace('+00:00', 'Z')}"
    record = {
        "id": comment_id, "text": text, "edit_type": getattr(args, "edit_type", "general"), "scope": args.scope,
        "target": args.target, "priority": args.priority, "actor": args.actor,
        "status": "open", "created_at": utc_now(), "resolution_history": [],
    }
    path = manuscript_workflow.user_comments_path(root.parent)

    def append(value):
        comments = value.setdefault("comments", [])
        if any(item.get("id") == comment_id for item in comments):
            raise ValueError(f"duplicate user comment ID: {comment_id}")
        comments.append(record)
        value["schema_version"] = 1
        value["artifact"] = "user_comment_registry"
        return value

    update_json(path, append, {"comments": []})
    manuscript_workflow.reopen_for_user_feedback(root.parent, comment_id)
    print(json.dumps({"recorded": comment_id, "status": "open"}, indent=2))


def command_revision(args):
    root = paper_dir(args.workspace, args.run)
    value = dict(load_object_argument(args.input, Path(args.workspace)))
    review_path = root / "review.json"
    value.update({
        "schema_version": 2, "artifact": "manuscript_revision",
        "revised_at": utc_now(), "source_review_sha256": file_sha256(review_path),
    })
    manuscript_workflow.validate_revision(root.parent, value)
    write_json(root / "revision.json", value)
    responses = {item["comment_id"]: item for item in value["user_comment_responses"]}
    comments_path = manuscript_workflow.user_comments_path(root.parent)

    def resolve(registry):
        for comment in registry.get("comments", []):
            response = responses.get(comment.get("id"))
            if not response:
                continue
            comment["resolution_history"].append({**response, "resolved_at": utc_now()})
            comment["status"] = "addressed" if response["disposition"] == "addressed" else "open"
        return registry

    update_json(comments_path, resolve, {"schema_version": 1, "artifact": "user_comment_registry", "comments": []})
    print(json.dumps({"written": str(root / "revision.json"), "comments_considered": len(responses)}, indent=2))


def command_final_package(args):
    root = paper_dir(args.workspace, args.run)
    value = dict(load_object_argument(args.input, Path(args.workspace)))
    bound_files = []
    for item in value.get("files", []):
        if isinstance(item, str):
            path = manuscript_workflow.safe_paper_path(root.parent, item)
            if not path.is_file():
                raise ValueError(f"final package file is missing: {item}")
            bound_files.append({"path": item, "sha256": file_sha256(path)})
        else:
            bound_files.append(item)
    value["files"] = bound_files
    value.update({
        "schema_version": 2,
        "artifact": "final_paper_package",
        "packaged_at": utc_now(),
        "theory_bundle_sha256": file_sha256(root.parent / "artifacts" / "theory_bundle.json"),
    })
    manuscript_workflow.validate_final(root.parent, value)
    write_json(root / "final_package.json", value)
    print(json.dumps({
        "written": str(root / "final_package.json"),
        "ready_for_submission_check": value["ready_for_submission_check"],
        "files": len(value["files"]),
    }, indent=2))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", default=".")
    result.add_argument("--run")
    commands = result.add_subparsers(dest="command", required=True)
    section = commands.add_parser("write-section")
    section.add_argument("--name", required=True)
    section.add_argument("--title", required=True)
    section.add_argument("--input")
    section.add_argument("--content-base64")
    section.add_argument("--location", choices=("main", "appendix"), default="main")
    section.add_argument("--claims-json", default="[]")
    section.add_argument("--citations-json", default="[]")
    section.add_argument("--replace", action="store_true")
    section.add_argument("--reason")
    section.set_defaults(function=command_section)
    assemble = commands.add_parser("assemble")
    assemble.add_argument("--title", required=True)
    assemble.add_argument("--authors-json", default="[]")
    assemble.set_defaults(function=command_assemble)
    compile_parser = commands.add_parser("compile")
    compile_parser.add_argument("--timeout", type=int, default=180)
    compile_parser.set_defaults(function=command_compile)
    review = commands.add_parser("write-review")
    review.add_argument("--input", required=True)
    review.set_defaults(function=command_review)
    comment = commands.add_parser("add-user-comment")
    comment.add_argument("--text", required=True)
    comment.add_argument("--id")
    comment.add_argument("--edit-type", choices=USER_EDIT_TYPES, default="general")
    comment.add_argument("--scope", choices=("paper", "section", "claim", "figure", "citation", "formatting"), default="paper")
    comment.add_argument("--target")
    comment.add_argument("--priority", choices=("suggestion", "required", "blocking"), default="required")
    comment.add_argument("--actor", default="user")
    comment.set_defaults(function=command_add_comment)
    revision = commands.add_parser("write-revision")
    revision.add_argument("--input", required=True)
    revision.set_defaults(function=command_revision)
    final_package = commands.add_parser("write-final-package")
    final_package.add_argument("--input", required=True)
    final_package.set_defaults(function=command_final_package)
    return result


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
