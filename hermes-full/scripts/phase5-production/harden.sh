#!/bin/bash
# Phase 5: Production Hardening — Security, monitoring, backup, log rotation
# Run as: sudo bash harden.sh
set -e

echo "=== Phase 5: Production Hardening ==="

# ─── 1. UFW Firewall ──────────────────────────────────────────────────────────
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp   # Open WebUI (direct access)
# Internal-only ports — block external access
ufw deny 8000/tcp    # Agent Gateway (behind Nginx)
ufw deny 8001/tcp    # Voice Gateway (behind Nginx)
ufw deny 6379/tcp    # Redis
# Allow existing iptables rule for Shiba Memory
ufw allow from 172.0.0.0/8 to any port 18789
ufw --force enable
echo "✓ UFW firewall configured"

# ─── 2. Rate limiting in Nginx ────────────────────────────────────────────────
cat > /etc/nginx/conf.d/hermes-ratelimit.conf << 'RATECFG'
limit_req_zone $binary_remote_addr zone=hermes_api:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=hermes_voice:10m rate=10r/m;
RATECFG

# Add rate limit directives to Nginx site config
sed -i 's|location /api/hermes/|limit_req zone=hermes_api burst=10 nodelay;\n        location /api/hermes/|' \
    /etc/nginx/sites-available/hermes-chat
nginx -t && systemctl reload nginx
echo "✓ Nginx rate limiting applied (30 req/min API, 10 req/min Voice)"

# ─── 3. Fail2Ban ─────────────────────────────────────────────────────────────
apt-get install -y fail2ban
cat > /etc/fail2ban/jail.d/hermes.conf << 'F2BCFG'
[sshd]
enabled = true
maxretry = 5
bantime  = 3600

[nginx-http-auth]
enabled = true
maxretry = 10
bantime  = 600
F2BCFG
systemctl restart fail2ban
echo "✓ Fail2Ban configured"

# ─── 4. Log rotation ─────────────────────────────────────────────────────────
cat > /etc/logrotate.d/hermes << 'LOGCFG'
/var/log/hermes-gateway.log
/var/log/hermes-voice.log
/var/log/nginx/access.log
/var/log/nginx/error.log
{
    daily
    rotate 7
    compress
    missingok
    notifempty
    sharedscripts
    postrotate
        systemctl reload nginx >/dev/null 2>&1 || true
    endscript
}
LOGCFG
echo "✓ Log rotation configured (7-day retention)"

# ─── 5. Automated daily backup ───────────────────────────────────────────────
mkdir -p /opt/backups/hermes

cat > /opt/hermes-chat/backup.sh << 'BACKUPEOF'
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M)
DEST="/opt/backups/hermes/${DATE}"
mkdir -p "$DEST"

# Backup configurations
cp -r /opt/hermes-chat/config     "$DEST/config"      2>/dev/null || true
cp -r /opt/hermes-gateway/.env*   "$DEST/"             2>/dev/null || true
cp -r /opt/hermes-voice/.env      "$DEST/voice.env"    2>/dev/null || true
cp -r /opt/azure-speech           "$DEST/azure-speech" 2>/dev/null || true

# Backup Open WebUI data volume
docker run --rm \
    --volumes-from open-webui \
    -v "$DEST:/backup" \
    alpine tar czf /backup/open-webui-data.tar.gz /app/backend/data \
    2>/dev/null || true

# Remove backups older than 14 days
find /opt/backups/hermes -maxdepth 1 -mtime +14 -type d -exec rm -rf {} + 2>/dev/null || true

echo "Backup complete: $DEST"
BACKUPEOF
chmod +x /opt/hermes-chat/backup.sh

# Schedule daily at 3 AM
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/hermes-chat/backup.sh >> /var/log/hermes-backup.log 2>&1") | crontab -
echo "✓ Daily backup scheduled at 03:00 → /opt/backups/hermes/"

# ─── 6. Systemd watchdog for all services ────────────────────────────────────
cat > /opt/hermes-chat/watchdog.sh << 'WDEOF'
#!/bin/bash
SERVICES="open-webui hermes-gateway hermes-voice nginx redis-server"
for svc in $SERVICES; do
    if ! systemctl is-active --quiet "$svc" 2>/dev/null; then
        echo "[$(date)] Restarting $svc"
        systemctl restart "$svc" 2>/dev/null || docker restart "$svc" 2>/dev/null || true
    fi
done
WDEOF
chmod +x /opt/hermes-chat/watchdog.sh
(crontab -l 2>/dev/null; echo "*/3 * * * * /opt/hermes-chat/watchdog.sh >> /var/log/hermes-watchdog.log 2>&1") | crontab -
echo "✓ Watchdog cron registered (every 3 min)"

# ─── Final check ─────────────────────────────────────────────────────────────
echo ""
echo "=== Phase 5 Complete — Production Hardening Done ==="
echo ""
echo "Security:"
echo "  UFW:       $(ufw status | head -1)"
echo "  Fail2Ban:  $(fail2ban-client status | head -2 | tail -1)"
echo ""
echo "Services:"
bash /opt/hermes-chat/health-check.sh 2>/dev/null || true
echo ""
echo "All phases complete. Hermes Chat Interface is production-ready."
