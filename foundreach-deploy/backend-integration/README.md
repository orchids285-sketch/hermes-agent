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
