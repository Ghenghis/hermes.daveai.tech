# Audit Framework

> **Release:** v7.2.14+full-cockpit
> **Branch:** feat/azure-voice-studio
> **Last updated:** 2026-04-18
> **Status:** ACTIVE

This document defines the audit process for the KiloCode V4 full-cockpit release. It governs how features are verified, defects are tracked, and the release verdict is determined.

---

## 1. Audit Swarm Model

The audit is conducted by a coordinated swarm of agents, each with a distinct role. No single agent both fixes and closes a defect.

### Lead Auditor (Claude Opus 4.7)
- Owns the master audit contract
- Reads the entire codebase to build ground truth
- Decomposes work into audit passes (A-F)
- Assigns passes to builder and challenger agents
- Makes final pass/fail decisions on each pass
- Writes the release verdict
- Can reopen any defect at any time

### Builder Agents (Claude Opus 4.7)
- Fix issues found during audit passes
- Implement missing wiring, correct broken logic, add error handling
- Submit fixes with evidence of the fix
- May NOT close their own defects

### Challenger Agents (Claude Opus 4.7)
- Attempt to break claims made by builder agents
- Test failure paths, edge cases, invalid inputs
- Reopen defects that were insufficiently fixed
- Verify that error messages are clear and actionable
- Run adversarial tests against each subsystem

### Execution Layer
- Runs commands: build, typecheck, test, package
- Produces raw output (stdout, stderr, exit codes)
- Captures screenshots and logs
- Manages the VSIX build pipeline

### Evidence Steward
- Updates the Feature Truth Matrix after each pass
- Appends entries to the Run Ledger
- Files evidence artifacts in `docs/audit/EVIDENCE/`
- Updates the Defect Ledger when defects are opened, fixed, or closed
- Updates the Release Verdict as gates are satisfied
- Maintains cross-references between all truth documents

---

## 2. Audit Passes

### Pass A: Static Structure Audit

**Goal:** Verify that every feature has code, wiring, and UI surface -- without running the extension.

**Checks:**
1. Every settings tab exists as a `.tsx` component in `webview-ui/src/components/settings/`
2. Every service exists as a TypeScript class in `src/services/`
3. Every service is imported and instantiated in `extension.ts`
4. Every message type has a `case` in `KiloProvider.ts`
5. Every service has proper disposal (subscriptions cleaned up)
6. No unused imports, no circular dependencies
7. `tsc --noEmit` passes across all 12 packages
8. ESLint passes (if configured)

**Artifacts:** Tab list, service list, message route list, import graph, typecheck output

**Tabs to verify (22 total):**
- AboutKiloCodeTab, AutoApproveTab, AutocompleteTab, BrowserTab, CheckpointsTab, ContextTab, DisplayTab, ExperimentalTab, LanguageTab, ModelsTab, NotificationsTab, ProvidersTab, SpeechTab, AgentBehaviourTab, CommitMessageTab, GovernanceTab, VPSTab, TrainingTab, ZeroClawTab, RoutingTab, MemoryTab, SSHTab

**Services to verify (9 subsystems):**
- SSHService, VPSService, ZeroClawService, RoutingService, MemoryService, TrainingService, GovernanceService, HermesClient + HermesPipeline + HermesStatusService, Speech (inline in KiloProvider)

---

### Pass B: Subsystem Runtime Audit

**Goal:** Verify that each subsystem initializes, handles a happy-path request, and produces expected output.

**Subsystems and their tests:**

| Subsystem | Init Test | Happy Path | Expected Output |
|-----------|-----------|------------|-----------------|
| SSH | SSHService instantiates without error | Profile save + connect | Connection status message |
| VPS | VPSService instantiates without error | Server add + metrics refresh | Metrics data in UI |
| ZeroClaw | ZeroClawService + adapter instantiate | Submit low-risk task | Task result displayed |
| Routing | RoutingService instantiates, providers loaded | Route a contract task to Claude | Route trace showing Claude selected |
| Memory | MemoryService instantiates, Shiba reachable | Write + recall | Recalled content matches written |
| Training | TrainingService instantiates | Register dataset | Dataset appears in registry |
| Governance | GovernanceService instantiates | Set tier + approve action | Approval in audit log |
| Speech | Speech settings load from config | TTS request to Azure | Audio output or valid error |

---

### Pass C: Failure-Path Audit

**Goal:** Verify that every subsystem handles failures gracefully -- no crashes, no silent swallowing, clear error messages.

| Failure Scenario | Subsystem | Expected Behavior |
|-----------------|-----------|-------------------|
| Bad SSH credentials | SSH | Error message with "authentication failed", no crash |
| Unreachable host | SSH, VPS | Timeout with clear message, connection status updated |
| Out-of-scope task | ZeroClaw | Rejection with reason, task status set to rejected |
| Provider API key invalid | Routing | Provider marked unhealthy, fallback to next provider |
| Provider unreachable | Routing | Timeout, fallback chain activated |
| Empty recall (no matching memories) | Memory | Empty result set with informational message, no error |
| Shiba unreachable | Memory | Degraded status, reconnect offered |
| Failed training job | Training | Job status set to failed, error details preserved |
| Dataset validation failure | Training | Validation errors listed, job launch blocked |
| Denied action (governance block) | Governance | Action blocked with policy reason, logged in audit trail |
| Speech service unavailable | Speech | Graceful degradation, text-only fallback |
| Azure TTS invalid key | Speech | Clear error, settings link offered |
| Hermes disconnected | Hermes | Status updated, queue paused, reconnect offered |

---

### Pass D: Integration Audit

**Goal:** Verify that subsystems work together across boundaries.

**Integration paths to test:**

1. **Bot -> Hermes -> KiloCode**
   - A message from Telegram/Discord reaches Hermes
   - Hermes routes it through the pipeline to KiloCode
   - KiloCode processes and responds back through Hermes

2. **KiloCode -> Hermes -> ZeroClaw**
   - KiloCode initiates a task
   - Hermes routes it to ZeroClaw for bounded execution
   - ZeroClaw executes, result flows back to KiloCode

3. **Route trace -> Ledger**
   - A routed request produces a trace
   - The trace is appended to the routing ledger
   - The trace is visible in the Routing tab

4. **Memory write -> Recall**
   - An agent writes a memory during task execution
   - A subsequent task recalls that memory
   - The recall trace shows the match

5. **Approval -> Execution**
   - A high-risk task triggers an approval request
   - The governance tab shows the pending approval
   - Approval grants execution, result logged

---

### Pass E: E2E Product Audit

**Goal:** Verify complete user-facing workflows from start to finish.

**Workflows to test:**

1. **Contract -> Execution -> Result -> Speech**
   - Submit a contract-level task
   - Claude processes contract, MiniMax executes
   - Result displayed in cockpit
   - Result spoken via TTS (if speech enabled)

2. **Fallback Chain**
   - Primary provider (Claude) fails intentionally
   - Routing falls back to MiniMax
   - If MiniMax fails, falls back to SiliconFlow
   - Task still completes, trace shows fallback path

3. **Memory Continuity**
   - Agent A writes memory in session 1
   - Agent B recalls that memory in session 2
   - Cross-agent memory verified

4. **Project Creation (full lifecycle)**
   - Spec defined
   - Files created
   - Commands run
   - Results verified
   - Activity logged
   - Memory written
   - Announcement sent (via Hermes)

---

### Pass F: Release Audit

**Goal:** Verify that the release artifact is clean, installable, and rollback-ready.

**Checks:**
1. VSIX builds without errors
2. VSIX installs on a clean VS Code instance
3. Extension activates without errors in output channel
4. All 22 tabs render without blank screens or console errors
5. All services initialize (check output channel)
6. Extension deactivates cleanly
7. Uninstall leaves no orphaned state
8. Release notes are accurate and complete
9. Rollback plan is documented and tested
10. GitHub release artifacts are uploaded (if applicable)

---

## 3. Evidence Gates

Four gates must be satisfied before the release verdict can be PASS.

### Gate 1: Subsystem Proof

Every subsystem (SSH, VPS, ZeroClaw, Routing, Memory, Training, Governance, Speech) must have:
- A successful happy-path test (Pass B)
- A successful failure-path test (Pass C)
- Logs captured during both tests
- At least one screenshot showing the UI state
- A corresponding entry in the Run Ledger

### Gate 2: Routing Proof

The multi-provider routing system must demonstrate:
- Claude is used for contract-level tasks (planning, architecture)
- MiniMax is used for standard execution tasks (code generation, repetitive fixes)
- Fallback is proven: when the primary provider fails, the next provider in the chain handles the task
- Local providers (Ollama, LM Studio) stay local -- no data sent to cloud APIs
- Route traces are captured and match expected routing decisions

### Gate 3: Memory Proof

The memory system must demonstrate:
- A write operation stores data that persists
- A recall operation retrieves previously written data
- Cross-agent recall works (agent A writes, agent B recalls)
- A failed recall (no matching memories) is surfaced clearly, not silently swallowed

### Gate 4: Project Creation Proof

A complete project creation workflow must demonstrate:
- Specification is defined and accepted
- Files are created on disk
- Commands are executed (e.g., npm init, git init)
- Results are verified (files exist, commands succeeded)
- Activity is logged in the task ledger
- Memory is written for future recall
- Announcement is sent via Hermes (Telegram/Discord)

---

## 4. Multi-Layered Correction Loop

When a defect is found, it passes through multiple hands before closure:

```
Discovery (any agent)
    |
    v
Owner fixes (Builder agent)
    |
    v
Confirmer reruns proof (different Builder or Lead Auditor)
    |
    v
Challenger break-tests (Challenger agent)
    |
    v
Lead Auditor closes or reopens
```

**Rules:**
- The agent that fixes a defect (Owner) may NOT be the agent that closes it (Closer)
- The Confirmer must rerun the exact test that originally failed
- The Challenger must attempt at least one adversarial variation
- The Lead Auditor makes the final call: Closed or Reopened
- Reopened defects restart the loop from Owner
- All transitions are logged in the Defect Ledger with timestamps

---

## 5. Provider Stack

### Cloud Providers

| Provider | Role | API Endpoint | Use Cases |
|----------|------|-------------|-----------|
| Claude Opus 4.7 | Master auditor, contract controller, final verdict | Anthropic API | Architecture decisions, contract decomposition, audit verdicts, complex reasoning |
| MiniMax | Always-on standard execution worker | MiniMax API | Repetitive fixes, code generation, parallel tasks, bulk operations |
| SiliconFlow | Fallback, overflow | `https://api.siliconflow.com/v1` (international) | Fallback when Claude/MiniMax unavailable, overflow during peak load |

**Note on SiliconFlow endpoints:**
- International: `api.siliconflow.com` -- use this for non-China deployments
- China: `api.siliconflow.cn` -- only for China-region deployments
- Dashboard/docs: `cloud.siliconflow.com` -- NOT an API endpoint
- See defect D-001 in the Defect Ledger for endpoint verification status

### Local Providers

| Provider | Role | Location | Use Cases |
|----------|------|----------|-----------|
| Ollama | Local private inference | Workstation | Embeddings, memory operations, privacy-sensitive tasks |
| LM Studio | Local private inference | Workstation | Alternative local inference, model testing |

### Integration Services

| Service | Role | Connectivity | Use Cases |
|---------|------|-------------|-----------|
| Hermes | Routing, memory, policy, ledgers | Telegram + Discord | Cross-agent communication, task routing, memory operations, policy enforcement |
| ZeroClaw | Bounded execution | Via Hermes adapter | Test runs, file operations, sandboxed code execution |
| KiloCode | Cockpit, proofs, approval UI | VS Code extension | User interface, evidence capture, approval workflows, log viewing |

---

## 6. Ecosystem Integration

### Infrastructure

| Component | Details |
|-----------|---------|
| VPS | daveai.tech (user's production website) |
| Workstation | MSI X570S, RTX 3090 Ti 24GB, 128GB DDR4 |
| Local inference | LM Studio + Ollama (both running on workstation) |
| Docker | Available on workstation and VPS when needed |

### External Tool Connections

| Tool | Direction | Purpose |
|------|-----------|---------|
| Windsurf | Bidirectional | Alternative IDE, cross-IDE workflows |
| Claude Desktop | Bidirectional | Desktop agent communication |
| Telegram | Via Hermes | Bot-to-human communication, notifications |
| Discord | Via Hermes | Bot-to-human communication, team channels |

---

## 7. Release Checklist

All items must be checked before the release verdict can be PASS.

| # | Check | Pass | Status |
|---|-------|------|--------|
| 1 | Build passes (`npm run build` or equivalent) | F | ⬜ |
| 2 | Typecheck passes (12/12 packages, `tsc --noEmit`) | A | ⬜ |
| 3 | Extension activates on clean install (no errors in output channel) | F | ⬜ |
| 4 | All 22 tabs render (no blank screens, no console errors) | A, F | ⬜ |
| 5 | All 9 services initialize (confirmed via output channel logs) | B | ⬜ |
| 6 | 3 E2E workflows pass (contract-execution-result, fallback chain, memory continuity) | E | ⬜ |
| 7 | Project-creation test passes (spec-files-commands-runs-logged-memorized-announced) | E | ⬜ |
| 8 | No open Critical defects | -- | ⬜ |
| 9 | Release verdict written and signed | -- | ⬜ |
| 10 | Rollback notes written and tested | F | ⬜ |

---

## 8. Truth Document Locations

All live truth documents for this audit:

| Document | Path | Purpose |
|----------|------|---------|
| Feature Truth Matrix | `docs/audit/FEATURE_TRUTH_MATRIX.md` | Tracks code/wired/UI/runtime/evidence status per feature |
| Defect Ledger | `docs/audit/DEFECT_LEDGER.md` | Tracks all defects with severity, status, and evidence |
| Run Ledger | `docs/audit/RUN_LEDGER.jsonl` | Append-only log of every test run |
| Release Verdict | `docs/audit/RELEASE_VERDICT.md` | Final pass/fail decision with gate status |
| Audit Framework | `docs/audit/AUDIT_FRAMEWORK.md` | This document -- process definition |
| Evidence Directory | `docs/audit/EVIDENCE/` | Screenshots, logs, traces, artifacts |

### Relationship to Kit Truth Files

The files at `docs/kilocode_v4_2_hardened_kit/02_TRUTH/` are the original templates that defined the audit schema. The files at `docs/audit/` are the LIVE working copies that are updated as the audit runs. The templates are not modified during the audit.

---

## 9. How to Run the Audit

### Starting a new pass

1. Lead Auditor announces the pass (A-F) and assigns agents
2. Evidence Steward creates a Run Ledger entry with status "in-progress"
3. Assigned agents execute their checks
4. Results are appended to the Run Ledger as JSONL entries
5. Feature Truth Matrix is updated based on results
6. Any failures are opened as defects in the Defect Ledger
7. Evidence Steward updates the Release Verdict pass status

### Closing a pass

1. All checks in the pass have Run Ledger entries
2. All failures have corresponding defects
3. Lead Auditor reviews and marks the pass as green (all pass), yellow (non-blocking issues), or red (blocking issues)
4. Release Verdict is updated

### Closing a defect

1. Owner submits a fix with evidence
2. Confirmer reruns the original test
3. Challenger attempts to break the fix
4. Lead Auditor reviews all evidence
5. If satisfied: status -> Closed, Closer field populated
6. If not: status -> Reopened, loop restarts
