"""lib/eigent_client.py — connect the (previously orphaned) Eigent multi-agent brain.

You deployed eigent-brain and only embedded it as an iframe; it directed nothing. This makes
it a CONSULTABLE brain the autopilot can call for hard multi-step reasoning (AUGMENT, alongside
agno/Hermes — not a replacement). Graceful: '' if Eigent is unset/down. API-shape tolerant.
    is_configured() -> bool
    consult(task, context="") -> str
"""
from __future__ import annotations
import json, os, urllib.request
from lib.logger import get_logger
log = get_logger()

_URL = (os.environ.get("EIGENT_URL") or os.environ.get("RAILWAY_SERVICE_EIGENT_BRAIN_URL", "") or "").strip()
if _URL and not _URL.startswith("http"):
    _URL = "https://" + _URL
_URL = _URL.rstrip("/")
_KEY = os.environ.get("EIGENT_API_KEY", "")
_TIMEOUT = float(os.environ.get("EIGENT_TIMEOUT", "90"))


def is_configured() -> bool:
    return bool(_URL)


def consult(task: str, context: str = "") -> str:
    """Ask Eigent's multi-agent brain to work a task; return its result text. '' if off/down."""
    if not is_configured() or not task:
        return ""
    headers = {"Content-Type": "application/json"}
    if _KEY:
        headers["Authorization"] = "Bearer " + _KEY
    body = {"task": task, "context": context, "input": task, "prompt": task}  # tolerant to API shape
    for path in ("/run", "/api/run", "/v1/run", "/task", "/solve", "/v1/chat/completions"):
        try:
            req = urllib.request.Request(_URL + path, data=json.dumps(body).encode(),
                                         headers=headers, method="POST")
            r = json.load(urllib.request.urlopen(req, timeout=_TIMEOUT))
            for k in ("result", "output", "answer", "text", "response"):
                if isinstance(r.get(k), str) and r[k].strip():
                    return r[k].strip()
            ch = r.get("choices")
            if ch and isinstance(ch, list):
                return (ch[0].get("message", {}).get("content", "") or "").strip()
        except Exception:
            continue
    return ""
