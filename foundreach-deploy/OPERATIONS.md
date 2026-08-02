# Operations — so this survives without one person

A system only one human can operate is not an asset a buyer, an investor or an enterprise
customer will accept. This is what someone else needs to run it.

## The shape of it

```
foundreach-app (backend, FastAPI)          the brain
├─ services/skills.py        the jobs it can hold (built-ins + JSON packages + per-company overlays)
├─ services/agent_approvals.py  the gate on irreversible acts (fingerprinted, single-use, fails CLOSED)
├─ services/outcome_ledger.py   what ran, on what basis, who allowed it, did it hold up
├─ services/agent_evals.py      governance suite + behavioural score (refuses to invent numbers)
├─ services/agent_graph.py      the LangGraph tool-calling agent
├─ ultimate_agent/core/brain.py the multi-agent loop, with the Hermes quality gate
└─ lib/{ego_web,letta,onyx,pipeshub,eigent,mautic,huginn}_client.py   the organs

ego-web (browser, Node + Playwright)       the hands
├─ playbooks.mjs   13 apps / 34 tasks — procedural knowledge, not selectors
├─ agent.mjs       observe → decide → act → verify
├─ guard.mjs       injection defence, automation posture, blast radius
└─ bridge.mjs      API-first back to the backend, knowledge, audit

hermes-agent                               the director (quality gate that redoes bad work)
```

**The rule that runs through all of it:** every organ is optional. Unset its env var and it
becomes a graceful no-op — nothing breaks. That is why the platform can be deployed in pieces.

## Daily

Nothing. The autopilot runs itself. Two things are worth a glance:

```bash
curl "$FR_API_URL/api/outcomes/evals?user_id=<id>"        # governance must stay 15/15
curl "$FR_API_URL/api/agent-approvals"                    # anything waiting on a human?
```

If `self_delusion_gap` widens, the agent is completing work humans then reject — investigate
before adding features.

## After any model, prompt or playbook change

```bash
cd ego-web && EGO_LLM_KEY=... node evals/run.mjs     # must stay 6/6
cd backend && python -m pytest tests/ -q             # must stay green
```

Evaluation drift is the failure mode that kills agent deployments quietly. Skipping this is
how a working system becomes a broken one without anyone noticing.

## Deploying

See `PAYMENT_DAY.md`. One command (`GO_LIVE_ALL.py`), then `SMOKE_TEST.py` to prove it.

## When something is wrong

| symptom | first thing to check |
|---|---|
| Everything 404s at once | Railway billing state — a frozen account looks exactly like an outage |
| Agent does nothing, no error | `EGO_LLM_KEY` missing → the loop cannot reason |
| Agent works but ignores company knowledge | `FR_API_URL` unset on ego-web → the bridge home is dead |
| Irreversible actions refused unexpectedly | correct behaviour if the DB is unreachable — **the gate fails closed by design** |
| An organ silently does nothing | it is unconfigured; check its env var. This is intended, not a bug |
| `use_software` missing from the agent's tools | `EGO_WEB_URL` unset — dead organs are never offered to the model |

## Backups

State that matters, in order:

1. **Postgres** — skills overlays (`agent_skills`), approvals (`agent_approvals`), outcomes
   (`agent_outcomes`), plus the product tables. **The outcome ledger is the irreplaceable one:
   it is the compliance record and the labelled corpus. Losing it loses the moat.**
2. **ego-web `/data` volume** — task-space profiles, i.e. customers' logged-in sessions.
   Losing it means every customer logs in again. Treat as sensitive: it is credential material.
3. **Hermes `/opt/data`** — its memory and learned skills.

Git holds everything else. Nothing about the running system is un-rebuildable except (1).

## Known single points of failure

Recorded honestly, because a buyer will find them anyway:

- **One Railway account.** Frozen billing takes down the entire fleet. There is no second region.
- **One maintainer.** This document exists to reduce that; it does not remove it.
- **One model provider** (OpenRouter free tier). A price or policy change alters the unit
  economics overnight. `EGO_LLM_URL` / `EGO_LLM_MODEL` make switching a config change, which is
  the mitigation — but the dependency is real.
- **Third-party UIs.** 13 vendors redesign on their own schedule. Playbooks are procedural
  rather than selector-based to blunt this; it remains a permanent maintenance tax.
