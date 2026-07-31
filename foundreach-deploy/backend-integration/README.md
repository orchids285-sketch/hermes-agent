# Hermes DIRECTS the real agent brain (root-cause fix for "bad results")

## The real stack (NOT just agno)
`ultimate_agent/core/brain.py` = a LangGraph loop:
perceive(scrapers) → plan(**BabyAGI**) → delegate(**CrewAI**) → critique(**AutoGen**)
→ memorize(**ChromaDB**) → decide → loop. Plus the computer-use engine
(`backend/services/autopilot_engine.py` = **Agent-S + OpenInterpreter** on E2B),
`mission_runner.py`, `agent_graph.py`, and agno/dust/eigent/steel elsewhere.

## The bug (why results were mediocre)
The **AutoGen critique was computed then IGNORED** — `critique → memorize → decide`,
and `decide` always returned `keep_going=True`. Quality was measured, never enforced;
no cross-run learning. The crew shipped whatever it produced.

## The fix (Hermes as DIRECTOR — augments, doesn't replace)
- `hermes_director.py` — new module. `quality_gate()` reads outputs + critiques and
  ACCEPTS or emits concrete REDO tasks (closes the loop); `strategize()` seeds BabyAGI
  from cross-run memory; `learn()` persists outcomes to Hermes' durable memory;
  `should_continue()` replaces blind looping.
- `brain.py.patched` — adds a `gate` node: `critique → gate → {redo→delegate | ok→memorize}`,
  plus Hermes hooks in plan/memorize/decide. **Graceful**: with `HERMES_API_URL`/`HERMES_API_KEY`
  unset, every hook is a no-op and the brain behaves exactly as before.

## Apply
Copy `hermes_director.py` to `ultimate_agent/core/`, replace `ultimate_agent/core/brain.py`
with `brain.py.patched`, set `HERMES_API_URL` + `HERMES_API_KEY` (+ optional
`HERMES_QUALITY_BAR`, default 7). VALIDATED live: gate scored a weak output 2/10 and
emitted a concrete corrective task; strategize returned a real ICP + Sales-Nav filters.

## 2nd orchestrator fixed — the SUPERVISOR (continuous-agent worker, live outreach)
`backend/orchestrator/supervisor.py` runs per-ICP: scraper → evaluator → enrich →
**dispatch(SENDS outreach)** → notify → pipeline → finalize. Its `evaluator` only
gated search breadth, NOT quality → mediocre outreach could be sent.
Added `gate_agent` (Hermes) between enrich and dispatch: `enrich → gate → {refine→broaden | ok→dispatch}`.
**SAFE: advisory by default** (`HERMES_GATE_DISPATCH=advisory`) — only logs a score,
changes nothing. Set `HERMES_GATE_DISPATCH=block` (+ `HERMES_GATE_BAR`, default 6) to
route low-quality batches to one `broaden` before dispatching. Hermes off → pass-through.
Files: supervisor.py.patched + supervisor_nodes.py.patched.

## Coverage map (which orchestrators are gated)
- ✅ `ultimate_agent/core/brain.py` (research/content loop) — gate ENFORCED (redo).
- ✅ `backend/orchestrator/supervisor.py` (outreach loop) — gate ADVISORY (opt-in block).
- ▫ `backend/main.py:2903` graph, `services/mission_runner.py`, `services/agent_graph.py`,
   `services/autopilot_engine.py` (computer-use) — same `HermesBrain`/gate pattern applies;
   wire as needed once the two main loops are validated live.

## 3rd orchestrator fixed — the CAMPAIGN graph (backend/orchestrator/graph.py)
Flow: analyze_icp → plan → searches → score → generate(messages) → **send**. No gate
between generate and send → messages were sent ungated. Added `gate_messages` (Hermes):
`generate → gate → {refine→generate | ok→send}`. **SAFE: advisory by default**
(`HERMES_GATE_DISPATCH=advisory`, logs a score, changes nothing); `=block` regenerates once
on a low score. Files under `campaign/`: graph.py.patched, nodes.py.patched, state.py.patched.

## FINAL coverage — 3 core result-loops GATED
- ✅ brain (content) — enforced redo · ✅ supervisor (outreach) — advisory · ✅ campaign (outreach) — advisory
- ▫ mission_runner — already send-safe (drafts stay drafts, approval-gated, compliance_guard); add a quality hook on request
- ▫ agent_graph.py, autopilot_engine (computer-use) — secondary / different modality; wire on request
All gates: Hermes off => pass-through (zero behaviour change). Activate with HERMES_API_URL + HERMES_API_KEY.

## BUGFIX found via a LIVE real-engine run (2026-08-01)
Running the REAL brain.py graph against live Hermes revealed the `gate` judged the
ACCUMULATED `crew_outputs` (operator.add) — so a stale weak output failed every retry
→ it hit the redo cap instead of accepting good work. FIX: added a non-accumulating
`last_outputs` field; delegate sets it; the gate judges `last_outputs` (the current
attempt). Re-verified live: reject 3/10 → redo → **accept 8/10** → memorize → decide
(clean convergence, one redo). This is why you run it for real. (brain.py.patched updated.)
