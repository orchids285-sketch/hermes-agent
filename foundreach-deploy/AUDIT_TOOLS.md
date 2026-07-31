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

## 🚩 GIVEN BUT NOT CONNECTED (this is the real gap — validates your suspicion)
| Tool | Files | Verdict |
|---|---|---|
| **Letta** | **0** | Deployed as an "ultra-employee organ" but ZERO references anywhere. Orphaned. |
| **Onyx** | **0** | ZERO references. Orphaned. |
| **PipesHub** | **0** | Deployed per notes, ZERO references. Orphaned. |
| **Eigent** (eigent-brain) | 3 (frontend only) | Shown as an **iframe embed** (`EmbedViews`, `GhostOverlay`) — its "brain" is **NOT wired to the autopilot**. It directs nothing. |
| **Frappe CRM** | **0** | Absent — **replaced by Twenty**. (You warned: "pas remplacer".) |

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
