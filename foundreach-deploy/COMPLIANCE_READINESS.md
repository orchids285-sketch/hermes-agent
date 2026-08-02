# Compliance readiness — what exists, what does not, what only a human can do

An auditor and an enterprise buyer ask the same question in different words: *show me.* This
maps each control to the code that implements it, and states plainly where there is nothing to
show. Overstating readiness is how a deal dies in the security review, so nothing here is
marked done unless it is.

## SOC 2 — Trust Services Criteria

| Control | Status | Evidence in the code |
|---|---|---|
| CC6.1 Logical access | 🟡 partial | `lib/security_gate.py`, Clerk auth, ego-web bearer + per-user browser profiles (`space=u_<id>`), so one customer can never reach another's session |
| CC6.6 Least privilege | 🟢 built | `services/skills.py` — a job may use only its declared tools; a CRM-hygiene run keeps 4 of 9. Overlays may restrict, **never widen** |
| CC7.2 Monitoring | 🟡 partial | `/api/audit/log` per agent step; uptime router. **No alerting on anomalies** |
| CC7.3 Incident response | 🔴 missing | No documented IR process, no on-call, no severity ladder |
| CC8.1 Change management | 🟡 partial | Every change ships via PR to `main`; 20 unit tests + a 6-case behavioural eval. **No formal approval gate on release** |
| CC5.2 Risk mitigation | 🟢 built | Approval gate **fails closed**; blast radius capped per app; automation posture refuses prohibited vendors |
| A1.2 Availability | 🔴 weak | Single Railway account, single region, no failover (see `OPERATIONS.md`) |
| C1.1 Confidentiality | 🟡 partial | Secrets in env + `credential_vault`/`keystore`. **ego-web holds live customer sessions on a volume — the highest-value asset and the weakest link** |

## GDPR

| Requirement | Status | Where |
|---|---|---|
| Right of access / portability | 🟢 built | `/api/privacy/export`, `/api/export/all` — *both were unmounted until this cycle; the endpoints existed and did not answer* |
| Right to erasure | 🟢 built | `/api/privacy/forget` |
| CCPA do-not-sell | 🟢 built | `/api/ccpa/do-not-sell`, `/delete` — also unmounted until this cycle |
| Record of processing | 🟡 partial | `agent_outcomes` is the substance of it; not yet formatted as an Article 30 register |
| Lawful basis for automated processing | 🔴 **human decision** | An agent reading a CRM **is** processing personal data. Legitimate interest must be assessed and documented — counsel, not code |
| DPA with sub-processors | 🔴 missing | Model providers, Railway, Vercel each process customer data |
| Data residency | 🔴 missing | Free OpenRouter models give no residency guarantee. An EU enterprise will refuse on this alone |

## EU AI Act

| Requirement | Status | Where |
|---|---|---|
| Traceability of automated decisions | 🟢 built | `agent_outcomes` records task, **basis**, approval, outcome; `/api/outcomes/export` is the artefact |
| Human oversight | 🟢 built | `agent_approvals` — fingerprinted, single-use, fails closed. Not advisory: the agent cannot proceed |
| Risk classification | 🔴 **human decision** | The `recruiting` skill touches employment → likely **high-risk**. Either classify and comply, or withdraw the skill |
| Transparency to affected people | 🔴 missing | Nobody is told an agent acted on their record |

## The three that no amount of code will close

1. **Counsel on third-party ToS.** `guard.mjs` encodes a posture per vendor and refuses
   prohibited ones — that is mitigation, not a legal opinion. The commercial model depends on
   an answer here, so get it early rather than after a cease-and-desist.
2. **Insurance / liability.** Blast radius is bounded specifically to make the risk priceable.
   An actual policy still has to be bought, and an underwriter will ask for the eval numbers
   and the incident history — which now exist.
3. **Certification.** SOC 2 Type II requires an observation window (6–12 months) and an
   auditor. Controls can be built today; the calendar cannot be compressed.

## Honest summary

The **governance and traceability** story is genuinely strong — approvals that fail closed,
least privilege, a compliance-grade ledger, an injection defence proven end to end. That is
unusual for a product this young and it is the right thing to lead with.

The **operational resilience** story is weak: one account, one region, one maintainer, one
model provider. Leading with the first while a buyer discovers the second is how trust is lost
in a security review. State both.
