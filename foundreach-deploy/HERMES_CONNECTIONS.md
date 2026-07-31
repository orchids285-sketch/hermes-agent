# Hermes → "branché à tous les services Railway ET l'autopilote"

Full connection manifest for the `twenty` Railway project (50 services, enumerated live
2026-07-31). Hermes doesn't need to be co-located — it connects over HTTPS. This wires it
to the whole fleet + the autopilot the moment Railway is un-frozen (paid). Hermes AUGMENTS
the autopilot; it does not replace it.

## Primary wiring (do these 3 → Hermes reaches everything)

### 1) Tool hub — the `mcp` service (gives Hermes ALL SaaS tools in one shot)
```
hermes mcp add foundreach-tools --url https://mcp-production-bc85.up.railway.app/mcp --header "Authorization: Bearer <MCP_CLIENT_KEY>"
```
The `mcp` service aggregates the SaaS toolset (per-client keys). One MCP connection =
Hermes can drive the tools the autopilot uses. (Key minted by the mcp/backend once alive.)

### 2) Main backend + autopilot — `foundrreach-app`
- Base: `https://foundrreach-app-production.up.railway.app`
- Autopilot AUGMENTATION = drop `autopilot_hermes_tool.py` into this backend, register
  `HermesBrain()` on the agno autopilot, set `HERMES_API_URL` + `HERMES_API_KEY`
  (Hermes' Railway domain + `4dbb85d0…`). The autopilot then calls Hermes for
  memory / self-improving reasoning on hard decisions.
- Spine/API for Hermes to read state: `/api/spine/*`, `/api/*`.

### 3) External SaaS apps — Composio (already keyed, hosted, NOT on Railway)
- `COMPOSIO_API_KEY` in env. Connected accounts (live probe): gmail ACTIVE (+ several
  EXPIRED: reddit, twitter, airtable, gmail). 50 toolkits available (Gmail, GitHub,
  Calendar, Notion, Sheets, Slack, Supabase, Outlook, Twitter, Drive, Docs, HubSpot, Linear…).
- Add as MCP/tools so Hermes can act on external apps under the owner's accounts
  (⚠️ gate write actions behind explicit approval — compliance).

## Direct service endpoints (optional deeper wiring)
| role | service | domain |
|---|---|---|
| CRM | twenty-server | twenty-server-production-0bed.up.railway.app |
| Tasks/PM | plane-api | plane-api-production-1e61.up.railway.app |
| Social | postiz-api | postiz-api-production-2401.up.railway.app |
| Docs | affine / wl-affine | affine-production-dae8… / wl-affine-production… |
| Search | searxng / meilisearch | searxng-production-591a… / meilisearch-production-2530… |
| Crawl | crawlee | crawlee-production-2b2a… |
| Browser | browser-worker | browser-worker-production-7f10… |
| Voice | livekit-server | livekit-server-production-a0c7… |
| Existing brain | eigent-brain | eigent-brain-production… |
| White-label proxies | wl-twenty, wl-plane, wl-postiz, wl-billix, wl-cal, wl-docs, wl-tasks, wl-avnac, wl-ansvisor | wl-*-production.up.railway.app |

(Full 50-service list saved in `railway_services.json`. Infra services — Postgres, Redis,
temporal, minio, mq, elasticsearch, *-migrator/-worker/-beat — are internal, no direct wiring.)

## Status
- ALL of the above is currently unreachable: **Railway workspace is `UNPAID` → whole fleet
  frozen (services 404).** Fire this wiring the moment the account is in good standing.
- The manifest + `deploy_hermes.py` + `autopilot_hermes_tool.py` together = deploy Hermes on
  Railway AND connect it to all services + augment the autopilot, in one pass.
