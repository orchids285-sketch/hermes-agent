"""lib/mautic_client.py — connect the (previously orphaned) Mautic marketing-automation organ.

You gave Mautic (MAUTIC_API_URL) as the nurture/drip backend, but nothing called it. This
wires it in: when a contact is synced to the CRM we also upsert it into Mautic so it enters
the marketing-automation flows. AUGMENT — the existing cadences/sequences are untouched.

Public API (graceful — no URL/creds or Mautic down => no-op returning None/False):
    is_configured() -> bool
    upsert_contact(email, first=None, last=None, company=None, tags=None) -> contact_id|None
    add_to_segment(contact_id, segment_id) -> bool

Auth: Mautic's REST API needs Basic auth. Set MAUTIC_USER + MAUTIC_PASSWORD (env currently has
only MAUTIC_API_URL — flag: add creds to make it live). Everything degrades gracefully so a
missing credential never breaks a CRM sync.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from typing import Any

from lib.logger import get_logger

log = get_logger()

_BASE = (os.environ.get("MAUTIC_API_URL", "") or "").rstrip("/")
_USER = os.environ.get("MAUTIC_USER", "")
_PASS = os.environ.get("MAUTIC_PASSWORD", "")
_SEGMENT = os.environ.get("MAUTIC_DEFAULT_SEGMENT", "")   # optional: auto-add to this segment id
_TIMEOUT = float(os.environ.get("MAUTIC_TIMEOUT", "20"))


def is_configured() -> bool:
    """Wired only if the URL AND Basic-auth creds are present."""
    return bool(_BASE and _USER and _PASS)


def _req(method: str, path: str, body: dict | None = None) -> Any:
    req = urllib.request.Request(
        _BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json",
                 "Authorization": "Basic " + base64.b64encode(f"{_USER}:{_PASS}".encode()).decode()},
        method=method)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def upsert_contact(email: str, first: str | None = None, last: str | None = None,
                   company: str | None = None, tags: list[str] | None = None) -> str | None:
    """Create/update a Mautic contact. Returns its id, or None (no-op) if not configured/down."""
    if not is_configured() or not email:
        return None
    payload: dict[str, Any] = {"email": email}
    if first: payload["firstname"] = first
    if last: payload["lastname"] = last
    if company: payload["company"] = company
    if tags: payload["tags"] = tags
    try:
        res = _req("POST", "/api/contacts/new", payload)   # Mautic upserts by email
        cid = str(((res or {}).get("contact") or {}).get("id") or "") or None
        if cid and _SEGMENT:
            add_to_segment(cid, _SEGMENT)
        return cid
    except Exception as e:  # noqa: BLE001 — must never break the CRM sync
        log.debug("mautic upsert_contact failed: %s", str(e)[:120])
        return None


def add_to_segment(contact_id: str, segment_id: str) -> bool:
    if not is_configured() or not (contact_id and segment_id):
        return False
    try:
        _req("POST", f"/api/segments/{segment_id}/contact/{contact_id}/add")
        return True
    except Exception:
        return False
