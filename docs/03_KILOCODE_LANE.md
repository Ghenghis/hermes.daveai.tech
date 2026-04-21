# Lane 3: KiloCode

## Purpose

The KiloCode lane provides IDE integration for the KiloCode Contract Kit v17. It synchronizes runtime state with the IDE environment, displays active tasks, submits completion packets, shows evidence, and provides settings autofill capabilities.

## Architecture Diagram

![Runtime Sync Flow](../diagrams/packet_flow.svg)

*See the packet flow diagram for task completion and evidence return patterns.*

---

## Components

### 1. Runtime Sync

**Purpose:** Synchronize canonical settings from Runtime Core API with the IDE environment.

**Source:** `v16_implementation_closure_master_kit` (canonical settings spec) + `hermes-agent` (settings loading)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Settings Fetcher | Pull settings from Runtime API | ⚠️ Partial |
| Settings Cache | Local cache of settings | ⚠️ Partial |
| Diff Detector | Detect settings changes | ⚠️ Partial |
| Sync Controller | Orchestrate sync operations | ⚠️ Partial |
| Conflict Resolver | Handle settings conflicts | ⚠️ Partial |

**Key Files:**
- `src/kilocode/runtime-sync/settings-fetcher.ts`
- `src/kilocode/runtime-sync/settings-cache.ts`
- `src/kilocode/runtime-sync/sync-controller.ts`

**Sync Protocol:**
```typescript
interface SyncMessage {
  type: 'full_sync' | 'incremental_sync' | 'settings_update';
  timestamp: string;
  payload: SettingsPayload;
  signature: string;  // HMAC signature for validation
}

interface SettingsPayload {
  keys: string[];
  values: Record<string, unknown>;
  metadata: {
    source: 'runtime' | 'user' | 'env';
    last_modified: string;
  };
}
```

**Configuration:**
```yaml
runtime_sync:
  enabled: true
  poll_interval: 5000  # ms
  retry_count: 3
  retry_delay: 1000
  cache_ttl: 3600
```

---

### 2. Active Task Panel

**Purpose:** Display current task, progress, and context in the IDE.

**Source:** `kilocode-Azure2` (VSIX agent-manager) + `opcode` (session list) + `claude-devtools` (turn-based context)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Task Display | Show current task details | ⚠️ Partial |
| Progress Bar | Visual progress indicator | ⚠️ Partial |
| Context Window | Turn-based context display | ⚠️ Partial |
| Sub-task List | Nested task breakdown | ⚠️ Partial |
| Time Tracker | Task duration tracking | ⚠️ Partial |

**Key Files:**
- `src/kilocode/task-panel/task-display.tsx`
- `src/kilocode/task-panel/progress-bar.tsx`
- `src/kilocode/task-panel/context-window.tsx`

**Task Display Structure:**
```typescript
interface TaskDisplay {
  task_id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  subtasks: SubTask[];
  started_at: string;
  estimated_completion: string;
}
```

---

### 3. Completion Packet Submitter

**Purpose:** Generate and submit completion packets with evidence when tasks complete.

**Source:** `VPS` (evidence ledger) + `v16` (completion packet schema)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Packet Generator | Build completion packets | ⚠️ Partial |
| Evidence Collector | Gather task evidence | ⚠️ Partial |
| File Diffs | Collect changed file information | ⚠️ Partial |
| Test Results | Aggregate test outcomes | ⚠️ Partial |
| Artifact Registry | Track task artifacts | ⚠️ Partial |
| Submitter | Send packets to evidence ledger | ⚠️ Partial |

**Key Files:**
- `src/kilocode/completion/packet-generator.ts`
- `src/kilocode/completion/evidence-collector.ts`
- `src/kilocode/completion/submitter.ts`

**Completion Packet Schema:**
```json
{
  "completion_packet": {
    "project_id": "uuid",
    "task_id": "uuid",
    "status": "success|failure",
    "phase": "string",
    "objective": "string",
    "changed_files": [
      {
        "path": "string",
        "operation": "create|modify|delete",
        "lines_added": 0,
        "lines_removed": 0
      }
    ],
    "tests": {
      "passed": 0,
      "failed": 0,
      "skipped": 0,
      "total": 0,
      "coverage": 0.0
    },
    "artifacts": [
      {
        "name": "string",
        "type": "file|directory|log|screenshot",
        "path": "string",
        "size": 0
      }
    ],
    "evidence_id": "uuid",
    "timestamp": "ISO8601",
    "agent_id": "string",
    "signature": "string"
  }
}
```

---

### 4. Provider/Mode Status

**Purpose:** Display current provider, mode indicators, and routing decisions.

**Source:** `kilocode-Azure2` (routing service) + `hermes-agent` (mode enforcement)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Provider Indicator | Current provider badge | ✅ Complete |
| Mode Badge | Active mode indicator | ✅ Complete |
| Routing Decision | Last routing choice display | ✅ Complete |
| Latency Monitor | Provider latency tracking | ✅ Complete |
| Fallback Status | Fallback chain state | ✅ Complete |

**Key Files:**
- `src/kilocode/status/provider-indicator.tsx`
- `src/kilocode/status/mode-badge.tsx`
- `src/kilocode/status/latency-monitor.ts`

**Modes:**

| Mode | Description | Tools Available |
|------|-------------|------------------|
| `auto` | Automatic provider selection | All tools |
| `supervisor` | H1 orchestrator only | delegate, memory |
| `coding` | H2 code generation | file, terminal, git |
| `testing` | H3 validation | execute_code, browser |
| `research` | H4 analysis | web, search |
| `repair` | H5 recovery | all + repair tools |

**Provider Fallback Chain:**
```
MiniMax → SiliconFlow → LM Studio → Ollama → (offline mode)
```

---

### 5. Evidence Return Panel

**Purpose:** Display evidence returned from completion packets and validation results.

**Source:** `claude-devtools` (tool call inspector, context reconstruction)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Evidence Viewer | Display completion evidence | ⚡ Adapt |
| Token Attribution | Show token usage breakdown | ⚡ Adapt |
| Tool Call Tree | Hierarchical tool call view | ⚡ Adapt |
| Diff Viewer | Side-by-side file changes | ⚡ Adapt |
| Test Report | Test result display | ⚡ Adapt |

**Key Files:**
- `src/kilocode/evidence/evidence-viewer.tsx`
- `src/kilocode/evidence/token-attribution.tsx`
- `src/kilocode/evidence/tool-call-tree.tsx`

**Evidence Display Structure:**
```typescript
interface EvidenceDisplay {
  evidence_id: string;
  completion_packet: CompletionPacket;
  tool_calls: ToolCall[];
  token_usage: {
    prompt: number;
    completion: number;
    total: number;
    cost_usd: number;
  };
  validation_results: ValidationResult[];
}
```

---

### 6. Settings Autofill

**Purpose:** Automatically fill missing settings from runtime, environment, or inference.

**Source:** `v16` (autofill spec) + `kilocode-Azure2` (onboarding service)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Settings Detector | Identify missing settings | ⚠️ Partial |
| Autofill Engine | Apply auto-fill logic | ⚠️ Partial |
| Question Prompter | Prompt for secrets | ⚠️ Partial |
| Inference Engine | Infer settings from context | ⚠️ Partial |
| Settings Validator | Validate completed settings | ⚠️ Partial |

**Key Files:**
- `src/kilocode/settings/autofill-engine.ts`
- `src/kilocode/settings/question-prompter.tsx`
- `src/kilocode/settings/inference-engine.ts`

**Autofill Priority:**
1. **Runtime Cache** - Canonical settings from Runtime API
2. **Environment Variables** - `HERMES_*`, provider API keys
3. **Inference** - Settings inferred from usage patterns
4. **User Input** - Only for secrets not available elsewhere

**Configuration:**
```yaml
settings_autofill:
  enabled: true
  priority:
    - runtime_cache
    - environment
    - inference
    - user_input
  infer_from_usage: true
  cache_duration: 3600
```

---

### 7. Command Palette

**Purpose:** Quick action access for common KiloCode operations.

**Source:** `opcode` (command palette patterns) + `kilocode-Azure2` (command system)

| Sub-component | Description | Status |
|---------------|-------------|--------|
| Action Registry | Available commands list | ⚠️ Partial |
| Fuzzy Search | Command search | ⚠️ Partial |
| Keybindings | Keyboard shortcuts | ⚠️ Partial |
| Command History | Recent commands | ⚠️ Partial |
| Custom Commands | User-defined commands | ⚡ Adapt |

**Key Files:**
- `src/kilocode/commands/action-registry.ts`
- `src/kilocode/commands/fuzzy-search.ts`
- `src/kilocode/commands/keybindings.ts`

**Default Commands:**

| Command | Shortcut | Description |
|---------|----------|-------------|
| `task:start` | `Ctrl+Enter` | Start new task |
| `task:complete` | `Ctrl+Shift+Enter` | Submit completion |
| `task:cancel` | `Ctrl+C` | Cancel current task |
| `settings:open` | `Ctrl+,` | Open settings |
| `providers:switch` | `Ctrl+P` | Switch provider |
| `evidence:view` | `Ctrl+E` | View evidence |
| `repair:trigger` | `Ctrl+R` | Trigger repair |

---

## Implementation Status Summary

| Component | Status | Source |
|-----------|--------|--------|
| Runtime Sync | ⚠️ Partial | v16 + hermes-agent |
| Active Task Panel | ⚠️ Partial | kilocode-Azure2 + opcode |
| Completion Submitter | ⚠️ Partial | VPS + v16 |
| Provider/Mode Status | ✅ Complete | kilocode-Azure2 + hermes-agent |
| Evidence Return Panel | ⚡ Adapt | claude-devtools |
| Settings Autofill | ⚠️ Partial | v16 + onboarding |
| Command Palette | ⚠️ Partial | opcode + kilo-ui |

---

## File Structure

```
src/kilocode/
├── runtime-sync/
│   ├── settings-fetcher.ts
│   ├── settings-cache.ts
│   ├── sync-controller.ts
│   └── conflict-resolver.ts
├── task-panel/
│   ├── task-display.tsx
│   ├── progress-bar.tsx
│   ├── context-window.tsx
│   └── time-tracker.tsx
├── completion/
│   ├── packet-generator.ts
│   ├── evidence-collector.ts
│   ├── file-diffs.ts
│   ├── test-aggregator.ts
│   └── submitter.ts
├── status/
│   ├── provider-indicator.tsx
│   ├── mode-badge.tsx
│   └── latency-monitor.ts
├── evidence/
│   ├── evidence-viewer.tsx
│   ├── token-attribution.tsx
│   ├── tool-call-tree.tsx
│   └── diff-viewer.tsx
├── settings/
│   ├── autofill-engine.ts
│   ├── question-prompter.tsx
│   ├── inference-engine.ts
│   └── settings-validator.ts
├── commands/
│   ├── action-registry.ts
│   ├── fuzzy-search.ts
│   └── keybindings.ts
└── extension.ts
```

---

## Integration with Other Lanes

### From Lane 1 (WebUI)
- **Receives:** User commands, task assignments, workflow triggers
- **Publishes:** Completion packets, evidence

### From Lane 3 (Runtime + Provider)
- **Receives:** Canonical settings updates, provider routing decisions
- **Publishes:** Runtime sync requests, settings queries

### To Lane 4 (Hermes + ZeroClaw)
- **Publishes:** Task delegations, completion evidence
- **Receives:** Task results, validation callbacks

### To Lane 5 (Proof / Testing)
- **Publishes:** Evidence for test validation

---

## Hermes Bridge (VSIX to Hermes Agent)

The KiloCode lane bridges the VSIX extension to the Hermes Agent via the Hermes Bridge service.

**Bridge Protocol:**
```typescript
interface HermesBridge {
  // VSIX → Hermes
  delegate_task(task: TaskPacket): Promise<DelegationResult>;
  submit_completion(packet: CompletionPacket): Promise<Receipt>;
  
  // Hermes → VSIX
  on_task_assigned(callback: (task: TaskPacket) => void): void;
  on_validation_result(callback: (result: ValidationResult) => void): void;
}
```

**Status:** ⚠️ Bridge incomplete (see GAP_ANALYSIS.md Lane 2)

---

## VSIX Services

The VSIX extension provides 21 services (from kilocode-Azure2):

| Service | Status | Purpose |
|---------|--------|---------|
| routing | ✅ Complete | Provider routing |
| governance | ✅ Complete | Policy enforcement |
| speech | ⚠️ Partial | TTS/STT (6 providers) |
| zeroclaw | ⚠️ Partial | ZeroClaw integration |
| ssh | ⚠️ Partial | SSH connectivity |
| vps | ⚠️ Partial | VPS probe |
| memory | ⚠️ Partial | Memory auto-attach |
| training | ⚠️ Partial | LoRA/QLoRA training |
| onboarding | ⚠️ Partial | Setup wizard |

---

## Testing Strategy

| Test Type | Coverage | Status |
|-----------|----------|--------|
| Unit Tests | Runtime sync, autofill | ❌ Not created |
| Integration Tests | VSIX ↔ Runtime API | ❌ Not created |
| E2E Tests | Task completion flow | ❌ Not created |
| Performance Tests | Sync latency | ❌ Not created |

---

## See Also

- [Five Lane Architecture](01_FIVE_LANE_ARCHITECTURE.md)
- [GAP Analysis](../GAP_ANALYSIS.md)
- [Merge Matrix](../MERGE_MATRIX.md)
- [WebUI Lane](02_WEBUI_LANE.md)
- [Runtime + Provider Lane](04_RUNTIME_PROVIDER_LANE.md)

---

*Document Version: 17.0*
*Generated: 2026-04-20*
