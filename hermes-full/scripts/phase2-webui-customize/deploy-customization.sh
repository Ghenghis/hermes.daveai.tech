#!/bin/bash
# Phase 2 Task 2.3: Deploy Open WebUI Customisation
# Run as: sudo bash deploy-customization.sh
set -e

echo "=== Phase 2 Task 2.3: Open WebUI Customisation ==="

# ── Install nginx sub_filter module (usually included) ────────────────────────
apt-get install -y nginx

# ── Create custom assets directory ───────────────────────────────────────────
mkdir -p /opt/hermes-chat/webui-custom
cp hermes_banner.js /opt/hermes-chat/webui-custom/
echo "✓ Custom assets deployed"

# ── Update nginx config ───────────────────────────────────────────────────────
cp inject-nginx.conf /etc/nginx/sites-available/hermes-chat
nginx -t
systemctl reload nginx
echo "✓ Nginx config updated with sub_filter injection"

echo ""
echo "=== Phase 2 Task 2.3 Complete ==="
echo "  Open WebUI:  http://YOUR_VPS_IP:3000"
echo "  Hermes JS:   http://YOUR_VPS_IP/hermes/hermes_banner.js"
echo ""
echo "Next: Phase 3 — Optimization"
