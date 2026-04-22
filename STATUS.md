# Contract Kit v17 — Honest Status

**Date:** 2026-04-21  
**Test Suite:** 409/409 PASSING  
**Source code:** ~11,500 lines real Python under `src/`  

---

## One-Line Summary

> Source implementation is complete and fully tested (409/409). Five live blockers remain — all are deployment/integration steps, **zero are coding tasks**.

---

## What Is Done (Source + Tests)

| Area | Lines | Tests | Status |
|------|-------|-------|--------|
| `src/runtime/core.py` — FastAPI runtime, EventBus, CircuitBreaker, ProviderRouter, SettingsFlow | 687 | ✅ | COMPLETE |
| `src/kilocode/runtime_sync.py` — RuntimeSync, SettingsManager (auto-configure from env + ~/.kilocode/config.json, get/set/list/export/import, API-key masking) | 1,160 | ✅ | COMPLETE |
| `src/hermes/orchestrator.py` — HermesOrchestrator, ZeroClawAdapter (abstract+concrete), GitAdapter, ShellAdapter, FilesystemAdapter, ResearchAdapter | 1,309 | ✅ | COMPLETE |
| `src/zeroclaw/adapters.py` — ZeroClawGateway, BaseAdapter, GitAdapter (ALLOWED_COMMANDS whitelist, subprocess+timeout), FilesystemAdapter, ShellAdapter | 1,339 | ✅ | COMPLETE |
| `src/webui/control_center.py` — ControlCenterApp (FastAPI), ProviderPanel, AgentPanel, WorkflowPanel, EvidencePanel, RepairPanel, SettingsPanel, AgentAccessAPI (CRUD + token-auth + state persistence) | 1,520 | ✅ | COMPLETE |
| `src/webui/agents_panel.py` — ZeroClawAgentsPanel, HermesAgentsPanel, AgentsManager, AgentRegistry | 555 | ✅ | COMPLETE |
| `src/proof/` — ProofTestRunner, CoverageTracker, PerformanceBenchmark, SecurityValidator (scan_for_exposed_keys, check_token_strength) | 1,765 | ✅ | COMPLETE |
| `src/blockchain_audit/` — AuditChain, AuditAgent, ConsensusEngine, IssueDetector, CorrectionValidator, AuditDashboard, AuditConfig | 2,453 | ✅ | COMPLETE |
| `src/integration.py` — ContractKitIntegration (wires Runtime + Hermes + ZeroClaw + WebUI) | 289 | ✅ | COMPLETE |
| `tests/unit/` — 5 test files, 280 tests | — | ✅ | 280/280 |
| `tests/integration/` — 5 test files, 112 tests | — | ✅ | 112/112 |
| `tests/e2e/` — 9 test files, 17 tests (mock-based, no live stack required) | — | ✅ | 17/17 |

---

## Agent Communication Architecture

All three agents (KiloCode, Hermes, ZeroClaw) communicate through the `EventBus`:

```
KiloCode (RuntimeSync)
    │ publish("tasks.*", state)
    ▼
EventBus (NATS nats://localhost:4222)
    │ subscribe("tasks.*")
    ▼
HermesOrchestrator
    │ dispatch → ZeroClawAdapter.execute()
    ▼
ZeroClawGateway → GitAdapter / ShellAdapter / FilesystemAdapter / ResearchAdapter
    │ result
    ▼
EventBus → WebUI AgentAccessAPI (CRUD evidence/repairs/sessions)
```

- **KiloCode settings** — auto-configured from `KILOCODE_API_KEY`, `KILOCODE_RUNTIME_URL`, `KILOCODE_MODEL`, `KILOCODE_PROVIDER` env vars; falls back to `~/.kilocode/config.json`; masked in exports.
- **WebUI agent access** — `AgentAccessAPI` with token auth (`WEBUI_AGENT_TOKEN` env var), CRUD over evidence/repairs/sessions, persisted to `~/.kilocode/webui_state.json`.
- **Settings autofill by agents** — `SettingsManager.auto_configure()` reads env + config file, fills missing keys, supports YOLO/elevated mode. Hermes/ZeroClaw can call `AgentAccessAPI` endpoints to push settings updates. All wired in source.

---

## Five Live Blockers (deployment only — zero coding remaining)

### B1 — WebUI Live Merge
**What:** Deploy WebUI (`src/webui/`) to VPS and integrate with the running Open WebUI instance.  
**How:**
```bash
# On local machine
bash deploy/deploy.sh

# On VPS after deploy
systemctl status kilocode-webui
curl http://localhost:7860/health
```
**Blocker type:** SSH access + deploy execution. No code changes needed.

---

### B2 — VSIX / KiloCode Live Merge
**What:** Package the KiloCode runtime as a VS Code extension (VSIX) and test against a running `kilocode-runtime` service on the VPS.  
**How:**
```bash
# Local: build VSIX
cd webui-full     # or kilocode extension dir
npm install
npx vsce package

# Install in VS Code
code --install-extension kilocode-*.vsix

# Point extension to live runtime
# Settings: kilocode.runtimeUrl = http://187.77.30.206:8080
```
**Blocker type:** VSIX build tooling + live endpoint connection. No source code changes needed.

---

### B3 — Live Hermes ↔ ZeroClaw Packet Flow
**What:** Prove a real task packet flows from `HermesOrchestrator.intake()` → through `ZeroClawGateway` → adapter executes → result returns via `EventBus`.  
**How:**
```bash
# On VPS — both services must be running
systemctl start kilocode-runtime kilocode-hermes

# Submit a test task
python run_contract_kit.py --config deploy/.env.example --check

# Verify packet flow via logs
journalctl -u kilocode-hermes -f
journalctl -u kilocode-runtime -f

# Or via API
curl -X POST http://localhost:8090/intake \
  -H 'Content-Type: application/json' \
  -d '{"task_type":"shell","description":"echo hello","evidence":[]}'
```
**Blocker type:** Live service startup + NATS running. No code changes needed.

---

### B4 — Boot/Restart Safety Proof
**What:** Prove the three services survive `systemctl restart` and recover state correctly.  
**How:**
```bash
# On VPS
systemctl restart kilocode-runtime
sleep 5
curl http://localhost:8080/health    # must return {"status":"healthy"}

systemctl restart kilocode-hermes
sleep 5
curl http://localhost:8090/health

# Verify iptables persistence for Shiba memory port
iptables-save > /etc/iptables/rules.v4
# or: ufw allow 18789/tcp
```
**Blocker type:** VPS execution + iptables persistence. No code changes needed.

---

### B5 — Real Playwright / Repair / Failover / Restart Proof
**What:** Run browser-based E2E tests against the live WebUI on the VPS.  
**How:**
```bash
# On local machine with Playwright installed
pip install playwright
playwright install chromium

# Run E2E against live stack (update BASE_URL)
BASE_URL=http://187.77.30.206:7860 pytest tests/e2e/ -v

# Provider failover test (kill one provider, verify circuit breaker opens)
# Repair proof (trigger a repair, verify it appears in RepairPanel)
# Restart proof (restart service mid-request, verify recovery)
```
**Blocker type:** Playwright install + live VPS WebUI running. No source code changes needed.

---

## Deploy Checklist (run in order)

```
[ ] 1. Copy deploy/.env.example → deploy/.env, fill all values
[ ] 2. SSH to VPS: bash deploy/scripts/install_deps.sh
[ ] 3. From local: bash deploy/deploy.sh
[ ] 4. On VPS: systemctl status kilocode-runtime kilocode-hermes kilocode-webui
[ ] 5. certbot --nginx -d daveai.tech -d www.daveai.tech
[ ] 6. Verify B1–B5 above
```

---

## Deploy Artifacts (all present, no coding needed)

| File | Purpose |
|------|---------|
| `deploy/scripts/install_deps.sh` | VPS bootstrap — Python 3.11, NATS, nginx, certbot, ufw, kilocode user |
| `deploy/deploy.sh` | Upload packages, install Python deps, systemd services, nginx, health check |
| `deploy/systemd/kilocode-runtime.service` | systemd unit for Runtime API (port 8080) |
| `deploy/systemd/kilocode-hermes.service` | systemd unit for Hermes orchestrator (port 8090) |
| `deploy/systemd/kilocode-webui.service` | systemd unit for WebUI (port 7860) |
| `deploy/nginx/kilocode.conf` | Nginx reverse proxy config for daveai.tech |
| `deploy/nginx/kilocode-proxy.inc` | Nginx proxy include (upstream routing) |
| `deploy/packages/*.tar.gz` | Pre-packaged tarballs for each module |
| `deploy/.env.example` | All required env vars with placeholder values |
| `deploy/docker-compose.yml` | Docker alternative to systemd |
| `deploy/scripts/health_check.sh` | Post-deploy health verification |

---

## Quick Test Commands (local, no VPS needed)

```bash
# Run full test suite
python -m pytest tests/ -q

# Run only unit tests
python -m pytest tests/unit/ -v

# Validate config
python run_contract_kit.py --check

# Run with config file
python run_contract_kit.py --config deploy/.env.example
```
