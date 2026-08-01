# Deploy + connect Onyx + PipesHub (the last 2 orphans)

Both are enterprise/knowledge SEARCH engines. Code is ALREADY wired (graceful): the autopilot
gets a `search_knowledge` tool (Onyx RAG answer + Onyx/PipesHub doc search) that appears only
once the org is configured. So: deploy → set 2 env vars → it lights up. No code change needed.

## Onyx (github.com/onyx-dot-app/onyx — ex-Danswer, MIT)
Multi-service (docker-compose): `api_server`, `web_server`, `background`, `model_server`,
`index` (Vespa), + Postgres + Redis. On Railway create those services from the repo's compose
(or use their one-click). Then set:
  ONYX_URL = https://<onyx-api>.up.railway.app
  ONYX_API_KEY = <key from Onyx admin>  (optional if auth disabled)
Client: `onyx_client.py` → `answer()` (RAG) + `search()` (semantic docs), endpoint-tolerant.

## PipesHub (github.com/pipeshub-ai/pipeshub-ai)
Multi-service: frontend + backend + Qdrant + Mongo (see their docker-compose). Deploy, then:
  PIPESHUB_URL = https://<pipeshub-backend>.up.railway.app
  PIPESHUB_API_KEY = <token>
Client: `pipeshub_client.py` → `search()`.

## Wiring (done)
- `agent_graph._tools` gains `search_knowledge` when ONYX_URL or PIPESHUB_URL is set.
- Both clients graceful: unset/down => [] / "" — the autopilot never calls a dead organ.

## Status
Deploying the full multi-service stacks needs the Railway fleet provisioning to be active; the
CODE side is complete and waiting on the 2 env vars. Same pattern as Hermes' deploy_hermes.py.
