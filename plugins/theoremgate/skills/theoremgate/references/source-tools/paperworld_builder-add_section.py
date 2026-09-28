from runtime.workspace import load_theorem_state, save_theorem_state, log_event

SCHEMA = {
    "name": "add_section",
    "description": "Add a section to the paper structure. Call once per section in order.",
    "input_schema": {
        "type": "object",
        "properties": {
            "section_number": {
                "type": "string",
                "description": "Section number e.g. '1', '2', 'A' for appendix"
            },
            "title": {
                "type": "string",
                "description": "Section title"
            },
            "location": {
                "type": "string",
                "enum": ["main", "appendix"],
                "description": "Main paper or appendix"
            },
            "statements_included": {
                "type": "array",
                "items": {"type": "string"},
                "description": "IDs of statements that appear in this section e.g. ['T1', 'L1']"
            },
            "description": {
                "type": "string",
                "description": "Brief description of what this section covers"
            },
            "section_type": {
                "type": "string",
                "enum": [
                    "abstract", "introduction", "setting", "main_results",
                    "empirical", "related_work", "discussion", "conclusion",
                    "proof_appendix", "extended_results", "custom"
                ],
                "description": (
                    "Canonical section type — determines which writing skill is loaded. "
                    "Use 'custom' only for unusual sections like 'Method Overview' or named algorithms. "
                    "abstract=abstract, introduction=intro, setting=setting/preliminaries, "
                    "main_results=theorems/propositions, empirical=experiments/checks, "
                    "related_work=related work, discussion=discussion/limitations, "
                    "conclusion=conclusion, proof_appendix=proof appendix, "
                    "extended_results=additional results appendix."
                )
            }
        },
        "required": ["section_number", "title", "location", "section_type"]
    }
}


def run(section_number, title, location, section_type="custom", statements_included=None, description=""):
    state = load_theorem_state()
    state.setdefault("paperworld", {}).setdefault("sections", [])

    section = {
        "number": section_number,
        "title": title,
        "location": location,
        "section_type": section_type,
        "statements_included": statements_included or [],
        "description": description,
    }
    state["paperworld"]["sections"].append(section)
    save_theorem_state(state)
    log_event("add_section", {"section": f"{section_number}. {title}", "location": location})
    return f"Section added: {section_number}. {title} ({location})"