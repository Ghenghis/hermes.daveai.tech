#!/bin/bash
# Phase 3: Optimization — performance tuning, caching, rate-limit hardening
# Run as: sudo bash optimize.sh
set -e

echo "=== Phase 3: Optimization ==="

# ── 1. Redis tuning ───────────────────────────────────────────────────────────
cat >> /etc/redis/redis.conf << 'REDISCFG'
maxmemory 256mb
maxmemory-policy allkeys-lru
save ""
REDISCFG
systemctl restart redis-server
echo "✓ Redis tuned (256MB LRU, persistence off)"

# ── 2. Increase gateway workers based on CPU count ───────────────────────────
CPUS=$(nproc)
WORKERS=$((CPUS * 2))
sed -i "s/--workers [0-9]*/--workers $WORKERS/" /etc/systemd/system/hermes-gateway.service
systemctl daemon-reload
systemctl restart hermes-gateway
echo "✓ Gateway workers set to $WORKERS (${CPUS} vCPUs)"

# ── 3. Nginx performance tuning ───────────────────────────────────────────────
cat > /etc/nginx/conf.d/hermes-perf.conf << 'NGINXCFG'
# Gzip compression
gzip on;
gzip_comp_level 5;
gzip_types text/plain application/json text/javascript application/javascript text/css;
gzip_min_length 1024;

# Buffer tuning
client_body_buffer_size 16k;
client_max_body_size 50m;
proxy_buffer_size 16k;
proxy_buffers 4 32k;
proxy_busy_buffers_size 64k;

# Keep-alive
keepalive_timeout 65;
keepalive_requests 1000;
NGINXCFG
nginx -t && systemctl reload nginx
echo "✓ Nginx performance tuning applied"

# ── 4. Docker container resource limits (Open WebUI) ────────────────────────
docker update --memory="2g" --cpus="2" open-webui 2>/dev/null && echo "✓ Open WebUI resource limits set" || echo "→ Open WebUI resource limits skipped (container not found)"

# ── 5. System ulimits ────────────────────────────────────────────────────────
cat >> /etc/security/limits.conf << 'LIMITS'
root soft nofile 65535
root hard nofile 65535
LIMITS
echo "✓ System file descriptor limits increased"

# ── 6. Health check script ────────────────────────────────────────────────────
cat > /opt/hermes-chat/health-check.sh << 'HEALTHEOF'
#!/bin/bash
echo "=== Hermes Health Check ==="
echo -n "Open WebUI (3000):    " ; curl -sf http://localhost:3000 > /dev/null && echo "✓ UP" || echo "✗ DOWN"
echo -n "Agent Gateway (8000): " ; curl -sf http://localhost:8000/health > /dev/null && echo "✓ UP" || echo "✗ DOWN"
echo -n "Redis:                " ; redis-cli ping | grep -q PONG && echo "✓ UP" || echo "✗ DOWN"
echo -n "Nginx:                " ; systemctl is-active nginx | grep -q active && echo "✓ UP" || echo "✗ DOWN"
echo ""
echo "TPS Status:"
curl -sf http://localhost:8000/tps | python3 -m json.tool 2>/dev/null || echo "  (gateway offline)"
HEALTHEOF
chmod +x /opt/hermes-chat/health-check.sh
echo "✓ Health check script: /opt/hermes-chat/health-check.sh"

# ── 7. Cron: auto-restart on failure ─────────────────────────────────────────
(crontab -l 2>/dev/null; echo "*/5 * * * * systemctl is-active hermes-gateway || systemctl restart hermes-gateway") | crontab -
echo "✓ Auto-restart cron registered (every 5 min)"

echo ""
echo "=== Phase 3 Complete ==="
echo "  Run health check: bash /opt/hermes-chat/health-check.sh"
