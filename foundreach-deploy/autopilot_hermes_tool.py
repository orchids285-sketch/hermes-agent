"""
autopilot_hermes_tool.py — drop-in AUGMENTATION of the FoundReach agno autopilot.

GOAL (user): Hermes must *improve* the existing autopilot, NOT replace it.
So this does NOT swap the autopilot's LLM. It ADDS a tool the agno autopilot can
call to tap Hermes' unique strengths — persistent cross-session MEMORY, a model of
the user, self-created SKILLS, and its self-improving reasoning loop — for the hard
decisions where "crème de la crème" quality matters. The agno autopilot stays the
orchestrator; Hermes becomes a consultable senior brain + long-term memory.

INTEGRATION (once Hermes is live on Railway):
  1. Copy this file into the backend (next to the autopilot's agno setup).
  2. Set env:  HERMES_API_URL = https://<hermes-on-railway>/v1
               HERMES_API_KEY = 4dbb85d07ea03929aec8e54ec4d97564a1eab3fbeddf088b421fa04daa8e748b
  3. Register it on the existing autopilot Agent/Team (do NOT remove its current tools/model):
         from autopilot_hermes_tool import HermesBrain
         agent = Agent(model=<UNCHANGED>, tools=[*existing_tools, HermesBrain()])
     (agno Team: append HermesBrain() to the members' / leader's tools the same way.)

Hermes is OpenAI-API compatible, so this is a plain authenticated POST — no agno
version lock-in. Falls back gracefully (returns a short note) if Hermes is down,
so it can never break an autopilot run.
"""
from __future__ import annotations
import os, json, urllib.request, urllib.error

HERMES_API_URL = os.environ.get("HERMES_API_URL", "").rstrip("/")
HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")
_TIMEOUT = float(os.environ.get("HERMES_TIMEOUT", "90"))
_MODEL = os.environ.get("HERMES_MODEL", "hermes-agent")  # Hermes routes this to its configured slug


def _call_hermes(messages: list[dict], max_tokens: int = 800) -> str:
    """Low-level authenticated call to Hermes' OpenAI-compatible endpoint."""
    if not HERMES_API_URL or not HERMES_API_KEY:
        return "[hermes not configured: set HERMES_API_URL + HERMES_API_KEY]"
    body = json.dumps({"model": _MODEL, "messages": messages,
                       "max_tokens": max_tokens, "stream": False}).encode()
    req = urllib.request.Request(
        HERMES_API_URL + "/v1/chat/completions" if not HERMES_API_URL.endswith("/v1")
        else HERMES_API_URL + "/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + HERMES_API_KEY, "Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=_TIMEOUT))
        return (r.get("choices") or [{}])[0].get("message", {}).get("content", "") or "[hermes: empty]"
    except urllib.error.HTTPError as e:
        return "[hermes http %d: %s]" % (e.code, e.read()[:160])
    except Exception as e:
        return "[hermes unavailable: %s]" % (str(e)[:160])


# ---- agno-native Toolkit (preferred) -------------------------------------------------
try:
    from agno.tools import Toolkit

    class HermesBrain(Toolkit):
        """Augments the autopilot with Hermes' memory + self-improving reasoning."""

        def __init__(self):
            super().__init__(name="hermes_brain")
            # register the callables so agno exposes them as tools
            for fn in (self.consult_hermes, self.hermes_remember, self.hermes_recall):
                try:
                    self.register(fn)
                except Exception:
                    pass

        def consult_hermes(self, task: str, context: str = "") -> str:
            """Ask Hermes (self-improving agent w/ long-term memory + a model of the user) to
            reason about a hard autopilot decision and return its best recommendation.
            Use for high-stakes / quality-critical steps to lift results to top tier.
            Args: task = what to decide/produce; context = relevant state so far."""
            return _call_hermes([
                {"role": "system", "content": "You are the senior brain augmenting an autonomous "
                 "sales/growth autopilot. Use your persistent memory and self-improvement to give the "
                 "single best, concrete recommendation. Be decisive and specific."},
                {"role": "user", "content": f"AUTOPILOT TASK:\n{task}\n\nCONTEXT:\n{context}"}])

        def hermes_remember(self, fact: str) -> str:
            """Persist a durable learning/outcome into Hermes' cross-session memory so future
            autopilot runs benefit (this is how the autopilot 'self-improves' over time)."""
            return _call_hermes([
                {"role": "user", "content": "Commit this to your long-term memory for future "
                 "autopilot decisions, then confirm in one line:\n" + fact}], max_tokens=120)

        def hermes_recall(self, query: str) -> str:
            """Retrieve relevant prior learnings/context from Hermes' memory to inform a decision."""
            return _call_hermes([
                {"role": "user", "content": "From your long-term memory, recall anything relevant to: "
                 + query + "\nReturn only the useful facts, concise."}], max_tokens=400)

except Exception:
    # ---- framework-agnostic fallback (plain callables) -------------------------------
    class HermesBrain:  # type: ignore
        """Plain-callable fallback if agno.tools.Toolkit isn't importable at load time."""
        def consult_hermes(self, task: str, context: str = "") -> str:
            return _call_hermes([{"role": "user", "content": f"{task}\n\nCONTEXT:\n{context}"}])
        def hermes_remember(self, fact: str) -> str:
            return _call_hermes([{"role": "user", "content": "Remember: " + fact}], max_tokens=120)
        def hermes_recall(self, query: str) -> str:
            return _call_hermes([{"role": "user", "content": "Recall: " + query}], max_tokens=400)


if __name__ == "__main__":
    # Smoke test against a live Hermes (set the two env vars first).
    hb = HermesBrain()
    print(hb.consult_hermes("Pick the single best next outreach action for a cold B2B lead in fintech.",
                            "Lead opened 2 emails, no reply, company just raised a seed round."))
