"""lib/huginn_client.py — connect the (previously orphaned) Huginn automation organ.

You gave Huginn (HUGINN_URL) for event-driven automations, but nothing emitted to it. This
sends events into a Huginn Webhook Agent so its scenarios can react (notify, chain actions,
schedule). AUGMENT — the built-in automation_runner still runs; we just also fan out to Huginn.

Graceful: no-op unless a full webhook URL is configured (Huginn webhooks are per-agent with a
secret path — env has only HUGINN_URL, so set HUGINN_WEBHOOK_URL to activate).
    is_configured() -> bool
    emit_event(payload: dict) -> bool
"""
from __future__ import annotations
import json, os, urllib.request
from lib.logger import get_logger
log = get_logger()

_BASE = (os.environ.get("HUGINN_URL", "") or "").rstrip("/")
_WEBHOOK = os.environ.get("HUGINN_WEBHOOK_URL", "")          # full per-agent webhook URL (preferred)
_PATH = os.environ.get("HUGINN_WEBHOOK_PATH", "")            # or a path appended to HUGINN_URL
_TIMEOUT = float(os.environ.get("HUGINN_TIMEOUT", "15"))


def _target() -> str:
    return _WEBHOOK or ((_BASE + _PATH) if (_BASE and _PATH) else "")


def is_configured() -> bool:
    return bool(_target())


def emit_event(payload: dict) -> bool:
    """POST an event into Huginn for its scenarios. No-op if unconfigured/down."""
    url = _target()
    if not url:
        return False
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=_TIMEOUT).read()
        return True
    except Exception as e:  # noqa: BLE001 — automations must never break on Huginn
        log.debug("huginn emit failed: %s", str(e)[:120])
        return False
