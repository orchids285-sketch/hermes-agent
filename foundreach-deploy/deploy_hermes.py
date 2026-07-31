#!/usr/bin/env python3
"""
Deploy Hermes Agent (NousResearch) on Railway as a self-improving orchestration
brain that exposes an OpenAI-compatible API (port 8642) for the SaaS autopilot.

RUN THIS ONLY AFTER the Railway usage HARD LIMIT is raised/removed
(Settings -> Usage). While the limit is exceeded every provisioning call returns
"Usage limit exceeded". This script is idempotent-ish: it prints each step.

Required env before running:
  OPENROUTER_API_KEY   the model key Hermes uses (reuse the SaaS's OpenRouter key;
                       "no new paid keys" -> point model.default at a FREE model).

Everything else is baked in below.
"""
import json, os, subprocess, sys, time

TOKEN = "54a27d9f-f4f4-429d-bb33-c2d02e65f1be"
PROJECT = "e0b2217e-25ec-4fa6-ae2d-47cf49d54470"          # Railway project "twenty"
ENVV    = "5589c1df-c5ff-4e46-b20c-4a7d180f6b75"          # env "production"
REPO    = "orchids285-sketch/hermes-agent"                # my fork of NousResearch/hermes-agent
API_KEY = "4dbb85d07ea03929aec8e54ec4d97564a1eab3fbeddf088b421fa04daa8e748b"  # Hermes API_SERVER_KEY
CORS    = "https://foundreach-app.vercel.app"             # lock CORS to the SaaS (not '*')

def gql(q, variables=None):
    body = {"query": q}
    if variables: body["variables"] = variables
    open("_q.json", "w").write(json.dumps(body))
    out = subprocess.run(
        ["curl", "-s", "-X", "POST", "https://backboard.railway.app/graphql/v2",
         "-H", "Authorization: Bearer " + TOKEN, "-H", "Content-Type: application/json",
         "--data", "@_q.json"], capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return {"_raw": out[:300]}

def die_if_blocked(r):
    if "errors" in r and "Usage limit" in json.dumps(r["errors"]):
        print("BLOCKED: Railway usage hard limit still in place — raise it first, then re-run.")
        sys.exit(1)

ork = os.environ.get("OPENROUTER_API_KEY")
if not ork:
    print("Set OPENROUTER_API_KEY first (the model key Hermes uses).")
    sys.exit(1)

# 1) Create the service connected to the Hermes fork ------------------------------
r = gql('''mutation($i:ServiceCreateInput!){ serviceCreate(input:$i){ id name } }''',
        {"i": {"projectId": PROJECT, "name": "hermes-agent",
               "source": {"repo": REPO}}})
die_if_blocked(r)
svc = (r.get("data") or {}).get("serviceCreate", {}).get("id")
print("service:", svc, r.get("errors", ""))
if not svc: sys.exit(1)

# 2) Env vars: enable + key-gate the OpenAI-compatible API server (security!) -----
env_vars = {
    "OPENROUTER_API_KEY": ork,
    "API_SERVER_ENABLED": "true",
    "API_SERVER_HOST": "0.0.0.0",
    "API_SERVER_KEY": API_KEY,
    "API_SERVER_CORS_ORIGINS": CORS,
    "HERMES_UID": "10000", "HERMES_GID": "10000",
    # keep the dashboard OFF the public net (June-2026 exploit was an unauth dashboard)
    "HERMES_DASHBOARD_HOST": "127.0.0.1",
}
r = gql('''mutation($i:VariableCollectionUpsertInput!){ variableCollectionUpsert(input:$i) }''',
        {"i": {"projectId": PROJECT, "environmentId": ENVV, "serviceId": svc,
               "variables": env_vars}})
die_if_blocked(r); print("env:", r.get("data") or r.get("errors"))

# 3) Persistent volume for ALL Hermes state (memory, skills, sessions, config) ---
r = gql('''mutation($i:VolumeCreateInput!){ volumeCreate(input:$i){ id } }''',
        {"i": {"projectId": PROJECT, "environmentId": ENVV, "serviceId": svc,
               "mountPath": "/opt/data"}})
die_if_blocked(r); print("volume:", r.get("data") or r.get("errors"))

# 4) Public domain targeting the API-server port (8642) --------------------------
r = gql('''mutation($i:ServiceDomainCreateInput!){ serviceDomainCreate(input:$i){ domain } }''',
        {"i": {"environmentId": ENVV, "serviceId": svc, "targetPort": 8642}})
die_if_blocked(r)
dom = (r.get("data") or {}).get("serviceDomainCreate", {}).get("domain")
print("domain:", dom, r.get("errors", ""))

# 5) Deploy latest of the fork's default branch ----------------------------------
r = gql('''mutation($s:String!,$e:String!){ serviceInstanceDeployV2(serviceId:$s, environmentId:$e) }''',
        {"s": svc, "e": ENVV})
die_if_blocked(r); print("deploy:", r.get("data") or r.get("errors"))

print("\n=== NEXT (once it builds) — VALIDATED recipe from the E2B live run ===")
print(" Hermes OpenAI-compatible API : https://%s/v1" % (dom or "<domain>"))
print(" Auth header                  : Authorization: Bearer %s" % API_KEY)
print(" Seed config (railway ssh/run):")
print("   hermes config set api_server.enabled true")
print("   hermes config set api_server.host 0.0.0.0 && hermes config set api_server.port 8642")
print("   hermes config set api_server.key %s" % API_KEY)
print("   hermes config set model.provider openrouter")
print("   hermes config set model.default nvidia/nemotron-3-super-120b-a12b:free   # VALIDATED free model")
print(" INTEGRATION = AUGMENT the existing agno autopilot (NOT replace): expose Hermes as a")
print("   memory/self-improvement capability the autopilot calls into. Needs backend access.")
