# Hermes Chat Interface — Implementation Guide

## Quick Start

This guide provides step-by-step instructions for implementing the Hermes Chat Interface architecture.

## Prerequisites

### Hardware
- VPS: YOUR_VPS_IP (Hostinger)
- Local PC 1: Windows with RTX 3090 Ti (24GB VRAM, 700GB disk for models)
- Local PC 2: Windows with AMD 7800XT (16GB VRAM)

### Software
- Docker installed on VPS
- LM Studio installed on both local PCs
- Tailscale installed on all systems
- Python 3.11+ on VPS
- Git on VPS

### API Keys
- MiniMax API key (configured)
- SiliconFlow API keys (configured)
- GitHub tokens (configured)

## Phase 1: Infrastructure Setup (Week 1)

### Task 1.1: Deploy Open WebUI

**On VPS:**
```bash
cd /opt/hermes-agent-2026.4.13/hermes-agent-2026.4.13/scripts
chmod +x phase1-deploy-open-webui.sh
./phase1-deploy-open-webui.sh
```

**Verify:**
```bash
curl http://localhost:3000/health
```

Expected: `{"status": "ok"}`

---

### Task 1.2: Set Up LM Link Bridge

**On Local PC 1 (RTX 3090 Ti):**
1. Install LM Studio from https://lmstudio.ai/
2. Configure:
   - API Port: 11434
   - Host: 0.0.0.0
   - CORS: Enabled

**On Local PC 2 (AMD 7800XT):**
1. Install LM Studio
2. Configure same settings (use port 11435 if needed)

**On Both PCs:**
```bash
# Install Tailscale
# Download from https://tailscale.com/
tailscale up
# Note the Tailscale IP
```

**On VPS:**
```bash
cd /opt/hermes-agent-2026.4.13/hermes-agent-2026.4.13/scripts
python3 phase1-lm-link-bridge.py
```

**Update the script** with actual Tailscale IPs:
```python
self.gpus = {
    'rtx3090': {
        'url': 'http://100.x.x.x:11434',  # Update with actual IP
        ...
    },
    'amd7800': {
        'url': 'http://100.x.y.y:11434',  # Update with actual IP
        ...
    }
}
```

**Verify:**
```bash
curl http://<TAILSCALE_IP_RTX>:11434/api/tags
curl http://<TAILSCALE_IP_AMD>:11434/api/tags
```

---

### Task 1.3: Load Local Models

**On RTX 3090 Ti via LM Studio UI:**
Download these models:
- llama-3-70b-instruct (40GB)
- mixtral-8x7b-instruct (26GB)
- qwen-72b-chat (40GB)
- deepseek-coder-33b (20GB)
- code-llama-34b (20GB)

**On AMD 7800XT via LM Studio UI:**
Download these models:
- llama-3-8b-instruct (4GB)
- mistral-7b-instruct (4GB)
- phi-3-medium (8GB)
- gemma-7b (4GB)

**Test models:**
```bash
curl -X POST http://<TAILSCALE_IP_RTX>:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-3-70b-instruct", "prompt": "Hello", "stream": false}'
```

---

### Task 1.4: Configure Cloud APIs

**On VPS:**
```bash
cd /opt/hermes-agent-2026.4.13/hermes-agent-2026.4.13/scripts
python3 phase1-cloud-api-config.py
```

This will:
- Test MiniMax API
- Test SiliconFlow API
- Save configurations to `/opt/hermes-gateway/`

---

### Task 1.5: Configure Nginx Reverse Proxy

**On VPS:**
```bash
cd /opt/hermes-agent-2026.4.13/hermes-agent-2026.4.13/scripts
chmod +x phase1-nginx-setup.sh
DOMAIN_NAME=chat.yourdomain.com ./phase1-nginx-setup.sh
```

**Update DNS:**
Point `chat.yourdomain.com` to VPS IP (YOUR_VPS_IP)

**Verify:**
```bash
curl https://chat.yourdomain.com
```

---

## Phase 2: Hermes Integration (Week 2)

### Task 2.1: Build Agent Gateway

**On VPS:**
```bash
# Create project structure
mkdir -p /opt/hermes-gateway/{app,models,utils}
cd /opt/hermes-gateway

# Create requirements.txt
cat > requirements.txt <<EOF
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0
pydantic==2.5.3
httpx==0.26.0
redis==5.0.1
prometheus-client==0.19.0
paramiko==3.4.0
EOF

# Install dependencies
pip install -r requirements.txt

# Create Dockerfile
cat > Dockerfile <<EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", 8000"]
EOF

# Build and deploy
docker build -t hermes-gateway .
docker run -d --name hermes-gateway -p 8000:8000 hermes-gateway
```

**Implement the code files** as specified in CONTRACT_ROADMAP.md Task 2.1

---

### Task 2.2: Integrate Hermes Agents

The Hermes adapter code is in CONTRACT_ROADMAP.md Task 2.2

**Test integration:**
```bash
curl -X POST http://localhost:8000/api/hermes/hermes1 \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

---

### Task 2.3: Customize Open WebUI

Follow the steps in CONTRACT_ROADMAP.md Task 2.3

---

### Task 2.4: Migrate Discord History

**On VPS:**
```bash
pip install discord-chat-exporter
discord-chat-exporter export \
  --token <discord-bot-token> \
  --channel <channel-id> \
  --format json \
  --output discord_history.json
```

---

### Task 2.5: Parallel Testing

Run both Discord and WebUI in parallel, compare responses using the script in CONTRACT_ROADMAP.md

---

## Phase 3-5: Optimization, Advanced Features, Production

Follow the detailed steps in CONTRACT_ROADMAP.md for Phases 3, 4, and 5.

---

## Troubleshooting

### Open WebUI won't start
```bash
docker logs open-webui
docker-compose down
docker-compose up -d
```

### LM Link bridge can't connect
- Check Tailscale is running on both PCs
- Verify LM Studio is running
- Check firewall allows port 11434
- Test connectivity: `curl http://<tailscale-ip>:11434/api/tags`

### Models won't load
- Check disk space (RTX 3090 Ti needs 700GB+)
- Verify LM Studio has write permissions
- Check network connection for downloads

### Cloud API fails
- Verify API keys are correct
- Check network connectivity
- Verify API quota limits
- Test with curl command

### Nginx SSL fails
- Check DNS is configured correctly
- Verify port 80 and 443 are open in firewall
- Check certbot logs: `journalctl -u certbot`

---

## Monitoring

### Check container status
```bash
docker ps
docker stats
```

### Check logs
```bash
docker logs -f open-webui
docker logs -f hermes-gateway
```

### Check resource usage
```bash
htop
df -h
free -h
```

---

## Backup

### Backup configurations
```bash
tar czf hermes-configs-backup-$(date +%Y%m%d).tar.gz \
  /opt/open-webui \
  /opt/hermes-gateway \
  /etc/nginx
```

### Backup Docker volumes
```bash
docker run --rm \
  -v open-webui-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/open-webui-data-$(date +%Y%m%d).tar.gz /data
```

---

## Rollback Procedures

### Rollback Open WebUI
```bash
docker stop hermes-webui
docker rm hermes-webui
docker start open-webui
```

### Rollback Agent Gateway
```bash
docker stop hermes-gateway
docker rm hermes-gateway
# Rebuild with previous version
```

### Rollback to Discord
- Keep Discord bots running during migration
- If WebUI fails, continue using Discord
- Fix issues before attempting cutover again

---

## Support

For issues or questions, refer to:
- CONTRACT_ROADMAP.md for detailed architecture
- HERMES_CHAT_INTERFACE_ARCHITECTURE.md for design decisions
- VPS logs: `/var/log/`
- Docker logs: `docker logs <container>`
