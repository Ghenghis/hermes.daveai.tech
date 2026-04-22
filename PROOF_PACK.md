# Deployment Proof Pack

**Project:** Contract Kit v17  
**State:** Implementation-complete, deployment-pending  
**Source tests:** 409/409 passing  
**Coding remaining:** 0  
**Authority doc:** STATUS.md  

Fill each section with real operational evidence as you close each blocker.  
Do not edit STATUS.md again until all five are checked.

---

## B1 — WebUI Live

**Command:**
```bash
bash deploy/deploy.sh
systemctl status kilocode-webui
curl -s http://localhost:7860/health | python3 -m json.tool
```

**Evidence to paste here:**
```
# systemctl status output:
[paste here]

# curl /health response:
[paste here]
```

**Closed:** ☐  

---

## B2 — VSIX / KiloCode Live

**Commands:**
```bash
# Local — build VSIX
npm install
npx vsce package

# Install in VS Code
code --install-extension kilocode-*.vsix

# Verify extension connects to live runtime
curl -s http://187.77.30.206:8080/health | python3 -m json.tool
```

**Evidence to paste here:**
```
# VSIX build output (last line):
[paste here]

# Runtime /health from VS Code machine:
[paste here]

# Extension logs showing successful connection:
[paste here]
```

**Closed:** ☐  

---

## B3 — Hermes ↔ ZeroClaw Live with NATS

**Commands:**
```bash
# On VPS — verify NATS running
systemctl status nats
nats-server --version

# Submit intake packet
curl -s -X POST http://localhost:8090/intake \
  -H 'Content-Type: application/json' \
  -d '{"task_type":"shell","description":"echo proof-b3","evidence":[]}' \
  | python3 -m json.tool

# Watch Hermes dispatch to ZeroClaw
journalctl -u kilocode-hermes -n 20 --no-pager
```

**Evidence to paste here:**
```
# NATS status:
[paste here]

# intake POST response:
[paste here]

# journalctl showing dispatch + ZeroClaw execution:
[paste here]
```

**Closed:** ☐  

---

## B4 — Boot / Restart Safety

**Commands:**
```bash
# Restart each service, verify health recovers
for svc in kilocode-runtime kilocode-hermes kilocode-webui; do
  systemctl restart $svc
  sleep 5
  STATUS=$(systemctl is-active $svc)
  HEALTH=$(curl -sf http://localhost:8080/health 2>/dev/null || echo "no-response")
  echo "$svc: systemd=$STATUS health=$HEALTH"
done

# Persist iptables rule for Shiba memory port
iptables-save > /etc/iptables/rules.v4
iptables -L INPUT -n | grep 18789
```

**Evidence to paste here:**
```
# Service restart + health loop output:
[paste here]

# iptables persistence confirmation:
[paste here]
```

**Closed:** ☐  

---

## B5 — Playwright E2E Against Live VPS

**Commands:**
```bash
# Install (local machine)
pip install playwright
playwright install chromium

# Run against live stack
BASE_URL=http://187.77.30.206:7860 pytest tests/e2e/ -v --html=proof/playwright-report.html

# Key assertions to verify manually:
#   - WebUI loads at /
#   - /health returns {"status":"healthy"}
#   - Provider failover: kill one provider, circuit opens within 5 req
#   - Repair: POST /repairs, verify in RepairPanel
#   - Restart proof: restart kilocode-webui mid-session, verify recovery
```

**Evidence to paste here:**
```
# pytest summary line:
[paste here]

# playwright-report.html generated at:
[paste here]

# Any manual failover/repair/restart observations:
[paste here]
```

**Closed:** ☐  

---

## Completion Gate

All five closed = **production proven**.

| Blocker | Closed |
|---------|--------|
| B1 WebUI live | ☐ |
| B2 VSIX/KiloCode live | ☐ |
| B3 Hermes↔ZeroClaw+NATS live | ☐ |
| B4 Boot/restart safety | ☐ |
| B5 Playwright E2E | ☐ |

When all five are ✅, update this file's header to:  
`State: PRODUCTION PROVEN — [date]`
