# Connecting the orphaned organs (Letta, Mautic, Huginn, Eigent)

The audit found these were given/deployed but never wired. Now connected — AUGMENT, graceful
(organ unset/down => no-op, never breaks the host path). Verified: all compile + degrade cleanly.

| Organ | Client | Wired into | Role | Config to go live |
|---|---|---|---|---|
| **Letta** | `letta_client.py` | `prospect_memory.py` (remember→store, recall_summary→search) | semantic long-term memory | already has LETTA_BASE_URL/TOKEN/MODEL/EMBEDDING ✅ |
| **Mautic** | `mautic_client.py` | `twenty_direct.sync_signal` (contact → nurture) | marketing automation | add `MAUTIC_USER`+`MAUTIC_PASSWORD` (only URL is set) |
| **Huginn** | `huginn_client.py` | `automation_runner.run_once` (fired automation → event) | event automations | add `HUGINN_WEBHOOK_URL` (only HUGINN_URL is set) |
| **Eigent** | `eigent_client.py` | `agent_graph._tools` (consult_eigent tool, only when configured) | multi-agent brain | set `EIGENT_URL`(+`EIGENT_API_KEY`); RAILWAY_SERVICE_EIGENT_BRAIN_URL present |

Onyx + PipesHub have NO config/URL anywhere → they must be (re)deployed first, then wired the same way.
