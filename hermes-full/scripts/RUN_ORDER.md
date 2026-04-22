# Hermes Chat Interface — Deployment Run Order

Execute each script on VPS (YOUR_VPS_IP) **in order**, one at a time.
SSH in: `ssh root@YOUR_VPS_IP`

---

## Phase 1 — Infrastructure Setup

```bash
bash /tmp/phase1-complete-deployment.sh
```
**Then:** Update `/opt/hermes-chat/config/cloud_apis.json` with API keys
**Verify:** `curl http://localhost:3000`

---

## Phase 2 — Hermes Integration

```bash
# 2.1 Deploy Agent Gateway
cd /opt && mkdir -p hermes-gateway
# Upload: scripts/phase2-agent-gateway/* → /opt/hermes-gateway/
cd /opt/hermes-gateway
bash deploy.sh

# 2.2 Verify Gateway
curl http://localhost:8000/health
curl http://localhost:8000/agents

# 2.3 Deploy WebUI Customisation
# Upload: scripts/phase2-webui-customize/* → /tmp/webui-custom/
cd /tmp/webui-custom
bash deploy-customization.sh
```
**Verify:** Open http://YOUR_VPS_IP:3000 — Hermes agent selector bar should appear at top

---

## Phase 3 — Optimization

```bash
# Upload: scripts/phase3-optimization/optimize.sh → /tmp/
bash /tmp/optimize.sh
bash /opt/hermes-chat/health-check.sh
```

---

## Phase 4 — Voice UI

```bash
# Upload: scripts/phase4-voice-ui/* → /tmp/voice/
cd /tmp/voice
bash deploy-voice.sh

curl http://localhost:8001/health
curl http://localhost:8001/voices
```
**Verify:** Voice mic button (🎤) appears bottom-right in WebUI

---

## Phase 5 — Production Hardening

```bash
# Upload: scripts/phase5-production/harden.sh → /tmp/
bash /tmp/harden.sh
```
**Final check:** `bash /opt/hermes-chat/health-check.sh`

---

## Service Ports Summary

| Service          | Port | Access          |
|-----------------|------|-----------------|
| Open WebUI       | 3000 | Public (Nginx)  |
| Agent Gateway    | 8000 | Internal only   |
| Voice Gateway    | 8001 | Internal only   |
| Redis            | 6379 | Internal only   |
| Nginx            | 80   | Public          |

## Quick Status Check (run anytime)

```bash
bash /opt/hermes-chat/health-check.sh
```
