"""lib/letta_client.py — connect the (previously orphaned) Letta memory organ.

You gave Letta (LETTA_BASE_URL/TOKEN/MODEL/EMBEDDING) as the agent's long-term memory,
but nothing read it. This wires it in as a SEMANTIC memory layer on top of the existing
per-person facts (prospect_memory) — AUGMENT, not replace.

Public API (all graceful — if Letta is unset/down, store() is a no-op and search() returns []):
    store(text, tags=None)         -> bool   (insert a passage into shared archival memory)
    search(query, k=5)             -> list[str]

Design: one shared Letta agent ("foundreach-memory"), created on first use and cached.
Archival memory = Letta's vector store; we insert passages and semantic-search them.
Version-tolerant: tries the known endpoint shapes and swallows any error.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.request
import urllib.error
import urllib.parse
from typing import Any

from lib.logger import get_logger

log = get_logger()

_BASE = (os.environ.get("LETTA_BASE_URL", "") or "").rstrip("/")
_TOKEN = os.environ.get("LETTA_TOKEN", "")
_MODEL = os.environ.get("LETTA_MODEL", "groq/openai/gpt-oss-120b")
_EMBED = os.environ.get("LETTA_EMBEDDING", "letta/letta-free")
_AGENT_NAME = os.environ.get("LETTA_AGENT_NAME", "foundreach-memory")
_TIMEOUT = float(os.environ.get("LETTA_TIMEOUT", "20"))

_lock = threading.Lock()
_agent_id: str | None = None


def enabled() -> bool:
    return bool(_BASE)


def _req(method: str, path: str, body: dict | None = None) -> Any:
    url = _BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if _TOKEN:
        headers["Authorization"] = "Bearer " + _TOKEN
        headers["X-BARE-PASSWORD"] = "password " + _TOKEN  # Letta server password variants
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def _ensure_agent() -> str | None:
    """Get/create the shared memory agent; cache its id. None if Letta is off/unreachable."""
    global _agent_id
    if not enabled():
        return None
    if _agent_id:
        return _agent_id
    with _lock:
        if _agent_id:
            return _agent_id
        try:
            # reuse by name if it exists
            found = _req("GET", "/v1/agents/?name=" + urllib.parse.quote(_AGENT_NAME))
            items = found if isinstance(found, list) else (found.get("agents") or found.get("data") or [])
            if items:
                _agent_id = items[0].get("id")
                return _agent_id
        except Exception as e:  # noqa: BLE001
            log.debug("letta list agents failed: %s", str(e)[:120])
        try:
            created = _req("POST", "/v1/agents/", {
                "name": _AGENT_NAME,
                "model": _MODEL,
                "embedding": _EMBED,
                "memory_blocks": [{"label": "persona", "value": "Shared long-term memory for the FoundReach autopilot."}],
            })
            _agent_id = created.get("id")
            log.info("letta: created memory agent %s", _agent_id)
        except Exception as e:  # noqa: BLE001
            log.debug("letta create agent failed: %s", str(e)[:120])
    return _agent_id


def store(text: str, tags: dict[str, Any] | None = None) -> bool:
    """Insert a passage into Letta's archival memory. No-op (False) if Letta is off/down."""
    aid = _ensure_agent()
    if not aid or not text:
        return False
    payload = text if not tags else (text + " | " + json.dumps(tags))
    for path, body in (
        (f"/v1/agents/{aid}/archival-memory", {"text": payload[:4000]}),
        (f"/v1/agents/{aid}/passages", {"text": payload[:4000]}),
    ):
        try:
            _req("POST", path, body)
            return True
        except Exception:
            continue
    return False


def search(query: str, k: int = 5) -> list[str]:
    """Semantic-search Letta's archival memory. Returns [] if Letta is off/down/empty."""
    aid = _ensure_agent()
    if not aid or not query:
        return []
    import urllib.parse as _p
    q = _p.quote(query[:400])
    for path in (
        f"/v1/agents/{aid}/archival-memory?search={q}&limit={k}",
        f"/v1/agents/{aid}/passages?search={q}&limit={k}",
    ):
        try:
            res = _req("GET", path)
            rows = res if isinstance(res, list) else (res.get("passages") or res.get("data") or [])
            out = [(r.get("text") or r.get("content") or "").strip() for r in rows if isinstance(r, dict)]
            out = [x for x in out if x]
            if out:
                return out[:k]
        except Exception:
            continue
    return []
