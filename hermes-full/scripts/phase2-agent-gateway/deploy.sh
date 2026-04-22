#!/bin/bash
# Phase 2 Task 2.1: Deploy Hermes Agent Gateway on VPS
# Run as: sudo bash deploy.sh
set -e

echo "=== Phase 2: Hermes Agent Gateway Deployment ==="

# ── Install dependencies ──────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y python3-pip python3-venv redis-server

# ── Create gateway directory ──────────────────────────────────────────────────
mkdir -p /opt/hermes-gateway
cp -r ./* /opt/hermes-gateway/
cd /opt/hermes-gateway

# ── Python virtual environment ────────────────────────────────────────────────
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ── Environment file (.env.gateway) ──────────────────────────────────────────
# Copy and fill from /opt/data/.env on the VPS
ENV_FILE="/opt/hermes-gateway/.env.gateway"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'ENVEOF'
VPS_HOST=YOUR_VPS_IP
VPS_USER=root
VPS_SSH_KEY=/root/.ssh/id_ed25519
MINIMAX_API_KEY=FILL_FROM_OPT_DATA_ENV
SILICONFLOW_API_KEY=FILL_FROM_OPT_DATA_ENV
RTX_3090_URL=http://TAILSCALE_RTX_IP:11434
AMD_7800_URL=http://TAILSCALE_AMD_IP:11434
ENVEOF
    echo "→ Created $ENV_FILE — fill in Tailscale IPs and API keys"
fi

# Auto-populate API keys from existing /opt/data/.env
if [ -f /opt/data/.env ]; then
    MINIMAX=$(grep "MINIMAX_API_KEY" /opt/data/.env | cut -d= -f2)
    SF=$(grep "SILICONFLOW_API_KEY" /opt/data/.env | cut -d= -f2)
    [ -n "$MINIMAX" ] && sed -i "s|FILL_FROM_OPT_DATA_ENV|$MINIMAX|1" "$ENV_FILE"
    [ -n "$SF" ]      && sed -i "s|FILL_FROM_OPT_DATA_ENV|$SF|1"      "$ENV_FILE"
    echo "✓ API keys populated from /opt/data/.env"
fi

# ── Start Redis ───────────────────────────────────────────────────────────────
systemctl enable redis-server
systemctl start redis-server
echo "✓ Redis started"

# ── Systemd service ───────────────────────────────────────────────────────────
cat > /etc/systemd/system/hermes-gateway.service << 'SVCEOF'
[Unit]
Description=Hermes Agent Gateway
After=network.target redis-server.service

[Service]
WorkingDirectory=/opt/hermes-gateway
EnvironmentFile=/opt/hermes-gateway/.env.gateway
ExecStart=/opt/hermes-gateway/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable hermes-gateway
systemctl start hermes-gateway

sleep 3

# ── Verify ────────────────────────────────────────────────────────────────────
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✓ Hermes Agent Gateway running on port 8000"
    echo "  Test: curl http://localhost:8000/agents"
else
    echo "✗ Gateway failed to start"
    journalctl -u hermes-gateway -n 20
    exit 1
fi

echo ""
echo "=== Phase 2 Task 2.1 Complete ==="
echo "  Health:  http://YOUR_VPS_IP:8000/health"
echo "  Agents:  http://YOUR_VPS_IP:8000/agents"
echo "  Models:  http://YOUR_VPS_IP:8000/models"
echo "  TPS:     http://YOUR_VPS_IP:8000/tps"
echo ""
echo "Next: Update Tailscale IPs in $ENV_FILE then restart gateway"
echo "  systemctl restart hermes-gateway"
