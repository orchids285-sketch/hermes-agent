"""lib/onyx_client.py — connect the (previously orphaned) Onyx enterprise-search/RAG organ.

You gave Onyx (Danswer) for enterprise/document search + RAG, but it was never deployed/wired.
This makes it a SEARCH capability the autopilot + knowledge features can call. AUGMENT — the
existing free_web_search/knowledge_base stay; Onyx adds grounded document/RAG answers.

Graceful: [] / "" if ONYX_URL is unset or Onyx is down. API-shape tolerant (Onyx endpoints
have shifted across versions).
    is_configured() -> bool
    search(query, k=5) -> list[str]      # top document snippets
    answer(query) -> str                 # RAG answer with sources (best-effort)
"""
from __future__ import annotations
import json, os, urllib.request
from lib.logger import get_logger
log = get_logger()

_URL = (os.environ.get("ONYX_URL") or os.environ.get("DANSWER_URL", "") or "").rstrip("/")
_KEY = os.environ.get("ONYX_API_KEY") or os.environ.get("DANSWER_API_KEY", "")
_TIMEOUT = float(os.environ.get("ONYX_TIMEOUT", "45"))


def is_configured() -> bool:
    return bool(_URL)


def _post(path: str, body: dict):
    h = {"Content-Type": "application/json"}
    if _KEY:
        h["Authorization"] = "Bearer " + _KEY
    req = urllib.request.Request(_URL + path, data=json.dumps(body).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def search(query: str, k: int = 5) -> list[str]:
    if not is_configured() or not query:
        return []
    for path, body in (
        ("/api/query/document-search", {"message": query, "search_type": "semantic"}),
        ("/api/search", {"query": query, "limit": k}),
    ):
        try:
            r = _post(path, body)
            docs = r.get("top_documents") or r.get("documents") or r.get("results") or []
            out = [(d.get("blurb") or d.get("content") or d.get("text") or "").strip()
                   for d in docs if isinstance(d, dict)]
            out = [x for x in out if x]
            if out:
                return out[:k]
        except Exception as e:  # noqa: BLE001
            log.debug("onyx search failed (%s): %s", path, str(e)[:100])
            continue
    return []


def answer(query: str) -> str:
    if not is_configured() or not query:
        return ""
    for path, body in (
        ("/api/query/answer-with-quote", {"messages": [{"message": query, "role": "user"}]}),
        ("/api/chat/send-message", {"message": query}),
    ):
        try:
            r = _post(path, body)
            a = r.get("answer") or r.get("message") or (r.get("llm_answer") or "")
            if isinstance(a, str) and a.strip():
                return a.strip()
        except Exception:
            continue
    return ""
