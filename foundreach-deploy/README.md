# FoundReach × Hermes — deploy + autopilot augmentation (100% Railway)

Hermes Agent as the **self-improving brain that AUGMENTS the FoundReach autopilot**
(memory + auto-improvement). It does NOT replace the agno autopilot — it adds tools.

- `deploy_hermes.py` — deploy Hermes on **Railway** (project `twenty`): service from this
  fork + `/opt/data` volume + API server (:8642, key-gated) + domain. Fire once the Railway
  account is in good standing. Validated free model: `nvidia/nemotron-3-super-120b-a12b:free`.
- `autopilot_hermes_tool.py` — drop-in agno `Toolkit` (`HermesBrain`): `consult_hermes`,
  `hermes_remember`, `hermes_recall`. Append `HermesBrain()` to the autopilot's tools and set
  `HERMES_API_URL` + `HERMES_API_KEY`. VALIDATED against a live OpenAI-compatible endpoint.
- `HERMES_PLAN.md` — architecture + integration notes.

Recipe proven live on an E2B microVM (install→config→gateway→public API→real inference, auth-gated).
