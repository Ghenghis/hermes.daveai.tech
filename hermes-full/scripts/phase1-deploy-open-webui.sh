#!/bin/bash
# Phase 1, Task 1.1: Open WebUI Deployment
# This script deploys Open WebUI on the VPS

set -e

echo "=== Phase 1.1: Open WebUI Deployment ==="
echo ""

# Configuration
OPEN_WEBUI_DIR="/opt/open-webui"
WEBUI_PORT=3000
OLLAMA_BASE_URL="http://localhost:11434"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Create directory
echo "Creating Open WebUI directory..."
mkdir -p $OPEN_WEBUI_DIR
cd $OPEN_WEBUI_DIR

# Clone repository
echo "Cloning Open WebUI repository..."
if [ ! -d "open-webui" ]; then
    git clone https://github.com/open-webui/open-webui.git
    cd open-webui
else
    cd open-webui
    git pull
fi

# Create docker-compose.yml
echo "Creating docker-compose.yml..."
cat > docker-compose.yml <<EOF
version: '3.8'
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "${WEBUI_PORT}:8080"
    environment:
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL}
      - WEBUI_SECRET_KEY=\${WEBUI_SECRET_KEY}
      - OPENAI_API_KEY=\${OPENAI_API_KEY}
    volumes:
      - open-webui-data:/app/backend/data
    restart: unless-stopped

volumes:
  open-webui-data:
EOF

# Create .env file if it doesn't exist
echo "Creating .env file..."
if [ ! -f ".env" ]; then
    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)
    cat > .env <<EOF
WEBUI_SECRET_KEY=${SECRET_KEY}
OPENAI_API_KEY=
EOF
    echo "Generated new WEBUI_SECRET_KEY"
else
    echo ".env file already exists"
fi

# Deploy container
echo "Deploying Open WebUI container..."
docker-compose down
docker-compose up -d

# Wait for container to start
echo "Waiting for container to start..."
sleep 10

# Verify deployment
echo "Verifying deployment..."
if curl -f http://localhost:${WEBUI_PORT}/health > /dev/null 2>&1; then
    echo "✅ Open WebUI deployed successfully"
    echo "Access at: http://YOUR_VPS_IP:${WEBUI_PORT}"
else
    echo "❌ Deployment verification failed"
    docker-compose logs
    exit 1
fi

echo ""
echo "=== Deployment Complete ==="
echo "Next steps:"
echo "1. Configure Nginx reverse proxy (Task 1.5)"
echo "2. Set up LM Link bridge (Task 1.2)"
echo "3. Load local models (Task 1.3)"
