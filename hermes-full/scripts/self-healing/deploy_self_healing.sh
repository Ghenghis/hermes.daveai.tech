#!/bin/bash
# deploy_self_healing.sh
# Deploys the Hermes self-healing watchdog + safemode repair server to the VPS.
# Run: scp -r scripts/self-healing root@YOUR_VPS_IP:/opt/ && ssh root@YOUR_VPS_IP bash /opt/self-healing/deploy_self_healing.sh

set -e

INSTALL_DIR="/opt/self-healing"
REPAIR_DIR="/opt/repair"
VENV="$INSTALL_DIR/.venv"

echo "=== 1. Setup directories ==="
mkdir -p "$REPAIR_DIR"
mkdir -p "$INSTALL_DIR"
chmod 750 "$REPAIR_DIR"

echo "=== 2. Install Python deps ==="
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet fastapi uvicorn websockets httpx

echo "=== 3. Copy scripts ==="
# Already in /opt/self-healing from scp
ls -la "$INSTALL_DIR/"

echo "=== 4. Create watchdog systemd service ==="
cat > /etc/systemd/system/hermes-watchdog.service << 'SERVICE'
[Unit]
Description=Hermes System Watchdog
After=docker.service network.target
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/self-healing
ExecStart=/opt/self-healing/.venv/bin/python3 /opt/self-healing/watchdog.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=WATCHDOG_INTERVAL=60
EnvironmentFile=-/opt/litellm/.env

[Install]
WantedBy=multi-user.target
SERVICE

echo "=== 5. Create safemode systemd service ==="
cat > /etc/systemd/system/hermes-safemode.service << 'SERVICE'
[Unit]
Description=Hermes Safe-Mode Repair Server
After=docker.service network.target
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/self-healing
ExecStart=/opt/self-healing/.venv/bin/python3 /opt/self-healing/safemode_server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=SAFEMODE_PORT=7861
Environment=WEBUI_URL=http://localhost:7860
EnvironmentFile=-/opt/litellm/.env

[Install]
WantedBy=multi-user.target
SERVICE

echo "=== 6. Add nginx safemode proxy location ==="
# Add :7861 as available upstream (safemode stays dormant unless watchdog activates it)
if ! grep -q "7861" /etc/nginx/sites-enabled/* 2>/dev/null; then
  cat >> /etc/nginx/conf.d/hermes-safemode-upstream.conf << 'NGINX'
# Hermes safemode upstream — activated by watchdog when needed
upstream hermes_safemode {
    server 127.0.0.1:7861;
}
NGINX
fi

echo "=== 7. Setup daily backup (protect webui.db) ==="
cat > /etc/cron.daily/hermes-backup << 'CRON'
#!/bin/bash
BACKUP_DIR="/opt/backups"
mkdir -p "$BACKUP_DIR"
# Rotate: keep last 7 days
find "$BACKUP_DIR" -name "webui.db.*" -mtime +7 -delete 2>/dev/null || true
# Backup webui DB
DB="/var/lib/docker/volumes/open-webui/_data/webui.db"
[ -f "$DB" ] && cp "$DB" "$BACKUP_DIR/webui.db.$(date +%Y%m%d)" && echo "webui.db backed up"
# Backup litellm config
cp /opt/litellm/config.yaml "$BACKUP_DIR/litellm-config.$(date +%Y%m%d).yaml" 2>/dev/null || true
cp /opt/litellm/.env "$BACKUP_DIR/litellm-env.$(date +%Y%m%d)" 2>/dev/null || true
CRON
chmod +x /etc/cron.daily/hermes-backup

echo "=== 8. Run first backup now ==="
bash /etc/cron.daily/hermes-backup

echo "=== 9. Enable and start services ==="
systemctl daemon-reload
systemctl enable hermes-watchdog
systemctl enable hermes-safemode
systemctl start hermes-safemode
sleep 3
systemctl start hermes-watchdog

echo "=== 10. Verify ==="
sleep 5
systemctl is-active hermes-watchdog && echo "  watchdog: RUNNING" || echo "  watchdog: FAILED"
systemctl is-active hermes-safemode && echo "  safemode: RUNNING" || echo "  safemode: FAILED"
curl -sf http://localhost:7861/health && echo "  safemode API: OK" || echo "  safemode API: not ready yet"

echo ""
echo "=== 11. Run initial health check ==="
"$VENV/bin/python3" /opt/self-healing/health_checks.py

echo ""
echo "=== DEPLOY COMPLETE ==="
echo "  Watchdog:       systemctl status hermes-watchdog"
echo "  Safemode UI:    http://YOUR_VPS_IP:7861"
echo "  Repair trigger: curl -X POST http://localhost:7861/repair/trigger"
echo "  Logs:           journalctl -u hermes-watchdog -f"
echo "  Repair log:     tail -f /opt/repair/repair.log"
