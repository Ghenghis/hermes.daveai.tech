#!/bin/bash
# Phase 1, Task 1.5: Nginx Reverse Proxy Setup
# This script configures Nginx as a reverse proxy for Open WebUI

set -e

echo "=== Phase 1.5: Nginx Reverse Proxy Setup ==="
echo ""

# Configuration
DOMAIN_NAME="${DOMAIN_NAME:-chat.hermes.example.com}"  # Update this
WEBUI_PORT=3000
NGINX_CONF_DIR="/etc/nginx/sites-available"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Install Nginx and Certbot if not installed
echo "Installing Nginx and Certbot..."
apt update
apt install -y nginx certbot python3-certbot-nginx

# Create Nginx configuration
echo "Creating Nginx configuration..."
cat > ${NGINX_CONF_DIR}/hermes-chat <<EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    location / {
        proxy_pass http://localhost:${WEBUI_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }
}
EOF

# Enable site
echo "Enabling Nginx site..."
ln -sf ${NGINX_CONF_DIR}/hermes-chat /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "Testing Nginx configuration..."
nginx -t

# Reload Nginx
echo "Reloading Nginx..."
systemctl reload nginx

# Enable SSL with Certbot
echo "Enabling SSL with Let's Encrypt..."
read -p "Do you want to enable SSL now? (y/n): " enable_ssl

if [ "$enable_ssl" = "y" ]; then
    certbot --nginx -d ${DOMAIN_NAME}
    
    echo ""
    echo "✅ SSL enabled successfully"
else
    echo "Skipping SSL for now"
    echo "To enable later, run: certbot --nginx -d ${DOMAIN_NAME}"
fi

# Test configuration
echo "Testing configuration..."
if curl -f http://localhost > /dev/null 2>&1; then
    echo "✅ Nginx configured successfully"
    echo "Access at: http://${DOMAIN_NAME}"
else
    echo "❌ Configuration test failed"
    exit 1
fi

echo ""
echo "=== Setup Complete ==="
echo "Configuration file: ${NGINX_CONF_DIR}/hermes-chat"
echo "Domain: ${DOMAIN_NAME}"
echo ""
echo "Next steps:"
echo "1. Update DNS to point ${DOMAIN_NAME} to VPS IP"
echo "2. Test HTTPS access"
echo "3. Configure firewall to allow ports 80 and 443"
