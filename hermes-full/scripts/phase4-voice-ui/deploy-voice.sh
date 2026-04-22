#!/bin/bash
# Phase 4: Deploy Hermes Voice Gateway (Azure TTS/STT)
# Run as: sudo bash deploy-voice.sh
set -e

echo "=== Phase 4: Azure Voice Gateway Deployment ==="

# ── Install Python deps ───────────────────────────────────────────────────────
pip3 install azure-cognitiveservices-speech==1.34.0 fastapi uvicorn python-multipart

# ── Deploy voice gateway ───────────────────────────────────────────────────────
mkdir -p /opt/hermes-voice
cp voice_gateway.py /opt/hermes-voice/

# ── Populate Azure key from existing env ─────────────────────────────────────
AZURE_KEY=""
if [ -f /opt/data/.env ]; then
    AZURE_KEY=$(grep "AZURE_SPEECH_KEY" /opt/data/.env | cut -d= -f2)
fi

cat > /opt/hermes-voice/.env << ENVEOF
AZURE_SPEECH_KEY=${AZURE_KEY:-YOUR_AZURE_SPEECH_KEY}
AZURE_SPEECH_REGION=eastus
ENVEOF

# ── Systemd service ───────────────────────────────────────────────────────────
cat > /etc/systemd/system/hermes-voice.service << 'SVCEOF'
[Unit]
Description=Hermes Voice Gateway
After=network.target

[Service]
WorkingDirectory=/opt/hermes-voice
EnvironmentFile=/opt/hermes-voice/.env
ExecStart=/usr/bin/python3 -m uvicorn voice_gateway:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable hermes-voice
systemctl start hermes-voice
sleep 3

# ── Deploy Voice UI JS ────────────────────────────────────────────────────────
cp voice_ui.js /opt/hermes-chat/webui-custom/
echo "✓ voice_ui.js deployed to /opt/hermes-chat/webui-custom/"

# Update nginx to inject voice UI JS as well
sed -i 's|/hermes/hermes_banner.js|/hermes/hermes_banner.js"></script><script src="/hermes/voice_ui.js|' \
    /etc/nginx/sites-available/hermes-chat
nginx -t && systemctl reload nginx

# ── Verify ────────────────────────────────────────────────────────────────────
if curl -sf http://localhost:8001/health > /dev/null; then
    echo "✓ Voice Gateway running on port 8001"
    echo "  Voices: curl http://localhost:8001/voices"
else
    echo "✗ Voice Gateway failed to start"
    journalctl -u hermes-voice -n 20
    exit 1
fi

echo ""
echo "=== Phase 4 Complete ==="
echo "  Voice Health: http://YOUR_VPS_IP:8001/health"
echo "  Voice List:   http://YOUR_VPS_IP:8001/voices"
echo ""
echo "Next: Phase 5 — Production hardening"
