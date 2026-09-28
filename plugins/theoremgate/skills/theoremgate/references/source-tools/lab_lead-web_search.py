from tools.web_tools import run_web_search

SCHEMA = {
    "name": "web_search",
    "description": "Search the web for papers, prior work, or evidence. Returns titles and URLs. Use web_fetch to read a page after searching.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
}

def run(query, max_results=5):
    return run_web_search(query, max_results)