# FoundReach × Hermes — complete integration (summary)

**Goal:** deploy Hermes (self-improving agent w/ memory) and make it DIRECT the FoundReach
autopilot — every agent, for top-tier results. Status: **integration built, proven live,
hardened, and pushed.** One step remains: set 2 env vars on the running backend.

## 1. Hermes deploy (the brain)
- `deploy_hermes.py` — deploy Hermes on **Railway** (project `twenty`) from the fork, `/opt/data`
  volume, API server on :8642 (key-gated), domain. `go_live_on_railway.py` = one-shot deploy +
  wires HERMES_* onto the backend, with a billing pre-check guard.
- **Validated recipe** (proven live on an E2B microVM, reproducible): `uv venv --python 3.11`
  → `uv pip install 'hermes-agent[cli]==0.19.0' aiohttp aiohttp-cors` → `hermes config set
  api_server.* / model.provider openrouter / model.default <FREE slug>` → env `API_SERVER_KEY`
  + `API_SERVER_HOST=0.0.0.0` + `OPENROUTER_API_KEY` → `hermes gateway run`. Model:
  `nvidia/nemotron-3-super-120b-a12b:free` (deepseek/gemma free slugs were retired/rate-limited).
- Proven: external `POST /v1/chat/completions` → 200 real inference; no key → 401.

## 2. Hermes DIRECTS all 6 orchestrators (augment, never replace)
Shared module `hermes_director.py` (strategize / quality_gate / learn / should_continue).
All GRACEFUL: with `HERMES_API_URL`+`HERMES_API_KEY` unset, every hook is a no-op → behaviour
identical to before.

| # | File | How Hermes directs it | Proven live |
|---|------|-----------------------|-------------|
| 1 | `ultimate_agent/core/brain.py` | `gate` node closes the open AutoGen critique loop: reject → redo with corrective tasks (ENFORCED). Also strategy seed + cross-run learn + smart decide. | reject 3/10 → redo → **accept 8/10** → memorize → decide |
| 2 | `backend/orchestrator/supervisor.py` | `gate_agent` scores HOT leads before dispatch (advisory; `HERMES_GATE_DISPATCH=block` → broaden) | ✅ |
| 3 | `backend/orchestrator/graph.py` (+nodes,state) | `gate_messages` scores drafts before send (advisory; block → regenerate) | ✅ |
| 4 | `backend/services/mission_runner.py` | `_hermes_refine_step` in `_decide` picks a better next organ (opt-in `HERMES_DIRECT_MISSION=1`) | premature `finish` → redirected to `hunt` |
| 5 | `backend/services/agent_graph.py` | `_hermes_mission_strategy` prepends memory-informed directives to the Claude-Opus react agent's system prompt (opt-in) | concrete directives injected |
| 6 | `backend/services/autopilot_engine.py` | `_hermes_ok` verifies each GUI action before `exec` (advisory; `HERMES_GATE_ACTIONS=block` → veto) | safe click → ok; `rmtree('/home')` → **vetoed** |

## 3. Hardening (found by running it for real)
Running the REAL brain.py graph against live Hermes revealed the gate judged the ACCUMULATED
`crew_outputs` → stale weak output failed every retry → hit the cap. **Fixed** with a
non-accumulating `last_outputs`; re-verified clean convergence. Adaptive gate confirmed on real
LLM content: accepts genuinely-good (8/10), rejects weak (3/10, 6.5/10), bounded.

## 4. Activation (the one remaining step)
On the backend service set:
```
HERMES_API_URL = https://<hermes-on-railway>/v1
HERMES_API_KEY = <the API_SERVER_KEY on the Hermes service>
```
→ all 6 directors turn on at once. Optional (advisory → enforcing):
`HERMES_GATE_DISPATCH=block`, `HERMES_DIRECT_MISSION=1`, `HERMES_GATE_ACTIONS=block`.

Patched files are under `backend-integration/` (…`.patched`); copy them over the originals
(or apply the diffs) when deploying.
