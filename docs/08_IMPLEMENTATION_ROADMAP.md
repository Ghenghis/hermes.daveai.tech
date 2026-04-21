# Implementation Roadmap

Contract-kit v17 implementation spans 36 phases organized into 6 lanes, with acceptance gates (A through G) marking transitions between major milestones. This roadmap defines the chronological sequence, lane assignments, and concrete acceptance criteria for each phase.

## Roadmap Overview

| Lane | Phases | Focus |
|------|--------|-------|
| Core Infrastructure | 1-8 | Foundation, messaging, state management |
| WebUI Lane | 9-16 | Human-facing interface, approval workflows |
| KiloCode Lane | 17-24 | Agentic coding integration |
| Runtime + Provider Lane | 25-30 | LLM provider abstraction, task execution |
| Hermes + ZeroClaw Lane | 31-34 | Multi-agent coordination, deployment |
| Proof Lane | 35-36 | Acceptance, evidence, compliance |

---

## Acceptance Gates

Gates are formal checkpoints requiring demonstrable evidence before progression. Each gate has a defined set of acceptance criteria, evidence types, and the approving authority.

### Gate A: Foundation Proven

**Authority**: Technical lead  
**Gatekeepers**: Core Infrastructure lane agent  
**Criteria**:
- All 6 NATS streams provisioned and verified with `nats stream ls`
- Stream health check returns all streams in `ACTIVE` state
- Provider health endpoints respond within 500ms
- No hardcoded paths outside `HERMES_HOME`
- Full test suite passes at >95% coverage

**Evidence Required**:
- `nats_stream_provision.txt`: Output of `nats stream ls` showing all 6 streams
- `provider_health_check.json`: JSON results from health endpoint probes
- `test_coverage.html`: Coverage report showing >95%
- `path_audit.txt`: Output of path audit grep showing no hardcoded paths

---

### Gate B: Messaging Topology Verified

**Authority**: Messaging architect  
**Gatekeepers**: Core Infrastructure lane agent, Hermes lane agent  
**Criteria**:
- All consumer groups defined and connected
- End-to-end packet delivery tested across all 6 subject namespaces
- Packet round-trip latency < 100ms for control packets
- No message loss under 10x normal load for 60 seconds
- Dead letter queue configured and functional

**Evidence Required**:
- `consumer_check.txt`: Output of `nats consumers ls` for each stream
- `e2e_delivery_test.json`: Latency and loss measurements
- `dlq_config.json`: DLQ stream configuration and test result

---

### Gate C: Schema Compliance

**Authority**: Protocol lead  
**Gatekeepers**: Core Infrastructure lane agent, all lane agents  
**Criteria**:
- All 4 packet schemas (`ControlPacket`, `TaskPacket`, `CompletionPacket`, `RepairPacket`) validate against `packet_schema.json` without errors
- `runtime_settings_schema.json` validates all provider configurations
- `nats_subjects.json` matches actual NATS configuration
- No schema violations in 10,000-sample packet generation stress test
- All external repository integrations declare their license and attribution

**Evidence Required**:
- `schema_validation.json`: Output of JSON Schema validator on all packets
- `stress_test.json`: 10,000-sample test results showing 0 violations
- `attribution_manifest.json`: License and attribution declarations for each external repo

---

### Gate D: Lane Integration Points Operational

**Authority**: Integration lead  
**Gatekeepers**: Each lane's primary agent  
**Criteria**:
- WebUI lane can receive, display, and respond to task updates via WebSocket
- KiloCode lane can spawn, monitor, and terminate agentic coding sessions
- Runtime lane can route tasks to all 4 providers (minimax, siliconflow, lmstudio, ollama)
- Hermes lane can delegate tasks and receive delegated tasks
- ZeroClaw lane can execute deploy, scale, and rollback operations
- No lane blocks another lane's message flow

**Evidence Required**:
- `lane_integration_test.json`: Results of each lane's integration test suite
- `cross_lane_flow.txt`: End-to-end test of task flowing through all relevant lanes
- `latency_budget.json`: Per-lane latency measurements within budget

---

### Gate E: Security Model Verified

**Authority**: Security lead  
**Gatekeepers**: Security lane agent, external security auditor  
**Criteria**:
- All secrets loaded from environment or encrypted vault, never in config files
- Scope boundaries enforced: file operations cannot escape `allowed_dirs`
- Mode transitions follow `mode_transition_policy` (approvals logged)
- Audit trail captures all packet send/receive events
- Provider API keys rotate without downtime
- Penetration test shows no critical or high vulnerabilities

**Evidence Required**:
- `security_audit.html`: Security audit report
- `secrets_audit.txt`: Output showing no secrets in config files
- `scope_test.json`: File operation scope boundary test results
- `audit_trail_sample.json`: Sample of audit trail entries
- `mode_transition_log.json`: Mode change approvals and denials

---

### Gate F: Evidence and Acceptance System Functional

**Authority**: QA lead  
**Gatekeepers**: WebUI lane agent, acceptance engine agent  
**Criteria**:
- Every completed task produces a `CompletionPacket` with all required evidence
- Acceptance criteria from `TaskPacket` are evaluated against `CompletionPacket`
- Acceptance results show correct pass/fail/partial determination
- Evidence bundles are retrievable by `bundle_id` within 2 seconds
- Screenshot capture triggers on `screenshots_required > 0`
- Metrics (token usage, latency, error rate) recorded per task

**Evidence Required**:
- `acceptance_test.json`: Results of acceptance system test suite
- `evidence_retrieval.json`: Retrieval latency measurements
- `screenshot_capture_test.json`: Screenshot capture verification
- `metrics_collected.json`: Sample of collected metrics

---

### Gate G: Production Readiness

**Authority**: Release manager  
**Gatekeepers**: All lane agents, external compliance auditor  
**Criteria**:
- Zero unblocked critical or high severity issues
- All 6 acceptance gates passed and documented
- Runbook complete for each failure mode
- Rollback procedure tested and documented
- External legal review of AGPL-attributed components complete
- Customer-facing documentation complete
- Disaster recovery plan tested

**Evidence Required**:
- `gate_summary.json`: All 6 gates with pass/fail and evidence references
- `runbook_index.json`: Index of all runbooks
- `rollback_test.json`: Rollback procedure test results
- `legal_review.json`: Legal sign-off on AGPL components
- `dr_test.json`: Disaster recovery test results

---

## Phase Sequence

### Phase 1: NATS JetStream Provisioning

**Lane**: Core Infrastructure  
**Duration**: 1 day  
**Prerequisites**: None

**Tasks**:
- Install and configure NATS server v2.10+
- Provision 6 JetStream streams matching `nats_subjects.json`
- Configure retention, max bytes, and replica settings per stream
- Create consumer groups for each stream
- Set up TLS for NATS connections
- Configure authentication (token or nkeys)

**Acceptance**: Gate A  
**Evidence**: `nats_stream_provision.txt`

---

### Phase 2: Packet Schema Implementation

**Lane**: Core Infrastructure  
**Duration**: 2 days  
**Prerequisites**: Phase 1

**Tasks**:
- Implement JSON Schema validators for all 4 packet types
- Add schema validation to NATS publish/subscribe paths
- Create packet factory functions with validation
- Implement schema versioning for forward compatibility
- Add schema evolution strategy documentation

**Acceptance**: Gate C  
**Evidence**: `schema_validation.json`

---

### Phase 3: Provider Health Monitoring

**Lane**: Core Infrastructure  
**Duration**: 1 day  
**Prerequisites**: Phase 1

**Tasks**:
- Implement health check endpoints for all 4 providers
- Build health check scheduler with configurable intervals
- Implement unhealthy threshold and auto-disable logic
- Add health status to runtime settings
- Create provider fallback chain configuration

**Acceptance**: Gate A  
**Evidence**: `provider_health_check.json`

---

### Phase 4: Message Bus Integration Layer

**Lane**: Core Infrastructure  
**Duration**: 2 days  
**Prerequisites**: Phase 1, Phase 2

**Tasks**:
- Implement `MessageBus` class abstracting NATS
- Add connection pooling and automatic reconnection
- Implement publisher confirms
- Add dead letter queue handling
- Create message serialization/deserialization layer
- Implement request/reply pattern for control packets

**Acceptance**: Gate B  
**Evidence**: `e2e_delivery_test.json`

---

### Phase 5: Task Lifecycle State Machine

**Lane**: Core Infrastructure  
**Duration**: 2 days  
**Prerequisites**: Phase 2

**Tasks**:
- Define task states: `pending`, `running`, `blocked`, `retry`, `close`, `reopen`, `blocked`
- Implement state transition validation
- Add state transition audit logging
- Implement deadline enforcement
- Add priority queue management
- Create task cancellation support

**Acceptance**: Gate A  
**Evidence**: `test_coverage.html`

---

### Phase 6: Evidence Storage and Retrieval

**Lane**: Core Infrastructure  
**Duration**: 2 days  
**Prerequisites**: Phase 1, Phase 2

**Tasks**:
- Implement evidence bundle storage (file-based, S3-compatible)
- Create evidence metadata index
- Implement bundle retrieval by ID
- Add evidence retention and expiry policies
- Implement evidence bundle signing for integrity
- Add evidence compression for large bundles

**Acceptance**: Gate F  
**Evidence**: `evidence_retrieval.json`

---

### Phase 7: Audit Trail System

**Lane**: Core Infrastructure  
**Duration**: 2 days  
**Prerequisites**: Phase 4

**Tasks**:
- Implement audit event capture on all packet send/receive
- Create audit log format with required fields (timestamp, identity, action, result)
- Implement audit log rotation and archival
- Add audit log query API
- Implement audit log tamper detection (hash chaining)
- Create audit report generator

**Acceptance**: Gate E  
**Evidence**: `audit_trail_sample.json`

---

### Phase 8: Configuration Management System

**Lane**: Core Infrastructure  
**Duration**: 1 day  
**Prerequisites**: Phase 3

**Tasks**:
- Implement YAML configuration loader with schema validation
- Add environment variable override support
- Create config hot-reload without restart
- Implement profile support for multi-instance isolation
- Add config version migration system
- Create config diff and rollback

**Acceptance**: Gate A  
**Evidence**: `test_coverage.html`

---

### Gate A: Foundation Proven

All criteria verified. Core Infrastructure lane complete.

---

### Phase 9: WebUI Project Scaffold

**Lane**: WebUI  
**Duration**: 1 day  
**Prerequisites**: Gate A

**Tasks**:
- Set up React/Next.js project structure
- Configure build tooling (Vite or Next.js)
- Add TypeScript configuration
- Set up CSS/skin engine integration
- Create component library foundation
- Add WebSocket client for real-time updates

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 10: Task Dashboard

**Lane**: WebUI  
**Duration**: 2 days  
**Prerequisites**: Phase 9

**Tasks**:
- Implement task list view with filtering and sorting
- Create task detail panel
- Add task state visualization (phase indicator, progress bar)
- Implement real-time updates via WebSocket subscription
- Add search and pagination
- Create task creation form

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 11: Approval Workflow UI

**Lane**: WebUI  
**Duration**: 2 days  
**Prerequisites**: Phase 9

**Tasks**:
- Implement approval request dialog
- Add approval/deny action buttons
- Create approval history view
- Implement escalation path UI
- Add risk level indicator
- Create approval audit trail display

**Acceptance**: Gate D, Gate F  
**Evidence**: `acceptance_test.json`

---

### Phase 12: Evidence Viewer

**Lane**: WebUI  
**Duration**: 2 days  
**Prerequisites**: Phase 6, Phase 10

**Tasks**:
- Implement evidence bundle viewer
- Add trace visualization
- Create screenshot gallery
- Implement log viewer with search
- Add metrics charts and graphs
- Create evidence download functionality

**Acceptance**: Gate F  
**Evidence**: `evidence_retrieval.json`, `screenshot_capture_test.json`

---

### Phase 13: WebUI Authentication

**Lane**: WebUI  
**Duration**: 1 day  
**Prerequisites**: Phase 9

**Tasks**:
- Implement session management
- Add role-based access control
- Integrate with Hermes auth system
- Implement API key management UI
- Add audit log viewer for admin

**Acceptance**: Gate E  
**Evidence**: `security_audit.html`

---

### Phase 14: Real-time Notifications

**Lane**: WebUI  
**Duration**: 1 day  
**Prerequisites**: Phase 10

**Tasks**:
- Implement WebSocket notification delivery
- Add notification bell icon with badge
- Create notification history panel
- Implement browser push notifications
- Add sound alerts for critical events

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 15: WebUI Skin Engine

**Lane**: WebUI  
**Duration**: 1 day  
**Prerequisites**: Phase 9

**Tasks**:
- Integrate skin engine with WebUI theming
- Add skin preview in settings
- Implement custom skin upload
- Create skin persistence across sessions
- Add color palette customization

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 16: WebUI End-to-End Tests

**Lane**: WebUI  
**Duration**: 1 day  
**Prerequisites**: Phase 15

**Tasks**:
- Write Playwright E2E tests for all major flows
- Implement approval workflow E2E tests
- Add evidence viewer E2E tests
- Implement performance benchmarks
- Create visual regression tests
- Add accessibility tests (axe-core)

**Acceptance**: Gate D, Gate F  
**Evidence**: `acceptance_test.json`

---

### Gate B + C: Messaging Verified, Schemas Compliant

All criteria verified. WebUI lane functional.

---

### Phase 17: KiloCode Integration Scaffold

**Lane**: KiloCode  
**Duration**: 1 day  
**Prerequisites**: Gate A, Gate B

**Tasks**:
- Set up KiloCode agent environment
- Configure KiloCode CLI for contract-kit integration
- Implement task result parser
- Add KiloCode session lifecycle hooks
- Create session recovery logic
- Implement workspace isolation

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 18: Agentic Coding Session Manager

**Lane**: KiloCode  
**Duration**: 2 days  
**Prerequisites**: Phase 17

**Tasks**:
- Implement session spawn and termination
- Add working directory management
- Create session state persistence
- Implement concurrent session limits
- Add session priority management
- Create session timeout enforcement

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 19: File Operation Enforcement

**Lane**: KiloCode  
**Duration**: 2 days  
**Prerequisites**: Phase 17

**Tasks**:
- Implement scope boundary enforcement
- Add allowed directory validation
- Create denied pattern matching
- Implement file size limits
- Add read-only path enforcement
- Create operation audit logging

**Acceptance**: Gate E  
**Evidence**: `scope_test.json`

---

### Phase 20: Terminal Tool Integration

**Lane**: KiloCode  
**Duration**: 2 days  
**Prerequisites**: Phase 17

**Tasks**:
- Integrate terminal tool with KiloCode sessions
- Implement command allowlist enforcement
- Add environment variable injection
- Create environment variable restrictions
- Implement terminal output capture
- Add terminal session reuse

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 21: Tool Permission System

**Lane**: KiloCode  
**Duration**: 1 day  
**Prerequisites**: Phase 19, Phase 20

**Tasks**:
- Implement tool permission model
- Add permission check middleware
- Create permission escalation workflow
- Implement tool usage tracking
- Add permission audit logging
- Create permission policy configuration

**Acceptance**: Gate E  
**Evidence**: `security_audit.html`

---

### Phase 22: KiloCode Prompt Templates

**Lane**: KiloCode  
**Duration**: 1 day  
**Prerequisites**: Phase 17

**Tasks**:
- Create phase-specific prompt templates
- Implement prompt injection system
- Add context window management
- Create prompt versioning
- Implement prompt caching
- Add prompt A/B testing support

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 23: Multi-Agent Delegation

**Lane**: KiloCode  
**Duration**: 2 days  
**Prerequisites**: Phase 18

**Tasks**:
- Implement cross-agent delegation protocol
- Add delegation timeout management
- Create delegation result aggregation
- Implement delegation retry logic
- Add delegation failure handling
- Create delegation audit trail

**Acceptance**: Gate D  
**Evidence**: `cross_lane_flow.txt`

---

### Phase 24: KiloCode Test Suite

**Lane**: KiloCode  
**Duration**: 1 day  
**Prerequisites**: Phase 23

**Tasks**:
- Write integration tests for session manager
- Add scope boundary tests
- Implement tool permission tests
- Create delegation tests
- Add performance benchmarks
- Implement chaos testing

**Acceptance**: Gate D, Gate E  
**Evidence**: `security_audit.html`

---

### Gate D: Lane Integration Points Operational

All lane integration points verified and operational.

---

### Phase 25: LLM Provider Abstraction Layer

**Lane**: Runtime + Provider  
**Duration**: 2 days  
**Prerequisites**: Gate A

**Tasks**:
- Implement provider interface abstraction
- Add provider implementations for all 4 providers
- Create provider factory
- Implement provider health aggregation
- Add provider metrics collection
- Create provider cost tracking

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 26: Model Routing Engine

**Lane**: Runtime + Provider  
**Duration**: 2 days  
**Prerequisites**: Phase 25

**Tasks**:
- Implement model selection based on task requirements
- Add context window aware routing
- Create load balancing across providers
- Implement model fallback chains
- Add model preference respect
- Create routing policy configuration

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 27: Task Execution Engine

**Lane**: Runtime + Provider  
**Duration**: 2 days  
**Prerequisites**: Phase 5, Phase 26

**Tasks**:
- Implement task execution loop
- Add timeout enforcement
- Create retry with backoff logic
- Implement circuit breaker pattern
- Add execution cancellation support
- Create execution state persistence

**Acceptance**: Gate A  
**Evidence**: `test_coverage.html`

---

### Phase 28: Token and Cost Management

**Lane**: Runtime + Provider  
**Duration**: 1 day  
**Prerequisites**: Phase 25

**Tasks**:
- Implement token counting and budgeting
- Add cost calculation per provider
- Create spend limits per project
- Implement spend alerts
- Add token usage reports
- Create cost allocation by task/project

**Acceptance**: Gate D  
**Evidence**: `metrics_collected.json`

---

### Phase 29: Prompt Caching Implementation

**Lane**: Runtime + Provider  
**Duration**: 2 days  
**Prerequisites**: Phase 26

**Tasks**:
- Implement Anthropic prompt caching pattern
- Add cache key generation
- Create cache invalidation policy
- Implement cache hit tracking
- Add cache efficiency metrics
- Create cache warming for common prompts

**Acceptance**: Gate D  
**Evidence**: `metrics_collected.json`

---

### Phase 30: Runtime Health Dashboard

**Lane**: Runtime + Provider  
**Duration**: 1 day  
**Prerequisites**: Phase 3, Phase 28

**Tasks**:
- Implement health metrics aggregation
- Create provider status dashboard
- Add token usage visualization
- Implement cost tracking dashboard
- Create error rate monitoring
- Add alert configuration UI

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Gate E: Security Model Verified

Security model verified. Runtime lane complete.

---

### Phase 31: Hermes Agent Integration

**Lane**: Hermes + ZeroClaw  
**Duration**: 2 days  
**Prerequisites**: Gate A, Gate D

**Tasks**:
- Integrate Hermes CLI for delegation
- Implement Hermes message protocol
- Add Hermes session management
- Create context sharing protocol
- Implement cross-instance communication
- Add Hermes skill command support

**Acceptance**: Gate D  
**Evidence**: `cross_lane_flow.txt`

---

### Phase 32: Multi-Agent Coordination

**Lane**: Hermes + ZeroClaw  
**Duration**: 2 days  
**Prerequisites**: Phase 31

**Tasks**:
- Implement multi-agent task distribution
- Add agent capability advertisement
- Create agent selection algorithm
- Implement workload rebalancing
- Add coordination deadlock prevention
- Create agent priority system

**Acceptance**: Gate D  
**Evidence**: `cross_lane_flow.txt`

---

### Phase 33: ZeroClaw Deployment Integration

**Lane**: Hermes + ZeroClaw  
**Duration**: 2 days  
**Prerequisites**: Phase 31

**Tasks**:
- Integrate ZeroClaw deployment API
- Implement deployment workflow
- Add scaling operations
- Create rollback procedures
- Implement health check integration
- Add deployment approval workflow

**Acceptance**: Gate D  
**Evidence**: `lane_integration_test.json`

---

### Phase 34: Incident Management

**Lane**: Hermes + ZeroClaw  
**Duration**: 1 day  
**Prerequisites**: Phase 7, Phase 33

**Tasks**:
- Implement incident detection and classification
- Add incident alert routing
- Create incident timeline view
- Implement resolution workflow
- Add post-mortem generation
- Create incident metrics

**Acceptance**: Gate E  
**Evidence**: `incident_test.json`

---

### Gate F: Evidence and Acceptance System Functional

All acceptance criteria verified. Hermes + ZeroClaw lane complete.

---

### Phase 35: Acceptance Engine Finalization

**Lane**: Proof  
**Duration**: 2 days  
**Prerequisites**: Gate F

**Tasks**:
- Implement acceptance criteria evaluation engine
- Add acceptance result aggregation
- Create acceptance report generator
- Implement acceptance threshold configuration
- Add acceptance history tracking
- Create acceptance API

**Acceptance**: Gate G  
**Evidence**: `acceptance_test.json`

---

### Phase 36: Documentation and Runbooks

**Lane**: Proof  
**Duration**: 2 days  
**Prerequisites**: Phase 35

**Tasks**:
- Write operator runbooks for all failure modes
- Create disaster recovery procedures
- Write user-facing documentation
- Create API documentation
- Write deployment guide
- Create security hardening guide

**Acceptance**: Gate G  
**Evidence**: `runbook_index.json`, `dr_test.json`

---

## Gate G: Production Readiness

All gates passed. Contract-kit v17 is production ready.

---

## Timeline Summary

| Week | Phases | Gates |
|------|--------|-------|
| Week 1 | 1-8 | Gate A |
| Week 2 | 9-16 | Gates B, C |
| Week 3 | 17-24 | Gate D |
| Week 4 | 25-30 | Gate E |
| Week 5 | 31-34 | Gate F |
| Week 6 | 35-36 | Gate G |

**Total estimated duration**: 6 weeks  
**Team size**: 4-6 agents working in parallel across lanes  
**Critical path**: Phase 1 → Phase 2 → Phase 4 → Gate B → Gate C → Gate D → Gate E → Gate F → Gate G

---

## Parallel Lane Execution

Lanes can execute in parallel after their prerequisites are satisfied:

```
Core Infrastructure (sequential):
  Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Gate A

WebUI (parallel to Core after Gate A):
  Phase 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → Gate B/C

KiloCode (parallel to WebUI after Gate A/B):
  Phase 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24 → Gate D

Runtime + Provider (starts Phase 25 after Gate A):
  Phase 25 → 26 → 27 → 28 → 29 → 30 → Gate E

Hermes + ZeroClaw (starts Phase 31 after Gate A/D):
  Phase 31 → 32 → 33 → 34 → Gate F

Proof (sequential after all lanes):
  Phase 35 → 36 → Gate G
```
