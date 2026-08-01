# Audit — are ALL the tools you gave actually CONNECTED? (not just agno, not replaced)

Method: counted references to each tool across the whole `fr-live` code (backend `.py`
= functionally wired; frontend `.tsx` = surfaced as an embed), then read the wiring.

## ✅ CONNECTED — backend organs / integrations (called by real backend logic)
| Tool | Files | Where |
|---|---|---|
| **Agno** (autopilot brain) | 28 | `lib/llm.py`, `lib/playbook.py`, `birch/*`, `main.py` |
| **Composio** (tool gateway) | 88 | `services/composio_live`, `integrations/composio_*`, `lib/composio_outreach` |
| **Steel** (browser) | 4 | `lib/steel_client.py`, `routers/browser_proxy` |
| **Hermes** (director) | new | 6 orchestrators (see INTEGRATION_SUMMARY) |
| Semrush, Umami, OpenPanel, Matomo, Nango, Novu, Polar, Searxng, Meilisearch, Obscura, Mirofish, Cossistant, Ballerine, Apollo, Airtable, Resend, Hunter, Twilio, Findymail… | 3–30 each | dedicated clients in `lib/` + `integrations/` |

## ✅ CONNECTED — embedded tools (surfaced as tabs/iframes in the frontend)
Twenty (CRM), Plane (tasks), Postiz (social), Docmost/AFFiNE (docs), Suna (Growth), Dub (links),
Onlook (Studio), Billix (employee), Chatwoot (support), Sim Studio, Ycode (creatives), Cal.com,
AppFlowy — all wired in `EmbedViews.tsx` / `GrowthViews.tsx` / `MiscViews.tsx` (~20 embeds, wl-* proxies).

## 🚩 GIVEN BUT NOT CONNECTED (the real gap — validates your suspicion)
DEEP method: not just ref-counts — checked whether each tool's **configured env vars are actually
READ** by code (set-but-never-read = dead config = orphan) AND whether the tool NAME appears anywhere.

| Tool | Config in env | Used in code | Verdict |
|---|---|---|---|
| **Letta** (memory organ) | `LETTA_BASE_URL`+`LETTA_TOKEN`+`LETTA_MODEL`+`LETTA_EMBEDDING` (full) | **0** | Fully configured, **never read**. Orphan. |
| **Huginn** (automation agent) | `HUGINN_URL` | **0** | Configured, **never read**. Orphan. |
| **Mautic** (marketing automation) | `MAUTIC_API_URL` | **0** | Configured, **never read**. Orphan. |
| **Onyx** (enterprise/RAG search) | — | **0** | Absent everywhere. Orphan. |
| **PipesHub** (knowledge search) | — | **0** | Absent everywhere. Orphan. |
| **Eigent** (multi-agent brain) | `RAILWAY_SERVICE_EIGENT_BRAIN_URL` | 3 (frontend iframe only) | Shown as an embed; its brain **NOT wired to the autopilot**. Directs nothing. |
| **Frappe CRM** | — | **0** | Absent — **replaced by Twenty** (you warned: "pas remplacer"). |

**(Convex is NOT an orphan — the deep pass found it used in `backend/birch/*` (5 files), i.e. it backs Birch/Billix. Corrected.)**

## Completeness (this was exhaustive, not 5-6 tools)
Cross-checked **40+ tools from memory**, **199 env keys**, and **all 50 deployed Railway services**.
Deployed services confirmed USED: ansvisor (14), creatives (15), searxng (13), crawlee (8), meilisearch (8),
obscura (6), mirofish (5), convex (5), browser-worker (5), livekit (3), temporal (2). Only **huginn=0**
among services (orphan). So the FINAL orphan set = **Letta, Huginn, Mautic, Onyx, PipesHub** (fully) +
**Eigent** (embed-only) + **Frappe** (replaced). Everything else is genuinely connected.

**CORRECTION from the deep pass:** `n8n` looked orphaned by env-var (`N8N_WEBHOOK_URL`=0 reads) but the
NAME `n8n` is in **15 files** → it IS connected (via other config). The env-var check alone gives false
positives — hence the deep verification. Thin tools (1 file: OpenSEO, SerpBear, Ballerine, Postiz, Plane,
Cal.com, AFFiNE, Landing-agent) were spot-checked = **real** env reads, not stubs. ✅

**Bottom line (at audit time):** aside from **Agno** + **Hermes**, the extra organs you gave — **Letta,
Huginn, Mautic, Onyx, PipesHub, Eigent** — were NOT connected. Frappe was swapped for Twenty.

## ✅ RESOLUTION — all 6 orphans now CONNECTED in code (see `organs/`)
| Organ | Wired into | State |
|---|---|---|
| **Letta** | `prospect_memory` (semantic long-term memory) | ✅ wired + tested; fully configured |
| **Mautic** | `twenty_direct.sync_signal` (contact → nurture) | ✅ wired + tested; add `MAUTIC_USER`/`PASSWORD` |
| **Huginn** | `automation_runner` (fired automation → event) | ✅ wired + tested; add `HUGINN_WEBHOOK_URL` |
| **Eigent** | `agent_graph` tool `consult_eigent` | ✅ wired + tested; set `EIGENT_URL`(+key) |
| **Onyx** | `agent_graph` tool `search_knowledge` (RAG) | ✅ wired + tested; **deploy** + set `ONYX_URL` |
| **PipesHub** | `agent_graph` tool `search_knowledge` | ✅ wired + tested; **deploy** + set `PIPESHUB_URL` |
All AUGMENT (never replace) + GRACEFUL (organ unset/down => no-op, host path unaffected) + syntax-checked.
Nothing lights up / breaks anything until its env is set — so it's safe to ship as-is.

**In plain terms:** besides **Agno** (and now **Hermes**), the agent organs you gave to make the
autopilot smarter — **Letta, Onyx, PipesHub, Eigent** — are NOT connected to it. They were
deployed/embedded but never wired into the reasoning/execution path. Frappe was swapped for Twenty.

> Caveat: Letta/Onyx/PipesHub were noted as "grafted onto Billix" (a separate self-hosted app,
> embedded via the `wl-billix` iframe). Billix's own code is not in this repo, so IF they live
> inside Billix they're reachable only through that embed — not through the main autopilot. Either
> way, they do not power the main autopilot.

## FIX (same pattern as Hermes)
Wire the orphaned organs into the autopilot as capabilities it calls (augment, not replace):
Letta = long-term memory store; Onyx = enterprise doc/RAG search; PipesHub = knowledge/workplace
search; Eigent = its multi-agent brain as a sub-agent. Each becomes a tool/step the agno+Hermes
autopilot can invoke — with the same graceful-degradation contract (organ down => no-op).
