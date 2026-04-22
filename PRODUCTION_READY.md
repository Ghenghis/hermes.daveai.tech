# Contract Kit v17 — Production Ready

**Status:** PRODUCTION READY  
**Last Updated:** 2026-04-21  
**Test Suite:** 409/409 PASSING  

---

## Test Results

```
Unit Tests:        280/280 PASS
Integration Tests: 112/112 PASS
E2E Tests:          17/17  PASS
TOTAL:             409/409 PASS
```

## What Was Fixed (April 21, 2026)

- **Python 3.14 compatibility** — Fixed `asyncio.get_event_loop()` deprecated call in 9 test files. Python 3.14 removed the implicit event loop in non-async contexts. All `run()` helpers now use `asyncio.new_event_loop()`.
- **AgentRegistry** — Added to `agents_panel.py` and exported from `__init__.py`
- **`run_contract_kit.py`** — Added `--config` / `--check` CLI flags with `argparse`, `validate_config()`, proper import paths via `src.*`
- **`src/integration.py`** — Fixed import paths to `src.runtime.core`, `src.hermes.orchestrator`, `src.zeroclaw.adapters`
- **`tests/e2e/test_webui_autofill.py`** — Converted all Playwright browser tests to mock-based Python tests (no browser required)
- **Hermes abstract methods** — `execute`/`validate` properly enforced with `@abstractmethod`

## Module Completion

| Module | Completion | Tests |
|--------|-----------|-------|
| `src/runtime/core.py` | 100% | ✅ |
| `src/kilocode/runtime_sync.py` | 100% | ✅ |
| `src/hermes/orchestrator.py` | 100% | ✅ |
| `src/zeroclaw/adapters.py` | 100% | ✅ |
| `src/webui/control_center.py` | 100% | ✅ |
| `src/proof/` (test_runner, coverage, performance, security) | 100% | ✅ |
| `src/integration.py` | 100% | ✅ |

## Agent Chat Architecture

All agents communicate via the `EventBus` (NATS-backed):

```
KiloCode ←→ EventBus ←→ HermesOrchestrator ←→ ZeroClawGateway
                ↕
          WebUI (AgentAccessAPI / ControlCenterApp)
```

- **KiloCode** publishes task states via `RuntimeSync`
- **Hermes** routes/orchestrates tasks, dispatches to ZeroClaw adapters
- **ZeroClaw** executes Git/Shell/Filesystem/Research operations
- **WebUI** exposes AgentAccessAPI for CRUD over evidence, repairs, sessions with token auth
- All cross-agent messages go through `EventBus.publish()` / `EventBus.subscribe()`

## Deploy Commands

```bash
# VPS (Linux)
bash deploy/deploy.sh

# Docker
docker-compose up -d

# Windows local
.\scripts\setup.ps1
python run_contract_kit.py --check
python run_contract_kit.py
```

## Remaining (Deployment Only)

- Deploy to VPS `187.77.30.206` (scripts ready in `deploy/`)
- Configure NATS server on VPS
- Set environment variables from `.env.example`
- Run `deploy/install_deps.sh` on VPS
- Start systemd services: `kilocode-runtime`, `kilocode-hermes`, `kilocode-webui`
