# Feature Truth Matrix

> **Release:** v7.2.14+full-cockpit
> **Branch:** feat/azure-voice-studio
> **Last updated:** 2026-04-18
> **Status:** AUDIT IN PROGRESS

This is a LIVE document. It is updated as audit passes run. Every row must reach all-green before release.

## Legend

- Code: TypeScript service file exists and compiles
- Wired: Message case in KiloProvider.ts + service instantiated in extension.ts
- UI: Settings tab component exists in webview-ui
- Runtime Proof: Feature tested live in running extension (pass B+)
- Evidence: Screenshot, log, or trace captured and filed in `docs/audit/EVIDENCE/`

| Status | Meaning |
|--------|---------|
| ✅ | Verified |
| ⬜ | Pending audit |
| ❌ | Failed / missing |

---

## Block A: SSH (Phases 17-25)

Service: `packages/kilo-vscode/src/services/ssh/SSHService.ts`
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/SSHTab.tsx`
Message routes: sshProfileSave, sshProfileDelete, sshConnect, sshDisconnect, sshOpenTerminal, sshBrowseFiles, sshFileOpen, sshFileDownload, sshFileUpload, sshFilePreview, sshFileDiff, sshFileSaveRemote, sshGetErrors, sshTailLogs

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| SSH profile CRUD | A | 17 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| SSH key auth | A | 18 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| SSH password auth | A | 19 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| SSH connect/disconnect | A | 20 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| SSH terminal | A | 21 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| SFTP browse | A | 22 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Remote file open | A | 23 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Remote file edit/save diff | A | 24 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Remote log tailing | A | 25 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block B: VPS (Phases 27-34)

Service: `packages/kilo-vscode/src/services/vps/VPSService.ts`
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/VPSTab.tsx`
Message routes: vpsServerAdd, vpsServerRemove, vpsRefreshMetrics, vpsServiceAction, vpsDockerAction, vpsDeploy, vpsRollback, vpsBackup

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| VPS server inventory | B | 27 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| VPS metrics dashboard | B | 28 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| VPS service start/stop/restart | B | 29 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| VPS Docker container actions | B | 30 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| VPS deploy | B | 31 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| VPS rollback | B | 32 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| VPS backup create | B | 33 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| VPS backup restore | B | 34 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block C: ZeroClaw (Phases 35-44)

Service: `packages/kilo-vscode/src/services/zeroclaw/ZeroClawService.ts`
Adapter: `packages/kilo-vscode/src/services/zeroclaw/HermesZeroClawAdapter.ts`
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/ZeroClawTab.tsx`
Message routes: zeroClawSubmitTask, zeroClawCancelTask, zeroClawRetryTask, zeroClawApproveTask, zeroClawRejectTask, zeroClawGetHistory

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| Task submission (low risk) | C | 35 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Task parameter validation | C | 36 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Task execution tracking | C | 37 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Task result display | C | 38 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Task cancel | C | 39 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Task retry | C | 40 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Buffered diff review | C | 41 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Medium-risk approval gate | C | 42 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| High-risk approval gate | C | 43 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Task history ledger | C | 44 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block D: Routing (Phases 45-52)

Service: `packages/kilo-vscode/src/services/routing/RoutingService.ts`
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/RoutingTab.tsx`
Message routes: routingTestProvider, routingConfigureKey, routingSetRole, routingSetMode, routingSetFallbackOrder, routingGetTraces, routingGetHealth

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| Claude contract routing | D | 45 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Claude role assignment | D | 46 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| MiniMax execution routing | D | 47 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| SiliconFlow fallback | D | 48 | ✅ | ✅ | ✅ | ⬜ | ⬜ | D-001 |
| Ollama local routing | D | 49 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| LM Studio local routing | D | 50 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Fallback chain ordering | D | 51 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Provider health check | D | 52 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block E: Memory (Phases 53-58)

Service: `packages/kilo-vscode/src/services/memory/MemoryService.ts`
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/MemoryTab.tsx`
Message routes: memoryGetStatus, memoryRecall, memoryWrite, memoryReconnect, memoryGetHistory, memorySetPermission, memoryRunDiagnostics, memoryGetRecallTraces

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| Shiba connectivity | E | 53 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Memory recall | E | 54 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Memory write | E | 55 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Project-scoped memory | E | 56 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Recall trace display | E | 57 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Memory permissions | E | 58 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block F: Training (Phases 59-66)

Service: `packages/kilo-vscode/src/services/training/TrainingService.ts`
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/TrainingTab.tsx`
Message routes: trainingGetJobs, trainingRegisterDataset, trainingValidateDataset, trainingLaunchJob, trainingPauseJob, trainingResumeCheckpoint, trainingCompareRuns, trainingExportModel, trainingDetectGPU

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| Dataset registry | F | 59 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Dataset validation | F | 60 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Training job launch | F | 61 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Training job monitoring | F | 62 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Training job pause | F | 63 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Checkpoint resume | F | 64 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Run comparison | F | 65 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Model export | F | 66 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block G: Speech (Phase 67)

Config: `kilo-code.new.speech` (VS Code settings namespace)
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/SpeechTab.tsx`
Message route: requestSpeechSettings (KiloProvider.ts line 906)
TTS endpoint: Azure Cognitive Services (`{region}.tts.speech.microsoft.com`)

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| Speech input/output | G | 67 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block H: Governance (Phases 68-70)

Service: `packages/kilo-vscode/src/services/governance/GovernanceService.ts`
Tab: `packages/kilo-vscode/webview-ui/src/components/settings/GovernanceTab.tsx`
Message routes: governanceSetTier, governanceApproveAction, governanceRejectAction, governanceAddDangerousAction, governanceToggleBlock, governanceGetAuditLog, governanceCreateVerdict, governanceExportAudit

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| Authority tier assignment | H | 68 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Approval request/grant/deny | H | 69 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Approval audit log | H | 70 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Block I: Release / Hermes / Integration (Phases 71-72)

Service: `packages/kilo-vscode/src/services/hermes/HermesClient.ts`
Pipeline: `packages/kilo-vscode/src/services/hermes/HermesPipeline.ts`
Status: `packages/kilo-vscode/src/services/hermes/HermesStatusService.ts`
Commands: `packages/kilo-vscode/src/commands/hermes.ts`

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| VSIX build + packaging | I | 71 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Release verdict + rollback | I | 72 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Cross-cutting: Hermes Integration

These components span multiple blocks and are verified during integration passes (D+E).

| Feature | Block | Phase | Code | Wired | UI | Runtime Proof | Evidence | Defect IDs |
|---------|-------|-------|------|-------|----|---------------|----------|------------|
| Hermes client connectivity | I | 71-72 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Hermes pipeline routing | I | 71-72 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Hermes provider preset | I | 71-72 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| Hermes status polling | I | 71-72 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |
| HermesZeroClaw adapter | I | 35-44 | ✅ | ✅ | ✅ | ⬜ | ⬜ | |

---

## Summary

| Block | Features | Code | Wired | UI | Runtime Proof | Evidence |
|-------|----------|------|-------|----|---------------|----------|
| A: SSH | 9 | 9/9 | 9/9 | 9/9 | 0/9 | 0/9 |
| B: VPS | 8 | 8/8 | 8/8 | 8/8 | 0/8 | 0/8 |
| C: ZeroClaw | 10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 |
| D: Routing | 8 | 8/8 | 8/8 | 8/8 | 0/8 | 0/8 |
| E: Memory | 6 | 6/6 | 6/6 | 6/6 | 0/6 | 0/6 |
| F: Training | 8 | 8/8 | 8/8 | 8/8 | 0/8 | 0/8 |
| G: Speech | 1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 |
| H: Governance | 3 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 |
| I: Release/Hermes | 7 | 7/7 | 7/7 | 7/7 | 0/7 | 0/7 |
| **Total** | **60** | **60/60** | **60/60** | **60/60** | **0/60** | **0/60** |

> Note: The 72 phases map to 60 distinct features because many phases contribute to the same feature (e.g., phases 17-21 all contribute to SSH connectivity features). Each row above represents a testable capability, not a phase number.
