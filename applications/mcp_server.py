# demo_mcp_server.py
from typing import List, Dict, Optional, Any
import logging
import os

import sys
from mcp.server.fastmcp import FastMCP
from ddgs import DDGS
from pathlib import Path
import requests
from google_helpers import extract_file_id, fetch_doc, flatten_paragraphs, \
    post_file_comment

# logging.basicConfig(level=logging.DEBUG)

mcp = FastMCP("demo")

GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

@mcp.tool()
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web and return a small list of results.

    Args:
        query: What to search for.
        max_results: Max number of results to return (default 5).

    Returns:
        A list of objects like:
        [{ "title": "...", "url": "...", "snippet": "..." }, ...]
    """
    results: List[Dict[str, str]] = []

    # DDGS opens and closes its own session when used as a context manager
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
            )

    return results

# @mcp.tool()
# def google_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
#     """
#     Search Google using the Custom Search JSON API.

#     Args:
#         query: The search terms to look up.
#         max_results: Maximum number of results to return (default 5).

#     Returns:
#         A list of search result objects with title, url, and snippet.
#     """
#     if not GOOGLE_CSE_ID or not GOOGLE_API_KEY:
#         raise RuntimeError("GOOGLE_CSE_ID and GOOGLE_API_KEY environment variables must be set.")

#     params = {
#         "key": GOOGLE_API_KEY,
#         "cx": GOOGLE_CSE_ID,
#         "q": query,
#         "num": max(1, min(max_results, 10)),
#     }

#     try:
#         response = requests.get(
#             "https://www.googleapis.com/customsearch/v1",
#             params=params,
#             timeout=10,
#         )
#         response.raise_for_status()
#     except requests.RequestException as exc:
#         logging.exception("Google search request failed")
#         raise RuntimeError(f"Google search request failed: {exc}") from exc

#     data: Dict[str, Any] = response.json()
#     items = data.get("items", [])

#     results: List[Dict[str, str]] = []
#     for item in items[:max_results]:
#         results.append(
#             {
#                 "title": item.get("title", ""),
#                 "url": item.get("link", ""),
#                 "snippet": item.get("snippet", ""),
#             }
#         )

#     return results


@mcp.tool()
def write_text_file(filename: str, content: str, folder: str = ".") -> str:
    """
    Write text content to a local file.

    Args:
        filename: The name of the file to create (e.g. "notes.txt").
        content: The text content to write into the file.
        folder: Optional folder path (defaults to current directory).

    Returns:
        The absolute path of the written file.
    """
    folder_path = Path(folder).expanduser().resolve()
    folder_path.mkdir(parents=True, exist_ok=True)

    file_path = folder_path / filename
    file_path.write_text(content, encoding="utf-8")

    return f"File written to {file_path}"


ALLOW_FILE_IDS = set()   # fill with allowed files or leave empty to allow all
MAX_COMMENTS_PER_FILE_PER_DAY = 5
DEDUP = set()            # swap for Redis/DB in prod

def allowed(file_id: str) -> bool:
    return not ALLOW_FILE_IDS or file_id in ALLOW_FILE_IDS

def dedupe_key(file_id: str, suggestion: str) -> str:
    import hashlib
    return hashlib.sha256(f"{file_id}|{suggestion}".encode()).hexdigest()

@mcp.tool()
def post_drive_comment(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post a Google Drive comment to a Google Doc.

    Args:
        doc_url: The full Google Docs URL (e.g. "https://docs.google.com/document/d/FILE_ID/edit").
        suggestion: The text of the comment to post.

    Returns:
        The file id of the commented doc.
    """
    doc_url: str = args["doc_url"]
    suggestion: str = args["suggestion"].strip()
    quoted: Optional[str] = (args.get("quoted") or "").strip()[:240] or None
    
    file_id = extract_file_id(doc_url)
    if not allowed(file_id):
        return {"status": "skipped", "file_id": file_id, "explanation": "File not allow-listed"}

    # idempotency
    key = args.get("correlation_id") or dedupe_key(file_id, suggestion)
    if key in DEDUP:
        return {"status": "skipped", "file_id": file_id, "explanation": "Duplicate suggestion"}
    
    # (optional) rate-limit check here
    res = post_file_comment(file_id, content=suggestion, quoted=quoted)

    DEDUP.add(key)
    return file_id

def main() -> None:
    # Run over stdio so your Python backend can spawn this as a subprocess.
    # IMPORTANT: Don't use print() in this file – stdout is reserved for MCP traffic.
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
