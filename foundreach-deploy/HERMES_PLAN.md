# Hermes Agent → FoundReach autopilot brain — deployment + integration plan

**Goal:** run NousResearch **Hermes Agent** (MIT, self-improving, memory) on Railway
as an orchestration brain that *directs the autopilot* for best-in-class results.

## Why Hermes is the right tool (not hype — verified from the repo)
- **Closed learning loop**: curates its own memory (periodic nudges), autonomously
  creates skills after complex tasks, skills self-improve during use, FTS5 session
  search + LLM summarization for cross-session recall, Honcho dialectic user model.
- **OpenAI-compatible API server** (port **8642**) → the exact seam to make it the
  autopilot's brain with **zero backend rewrite of the reasoning core**.
- **Any model, no lock-in** (OpenRouter/Fireworks/Gemini/…) → use **free OpenRouter**
  models → respects "no new paid keys".
- **Runs anywhere**, hibernates when idle (cheap), delegates to subagents, cron.

## Deployment (Railway) — `deploy_hermes.py` (ready, DO NOT run until limit lifted)
- Service = my fork **orchids285-sketch/hermes-agent** (Railway builds its Dockerfile).
- **Volume `/opt/data`** = ALL state (config, keys, **memories, skills, sessions**) — persistence = the whole point.
- **Env**: `OPENROUTER_API_KEY` (reuse the SaaS's), `API_SERVER_ENABLED=true`,
  `API_SERVER_HOST=0.0.0.0`, `API_SERVER_KEY=4dbb85d0…` (generated), `API_SERVER_CORS_ORIGINS=<SaaS domain>`.
- **Domain → port 8642** (the OpenAI-compatible API). One-time: `hermes model` → pick a FREE model.

## Integration — "Hermes directs the autopilot"
The autopilot (agno, in the **backend** — NOT in this session) reasons via an LLM.
Point that LLM at Hermes:
```
OPENAI_BASE_URL = https://<hermes-domain>/v1
OPENAI_API_KEY  = 4dbb85d07ea03929aec8e54ec4d97564a1eab3fbeddf088b421fa04daa8e748b
model           = <whatever hermes routes> (e.g. hermes)
```
Every autopilot turn now flows through Hermes → it inherits Hermes' **memory,
self-created skills, and self-improvement**. Two wiring depths:
1. **Brain swap (minimal):** repoint the autopilot's `base_url`/`api_key` to Hermes. Fastest.
2. **Full orchestration:** give Hermes **tools/MCP** for the Railway stack (the SaaS
   `mcp` service, the backend `/api/*`, Composio) so Hermes can *act* across all
   services and drive missions, not just reason. Uses the existing MCP server
   (`mcp-production-bc85` per memory) as Hermes' tool gateway.

## SECURITY (mandatory — the docs cite a real June-2026 exploit)
Unauth API-server/dashboard on a public host → scanners drove agents to plant SSH
backdoors. So: **API_SERVER_KEY set (done)**, **CORS locked to the SaaS domain**,
**dashboard bound to 127.0.0.1** (not exposed). Never expose port 8642 without the key.

## BLOCKERS / required inputs (honest)
1. **Railway usage HARD LIMIT** — blocks ALL provisioning right now. User must raise/remove
   it (Settings → Usage). Nothing deploys until then. Hermes also *adds* usage → budget for it.
2. **OpenRouter key** for Hermes' models (reuse the SaaS's; not in this session).
3. **Backend access** for the full autopilot wiring (the autopilot code is in the backend,
   not in scratchpad). The brain-swap is 3 env vars; a deploy owner can set them.

## STATUS
- ✅ Repo forked, deploy script written, API key generated, security designed.
- ⏸️ Deploy blocked ONLY by the Railway usage limit. Fire `deploy_hermes.py` the moment it's lifted.
