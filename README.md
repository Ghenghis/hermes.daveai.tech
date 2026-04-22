# Hermes Ecosystem

The consolidated Hermes AI ecosystem including Contract Kit v17, Hermes agents, WebUI, and deployment tooling.

## Repository Structure

```
hermes.daveai.tech/
├── src/                        # Core source code
│   ├── kilocode/               # KiloCode audit engine (20 agents)
│   ├── hermes/                 # Hermes agent system
│   ├── webui/                  # WebUI Control Center
│   │   ├── agents_panel.py     # ZeroClaw + Hermes agent management
│   │   └── control_center.py   # Main FastAPI app
│   ├── runtime/                # Runtime engine
│   ├── zeroclaw/               # ZeroClaw agents
│   └── proof/                  # Proof system
├── hermes-full/                # Full Hermes agent (Discord bots H1-H5)
├── webui-full/                 # Full WebUI React frontend
├── tests/                      # Test suite (unit, integration, e2e)
├── deploy/                     # Deployment packages
├── docs/                       # Documentation
├── scripts/                    # Setup and utility scripts
├── .github/workflows/          # CI/CD pipelines
├── docker-compose.yml          # One-command deployment
├── .env.example                # Environment template
└── requirements.txt            # Python dependencies
```

## Quick Start

### Windows

```powershell
git clone https://github.com/Ghenghis/hermes.daveai.tech.git
cd hermes.daveai.tech
.\scripts\setup.ps1
```

### Linux / VPS

```bash
git clone https://github.com/Ghenghis/hermes.daveai.tech.git
cd hermes.daveai.tech
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
```

## Agents

### ZeroClaw Agents
| Agent | Role |
|-------|------|
| Git Agent | Repository management |
| Shell Agent | Command execution |
| Filesystem Agent | File operations |
| Research Agent | Web research |

### Hermes Discord Bots (H1-H5)
| Bot | Channel | Role |
|-----|---------|------|
| hermes1 | #general | Planning Strategist |
| hermes2 | #planning | Creative Brainstormer |
| hermes3 | #design | System Architect |
| hermes4 | #issues | Bug Triage Specialist |
| hermes5 | #problems | Root Cause Analyst |

## Configuration

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required keys:
- `SILICONFLOW_API_KEY` - Primary LLM API
- `MINIMAX_API_KEY` - Secondary LLM API
- `DISCORD_TOKEN` - For Hermes bots
- `GITHUB_TOKEN` - For GitHub operations
- `DATABASE_URL` - PostgreSQL connection

## Deployment

### Docker (Recommended)

```bash
docker-compose up -d
```

Services started:
- `webui` - React frontend on port 3000
- `api` - FastAPI backend on port 8000
- `db` - PostgreSQL on port 5432
- `redis` - Redis on port 6379
- `nginx` - Reverse proxy on port 80/443

### VPS Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full VPS deployment guide targeting `187.77.30.206`.

## Testing

```bash
# Python unit tests
python -m pytest tests/unit -v

# E2E tests with Playwright
python run_playwright_tests.py

# Full test suite
python -m pytest tests/ -v
```

## Related Repositories

- **KiloCode Azure**: https://github.com/Ghenghis/kilocode-Azure2
- **Hermes Agent**: https://github.com/Ghenghis/hermes-agent-2026.4.13

## License

Private - All rights reserved
