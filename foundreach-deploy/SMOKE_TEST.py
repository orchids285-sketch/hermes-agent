#!/usr/bin/env python3
"""SMOKE_TEST.py — after GO_LIVE_ALL, prove what is actually working.

A deploy that returns 200 on / proves nothing. This exercises the things built in this
workstream end to end and prints a verdict per capability, so nobody has to guess whether
the agent really has hands, a job, a memory and a gate.

    export FR_API_URL=https://<backend>
    export EGO_WEB_URL=https://<ego-web>   EGO_API_KEY=<key>
    export HERMES_API_URL=https://<hermes>/v1   HERMES_API_KEY=<key>
    python SMOKE_TEST.py

Exit code is the number of failures, so it can gate a release.
"""
import json
import os
import sys
import urllib.request

FR = (os.environ.get("FR_API_URL") or "").rstrip("/")
EGO = (os.environ.get("EGO_WEB_URL") or "").rstrip("/")
EGO_KEY = os.environ.get("EGO_API_KEY", "")
HERMES = (os.environ.get("HERMES_API_URL") or "").rstrip("/")
HERMES_KEY = os.environ.get("HERMES_API_KEY", "")

OK, FAIL, SKIP = "PASS", "FAIL", "skip"
results: list[tuple[str, str, str]] = []


def http(url, *, method="GET", body=None, headers=None, timeout=45):
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return r.status, (json.loads(raw) if raw else {})


def check(name, fn, needs=True):
    if not needs:
        results.append((SKIP, name, "not configured"))
        return
    try:
        detail = fn()
        results.append((OK, name, detail or ""))
    except Exception as e:  # noqa: BLE001
        results.append((FAIL, name, str(e)[:150]))


# ── backend: the brain ────────────────────────────────────────────────────────────
def _skills_list():
    s, j = http(f"{FR}/api/skills")
    ids = [x["id"] for x in j.get("skills", [])]
    assert s == 200 and ids, f"HTTP {s}"
    return f"{len(ids)} jobs: {', '.join(ids)}"


def _skills_route():
    s, j = http(f"{FR}/api/skills/route", method="POST",
                body={"intent": "clean the duplicate contacts in hubspot"})
    assert j.get("skill") == "crm_hygiene", f"routed to {j.get('skill')}"
    assert j.get("briefing"), "no briefing returned"
    return f"-> {j['skill']} ({len(j['briefing'])} chars of briefing, no hidden prompt)"


def _approvals():
    s, j = http(f"{FR}/api/agent-approvals?limit=1")
    assert s == 200 and j.get("ok"), f"HTTP {s}"
    return f"gate reachable ({j.get('count', 0)} pending)"


def _ccpa():
    s, j = http(f"{FR}/api/ccpa/do-not-sell")
    assert s == 200, f"HTTP {s}"
    return "mounted (was dead before)"


def _actions_catalog():
    s, j = http(f"{FR}/api/actions/catalog")
    assert s == 200, f"HTTP {s}"
    return "API-first catalog reachable"


# ── ego-web: the hands ────────────────────────────────────────────────────────────
def _ego_health():
    s, j = http(f"{EGO}/healthz")
    assert s == 200 and j.get("ok"), f"HTTP {s}"
    return f"headless={j.get('headless')}"


def _ego_assist():
    s, j = http(f"{EGO}/v1/goto", method="POST",
                headers={"Authorization": f"Bearer {EGO_KEY}"},
                body={"url": "https://app.hubspot.com/login", "space": "smoke"})
    s, j = http(f"{EGO}/v1/assist", method="POST",
                headers={"Authorization": f"Bearer {EGO_KEY}"}, body={"space": "smoke"})
    assert j.get("app") == "HubSpot", f"detected {j.get('app')}"
    assert j.get("llm"), "no model key on ego-web — the agent cannot reason"
    return f"recognised {j['app']}, {len(j.get('tasks', []))} tasks, llm={j['llm']}"


def _ego_agent():
    s, j = http(f"{EGO}/v1/goto", method="POST",
                headers={"Authorization": f"Bearer {EGO_KEY}"},
                body={"url": "https://example.com", "space": "smoke"})
    s, j = http(f"{EGO}/v1/agent", method="POST",
                headers={"Authorization": f"Bearer {EGO_KEY}"},
                body={"space": "smoke", "goal": "Report the main heading of this page.",
                      "max_steps": 3}, timeout=180)
    assert j.get("ok"), j.get("error")
    return f"status={j.get('status')} via={j.get('via', 'computer-use')} :: {str(j.get('result'))[:70]}"


def _ego_auth():
    try:
        http(f"{EGO}/v1/snapshot", method="POST", body={})
    except Exception as e:
        if "401" in str(e):
            return "unauthenticated calls rejected"
        raise
    raise AssertionError("ego-web accepted an unauthenticated API call")


# ── hermes: the director ──────────────────────────────────────────────────────────
def _hermes():
    s, j = http(f"{HERMES}/models", headers={"Authorization": f"Bearer {HERMES_KEY}"})
    assert s == 200, f"HTTP {s}"
    return f"models: {[m.get('id') for m in j.get('data', [])][:2]}"


check("backend / skills registry", _skills_list, bool(FR))
check("backend / skill routing", _skills_route, bool(FR))
check("backend / approval gate", _approvals, bool(FR))
check("backend / CCPA endpoint", _ccpa, bool(FR))
check("backend / API-first catalog", _actions_catalog, bool(FR))
check("ego-web / health", _ego_health, bool(EGO))
check("ego-web / auth enforced", _ego_auth, bool(EGO))
check("ego-web / app recognition", _ego_assist, bool(EGO and EGO_KEY))
check("ego-web / autonomous loop", _ego_agent, bool(EGO and EGO_KEY))
check("hermes / director API", _hermes, bool(HERMES))

print("\n================ SMOKE TEST ================")
for status, name, detail in results:
    print(f" {status:5} {name:32} {detail}")
fails = sum(1 for s, _, _ in results if s == FAIL)
skips = sum(1 for s, _, _ in results if s == SKIP)
print(f"\n {len(results) - fails - skips} passed, {fails} failed, {skips} skipped")
sys.exit(fails)
