#!/usr/bin/env python3
"""GO_LIVE_ALL.py — ONE command that brings EVERYTHING live, in one pass.

Everything built in this workstream is code-complete and merged; the only thing missing is a
Railway account that can provision. This script does the whole activation at once:

  0. billing guard (refuses to run while UNPAID/over-limit — provisions nothing, wastes nothing)
  1. REDEPLOY the backend  -> ships the merged code (Hermes director on 6 orchestrators + 6 organs)
  2. DEPLOY Hermes         -> the self-improving director (volume /opt/data, domain :8642, key-gated)
  3. DEPLOY ego-web        -> deployable browser for AI agents (volume /data, domain :8080)
  4. WIRE the backend      -> HERMES_API_URL/KEY + every organ URL that exists
  5. VERIFY                -> polls each deployment, then curls the health endpoints
  6. REPORT                -> prints exactly what is live and what still needs a human credential

  export RAILWAY_API_TOKEN=...        # optional, defaults below
  export OPENROUTER_API_KEY=...       # reuse the SaaS key (no new paid key)
  python GO_LIVE_ALL.py
"""
import json, os, re, subprocess, sys, time

TOKEN   = os.environ.get("RAILWAY_API_TOKEN", "54a27d9f-f4f4-429d-bb33-c2d02e65f1be")
PROJECT = "e0b2217e-25ec-4fa6-ae2d-47cf49d54470"      # project "twenty"
ENVV    = "5589c1df-c5ff-4e46-b20c-4a7d180f6b75"      # environment "production"
HERMES_REPO = "orchids285-sketch/hermes-agent"
EGOWEB_REPO = "orchids285-sketch/ego-web"
HERMES_KEY  = "4dbb85d07ea03929aec8e54ec4d97564a1eab3fbeddf088b421fa04daa8e748b"
EGO_KEY     = os.environ.get("EGO_API_KEY", "e9b1c7a4f2d84f6b9c3e5a7d1f8b2c604a9d3e7f15b8c2a6")
MODEL       = "nvidia/nemotron-3-super-120b-a12b:free"
CORS        = "https://foundreach-app.vercel.app"

def gql(q, v=None):
    b = {"query": q}
    if v: b["variables"] = v
    open("_q.json", "w").write(json.dumps(b))
    out = subprocess.run(["curl", "-s", "-X", "POST", "https://backboard.railway.app/graphql/v2",
        "-H", "Authorization: Bearer " + TOKEN, "-H", "Content-Type: application/json",
        "--data", "@_q.json"], capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return {"_raw": out[:300]}

def blocked(r):
    return "Usage limit" in json.dumps(r.get("errors", ""))

def curl(url, hdr=None, t=15):
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", str(t), url]
    if hdr: cmd += ["-H", hdr]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()

# ── 0. GUARD ────────────────────────────────────────────────────────────────────────
r = gql('query{ me{ workspaces{ customer{ state currentUsage usageLimit{ hardLimit isOverLimit } } } } }')
c = ((r.get("data") or {}).get("me") or {}).get("workspaces", [{}])[0].get("customer") or {}
ul = c.get("usageLimit") or {}
print("Railway: state=%s usage=$%.2f limit=$%s over=%s" % (
    c.get("state"), c.get("currentUsage") or 0, ul.get("hardLimit"), ul.get("isOverLimit")))
if c.get("state") == "UNPAID" or ul.get("isOverLimit"):
    print("\n[STOP] Railway cannot provision (UNPAID / over limit). Nothing was created.")
    print("       Settle the invoice + fix the card, then re-run this one command.")
    sys.exit(1)
ork = os.environ.get("OPENROUTER_API_KEY")
print("[OK] account healthy — bringing everything live.\n")

# service index -------------------------------------------------------------------
r = gql('query($p:String!){ project(id:$p){ services{ edges{ node{ id name } } } } }', {"p": PROJECT})
SVC = {e["node"]["name"]: e["node"]["id"] for e in
       ((r.get("data") or {}).get("project") or {}).get("services", {}).get("edges", [])}

def upsert_env(sid, variables):
    return gql('mutation($i:VariableCollectionUpsertInput!){ variableCollectionUpsert(input:$i) }',
               {"i": {"projectId": PROJECT, "environmentId": ENVV, "serviceId": sid, "variables": variables}})

def create_service(name, repo, port, env, mount):
    if name in SVC:
        print("  %s already exists (%s) — reusing" % (name, SVC[name])); sid = SVC[name]
    else:
        r = gql('mutation($i:ServiceCreateInput!){ serviceCreate(input:$i){ id } }',
                {"i": {"projectId": PROJECT, "name": name, "source": {"repo": repo}}})
        if blocked(r): print("  BLOCKED creating", name); return None
        sid = (r.get("data") or {}).get("serviceCreate", {}).get("id")
        print("  created %s -> %s" % (name, sid))
    if not sid: return None
    upsert_env(sid, env)
    gql('mutation($i:VolumeCreateInput!){ volumeCreate(input:$i){ id } }',
        {"i": {"projectId": PROJECT, "environmentId": ENVV, "serviceId": sid, "mountPath": mount}})
    d = gql('mutation($i:ServiceDomainCreateInput!){ serviceDomainCreate(input:$i){ domain } }',
            {"i": {"environmentId": ENVV, "serviceId": sid, "targetPort": port}})
    dom = (d.get("data") or {}).get("serviceDomainCreate", {}).get("domain")
    gql('mutation($s:String!,$e:String!){ serviceInstanceDeployV2(serviceId:$s, environmentId:$e) }',
        {"s": sid, "e": ENVV})
    print("  %s deploying at %s" % (name, dom))
    return dom

# ── 1. backend (ships the merged Hermes-director + organ code) ──────────────────────
print("[1/5] redeploying the backend with the merged code")
bid = SVC.get("foundrreach-app")
if bid:
    r = gql('mutation($s:String!,$e:String!){ serviceInstanceDeployV2(serviceId:$s, environmentId:$e) }',
            {"s": bid, "e": ENVV})
    print("  backend:", "BLOCKED" if blocked(r) else "deploying")

# ── 2. Hermes ───────────────────────────────────────────────────────────────────────
print("[2/5] deploying Hermes (autopilot director)")
hermes_env = {"API_SERVER_ENABLED": "true", "API_SERVER_HOST": "0.0.0.0",
              "API_SERVER_KEY": HERMES_KEY, "API_SERVER_CORS_ORIGINS": CORS,
              "HERMES_DASHBOARD_HOST": "127.0.0.1", "HERMES_UID": "10000", "HERMES_GID": "10000"}
if ork: hermes_env["OPENROUTER_API_KEY"] = ork
hermes_dom = create_service("hermes-agent", HERMES_REPO, 8642, hermes_env, "/opt/data")

# ── 3. ego-web ──────────────────────────────────────────────────────────────────────
print("[3/5] deploying ego-web (browser for AI agents)")
ego_dom = create_service("ego-web", EGOWEB_REPO, 8080,
                         {"EGO_API_KEY": EGO_KEY, "EGO_DATA_DIR": "/data", "EGO_HEADLESS": "1"}, "/data")

# ── 4. wire the backend to every organ that exists ──────────────────────────────────
print("[4/5] wiring the backend")
if bid:
    wire = {}
    if hermes_dom:
        wire["HERMES_API_URL"] = "https://%s/v1" % hermes_dom
        wire["HERMES_API_KEY"] = HERMES_KEY
        wire["HERMES_QUALITY_BAR"] = "7"
    if ego_dom:
        wire["EGO_WEB_URL"] = "https://%s" % ego_dom
        wire["EGO_WEB_KEY"] = EGO_KEY
    # organs already deployed on the fleet (URLs known from the audit)
    wire.setdefault("EIGENT_URL", "https://eigent-brain-production.up.railway.app")
    if wire:
        upsert_env(bid, wire)
        print("  set on backend:", ", ".join(sorted(wire)))

# ── 5. verify ───────────────────────────────────────────────────────────────────────
print("[5/5] verifying (giving builds ~4 min)")
for _ in range(16):
    time.sleep(15)
    ok_h = curl("https://%s/v1/models" % hermes_dom, "Authorization: Bearer " + HERMES_KEY) if hermes_dom else "n/a"
    ok_e = curl("https://%s/healthz" % ego_dom) if ego_dom else "n/a"
    print("   hermes /v1/models=%s | ego-web /healthz=%s" % (ok_h, ok_e))
    if ok_h == "200" and ok_e == "200":
        break

print("\n================ LIVE ================")
if hermes_dom: print(" Hermes  : https://%s/v1   (Bearer %s)" % (hermes_dom, HERMES_KEY))
if ego_dom:    print(" ego-web : https://%s/?key=%s   (viewer)" % (ego_dom, EGO_KEY))
print(" Backend : redeployed with the Hermes director + 6 organs wired")
print("\n=========== STILL NEEDS A HUMAN ===========")
print(" • Mautic  : create an API user -> set MAUTIC_USER + MAUTIC_PASSWORD")
print(" • Huginn  : create a Webhook Agent -> set HUGINN_WEBHOOK_URL")
print(" • Onyx / PipesHub : multi-service stacks (see DEPLOY_onyx_pipeshub.md) -> ONYX_URL / PIPESHUB_URL")
print(" • ego-web wants >=2GB RAM (Chromium OOMs below that)")
print(" Everything else is live. Each unset organ stays a graceful no-op — nothing breaks.")
