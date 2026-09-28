"""
write_section.py
Write one paper section and save to outputs/paper/sections/
"""

import json
import re
from pathlib import Path
from runtime.workspace import get_project_root, log_event

# Matches a run of 2+ backslashes immediately followed by an ASCII letter. This is the
# over-escaped-command pattern ("\\cite", "\\ref", "\\textbf") that some models emit when
# writing LaTeX inside a JSON string field. A genuine LaTeX line break ("\\") is never
# immediately followed by a letter (it is followed by newline, space, "*", or "[len]"),
# so collapsing to a single backslash here fixes commands without breaking line breaks.
_OVERESCAPED_CMD = re.compile(r"\\{2,}(?=[A-Za-z])")

# Unambiguous machine-internal vocabulary that must NEVER reach the manuscript. These are
# system tokens (governance statuses, agent/world names, internal IDs, tool names) with no
# legitimate use in a finished paper — so we hard-block a section containing any of them and
# make the writer rewrite. We deliberately do NOT list generic English like "of the form"
# (common in real math prose): that stylistic guidance stays in the prompt to avoid false
# rejections. Matching is case-insensitive substring, except the tag/ID patterns (regex).
_LEAK_TERMS = [
    # governance statuses / decision fields
    "conjecture_only", "theorem_ready", "proposition_ready", "repair_requested",
    "blocked_by_dependency", "conditional_draft", "new_status", "new_form",
    "paper_label", "flags_addressed", "min_viable_form",
    # world / pipeline vocabulary
    "negative_result_paper", "framework_paper", "theorem_paper",
    # tool-check vocabulary
    "safe_to_use", "computed_safe_to_use", "tool_check", "write_blueprint",
    "proof obligation", "proof_obligation",
    # agent / system names
    "theoremgate", "paperworld", "attack team", "method team", "senior skeptic",
    "lab lead", "arbiter",
    # overclaim tells that are specific enough to be safe to block
    "representative form", "intended estimation",
    # internal retreat/derivation vocabulary that must not appear in a finished paper
    "minimal viable form", "min viable form",
    # derivation-process narrative — the appendix must show the clean final construction,
    # never the trial-and-error path that produced it
    "first attempt", "second attempt", "this first attempt", "corrected variant",
    "does not flip", "this fails", "we retreat", "retreat within", "retreat explicitly",
    "retreat to the",
]
# Internal ID / tag patterns (e.g. PO-3, GAP-PO3-01, CHECK-PO-4-02, CLAIM-PO5-01, LEMMA-PO2-01)
_LEAK_ID_RX = re.compile(r"\b(?:PO-\d+|(?:GAP|CHECK|CLAIM|LEMMA)-PO?-?\d+)", re.IGNORECASE)


def _find_leaks(text):
    """Return the sorted set of internal tokens/IDs that leaked into `text`."""
    low = text.lower()
    hits = {t for t in _LEAK_TERMS if t in low}
    hits.update(m.group(0) for m in _LEAK_ID_RX.finditer(text))
    return sorted(hits)


OUTPUT_DIR = get_project_root() / "outputs" / "paper" / "sections"
TITLES_PATH = OUTPUT_DIR / "titles.json"

VALID_SECTIONS = {
    "abstract", "introduction", "setting", "main_results",
    "empirical", "related_work", "discussion", "conclusion",
    "proof_appendix", "extended_results"
}

SCHEMA = {
    "name": "write_section",
    "description": "Write one paper section and save to outputs/paper/sections/. Call once per section in order.",
    "input_schema": {
        "type": "object",
        "properties": {
            "section_name": {
                "type": "string",
                "enum": sorted(VALID_SECTIONS),
                "description": "Which section to write. This is the fixed internal routing key — it must match this enum exactly and is NOT the paper-facing heading. Use `title` for the visible heading."
            },
            "title": {
                "type": "string",
                "description": (
                    "Paper-facing section heading to render in the compiled LaTeX, e.g. "
                    "'Finite-Sample Excess-Risk Decomposition' or 'A Barrier for Uniform "
                    "Stability'. Generate this from the section's actual mathematical content "
                    "— do not reuse `section_name` or a mechanical title-cased version of it. "
                    "Leave empty/omit only for sections that conventionally keep a standard "
                    "generic heading (abstract, introduction, related_work, conclusion, "
                    "proof_appendix) — the compiler falls back to a sensible default in that "
                    "case. Do NOT put a \\section{} command inside `content`; the compiler adds "
                    "the heading from this field and will strip any \\section{} it finds in "
                    "`content` regardless."
                )
            },
            "content": {
                "type": "string",
                "description": "Full LaTeX content for this section, body only — do not include a \\section{} heading here; pass the heading via `title` instead."
            },
            "location": {
                "type": "string",
                "enum": ["main", "appendix"],
                "description": "Main paper or appendix"
            },
            "statements_included": {
                "type": "array",
                "items": {"type": "string"},
                "description": "IDs of statements included e.g. ['T1', 'P1']"
            }
        },
        "required": ["section_name", "content", "location"]
    }
}


def _sanitize_latex(text):
    """Strip stray control characters (e.g. form-feed ^^L = 0x0C) that break LaTeX math,
    and repair over-escaped LaTeX commands ("\\\\cite" -> "\\cite"). Keep normal whitespace
    (tab, newline, carriage return) and genuine "\\\\" line breaks."""
    text = "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 32)
    text = _OVERESCAPED_CMD.sub(r"\\", text)
    return text


def _sanitize_title(title):
    """Escape LaTeX special characters in a free-text title so a generated heading like
    'Risk under 20% Noise & Misspecification' cannot break compilation. Mirrors the
    escaping compile_paper._bib_escape applies to bibliography fields — titles are equally
    free text and were previously unescaped."""
    if not title:
        return title
    title = title.strip()
    # Order matters: escape backslash-producing replacements last isn't needed here since
    # we don't introduce literal backslashes except via the replacements below, and none of
    # the replacement targets reappear in a later replacement's output.
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        title = title.replace(old, new)
    return title


def _strip_section_heading(content):
    """Remove any \\section{...}/\\section*{...} the model wrote into content — the
    compiler renders the heading from `title` instead, so a leftover heading in content
    would either duplicate it or (if compile_paper's own stripping regex ever changes)
    silently disagree with it."""
    return re.sub(r"(?m)^[ \t]*\\section\*?\{[^}]*\}[ \t]*\n?", "", content)


def _load_titles():
    if TITLES_PATH.exists():
        try:
            return json.loads(TITLES_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_title(section_name, title):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    titles = _load_titles()
    titles[section_name] = title
    TITLES_PATH.write_text(json.dumps(titles, indent=2), encoding="utf-8")


def run(section_name, content, location, title=None, statements_included=None):
    if not content or not content.strip():
        return f"ERROR write_section({section_name}): content is empty"

    content = _sanitize_latex(content)
    content = _strip_section_heading(content)

    # Block internal-vocabulary leaks: force a clean rewrite rather than writing a section
    # that exposes system machinery (governance statuses, agent names, internal IDs). Check
    # the title too — a leaked internal term in the heading is just as bad as one in the body.
    leaks = _find_leaks(content)
    if title:
        leaks = sorted(set(leaks) | set(_find_leaks(title)))
    if leaks:
        log_event("write_section_leak_rejected", {"section": section_name, "leaks": leaks})
        return (
            f"ERROR write_section({section_name}): the content contains internal system "
            f"vocabulary that must not appear in the paper: {leaks}. Rewrite the section in "
            f"plain mathematical prose — describe the mathematics itself, never the pipeline, "
            f"its statuses, agents, or internal identifiers."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / f"{section_name}.tex"

    try:
        filepath.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"ERROR write_section({section_name}): {e}"

    title_note = ""
    if title and title.strip():
        clean_title = _sanitize_title(title)
        try:
            _save_title(section_name, clean_title)
            title_note = f", title=\"{clean_title}\""
        except Exception as e:
            # Don't fail the whole write over a title-persistence error — the section
            # content is already saved; compile_paper will just fall back to a default
            # heading for this section.
            log_event("write_section_title_save_failed", {"section": section_name, "error": str(e)})
            title_note = " (title not saved — compile_paper will use a default heading)"

    log_event("write_section", {
        "section": section_name,
        "location": location,
        "statements": statements_included or [],
        "chars": len(content),
        "title": title or None,
    })

    return f"Section written: {section_name} ({location}, {len(content)} chars{title_note}) → {filepath}"