from tools.web_tools import run_web_fetch

SCHEMA = {
    "name": "web_fetch",
    "description": "Fetch and read the text content of a URL. Use after web_search.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The full URL to fetch"},
            "max_chars": {"type": "integer", "default": 12000},
        },
        "required": ["url"],
    },
}

def run(url, max_chars=12000):
    return run_web_fetch(url, max_chars)