from runtime.workspace import load_theorem_state, save_theorem_state, log_event
from datetime import datetime

SCHEMA = {
    "name": "save_reference",
    "description": (
        "Persist a related-work paper that was FETCHED from a URL during the literature "
        "search, so it can be cited in the manuscript. Writes to theorem_state.json under "
        "related_work. Only call for a paper you actually opened from a real URL — never "
        "from memory. This builds the citable bibliography (references.bib)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cite_key": {
                "type": "string",
                "description": "Stable BibTeX key, e.g. 'bartlett2020benign'. Lowercase "
                               "first-author surname + year + first title word. Must be unique."
            },
            "title": {"type": "string", "description": "Full paper title"},
            "authors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Author names, e.g. ['Peter L. Bartlett', 'Philip M. Long']"
            },
            "year": {"type": "string", "description": "Publication year, e.g. '2020'"},
            "venue": {
                "type": "string",
                "description": "Journal/conference, e.g. 'PNAS' or 'NeurIPS' (optional)"
            },
            "url": {
                "type": "string",
                "description": "URL or arXiv ID the paper was fetched from (required — no URL, no reference)"
            },
            "relevance": {
                "type": "string",
                "description": "One sentence: how this paper relates to our work (for the writer's context)"
            }
        },
        "required": ["cite_key", "title", "authors", "year", "url"]
    }
}


def run(cite_key, title, authors, year, url, venue="", relevance=""):
    if not url:
        return "ERROR save_reference: url is required — never save a paper without a fetched URL."

    state = load_theorem_state()
    refs = state.setdefault("related_work", [])

    # Deduplicate on cite_key AND on the actual paper: the same arXiv id / title under a
    # DIFFERENT key is still one paper (this is what prevents "one paper saved under two keys",
    # the failure that let duplicate/fabricated references into the bibliography).
    from runtime.citations import arxiv_id as _arxiv_id, norm_title as _norm_title
    entry = {
        "cite_key": cite_key,
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "url": url,
        "relevance": relevance,
        "saved_by": "literature_lead",
        "saved_at": datetime.utcnow().isoformat(),
    }
    new_aid = _arxiv_id({"url": url})
    new_title = _norm_title({"title": title})
    for i, r in enumerate(refs):
        same_key = r.get("cite_key") == cite_key
        same_paper = ((new_aid and _arxiv_id(r) == new_aid)
                      or (new_title and _norm_title(r) == new_title))
        if same_key or same_paper:
            # Keep the existing cite_key (avoid key churn in already-written text); update fields.
            entry["cite_key"] = r.get("cite_key", cite_key)
            refs[i] = entry
            save_theorem_state(state)
            log_event("save_reference", {"cite_key": entry["cite_key"], "deduped": True})
            return f"Deduped onto existing reference {entry['cite_key']}: '{title}'"

    refs.append(entry)
    save_theorem_state(state)
    log_event("save_reference", {"cite_key": cite_key, "updated": False})
    return f"Saved reference {cite_key}: '{title}' ({len(refs)} total)"
