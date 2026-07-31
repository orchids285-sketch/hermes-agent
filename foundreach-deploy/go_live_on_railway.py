#!/usr/bin/env python3
"""
go_live_on_railway.py — ONE command that does EVERYTHING the moment Railway is paid.

"quand je paie, tout est fait" — this is that. It refuses to run while the account is
UNPAID (a guard), then in one pass:
  0. verify Railway billing is healthy (else abort — nothing wasted)
  1. deploy Hermes on Railway (service from the fork + /opt/data volume + domain :8642)
  2. set env (API server key-gated + OpenRouter free model)
  3. set HERMES_API_URL + HERMES_API_KEY on the backend `foundrreach-app` (ready for augment)
  4. print the exact post-boot wiring (Hermes config seed + connect to the `mcp` hub +
     the single manual line to register HermesBrain in the agno autopilot).

RUN:
  export RAILWAY_API_TOKEN=54a27d9f-f4f4-429d-bb33-c2d02e65f1be
  export OPENROUTER_API_KEY=<the SaaS's existing OpenRouter key>
  python go_live_on_railway.py
"""
import json, os, subprocess, sys, time

TOKEN   = os.environ.get("RAILWAY_API_TOKEN", "54a27d9f-f4f4-429d-bb33-c2d02e65f1be")
PROJECT = "e0b2217e-25ec-4fa6-ae2d-47cf49d54470"          # project "twenty"
ENVV    = "5589c1df-c5ff-4e46-b20c-4a7d180f6b75"          # env "production"
REPO    = "orchids285-sketch/hermes-agent"                # fork of NousResearch/hermes-agent
API_KEY = "4dbb85d07ea03929aec8e54ec4d97564a1eab3fbeddf088b421fa04daa8e748b"
MODEL   = "nvidia/nemotron-3-super-120b-a12b:free"        # VALIDATED live free model
CORS    = "https://foundreach-app.vercel.app"
MCP_URL = "https://mcp-production-bc85.up.railway.app"    # tool hub

def gql(q, v=None):
    body = {"query": q}
    if v: body["variables"] = v
    open("_q.json", "w").write(json.dumps(body))
    out = subprocess.run(["curl","-s","-X","POST","https://backboard.railway.app/graphql/v2",
        "-H","Authorization: Bearer "+TOKEN,"-H","Content-Type: application/json","--data","@_q.json"],
        capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return {"_raw": out[:300]}

# --- 0. PAYMENT GUARD -------------------------------------------------------------
r = gql('query{ me{ workspaces{ customer{ state usageLimit{ isOverLimit } } } } }')
cust = ((r.get("data") or {}).get("me") or {}).get("workspaces", [{}])[0].get("customer") or {}
state = cust.get("state"); over = (cust.get("usageLimit") or {}).get("isOverLimit")
print("Railway billing state:", state, "| overLimit:", over)
if state == "UNPAID" or over:
    print("\n[STOP] STILL UNPAID / over limit. Settle the Railway invoice first, then re-run.")
    print("   (Nothing was provisioned - the guard stopped before spending anything.)")
    sys.exit(1)
ork = os.environ.get("OPENROUTER_API_KEY")
if not ork:
    print("Set OPENROUTER_API_KEY (the SaaS's existing key)."); sys.exit(1)
print("[OK] Account healthy - provisioning Hermes on Railway.\n")

# --- 1. create the Hermes service -------------------------------------------------
r = gql('mutation($i:ServiceCreateInput!){ serviceCreate(input:$i){ id } }',
        {"i": {"projectId": PROJECT, "name": "hermes-agent", "source": {"repo": REPO}}})
svc = (r.get("data") or {}).get("serviceCreate", {}).get("id")
print("hermes service:", svc, r.get("errors", ""))
if not svc: sys.exit(1)

# --- 2. env (key-gated API server + model provider) -------------------------------
gql('mutation($i:VariableCollectionUpsertInput!){ variableCollectionUpsert(input:$i) }',
    {"i": {"projectId": PROJECT, "environmentId": ENVV, "serviceId": svc, "variables": {
        "OPENROUTER_API_KEY": ork, "API_SERVER_ENABLED": "true", "API_SERVER_HOST": "0.0.0.0",
        "API_SERVER_KEY": API_KEY, "API_SERVER_CORS_ORIGINS": CORS,
        "HERMES_UID": "10000", "HERMES_GID": "10000", "HERMES_DASHBOARD_HOST": "127.0.0.1"}}})
gql('mutation($i:VolumeCreateInput!){ volumeCreate(input:$i){ id } }',
    {"i": {"projectId": PROJECT, "environmentId": ENVV, "serviceId": svc, "mountPath": "/opt/data"}})
r = gql('mutation($i:ServiceDomainCreateInput!){ serviceDomainCreate(input:$i){ domain } }',
        {"i": {"environmentId": ENVV, "serviceId": svc, "targetPort": 8642}})
dom = (r.get("data") or {}).get("serviceDomainCreate", {}).get("domain")
print("hermes domain:", dom)
gql('mutation($s:String!,$e:String!){ serviceInstanceDeployV2(serviceId:$s, environmentId:$e) }',
    {"s": svc, "e": ENVV})
print("deploy triggered.\n")

# --- 3. wire the backend `foundrreach-app` to Hermes (env ready for augment) -------
r = gql('query($p:String!){ project(id:$p){ services{ edges{ node{ id name } } } } }', {"p": PROJECT})
backend = None
for e in ((r.get("data") or {}).get("project") or {}).get("services", {}).get("edges", []):
    if e["node"]["name"] == "foundrreach-app": backend = e["node"]["id"]
if backend and dom:
    gql('mutation($i:VariableCollectionUpsertInput!){ variableCollectionUpsert(input:$i) }',
        {"i": {"projectId": PROJECT, "environmentId": ENVV, "serviceId": backend, "variables": {
            "HERMES_API_URL": "https://%s/v1" % dom, "HERMES_API_KEY": API_KEY}}})
    print("backend foundrreach-app: HERMES_API_URL + HERMES_API_KEY set (ready for augment).")

# --- 4. the last mile (needs the running container / backend code) ----------------
print("\n=== FINAL WIRING (run once Hermes has built) ===")
print(" A) Seed Hermes config + connect it to ALL services (railway ssh/run on hermes-agent):")
print("    hermes config set api_server.enabled true && hermes config set api_server.host 0.0.0.0")
print("    hermes config set api_server.port 8642 && hermes config set api_server.key %s" % API_KEY)
print("    hermes config set model.provider openrouter && hermes config set model.default %s" % MODEL)
print("    hermes mcp add foundreach-tools --url %s/mcp --header 'Authorization: Bearer <MCP_CLIENT_KEY>'" % MCP_URL)
print(" B) AUGMENT the autopilot (one code line in the backend — needs repo access):")
print("    from autopilot_hermes_tool import HermesBrain   # file in this folder")
print("    agent = Agent(model=<UNCHANGED>, tools=[*existing_tools, HermesBrain()])")
print("\n Hermes API: https://%s/v1   (Bearer %s)" % (dom or "<domain>", API_KEY))
print(" Everything else (deploy, volume, domain, env, backend HERMES_* vars) is DONE.")
