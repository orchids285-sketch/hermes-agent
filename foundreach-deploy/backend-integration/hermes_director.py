"""core/hermes_director.py — Hermes as the DIRECTOR of the whole agent brain.

Why this exists (the bug it fixes):
  The LangGraph brain (core/brain.py) runs
      perceive → plan → delegate(CrewAI) → critique(AutoGen) → memorize → decide → loop
  but the AutoGen critique verdicts were computed and then IGNORED — no edge
  redid bad work, and `decide` always looped with keep_going=True. Quality was
  measured, never enforced; nothing learned across runs. => inconsistent output.

What Hermes adds (it DIRECTS every sub-agent, it does NOT replace them):
  * quality_gate()  — reads the AutoGen critiques + CrewAI outputs and DECIDES:
                       accept, or REDO with concrete corrective tasks. Closes the
                       open loop. CrewAI/AutoGen/BabyAGI keep doing their jobs;
                       Hermes just enforces the bar and redirects.
  * strategize()    — seeds `plan` (BabyAGI) with what worked in PAST runs
                       (Hermes' cross-session memory) => self-improvement.
  * learn()         — persists each run's outcome to Hermes' durable memory so
                       the next run is smarter (the missing cross-run loop).
  * should_continue()— smart stop/continue/redirect instead of blind keep_going.

Everything degrades gracefully: if Hermes is unreachable, each function returns
the SAME behaviour the brain had before (accept / no-op / keep going), so the
autopilot never hard-fails on Hermes being down. Hermes is OpenAI-API compatible,
so this is a plain authenticated POST — no framework lock-in.

Config (env):
  HERMES_API_URL   e.g. https://hermes-agent-production.up.railway.app/v1
  HERMES_API_KEY   the API_SERVER_KEY set on the Hermes service
  HERMES_MODEL     defaults to "hermes-agent" (Hermes routes it to its slug)
  HERMES_QUALITY_BAR   0-10, default 7 — redo below this
  HERMES_MAX_REDOS     default 2 — cap redo loops so it can't spin forever
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any

_URL = (os.environ.get("HERMES_API_URL", "") or "").rstrip("/")
_KEY = os.environ.get("HERMES_API_KEY", "")
_MODEL = os.environ.get("HERMES_MODEL", "hermes-agent")
_BAR = float(os.environ.get("HERMES_QUALITY_BAR", "7"))
_MAX_REDOS = int(os.environ.get("HERMES_MAX_REDOS", "2"))
_TIMEOUT = float(os.environ.get("HERMES_TIMEOUT", "90"))


def enabled() -> bool:
    """Hermes is wired only if both URL + key are present. Otherwise every
    function below is a no-op that preserves the brain's prior behaviour."""
    return bool(_URL and _KEY)


def _chat(system: str, user: str, max_tokens: int = 700,
          json_mode: bool = False) -> str:
    endpoint = _URL + ("/chat/completions" if _URL.endswith("/v1")
                       else "/v1/chat/completions")
    body: dict[str, Any] = {
        "model": _MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens, "stream": False,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        endpoint, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + _KEY,
                 "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=_TIMEOUT))
    return (r.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""


def _chat_json(system: str, user: str, max_tokens: int = 700) -> dict[str, Any]:
    try:
        txt = _chat(system, user, max_tokens, json_mode=True)
        # lax parse: grab the outermost {...}
        s, e = txt.find("{"), txt.rfind("}")
        return json.loads(txt[s:e + 1]) if s >= 0 and e > s else {}
    except Exception:
        return {}


# ── 1) strategy seed for BabyAGI's planner (cross-run self-improvement) ──────
def strategize(objective: str, signals: list[dict[str, Any]] | None = None) -> str:
    """Return extra planning guidance from Hermes' memory of past runs.
    Empty string if Hermes is off => planner behaves exactly as before."""
    if not enabled():
        return ""
    try:
        return _chat(
            "You are the director of a multi-agent growth autopilot (CrewAI workers, "
            "AutoGen critic, BabyAGI planner). Using your long-term memory of what "
            "worked and failed in PAST runs for this account, give 3-5 concrete, "
            "specific planning directives to make THIS run's output top-tier. "
            "No preamble, just the directives.",
            f"OBJECTIVE: {objective}\nSIGNALS (sample): "
            f"{json.dumps((signals or [])[:5])[:1500]}",
            max_tokens=400).strip()
    except Exception:
        return ""


# ── 2) THE quality gate — closes the open critique loop ─────────────────────
def quality_gate(crew_outputs: list[dict[str, Any]],
                 critiques: list[dict[str, Any]],
                 redo_count: int = 0) -> dict[str, Any]:
    """Decide whether the crew's work passes or must be redone.

    Returns {"accept": bool, "score": float, "reason": str,
             "redo_tasks": [ {task...}, ... ]}.
    If Hermes is off OR the redo cap is hit => accept (prior behaviour)."""
    if not enabled() or redo_count >= _MAX_REDOS:
        return {"accept": True, "score": None, "reason": "hermes-off-or-cap",
                "redo_tasks": []}
    verdict = _chat_json(
        "You are the quality director. Judge the crew's outputs against the "
        "critic's verdicts for an elite growth-agency bar. Return STRICT JSON: "
        '{"score": <0-10>, "accept": <bool>, "reason": "<short>", '
        '"redo_tasks": [{"role":"<agent>","instruction":"<precise fix>"}]}. '
        f"accept must be true only if score >= {_BAR}. If below, redo_tasks must "
        "contain concrete, corrective instructions for the crew; each instruction MUST "
        "direct the agent to OUTPUT ONLY the final corrected deliverable — no commentary, "
        "no meta-discussion, no notes-to-self, just the finished work.",
        f"CREW OUTPUTS:\n{json.dumps(crew_outputs)[:6000]}\n\n"
        f"CRITIC VERDICTS:\n{json.dumps(critiques)[:3000]}",
        max_tokens=900)
    if not verdict:
        return {"accept": True, "score": None, "reason": "hermes-parse-fail",
                "redo_tasks": []}
    score = float(verdict.get("score") or 0)
    accept = bool(verdict.get("accept")) or score >= _BAR
    return {"accept": accept, "score": score,
            "reason": (verdict.get("reason") or "")[:300],
            "redo_tasks": verdict.get("redo_tasks") or []}


# ── 3) cross-run memory (the missing self-improvement loop) ─────────────────
def learn(objective: str, crew_outputs: list[dict[str, Any]],
          critiques: list[dict[str, Any]], accepted: bool, score: float | None) -> None:
    """Persist this run's outcome to Hermes' durable memory. No-op if off."""
    if not enabled():
        return
    try:
        _chat(
            "Commit this autopilot run to your long-term memory so future runs "
            "improve: what the objective was, what the crew produced, the quality "
            "score, and the single most important lesson for next time. Reply 'ok'.",
            f"OBJECTIVE: {objective}\nSCORE: {score}\nACCEPTED: {accepted}\n"
            f"OUTPUTS: {json.dumps(crew_outputs)[:4000]}\n"
            f"CRITIQUES: {json.dumps(critiques)[:2000]}",
            max_tokens=120)
    except Exception:
        pass


# ── 4) smart decide (replace blind keep_going=True) ─────────────────────────
def should_continue(state: dict[str, Any]) -> bool:
    """Ask Hermes whether another loop is worth it. Defaults to True (prior
    behaviour) if Hermes is off or unsure — never falsely stops a run."""
    if not enabled():
        return True
    try:
        v = _chat_json(
            "You direct an autopilot loop. Given the state, decide if ANOTHER "
            'iteration will add real value. Return {"continue": <bool>, "why": "<short>"}. '
            "Prefer stopping once quality is high and marginal value is low.",
            f"ITERATION: {state.get('iteration')}\n"
            f"RECENT CRITIQUES: {json.dumps(state.get('critiques', [])[-5:])[:2000]}",
            max_tokens=120)
        return bool(v.get("continue", True))
    except Exception:
        return True
