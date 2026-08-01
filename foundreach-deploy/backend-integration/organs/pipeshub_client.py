"""lib/pipeshub_client.py — connect the (previously orphaned) PipesHub knowledge-search organ.

You gave PipesHub for workplace/knowledge search, never deployed/wired. This makes it a SEARCH
capability for the autopilot + knowledge features. AUGMENT — graceful, API-shape tolerant.
    is_configured() -> bool
    search(query, k=5) -> list[str]
"""
from __future__ import annotations
import json, os, urllib.request
from lib.logger import get_logger
log = get_logger()

_URL = (os.environ.get("PIPESHUB_URL", "") or "").rstrip("/")
_KEY = os.environ.get("PIPESHUB_API_KEY", "")
_TIMEOUT = float(os.environ.get("PIPESHUB_TIMEOUT", "45"))


def is_configured() -> bool:
    return bool(_URL)


def search(query: str, k: int = 5) -> list[str]:
    if not is_configured() or not query:
        return []
    h = {"Content-Type": "application/json"}
    if _KEY:
        h["Authorization"] = "Bearer " + _KEY
    for path, body in (
        ("/api/v1/search", {"query": query, "limit": k}),
        ("/api/search", {"q": query, "top_k": k}),
    ):
        try:
            req = urllib.request.Request(_URL + path, data=json.dumps(body).encode(), headers=h, method="POST")
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                res = json.loads(r.read() or b"{}")
            rows = res.get("results") or res.get("documents") or res.get("hits") or []
            out = [(x.get("content") or x.get("text") or x.get("snippet") or "").strip()
                   for x in rows if isinstance(x, dict)]
            out = [x for x in out if x]
            if out:
                return out[:k]
        except Exception as e:  # noqa: BLE001
            log.debug("pipeshub search failed (%s): %s", path, str(e)[:100])
            continue
    return []
