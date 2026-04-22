# Phase 1 Deployment Guide

## Prerequisites
- VPS: YOUR_VPS_IP
- SSH access to VPS
- Root or sudo privileges
- Internet connection on VPS

## Deployment Steps

### Step 1: Upload Deployment Script to VPS

**Option A: Using SCP (Windows PowerShell)**
```powershell
scp g:\Github\hermes-agent-2026.4.13\hermes-agent-2026.4.13\scripts\phase1-complete-deployment.sh root@YOUR_VPS_IP:/tmp/
```

**Option B: Using SFTP client (WinSCP, FileZilla)**
- Connect to YOUR_VPS_IP
- Upload `phase1-complete-deployment.sh` to `/tmp/`

**Option C: Copy paste directly on VPS**
- SSH into VPS: `ssh root@YOUR_VPS_IP`
- Create file: `nano /tmp/phase1-complete-deployment.sh`
- Copy script content from local file
- Save and exit (Ctrl+X, Y, Enter)

### Step 2: Execute Deployment Script on VPS

```bash
# SSH into VPS
ssh root@YOUR_VPS_IP

# Make script executable
chmod +x /tmp/phase1-complete-deployment.sh

# Execute script
sudo bash /tmp/phase1-complete-deployment.sh
```

### Step 3: Verify Deployment

After script completes, verify each component:

**Verify Open WebUI:**
```bash
docker ps | grep open-webui
curl http://localhost:3000
```

**Verify Nginx:**
```bash
systemctl status nginx
nginx -t
```

**Verify LM Link Bridge:**
```bash
cd /opt/lm-link
python3 lm-link-bridge.py &
curl http://localhost:8080/health
```

**Verify Azure Speech:**
```bash
cd /opt/azure-speech
source venv/bin/activate
python3 test_azure_speech.py
```

### Step 4: Configure API Keys

Edit cloud API configuration:
```bash
nano /opt/hermes-chat/config/cloud_apis.json
```

Replace placeholders with actual keys:
- `MINIMAX_API_KEY_PLACEHOLDER` with actual MiniMax key
- `SILICONFLOW_KEY_1_PLACEHOLDER` with first SiliconFlow key
- `SILICONFLOW_KEY_2_PLACEHOLDER` with second SiliconFlow key

Keys location (local):
- `C:\Users\Admin\Downloads\minimax.txt`
- `C:\Users\Admin\Downloads\siliconflow.txt`

### Step 5: Configure SSL (Optional but Recommended)

```bash
# Replace chat.yourdomain.com with actual domain
certbot --nginx -d chat.yourdomain.com
```

### Step 6: Access Open WebUI

- HTTP: http://YOUR_VPS_IP:3000
- HTTPS (after SSL): https://chat.yourdomain.com

## Troubleshooting

**Open WebUI not starting:**
```bash
docker logs open-webui
docker-compose -f /opt/open-webui/docker-compose.yml restart
```

**Nginx configuration error:**
```bash
nginx -t
cat /etc/nginx/sites-available/hermes-chat
```

**LM Link Bridge not responding:**
```bash
ps aux | grep lm-link-bridge
cd /opt/lm-link && python3 lm-link-bridge.py
```

**Azure Speech test failing:**
```bash
cd /opt/azure-speech
source venv/bin/activate
pip install --upgrade azure-cognitiveservices-speech
```

## Rollback

If any component fails, rollback:

```bash
# Stop Open WebUI
cd /opt/open-webui
docker-compose down

# Stop LM Link Bridge
pkill -f lm-link-bridge

# Restore Nginx default
rm -f /etc/nginx/sites-enabled/hermes-chat
systemctl reload nginx
```

## Next Phase

After Phase 1 complete, proceed to Phase 2: Hermes Integration
