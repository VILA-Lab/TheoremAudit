"""
Read an already-written manuscript section from outputs/paper/sections/.

This tool lets the Manuscript Compiler maintain cross-section consistency,
for example by reading the Introduction before writing Related Work.
"""

from __future__ import annotations

from runtime.workspace import get_project_root


ALLOWED = {
    "abstract",
    "introduction",
    "setting",
    "main_results",
    "empirical",
    "related_work",
    "discussion",
    "conclusion",
}


SCHEMA = {
    "name": "read_section",
    "description": (
        "Read an already-written manuscript section from outputs/paper/sections. "
        "Use this before writing dependent sections to maintain terminology, notation, "
        "scope, contribution framing, and paper voice."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "section_type": {
                "type": "string",
                "enum": sorted(ALLOWED),
                "description": (
                    "Section type to read, e.g. abstract, introduction, setting, "
                    "main_results, empirical, related_work, discussion, conclusion."
                ),
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum number of characters to return.",
                "default": 8000,
            },
        },
        "required": [],
    },
}


def run(section_type: str = "", max_chars: int = 8000):
    base = get_project_root() / "outputs" / "paper" / "sections"

    try:
        max_chars = int(max_chars)
    except Exception:
        max_chars = 8000

    max_chars = max(1000, min(max_chars, 30000))

    if not section_type:
        available = []
        if base.exists():
            available = sorted(p.stem for p in base.glob("*.tex"))

        # Useful fallback: after the abstract is written, the model may call
        # read_section({}) when it means "read the previous/available section".
        # Return abstract if present, because it is the safest cross-section context.
        abstract_path = base / "abstract.tex"
        if abstract_path.exists():
            text = abstract_path.read_text(encoding="utf-8", errors="replace")
            return {
                "ok": True,
                "section_type": "abstract",
                "path": str(abstract_path),
                "content": text[:max_chars],
                "truncated": len(text) > max_chars,
                "chars_total": len(text),
                "chars_returned": min(len(text), max_chars),
                "warning": (
                    "section_type was missing, so read_section defaulted to abstract. "
                    "Future calls should pass section_type explicitly."
                ),
                "available_sections": available,
            }

        return {
            "ok": False,
            "error": (
                "Missing required argument: section_type. "
                "Call read_section(section_type='abstract'), "
                "read_section(section_type='introduction'), or another allowed section type."
            ),
            "allowed": sorted(ALLOWED),
            "available_sections": available,
        }

    if section_type not in ALLOWED:
        return {
            "ok": False,
            "error": f"Unknown section_type: {section_type}",
            "allowed": sorted(ALLOWED),
        }

    path = base / f"{section_type}.tex"

    if not path.exists():
        available = []
        if base.exists():
            available = sorted(p.stem for p in base.glob("*.tex"))

        return {
            "ok": False,
            "section_type": section_type,
            "path": str(path),
            "error": "Section file does not exist yet.",
            "available_sections": available,
        }

    text = path.read_text(encoding="utf-8", errors="replace")

    return {
        "ok": True,
        "section_type": section_type,
        "path": str(path),
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
        "chars_total": len(text),
        "chars_returned": min(len(text), max_chars),
    }