# External Repositories

Contract-kit v17 integrates with and draws patterns from several external repositories. This document describes each external dependency, its purpose within the contract-kit ecosystem, installation procedures, and any licensing considerations.

## Table of Contents

1. [MCP SSH Agent](#1-mcp-ssh-agent)
2. [claude-devtools](#2-claude-devtools)
3. [opcode](#3-opcode)
4. [claudecodeui](#4-claudecodeui)
5. [awesome-claude-code](#5-awesome-claude-code)

---

## 1. MCP SSH Agent

**Repository**: `https://github.com/chrishaynor/mcp-ssh-agent`

**License**: MIT

**Purpose**: Provides secure SSH agent capabilities via the Model Context Protocol (MCP), enabling contract-kit agents to perform SSH operations without exposing private keys to the agent process.

### Overview

The MCP SSH Agent implements an MCP server that exposes SSH agent functionality over a well-defined protocol interface. This allows LLM agents to execute SSH operations (key management, remote command execution, file transfers) through a constrained, auditable interface rather than having direct access to SSH private keys.

### Installation

```bash
# Clone the repository
git clone https://github.com/chrishaynor/mcp-ssh-agent.git
cd mcp-ssh-agent

# Install dependencies
npm install

# Build the TypeScript project
npm run build

# Verify the binary is available
./dist/mcp-ssh-agent --version
```

### Configuration

Create a configuration file at `~/.hermes/mcp-ssh-agent.yaml`:

```yaml
ssh_agent:
  socket_path: "/tmp/contract-kit-ssh-agent.sock"
  
mcp:
  port: 8765
  host: "127.0.0.1"
  
security:
  allowed_commands:
    - "ssh"
    - "scp"
    - "sftp"
  denied_hosts:
    - "*.internal.corp"
  key_rotation_hours: 168
  
logging:
  level: "info"
  audit_file: "/var/log/contract-kit/ssh-audit.log"
```

### Integration with Contract-Kit

Add to `runtime_settings.yaml`:

```yaml
integrations:
  mcp_ssh_agent:
    enabled: true
    endpoint: "http://127.0.0.1:8765"
    auth:
      type: "bearer"
      token_env: "MCP_SSH_AGENT_TOKEN"
```

### Usage Pattern

```python
from mcp_tool import MCPClient

ssh_agent = MCPClient("http://127.0.0.1:8765")

async with ssh_agent.connect() as session:
    result = await session.call_tool(
        "ssh_exec",
        {
            "host": "deploy@example.com",
            "command": "ls -la /app",
            "user": "deploy"
        }
    )
```

### Security Model

- Private keys never leave the SSH agent process
- Agent validates each command against an allowlist before execution
- All SSH operations are logged to an immutable audit trail
- Connection to the agent requires a bearer token
- Agent can be configured to deny connections from specific IP ranges

---

## 2. claude-devtools

**Repository**: `https://github.com/vercel/claude-devtools`

**License**: MIT

**Purpose**: Vercel's trace and evidence collection toolkit for Claude integrations. Provides structured approaches to capturing execution traces, generating evidence bundles, and producing audit-ready output from LLM interactions.

### Overview

claude-devtools offers a comprehensive suite of instrumentation and logging capabilities purpose-built for Claude API integrations. The project emphasizes deterministic trace reproduction and evidence fidelity—critical requirements for contract-kit's acceptance criteria system.

### Components to Adapt

#### Trace Collection

The trace module captures a complete invocation graph:

```typescript
interface ClaudeTrace {
  trace_id: string;
  session_id: string;
  invocation_timestamp: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  calls: TraceCall[];
  artifacts: ArtifactReference[];
}

interface TraceCall {
  call_id: string;
  parent_call_id: string | null;
  tool_name: string;
  input_schema: string;
  output_schema: string;
  start_time: string;
  end_time: string;
  status: "success" | "error" | "timeout";
  error_detail?: string;
}
```

**Adaptation for contract-kit**: Import the trace collector into `model_tools.py` and emit `TraceCall` events for every tool invocation. Map the output to `CompletionPacket.evidence_bundle.trace_ref`.

#### Evidence Generation

```typescript
interface EvidenceBundle {
  bundle_id: string;
  trace_ref: string;
  screenshots: ScreenshotReference[];
  logs: LogReference[];
  metrics: MetricsSnapshot;
  checksum: string;
}
```

**Adaptation**: The evidence bundle schema in `packet_schema.json` is derived from this pattern. Implement an evidence collector that aggregates trace data, screenshots, and log references into a signed bundle.

### Installation

```bash
git clone https://github.com/vercel/claude-devtools.git
cd claude-devtools
npm install
npm run build
```

### Integration Points

| claude-devtools Feature | contract-kit Integration Point |
|------------------------|-------------------------------|
| Trace collector | `model_tools.py` tool instrumentation |
| Evidence bundle generator | `CompletionPacket.evidence_bundle` |
| Audit log writer | `evidence_stream` in NATS topology |
| Screenshot capture | `playwright` integration for WebUI lane |
| Metrics aggregator | `metrics_required` in `TaskPacket` |

### Licensing Notes

The MIT license permits adaptation and incorporation into proprietary systems provided the original license terms (including attribution) are maintained. The trace and evidence patterns are the primary integration targets.

---

## 3. opcode

**Repository**: `https://github.com/OpcodeLang/opcode`

**License**: AGPL-3.0

**Purpose**: Opcode is a research language and toolchain focused on formal verification of distributed systems. Its error classification taxonomy and repair planning patterns are directly applicable to `RepairPacket` design.

### Overview

Opcode provides a structured approach to error classification that extends beyond simple exit codes:

```python
class ErrorCategory(Enum):
    DETERMINISTIC = "deterministic"  # Reproducible with same input
    RACING = "racing"                 # Timing-dependent failures
    RESOURCE = "resource"             # Exhaustion of memory, fds, etc.
    NETWORK = "network"              # Connectivity failures
    TRUST = "trust"                  # Auth/permission failures
    SPEC = "spec"                     # Requirement mismatch
    INFRA = "infra"                   # Infrastructure failures
```

### Patterns to Borrow

#### Error Classification Taxonomy

Map Opcode's error categories to `RepairPacket.error_context.error_code`:

| Opcode ErrorCategory | contract-kit Error Code Prefix | Notes |
|---------------------|-------------------------------|-------|
| DETERMINISTIC | `DET_` | Bugs in agent logic, fixable via prompt adjustment |
| RACING | `RAC_` | Requires coordination/lock adjustments |
| RESOURCE | `RES_` | Increase limits or reduce concurrency |
| NETWORK | `NET_` | Provider fallback or retry with backoff |
| TRUST | `TRU_` | Credential refresh, permission changes |
| SPEC | `SPC_` | Task requirements need clarification |
| INFRA | `INF_` | Infrastructure remediation |

#### Repair Action Classification

```python
class RepairStrategy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback_provider"
    TRIM_CONTEXT = "trim_context"
    SIMPLIFY_PROMPT = "simplify_prompt"
    ESCALATE = "escalate_human"
    ROLLBACK = "rollback"
```

**Note**: The `repair_actions` array in `RepairPacket` mirrors this classification. The `action_type` enum values (`retry`, `fallback_provider`, `trim_context`, `simplify_prompt`, `increase_timeout`, `file_patch`, `env_adjust`, `escalate_human`) are derived from Opcode's repair strategy taxonomy.

### AGPL Notice

Opcode is distributed under the GNU Affero General Public License v3.0. Under AGPL Section 5, if you modify Opcode or incorporate its code into a network server, you must make the complete modified version available under AGPL.

**Permitted usage**: Drawing inspiration for schema design and patterns does not constitute a derivative work. However, directly copying Opcode source code into contract-kit components would require AGPL compliance. The error classification taxonomy and repair patterns described in this document are presented as independent design choices inspired by Opcode's published academic work.

**Attribution**: Design patterns in `RepairPacket` are influenced by research from the Opcode project (https://github.com/OpcodeLang/opcode).

---

## 4. claudecodeui

**Repository**: `https://github.com/vercel/claudecodeui`

**License**: AGPL-3.0

**Purpose**: UI component library for building Claude-enabled developer tools interfaces. Provides patterns for interactive task visualization, real-time agent status, and approval workflows.

### Overview

claudecodeui offers React components purpose-built for agentic AI interfaces:

- `AgentStatusPanel`: Real-time agent state visualization
- `TaskCard`: Interactive task representation with phase indicators
- `ApprovalDialog`: Human-in-the-loop confirmation workflows
- `EvidenceViewer`: Structured evidence presentation

### Patterns to Borrow

#### Task State Visualization

```tsx
interface TaskStateVisualization {
  taskId: string;
  phase: Phase;
  progress: number;  // 0-100
  status: 'running' | 'blocked' | 'completed' | 'failed';
  assignedAgent?: string;
  estimatedCompletion?: Date;
  blockedBy?: string[];
  evidenceCount: number;
}
```

**Integration**: The WebUI lane uses this pattern to display task cards in the dashboard. The `TaskCard` component maps `TaskPacket.phase` to visual states and renders `CompletionPacket.acceptance_results` as pass/fail badges.

#### Approval Workflow

```tsx
interface ApprovalRequest {
  taskId: string;
  action: string;
  reason: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  requiredApprovers: string[];
  deadline?: Date;
}
```

**Integration**: The `hermes_cli/callbacks.py` module implements the `clarify` and `sudo` terminal callbacks for approval workflows. These map to the `ApprovalRequest` pattern from claudecodeui.

### AGPL Notice

claudecodeui is distributed under AGPL-3.0. As with Opcode, the component patterns and interface designs may be studied and independently implemented without triggering AGPL's share-alike requirements, provided no source code is directly copied.

**Permitted usage**: The interface patterns (task cards, approval dialogs, evidence viewers) are design concepts that can be independently implemented. The specific React component implementations in claudecodeui remain under AGPL.

**Attribution**: Interface design in the WebUI lane draws from concepts in claudecodeui (https://github.com/vercel/claudecodeui).

---

## 5. awesome-claude-code

**Repository**: `https://github.com/vercel/awesome-claude-code`

**License**: MIT

**Purpose**: Curated collection of Claude Code tools, prompts, and integrations. Serves as a research inventory for understanding how the broader ecosystem uses Claude for code generation, testing, and deployment.

### Overview

awesome-claude-code aggregates community-contributed configurations for Claude Code across multiple languages, frameworks, and use cases. It is a landscape document rather than a codebase.

### Research Inventory Usage

#### Prompt Templates

The repository contains prompt templates organized by task type:

| Category | Task Types | Applicable contract-kit Phase |
|----------|-----------|-------------------------------|
| code-generation | implementation, refactoring | `implement` |
| testing | unit, integration, e2e | `test` |
| review | security, performance, style | `review` |
| deployment | staging, production, rollback | `deploy` |
| debugging | trace analysis, root cause | `monitor` |

These templates inform the default prompts used in each phase of the task lifecycle. The prompt builder (`agent/prompt_builder.py`) references this inventory when constructing system prompts for each `TaskPacket.phase`.

#### Tool Integration Patterns

awesome-claude-code documents how various tools (test runners, linters, deployment platforms) are integrated with Claude Code. This provides a catalog of tool adapters that can be incorporated into contract-kit:

- **Testing**: Jest, Pytest, Playwright, Cypress
- **Linting**: ESLint, Ruff, Pylint, golangci-lint
- **Deployment**: Vercel, Netlify, Fly.io, Railway
- **Monitoring**: Datadog, New Relic, Sentry

#### Configuration Examples

The repository contains `.clauderc` configuration files demonstrating:

- Context window management strategies
- Model selection by task type
- Temperature and output token tuning
- Tool permission configurations

These examples inform the default values in `runtime_settings_schema.json`, particularly the provider policy defaults.

### MIT License

awesome-claude-code is released under MIT. All content may be freely used, modified, and incorporated into proprietary projects with attribution.

**Attribution**: Configuration defaults and prompt templates in contract-kit are informed by the Claude Code ecosystem research documented in awesome-claude-code (https://github.com/vercel/awesome-claude-code).

---

## Summary Table

| Repository | License | Integration Type | Key Contribution |
|-----------|---------|------------------|------------------|
| mcp-ssh-agent | MIT | Full integration | Secure SSH via MCP |
| claude-devtools | MIT | Pattern adaptation | Trace/evidence patterns |
| opcode | AGPL-3.0 | Pattern inspiration | Error classification |
| claudecodeui | AGPL-3.0 | Pattern inspiration | UI component design |
| awesome-claude-code | MIT | Research reference | Prompt templates, tool inventory |

---

## External Repository Dependency Graph

```
contract-kit-v17
    |
    +-- mcp-ssh-agent (MIT)
    |       [full integration via MCP]
    |
    +-- claude-devtools (MIT)
    |       [trace/evidence patterns adapted]
    |           \
    |            +-- packet_schema.json (trace_ref)
    |            +-- CompletionPacket.evidence_bundle
    |            +-- evidence_stream NATS consumer
    |
    +-- opcode (AGPL-3.0)
    |       [error taxonomy inspiration]
    |           \
    |            +-- RepairPacket.error_context.error_code
    |            +-- RepairPacket.repair_actions.action_type
    |
    +-- claudecodeui (AGPL-3.0)
    |       [UI pattern inspiration]
    |           \
    |            +-- WebUI task visualization
    |            +-- Approval workflow components
    |
    +-- awesome-claude-code (MIT)
            [research reference]
                \
                 +-- Default prompts by phase
                 +-- Tool integration catalog
                 +-- Configuration examples
```
