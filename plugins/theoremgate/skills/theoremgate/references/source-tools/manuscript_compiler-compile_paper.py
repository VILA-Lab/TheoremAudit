"""
compile_paper.py
Assemble all written sections into final paper.tex using venue template.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from runtime.workspace import get_project_root, log_event, load_theorem_state


def _run_pdflatex(output_dir, has_bib):
    """Compile paper.tex to PDF if pdflatex is installed. Returns (ok, message)."""
    if shutil.which("pdflatex") is None:
        return False, "pdflatex not installed — wrote paper.tex only"
    try:
        def latex():
            subprocess.run(["pdflatex", "-interaction=nonstopmode", "paper.tex"],
                           cwd=str(output_dir), capture_output=True, timeout=180)
        latex()
        if has_bib and shutil.which("bibtex"):
            subprocess.run(["bibtex", "paper"], cwd=str(output_dir), capture_output=True, timeout=60)
            latex()
        latex()  # resolve refs/citations
        pdf = output_dir / "paper.pdf"
        if pdf.exists():
            return True, f"PDF written: {pdf}"
        return False, "pdflatex ran but no paper.pdf produced (check LaTeX errors)"
    except Exception as e:
        return False, f"pdflatex failed: {e}"


def _bib_escape(s):
    """Minimal BibTeX-field escaping."""
    return str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def _section_block(section_name, raw, title):
    """Return LaTeX for one section with EXACTLY ONE \\section header.
    Strips any \\section{...} the agent wrote (some files have it, some don't — e.g.
    introduction/related_work were headerless) and prepends the canonical title, so every
    section renders with its proper heading."""
    body = raw
    # remove any existing \section / \section* header lines (keep \label lines)
    body = re.sub(r"(?m)^[ \t]*\\section\*?\{[^}]*\}[ \t]*\n?", "", body)
    header = f"\\section{{{title}}}"
    return f"{header}\n{body.strip()}\n"


def _write_bib(references, output_dir):
    """Write references.bib from theorem_state related_work. Returns count written."""
    entries = []
    for r in references:
        key = r.get("cite_key")
        if not key:
            continue
        authors = r.get("authors") or []
        author_str = " and ".join(authors) if isinstance(authors, list) else str(authors)
        entry_type = "article" if r.get("venue") else "misc"
        fields = [
            f"  title = {{{_bib_escape(r.get('title', ''))}}}",
            f"  author = {{{_bib_escape(author_str)}}}",
            f"  year = {{{_bib_escape(r.get('year', ''))}}}",
        ]
        if r.get("venue"):
            fields.append(f"  journal = {{{_bib_escape(r.get('venue'))}}}")
        if r.get("url"):
            fields.append(f"  note = {{Available at \\url{{{r.get('url')}}}}}")
        entries.append(f"@{entry_type}{{{key},\n" + ",\n".join(fields) + "\n}")
    if not entries:
        return 0
    (output_dir / "references.bib").write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    return len(entries)


def _load_dynamic_titles(sections_dir):
    """Load agent-generated titles written by write_section's `title` param (persisted to
    sections_dir/titles.json). These take precedence over paperworld titles and the
    mechanical Title Case fallback — they are the whole point of the dynamic-title feature.
    Keys are matched case-insensitively against section_name."""
    titles_path = sections_dir / "titles.json"
    if not titles_path.exists():
        return {}
    try:
        raw = json.loads(titles_path.read_text(encoding="utf-8"))
        return {str(k).lower(): v for k, v in raw.items() if v and str(v).strip()}
    except Exception as e:
        log_event("compile_paper_warning",
                  {"issue": f"failed to read titles.json: {e}"})
        return {}


SCHEMA = {
    "name": "compile_paper",
    "description": "Assemble all written sections into final paper.tex. Call after all sections are written.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Paper title"},
            "authors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Author names"
            },
            "venue": {
                "type": "string",
                "enum": ["neurips", "iclr", "icml", "colt", "jmlr", "tmlr", "colm"]
            },
            "section_order": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of section names to include in main body"
            },
            "appendix_order": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of section names for appendix"
            }
        },
        "required": ["title", "venue", "section_order"]
    }
}


def run(title, venue, section_order, authors=None, appendix_order=None):
    project_root = get_project_root()
    sections_dir = project_root / "outputs" / "paper" / "sections"
    output_dir = project_root / "outputs" / "paper"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load venue template
    templates_root = project_root / "skills" / "paperworld" / "templates"
    template_dir = templates_root / venue
    sty_files = list(template_dir.glob("*.sty")) + list(template_dir.glob("*.cls"))

    # Fallback: if this venue ships no real style file, use the ICLR style (a clean,
    # professional Larochelle-lineage layout) instead of bare \documentclass{article}.
    # Guarantees NO venue ever renders unstyled (covers colt/jmlr and any future venue).
    fallback_meta = {}
    if not sty_files:
        iclr_dir = templates_root / "iclr"
        iclr_sty = list(iclr_dir.glob("*.sty"))
        if iclr_sty:
            template_dir = iclr_dir
            sty_files = iclr_sty
            fallback_meta = {"style_file": "iclr2026_conference.sty", "bibstyle": "iclr2026_conference"}
            log_event("compile_paper_style_fallback", {"venue": venue, "used": "iclr"})

    bst_files = list(template_dir.glob("*.bst"))
    aux_tex = [p for p in template_dir.glob("*.tex") if "conference" not in p.name and "template" not in p.name]

    # Copy style + bibliography + helper files (e.g. math_commands.tex) to output
    for f in sty_files + bst_files + aux_tex:
        shutil.copy(str(f), str(output_dir / f.name))

    # Copy registered figure images into the output dir so \includegraphics resolves. A section
    # may reference a figure by its project-relative path (e.g. outputs/figures/EC.pdf) or by bare
    # basename, and figure_path may have been stored ABSOLUTE or relative — so stage each figure at
    # EVERY location a section could reference it by.
    # (Bug fixed: an absolute figure_path made `output_dir / rel` collapse to the absolute source
    # — Python discards the left side when the right is absolute — so the figure never landed in
    # the compile-relative dir and its \includegraphics silently failed with "file not found".)
    for fig in load_theorem_state().get("figures", []):
        fig_path = fig.get("figure_path")
        if not fig_path:
            continue
        src = Path(fig_path)
        if not src.is_absolute():
            src = project_root / fig_path
        if not src.exists():
            log_event("compile_paper_warning", {"issue": f"figure not found: {fig_path}"})
            continue
        dests = set()
        try:
            dests.add(output_dir / src.relative_to(project_root))   # normalize absolute → relative
        except ValueError:
            pass
        dests.add(output_dir / "outputs" / "figures" / src.name)    # conventional location
        dests.add(output_dir / src.name)                            # bare-basename fallback
        for dest in dests:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(src), str(dest))

    # Get venue-specific preamble. The metadata file is named "<venue>_template.json"
    # (e.g. iclr_template.json); fall back to "template.json" for any that use that name.
    venue_meta = {}
    for candidate in (f"{venue}_template.json", "template.json"):
        tj = template_dir / candidate
        if tj.exists():
            with open(tj) as f:
                venue_meta = json.load(f)
            break
    # If we fell back to the ICLR style, force its style_file/bibstyle regardless of the
    # (possibly stale) venue metadata that pointed at a non-existent style.
    if fallback_meta:
        venue_meta.update(fallback_meta)

    author_str = " \\and ".join(authors) if authors else "Anonymous"

    # Build paper.tex. Only \usepackage the venue style if the .sty/.cls actually exists —
    # several venue template folders ship only metadata (no style file), and importing a
    # missing package is a fatal LaTeX error. Fall back to plain article in that case.
    lines = [f"\\documentclass{{article}}"]
    # Use the MAIN venue style named in template.json — never just the first glob result,
    # which could be a helper package (natbib.sty, fancyhdr.sty) rather than the real style.
    main_style = venue_meta.get("style_file", "")
    style_names = [f.name for f in sty_files]
    if main_style and main_style in style_names:
        lines.append(f"\\usepackage{{{main_style.replace('.sty', '').replace('.cls', '')}}}")
    elif sty_files:
        lines.append(f"\\usepackage{{{sty_files[0].name.replace('.sty', '').replace('.cls', '')}}}")
    else:
        log_event("compile_paper_warning",
                  {"venue": venue, "issue": f"no .sty/.cls in template; compiling as plain article"})
    lines += [
        "\\usepackage{amsmath,amssymb}",
        "\\usepackage{graphicx}",
        "\\usepackage{booktabs}",
        "\\usepackage{hyperref}",
        "",
        "% Theorem environments — load amsthm and declare each ONLY if the venue style"
        "% has not already provided them (e.g. jmlr2e defines theorem/proof itself).",
        "\\makeatletter",
        "\\@ifundefined{proof}{\\usepackage{amsthm}}{}",
        "\\providecommand{\\ensurethm}[2]{\\@ifundefined{#1}{\\newtheorem{#1}{#2}}{}}",
        "\\ensurethm{theorem}{Theorem}",
        "\\ensurethm{proposition}{Proposition}",
        "\\ensurethm{lemma}{Lemma}",
        "\\ensurethm{corollary}{Corollary}",
        "\\ensurethm{conjecture}{Conjecture}",
        "\\ensurethm{assumption}{Assumption}",
        "\\ensurethm{definition}{Definition}",
        "\\ensurethm{remark}{Remark}",
        "\\makeatother",
        "",
        f"\\title{{{title}}}",
        f"\\author{{{author_str}}}",
        "",
        "\\begin{document}",
        "\\maketitle",
        "",
    ]

    # Add abstract first if it exists. The section file sometimes already includes the
    # \begin{abstract} wrapper (and/or a redundant "Abstract" heading) — strip those so we
    # don't double-wrap or print "Abstract" twice.
    abstract_path = sections_dir / "abstract.tex"
    if abstract_path.exists():
        body = abstract_path.read_text(encoding="utf-8").strip()
        body = body.replace("\\begin{abstract}", "").replace("\\end{abstract}", "")
        # drop a leading "\section*{Abstract}" / "\section{Abstract}" / bare "Abstract" line
        body = re.sub(r"^\s*\\section\*?\{Abstract\}\s*", "", body)
        body = re.sub(r"^\s*Abstract\s*\n", "", body).strip()
        lines.append("\\begin{abstract}")
        lines.append(body)
        lines.append("\\end{abstract}")
        lines.append("")

    # Title precedence, highest first:
    #   1. dynamic_titles  — generated by the Compiler LLM per section, passed to
    #                        write_section(title=...) and persisted to titles.json.
    #                        This is the paper-facing title the dynamic-title feature
    #                        exists to produce; it wins whenever present.
    #   2. type_to_title   — static titles from paperworld_output.json, if PaperWorld
    #                        ran and named this section. May predate the Arbiter's final
    #                        decisions, so it only applies where no dynamic title exists.
    #   3. mechanical Title Case of the internal name — last-resort fallback only
    #      (e.g. "main_results" -> "Main Results"), used when nothing else is available.
    dynamic_titles = _load_dynamic_titles(sections_dir)

    pw_sections = load_theorem_state().get("paperworld", {}).get("sections", [])
    type_to_title = {}
    for s in pw_sections:
        for key in (s.get("section_type"), s.get("title")):
            if key:
                type_to_title.setdefault(str(key).lower().replace(" ", "_"), s.get("title"))

    def _title_for(name):
        key = name.lower()
        if key in dynamic_titles:
            return dynamic_titles[key]
        return type_to_title.get(key) or name.replace("_", " ").title()

    # Add main sections
    for section in section_order:
        if section == "abstract":
            continue
        section_path = sections_dir / f"{section}.tex"
        if section_path.exists():
            lines.append(f"% === {section.upper()} ===")
            lines.append(_section_block(section, section_path.read_text(encoding="utf-8"),
                                        _title_for(section)))
            lines.append("")

    # Add appendix — start on a fresh page so it is visually separated from the main body
    if appendix_order:
        lines.append("\\clearpage")
        lines.append("\\appendix")
        lines.append("")
        for section in appendix_order:
            section_path = sections_dir / f"{section}.tex"
            if section_path.exists():
                lines.append(f"% === APPENDIX: {section.upper()} ===")
                lines.append(_section_block(section, section_path.read_text(encoding="utf-8"),
                                            _title_for(section)))
                lines.append("")

    # Bibliography — emit references.bib from related_work and cite it (only if non-empty)
    references = load_theorem_state().get("related_work", [])
    bib_count = _write_bib(references, output_dir)
    if bib_count:
        # 'plain' needs no natbib; use it unless the venue template explicitly provides a style
        bib_style = venue_meta.get("bibstyle", "plain")
        lines.append(f"\\bibliographystyle{{{bib_style}}}")
        lines.append("\\bibliography{references}")
        lines.append("")

    # Add checklist if NeurIPS
    if venue == "neurips":
        checklist_src = template_dir / "checklist.tex"
        if checklist_src.exists():
            lines.append("% NeurIPS Checklist")
            lines.append(checklist_src.read_text(encoding="utf-8"))

    lines.append("\\end{document}")

    # Write paper.tex
    paper_tex = output_dir / "paper.tex"
    paper_tex.write_text("\n".join(lines), encoding="utf-8")

    # Build the PDF so the user can view it directly (no Overleaf needed)
    pdf_ok, pdf_msg = _run_pdflatex(output_dir, has_bib=bool(bib_count))

    log_event("compile_paper", {
        "venue": venue,
        "sections": len(section_order),
        "title": title[:60],
        "references": bib_count,
        "pdf_built": pdf_ok,
        "dynamic_titles_used": sorted(dynamic_titles.keys()),
    })

    return (f"Paper compiled: {paper_tex} ({len(lines)} lines, "
            f"{len(section_order)} sections, {bib_count} references). {pdf_msg}")
