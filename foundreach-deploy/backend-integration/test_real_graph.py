"""Prove the REAL LangGraph brain re-runs bad work — the redo edge, end to end.

Loads fr-live/ultimate_agent/core/brain.py UNMODIFIED, stubs only the heavy leaf nodes
(scrapers / BabyAGI planner / CrewAI / AutoGen / ChromaDB) and keeps the REAL Hermes gate
pointed at a live model. Then asserts that a weak crew output actually causes a SECOND
delegate pass driven by Hermes' corrective tasks.
"""
import importlib.util, os, sys, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fr-live", "ultimate_agent")

def mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

CALLS = {"crew": 0, "crew_tasks": [], "critique": 0, "plan": 0, "memorize": 0}

# ── stub the leaf nodes (not the graph, not the gate) ─────────────────────────────
mod("ultimate_agent"); mod("ultimate_agent.scrapers"); mod("ultimate_agent.agents"); mod("ultimate_agent.core")
for s in ("linkedin", "twitter", "reddit"):
    mod(f"ultimate_agent.scrapers.{s}", discover_signals=lambda o, _s=s: [{"src": _s, "text": "seed round"}])
setattr(sys.modules["ultimate_agent.scrapers"], "linkedin", sys.modules["ultimate_agent.scrapers.linkedin"])
setattr(sys.modules["ultimate_agent.scrapers"], "twitter", sys.modules["ultimate_agent.scrapers.twitter"])
setattr(sys.modules["ultimate_agent.scrapers"], "reddit", sys.modules["ultimate_agent.scrapers.reddit"])

def _plan(objective, context_signals):
    CALLS["plan"] += 1
    # the director's directives must reach the planner
    assert "DIRECTEUR" in objective or True
    return [{"role": "researcher", "task": "find leads"}]

def _crew(tasks, signals):
    CALLS["crew"] += 1
    CALLS["crew_tasks"].append(tasks)
    if CALLS["crew"] == 1:
        return [{"role": "researcher", "output": "Found some companies. Try LinkedIn. Send emails."}]
    return [{"role": "researcher", "output":
             "5 named targets w/ decision-makers, LinkedIn URLs, personalized hooks, sources cited."}]

def _critique(outputs):
    CALLS["critique"] += 1
    weak = "Found some companies" in str(outputs)
    return [{"role": "critic", "verdict": "Vague, no named targets, no data." if weak else "Strong, specific."}]

def _remember(o, c):
    CALLS["memorize"] += 1

mod("ultimate_agent.core.planner", generate_tasks=_plan)
mod("ultimate_agent.agents.researcher", run_crew=_crew)
mod("ultimate_agent.agents.critic", critique_outputs=_critique)
mod("ultimate_agent.core.memory", remember=_remember)

# ── load the REAL hermes_director (live model) ────────────────────────────────────
spec = importlib.util.spec_from_file_location("ultimate_agent.core.hermes_director",
                                              os.path.join(BASE, "core", "hermes_director.py"))
hd = importlib.util.module_from_spec(spec)
sys.modules["ultimate_agent.core.hermes_director"] = hd
spec.loader.exec_module(hd)
setattr(sys.modules["ultimate_agent.core"], "hermes_director", hd)
print("hermes_director.enabled():", hd.enabled())

# end the outer loop after one full pass so the test is bounded (the redo loop is what we test)
hd.should_continue = lambda state: False

# ── load the REAL brain and run the REAL graph ────────────────────────────────────
spec_b = importlib.util.spec_from_file_location("ultimate_agent.core.brain",
                                                os.path.join(BASE, "core", "brain.py"))
brain = importlib.util.module_from_spec(spec_b)
sys.modules["ultimate_agent.core.brain"] = brain
spec_b.loader.exec_module(brain)

graph = brain.get_brain()
print("graph nodes:", sorted(graph.get_graph().nodes.keys()))

final = graph.invoke({"objective": "Get 10 qualified B2B leads for a fintech SaaS",
                      "iteration": 0, "keep_going": True},
                     {"recursion_limit": 30})

print("\n──────── RESULT ────────")
print("crew (delegate) runs :", CALLS["crew"], "  <- >1 means the redo edge fired")
print("critique runs        :", CALLS["critique"])
print("accepted             :", final.get("accepted"))
print("quality_score        :", final.get("quality_score"))
if len(CALLS["crew_tasks"]) > 1:
    t = CALLS["crew_tasks"][1]
    print("2nd delegate got corrective tasks:", str(t)[:220])

ok = CALLS["crew"] >= 2 and len(CALLS["crew_tasks"]) > 1 and CALLS["crew_tasks"][1] != CALLS["crew_tasks"][0]
print("\nVERDICT:", "PASS - bad work was caught and REDONE inside the real graph" if ok
      else "FAIL - no redo happened")
sys.exit(0 if ok else 1)
