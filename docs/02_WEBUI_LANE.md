# Lane 2: WebUI

## Purpose

The WebUI lane provides the user-facing control center for the KiloCode Contract Kit v17. Built on Open WebUI's Functions/Tools/Pipelines model, it enables users to monitor system health, manage providers and agents, track workflow progress, inspect evidence, trigger repairs, and configure settings.

## Architecture Diagram

![Five-Lane Architecture Overview](../diagrams/five_lane_architecture.svg)

*See the main architecture diagram for inter-lane communication. Individual WebUI component diagrams will be generated during implementation.*

---

## Components

### 1. Control Center

**Purpose:** Main dashboard providing system-wide health visibility and quick actions.

**Source:** `v16_implementation_closure_master_kit` (spec) + `opcode` (patterns) + `hermes-agent` (React UI)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Health Matrix | System health indicators across all lanes | ⚠️ Partial |
| Quick Actions | Common operations (start, stop, restart) | ⚠️ Partial |
| Activity Feed | Real-time event stream | ⚠️ Partial |
| Session List | Active and recent sessions | ⚠️ Partial |
| Checkpoint Manager | Session checkpoint save/restore | ⚠️ Partial |

**Key Files:**
- `src/webui/control-center/health-matrix.tsx`
- `src/webui/control-center/quick-actions.tsx`
- `src/webui/control-center/activity-feed.tsx`

**Configuration Example:**
```yaml
display:
  control_center:
    refresh_interval: 5000  # ms
    show_checkpoints: true
    activity_feed_size: 50
```

**Integration Points:**
- Subscribes to NATS subjects: `contracts.control.*`, `contracts.repair.*`
- Publishes to: `contracts.control.{source}` (user actions)

---

### 2. Providers Panel

**Purpose:** Display provider health, routing status, and circuit breaker state.

**Source:** `kilocode-Azure2` (routing service) + `v16` (provider health spec) + `hermes-agent` (models)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Provider List | All configured providers with status | ⚠️ Partial |
| Health Indicators | Per-provider health (latency, errors) | ⚠️ Partial |
| Circuit Breaker | Circuit breaker state visualization | ⚠️ Partial |
| Routing Rules | Current routing configuration | ⚠️ Partial |
| Fallback Chain | Provider fallback order display | ⚠️ Partial |

**Key Files:**
- `src/webui/providers/provider-list.tsx`
- `src/webui/providers/circuit-breaker.tsx`
- `src/webui/providers/routing-rules.tsx`

**Provider Configuration:**
```yaml
providers:
  minimax:
    primary: true
    fallback: siliconflow
    circuit_breaker:
      threshold: 5
      timeout: 30000
  siliconflow:
    primary: false
    fallback: lmstudio
  lmstudio:
    primary: false
    fallback: ollama
  ollama:
    primary: false
    fallback: null
```

**Integration Points:**
- Reads from: Runtime settings (`src/runtime/settings/`)
- Displays: Provider health events from event bus

---

### 3. Agents Panel

**Purpose:** Manage agent roles, crews, and task assignments.

**Source:** `hermes-agent` (agent architecture) + `VPS` (5 Hermes agent roles H1-H5)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Agent Roster | All agent instances with roles | ⚠️ Partial |
| Role Assignment | Assign agents to roles | ⚠️ Partial |
| Crew Visualization | Hierarchical crew display | ⚠️ Partial |
| Task Distribution | Current task allocation | ⚠️ Partial |
| Performance Metrics | Per-agent metrics | ⚠️ Partial |

**Key Files:**
- `src/webui/agents/agent-roster.tsx`
- `src/webui/agents/crew-visualization.tsx`
- `src/webui/agents/task-distribution.tsx`

**Agent Roles (H1-H5):**

| Role | Name | Function | Status |
|------|------|----------|--------|
| H1 | Orchestrator | Primary task coordination | ✅ Complete |
| H2 | Coder | Code generation | ✅ Complete |
| H3 | Tester | Testing and validation | ✅ Complete |
| H4 | Researcher | Research and analysis | ✅ Complete |
| H5 | Repair | Repair and recovery | ✅ Complete |

**Configuration:**
```yaml
agents:
  roles:
    h1:
      name: "Orchestrator"
      max_concurrent_tasks: 1
      tools: ["delegate", "memory", "file_read"]
    h2:
      name: "Coder"
      max_concurrent_tasks: 3
      tools: ["file_write", "terminal", "git"]
    h3:
      name: "Tester"
      max_concurrent_tasks: 2
      tools: ["execute_code", "terminal", "browser"]
```

---

### 4. Workflows Panel

**Purpose:** Track packet lifecycle, phase progression, and workflow versioning.

**Source:** `v16` (packet lifecycle spec) + `kilocode-Azure2` (command palette) + `opcode` (timeline)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Packet Tracker | Track control/task/completion packets | ⚠️ Partial |
| Phase Progress | Current phase and progress | ⚠️ Partial |
| Timeline View | Historical workflow visualization | ⚠️ Partial |
| Version Control | Workflow version history | ⚠️ Partial |
| Command Palette | Quick command access | ⚠️ Partial |

**Key Files:**
- `src/webui/workflows/packet-tracker.tsx`
- `src/webui/workflows/phase-progress.tsx`
- `src/webui/workflows/timeline.tsx`

**Packet Lifecycle States:**
```
PENDING → RUNNING → VALIDATING → COMPLETING → COMPLETED
                ↓
            REPAIRING → VALIDATING
                ↓
            FAILED
```

**Configuration:**
```yaml
workflows:
  packet_tracking:
    enabled: true
    retention_days: 30
  phase_progress:
    auto_advance: true
    require_validation: true
  timeline:
    show_metadata: true
    max_entries: 1000
```

---

### 5. Evidence / DevTools

**Purpose:** Trace inspection, token attribution, session replay, and tool call analysis.

**Source:** `claude-devtools` (trace/evidence implementation) + `VPS` (evidence ledger) + `v16` (evidence requirements)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Trace Inspector | View tool call traces | ⚠️ Partial |
| Token Attribution | Show token usage per component | ⚠️ Partial |
| Session Replay | Replay conversation sessions | ⚠️ Partial |
| Tool Call Tree | Hierarchical tool call display | ⚠️ Partial |
| Evidence Ledger | Completion evidence display | ⚡ Adapt |

**Key Files:**
- `src/webui/evidence/trace-inspector.tsx`
- `src/webui/evidence/token-attribution.tsx`
- `src/webui/evidence/session-replay.tsx`
- `src/webui/evidence/tool-call-tree.tsx`

**Evidence Packet Structure:**
```json
{
  "completion_packet": {
    "project_id": "uuid",
    "status": "success|failure",
    "changed_files": ["path1", "path2"],
    "tests": {
      "passed": 42,
      "failed": 0,
      "total": 42
    },
    "artifacts": ["artifact1", "artifact2"],
    "evidence_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

**Integration Points:**
- Reads from: Completion packets in evidence ledger
- Displays: Tool call traces, token attributions, session logs

---

### 6. Repairs / Safemode

**Purpose:** Health matrix display, boot gate status, repair triggers, and safemode management.

**Source:** `v16` (boot_gate_repair.svg, repair flow spec)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Health Matrix | Lane-by-lane health grid | ⚠️ Partial |
| Boot Gate Status | Boot gate validation results | ⚠️ Partial |
| Safemode Toggle | Enable/disable safemode | ⚠️ Partial |
| Repair Triggers | Manual repair initiation | ⚠️ Partial |
| Repair History | Past repair actions log | ⚠️ Partial |

**Key Files:**
- `src/webui/repairs/health-matrix.tsx`
- `src/webui/repairs/boot-gate-status.tsx`
- `src/webui/repairs/repair-triggers.tsx`

**Health Matrix States:**
| State | Color | Description |
|-------|-------|-------------|
| HEALTHY | Green | Component operating normally |
| DEGRADED | Yellow | Component functioning with issues |
| FAILED | Red | Component non-operational |
| UNKNOWN | Gray | Health status unknown |

**Boot Gate Sequence:**
1. Check Runtime API connectivity
2. Verify NATS event bus status
3. Validate provider configurations
4. Check Hermes agent availability
5. Verify SSH MCP tool status

**Configuration:**
```yaml
safemode:
  auto_enable: true
  health_check_interval: 30000
  boot_gate_on_start: true
  repair_notifications: true
```

---

### 7. Settings / Missing Questions

**Purpose:** Runtime-owned canonical settings, user prompt flow for secrets, and settings autofill.

**Source:** `v16` (settings_closure.svg, settings autofill spec) + `kilocode-Azure2` (kilo-gateway auth)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Settings Overview | Display all settings | ⚠️ Partial |
| Question Flow | Prompt user for missing secrets | ⚠️ Partial |
| Autofill Preview | Preview auto-filled settings | ⚠️ Partial |
| Settings Editor | Manual settings override | ⚠️ Partial |
| Settings History | Settings change audit log | ⚠️ Partial |

**Key Files:**
- `src/webui/settings/settings-overview.tsx`
- `src/webui/settings/question-flow.tsx`
- `src/webui/settings/settings-editor.tsx`

**Settings Autofill Flow:**
```
Runtime Settings Store
         │
         ▼
    Check Required
    Settings Keys
         │
    ┌────┴────┐
    │         │
 Missing    All
   │        Present
   ▼         ▼
 Question    Use
   │        Cached
   ▼         │
 User        ▼
 Provides   Apply
   │
   ▼
 Validate
   │
   ▼
 Store &
 Distribute
```

**Configuration:**
```yaml
settings:
  autofill:
    enabled: true
    infer_from_env: true
    cache_duration: 3600
  questions:
    ask_for_secrets: true
    timeout: 300
    retry_count: 3
```

---

## Implementation Status Summary

| Component | Status | Source |
|-----------|--------|--------|
| Control Center | ⚠️ Partial | v16 + opcode + hermes-agent |
| Providers Panel | ⚠️ Partial | kilocode-Azure2 + v16 |
| Agents Panel | ⚠️ Partial | hermes-agent + VPS |
| Workflows Panel | ⚠️ Partial | v16 + opcode |
| Evidence/DevTools | ⚡ Adapt | claude-devtools + VPS |
| Repairs/Safemode | ⚠️ Partial | v16 |
| Settings/Questions | ⚠️ Partial | v16 + kilo-gateway |

---

## File Structure

```
src/webui/
├── control-center/
│   ├── health-matrix.tsx
│   ├── quick-actions.tsx
│   ├── activity-feed.tsx
│   └── session-list.tsx
├── providers/
│   ├── provider-list.tsx
│   ├── circuit-breaker.tsx
│   └── routing-rules.tsx
├── agents/
│   ├── agent-roster.tsx
│   ├── crew-visualization.tsx
│   └── task-distribution.tsx
├── workflows/
│   ├── packet-tracker.tsx
│   ├── phase-progress.tsx
│   └── timeline.tsx
├── evidence/
│   ├── trace-inspector.tsx
│   ├── token-attribution.tsx
│   ├── session-replay.tsx
│   └── tool-call-tree.tsx
├── repairs/
│   ├── health-matrix.tsx
│   ├── boot-gate-status.tsx
│   └── repair-triggers.tsx
├── settings/
│   ├── settings-overview.tsx
│   ├── question-flow.tsx
│   └── settings-editor.tsx
└── App.tsx
```

---

## Integration with Other Lanes

### From Lane 3 (Runtime + Provider)
- **Receives:** Canonical settings updates, provider health events, audit logs
- **Publishes:** Control packets (project.start, repair.run, settings.update)

### From Lane 4 (Hermes + ZeroClaw)
- **Receives:** Completion packets, repair requests, evidence
- **Publishes:** User approvals for repair actions

### To Lane 2 (KiloCode)
- **Publishes:** Task assignments, workflow commands

---

## Testing Strategy

| Test Type | Coverage | Status |
|-----------|----------|--------|
| Component Tests | Each panel component | ❌ Not created |
| Integration Tests | WebUI ↔ Runtime communication | ❌ Not created |
| E2E Tests | Full user workflows | ❌ Not created |
| Visual Regression | UI appearance | ❌ Not created |

---

## See Also

- [Five Lane Architecture](01_FIVE_LANE_ARCHITECTURE.md)
- [GAP Analysis](../GAP_ANALYSIS.md)
- [Merge Matrix](../MERGE_MATRIX.md)
- [Runtime + Provider Lane](04_RUNTIME_PROVIDER_LANE.md)
- [Hermes + ZeroClaw Lane](05_HERMES_ZEROCLAW_LANE.md)

---

*Document Version: 17.0*
*Generated: 2026-04-20*
