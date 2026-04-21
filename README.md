# KiloCode Contract Kit Version 17

## Consolidated Multi-Agent Contract Processing System

![Contract Kit Banner](diagrams/banner.svg)

---

## Overview

Version 17 represents the consolidation of all useful components, patterns, and implementations from multiple source folders and external repositories into a single, production-ready system featuring a five-lane architecture.

### Key Improvements Over Previous Versions

- **Complete packet-based contract system** with control, task, completion, and repair packets
- **Integrated SSH MCP tooling** for remote administration
- **Evidence/DevTools panel** inspired by claude-devtools
- **Full five-lane architecture** with WebUI, KiloCode, Runtime, Hermes, and Proof lanes
- **Comprehensive SVG documentation** embedded throughout

---

## Architecture Diagram

![Five-Lane Architecture](diagrams/five_lane_architecture.svg)

---

## Five-Lane Architecture

| Lane | Purpose | Key Components |
|------|---------|----------------|
| **Lane 1: WebUI** | Control Center | Control Center, Providers, Agents, Workflows, Evidence/DevTools, Repairs/Safemode, Settings |
| **Lane 2: KiloCode** | Runtime Sync | Active Task Panel, Completion Submitter, Provider Status, Evidence Return, Settings Autofill |
| **Lane 3: Runtime + Provider** | Infrastructure | Canonical Settings, Event Bus, Provider Router, Question Flow, Mode Enforcement |
| **Lane 4: Hermes + ZeroClaw** | Orchestration | Intake Normalization, Contract Creation, Task Fan-Out, Validation, Repair Routing |
| **Lane 5: Proof / Testing** | Validation | Playwright UI Tests, Boot-Gate Tests, Failover Tests, Autofill Tests, Repair Tests |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- NATS JetStream (or Redis for alternative event bus)

### Installation

```bash
# Clone the repository
git clone https://github.com/Ghenghis/hermes.daveai.tech.git
cd contract-kit-v17

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running the System

```bash
# Start the Runtime Core API (stub - implement src/runtime/core.py first)
python -m src.runtime.core

# Start the WebUI (requires implementation)
cd src/webui && npm run dev

# Start Hermes Agent (integrate with hermes-agent separately)
# python run_agent.py  # External - see hermes-agent repository
```

---

## Source Materials

This version consolidates components from:

### Local Sources

| Source | Key Contributions |
|--------|-------------------|
| `v16_implementation_closure_master_kit` | Packet schemas, boot gate flow, 36-phase plan |
| `kilocode-Azure2` | VSIX extension, 21 services, routing, governance |
| `hermes-agent-2026.4.13` | Base agent, tool registry, hierarchical crew |
| `VPS (C:\Users\Admin\Downloads\VPS)` | Evidence ledger, 5 agent roles, DaveAI platform |

### External Repositories

| Repository | Integration Method |
|------------|-------------------|
| [MCP SSH Agent](https://github.com/aiondadotcom/mcp-ssh) | Direct integration |
| [claude-devtools](https://github.com/matt1398/claude-devtools) | Adapted for evidence panels |
| [opcode](https://github.com/winfunc/opcode) | Pattern borrowing (AGPL) |
| [claudecodeui](https://github.com/siteboon/claudecodeui) | Pattern borrowing (AGPL) |
| [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | Research inventory |

---

## Documentation Structure

```
contract-kit-v17/
├── README.md                    # This file
├── GAP_ANALYSIS.md             # Detailed gap analysis
├── MERGE_MATRIX.md             # Source-to-lane mapping
├── ARCHITECTURE.md             # System architecture
├── docs/
│   ├── 01_FIVE_LANE_ARCHITECTURE.md    # Detailed lane specs
│   ├── 02_WEBUI_LANE.md               # WebUI implementation
│   ├── 03_KILOCODE_LANE.md            # KiloCode implementation
│   ├── 04_RUNTIME_PROVIDER_LANE.md    # Runtime implementation
│   ├── 05_HERMES_ZEROCLAW_LANE.md     # Hermes implementation
│   ├── 06_PROOF_TESTING_LANE.md       # Testing implementation
│   ├── 07_EXTERNAL_REPOSITORIES.md    # External repo integration
│   └── 08_IMPLEMENTATION_ROADMAP.md   # 36-phase implementation plan
├── diagrams/                   # SVG architecture diagrams
├── configs/                    # Packet schemas, settings
├── src/                        # Source code
└── tests/                      # E2E test suite
```

---

## Key Features

### Packet-Based Contract System

![Packet Flow](diagrams/packet_flow.svg)

All operations flow through typed packets:

- **Control Packets**: Source identity, actions (project.start, repair.run)
- **Task Packets**: Project ID, phase, objective, acceptance criteria
- **Completion Packets**: Status, changed files, tests, artifacts
- **Repair Packets**: Error context, repair actions, validation

### Boot Gate / Safemode

![Boot Gate](diagrams/boot_gate_repair.svg)

Health matrix validation before launch with forced safemode on failures.

### Settings Autofill

![Settings](diagrams/settings_closure.svg)

Runtime-owned canonical settings with user prompts only for secrets.

---

## Provider Routing

| Provider | Primary Use | Fallback |
|----------|-------------|----------|
| MiniMax | Primary execution | SiliconFlow |
| SiliconFlow | ZeroClaw-first | LM Studio |
| LM Studio | Local fallback | Ollama |
| Ollama | Offline fallback | None |

---

## Testing

```bash
# Run all tests (requires implementation)
pytest tests/ -v

# Run E2E tests (Playwright - requires implementation)
playwright test tests/e2e/

# Run specific lane tests
pytest tests/e2e/test_webui.py
pytest tests/e2e/test_kilocode.py
pytest tests/e2e/test_runtime.py
pytest tests/e2e/test_hermes.py
pytest tests/e2e/test_boot_gate.py
pytest tests/e2e/test_provider_failover.py

# Note: test_proof.py will be created when src/proof/ is implemented
```

---

## License

This project incorporates code from various sources with their respective licenses:

- **hermes-agent**: MIT License
- **kilocode-Azure2**: MIT License
- **MCP SSH Agent**: MIT License
- **claude-devtools**: MIT License
- **opcode**: AGPL-3.0 (patterns only)
- **claudecodeui**: AGPL-3.0 (patterns only)

See individual source repositories for details.

---

## Contributing

1. Read the [GAP_ANALYSIS.md](GAP_ANALYSIS.md) to understand what's missing
2. Check the [MERGE_MATRIX.md](MERGE_MATRIX.md) for integration strategies
3. Follow the [Implementation Roadmap](docs/08_IMPLEMENTATION_ROADMAP.md)

---

*Version 17.0 - Consolidated 2026-04-20*
