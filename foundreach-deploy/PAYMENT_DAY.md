# Payment day — the whole sequence, in order

Everything that could be built without a live Railway account **is built, merged to `main`
and tested**. Nothing below is design work; it is execution that takes minutes.

## 1. Unblock Railway
Settle the invoice and fix the card. Nothing else provisions until `state != UNPAID`.
`GO_LIVE_ALL.py` refuses to run before that and creates nothing, so it is safe to try early.

## 2. One command
```bash
export RAILWAY_API_TOKEN=<token>
export OPENROUTER_API_KEY=<the SaaS key already in use>   # free models; no new paid dep
python foundreach-deploy/GO_LIVE_ALL.py            # add --with-knowledge for the Onyx stack
```
It does, in order:
1. billing guard (aborts cleanly if still blocked)
2. **redeploys the backend** → ships everything merged this cycle
3. **deploys Hermes** (volume `/opt/data`, domain → 8642, key-gated, dashboard on loopback)
4. **deploys ego-web** (volume `/data`, domain → 8080) **with its model key and its bridge
   home wired** — without those the browser deploys but its agent cannot think and cannot
   reach company knowledge
5. sets `HERMES_API_URL/KEY`, `EGO_WEB_URL/KEY`, `EIGENT_URL`, `ONYX_URL` on the backend
6. polls until the health endpoints answer

## 3. Prove it
```bash
export FR_API_URL=https://<backend>  EGO_WEB_URL=https://<ego-web>  EGO_API_KEY=<key>
export HERMES_API_URL=https://<hermes>/v1  HERMES_API_KEY=<key>
python foundreach-deploy/SMOKE_TEST.py    # exit code = number of failures
```
Checks the skills registry and routing, the approval gate, the CCPA endpoint that used to be
unmounted, the API-first catalog, ego-web health and auth, HubSpot recognition, a real
autonomous loop, and the Hermes API.

## 4. The three things a human still has to create
These are accounts, not code — nobody can generate them for you:

| what | why | then set |
|---|---|---|
| Mautic API user | its REST API needs Basic auth | `MAUTIC_USER`, `MAUTIC_PASSWORD` |
| Huginn Webhook Agent | Huginn webhooks are per-agent with a secret path | `HUGINN_WEBHOOK_URL` |
| Onyx admin key *(if `--with-knowledge`)* | to read its API | `ONYX_URL`, `ONYX_API_KEY` |

Every organ stays a graceful no-op until its variable exists — nothing breaks in the meantime.

## 5. Sizing
ego-web needs **≥ 2 GB RAM** (Chromium; measured — it crashes at 478 MB). The Onyx stack is
seven services and is therefore opt-in behind `--with-knowledge`, so it never appears on the
bill by accident.

---

## What is already done and waiting

| | state |
|---|---|
| Hermes directs the autopilot (quality gate that redoes bad work) | merged, proven in the real LangGraph loop |
| 6 orphaned organs connected (Letta, Mautic, Huginn, Eigent, Onyx, PipesHub) | merged, graceful |
| 3 dead routers mounted (CCPA / data export / notes) | merged |
| `scrape_resilience` revived (robots.txt, retry, login-wall) | merged, verified live |
| ego-web: 13 apps / 34 tasks, agent loop, tabs, API-first bridge, de-branded embed | pushed |
| Skills Engine: 9 jobs, least privilege, per-company learning, JSON packages | merged |
| Approval gate: fingerprinted, single-use, fails closed | merged |
| 20 regression tests | green on a clean checkout of `main` |

## The one gap that genuinely needs a live system
**Agent evaluation against real behaviour.** The deterministic half exists (routing,
governance and gate properties are covered by the 20 tests). Scoring how well the agent
*actually performs a job* requires it to run against live systems — that is the only piece
that cannot be honestly built before deployment.
