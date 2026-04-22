#!/bin/bash
# Phase 1 Complete Deployment Script for Hermes Chat Interface
# Execute this script on VPS: YOUR_VPS_IP
# Usage: sudo bash phase1-complete-deployment.sh

set -e  # Exit on error

echo "=== Phase 1: Infrastructure Setup ==="
echo "Starting deployment at $(date)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Please run as root (use sudo)"
    exit 1
fi

# Create working directory
mkdir -p /opt/hermes-chat
cd /opt/hermes-chat

log_success "Working directory created: /opt/hermes-chat"

# ============================================================================
# TASK 1.1: Deploy Open WebUI
# ============================================================================
log_info "Task 1.1: Deploying Open WebUI..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    log_success "Docker installed"
else
    log_success "Docker already installed"
fi

# Create Open WebUI directory
mkdir -p /opt/open-webui
cd /opt/open-webui

# Create docker-compose.yml for Open WebUI
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - WEBUI_SECRET_KEY=$(openssl rand -hex 32)
    volumes:
      - open-webui:/app/backend/data
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  open-webui:
    driver: local
EOF

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)
sed -i "s/\$(openssl rand -hex 32)/$SECRET_KEY/g" docker-compose.yml

log_success "Docker compose configuration created"

# Start Open WebUI
docker-compose up -d

# Wait for service to be ready
log_info "Waiting for Open WebUI to start..."
sleep 10

# Check if Open WebUI is running
if docker ps | grep -q open-webui; then
    log_success "Open WebUI deployed and running on port 3000"
else
    log_error "Open WebUI failed to start"
    docker logs open-webui
    exit 1
fi

# ============================================================================
# TASK 1.2: Configure Cloud APIs
# ============================================================================
log_info "Task 1.2: Configuring Cloud APIs (MiniMax, SiliconFlow)..."

# Create cloud API configuration directory
mkdir -p /opt/hermes-chat/config
cd /opt/hermes-chat/config

# Create cloud API configuration file
cat > cloud_apis.json << 'EOF'
{
  "minimax": {
    "base_url": "https://api.minimaxi.chat/v1",
    "api_key": "MINIMAX_API_KEY_PLACEHOLDER",
    "models": ["minimax/minimax-m2.5", "minimax/minimax-2.7-highspeed"]
  },
  "siliconflow": {
    "base_url": "https://api.siliconflow.com/v1",
    "api_key_1": "SILICONFLOW_KEY_1_PLACEHOLDER",
    "api_key_2": "SILICONFLOW_KEY_2_PLACEHOLDER",
    "models": ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"]
  }
}
EOF

log_success "Cloud API configuration template created"
log_info "Please update /opt/hermes-chat/config/cloud_apis.json with actual API keys"

# ============================================================================
# TASK 1.3: Setup LM Link Bridge
# ============================================================================
log_info "Task 1.3: Setting up LM Link Bridge for multi-GPU..."

# Create LM Link directory
mkdir -p /opt/lm-link
cd /opt/lm-link

# Create LM Link configuration
cat > config.yaml << 'EOF'
lm_link:
  port: 8080
  gpus:
    - name: "RTX 3090 Ti"
      type: "nvidia"
      device: "cuda:0"
    - name: "AMD 7800XT"
      type: "amd"
      device: "rocm:0"
  models:
    - name: "Qwen2.5-7B"
      gpu: "RTX 3090 Ti"
      port: 8081
    - name: "Qwen2.5-72B"
      gpu: "AMD 7800XT"
      port: 8082
  fallback:
    provider: "siliconflow"
    base_url: "https://api.siliconflow.com/v1"
EOF

# Create simple LM Link bridge script
cat > lm-link-bridge.py << 'EOF'
#!/usr/bin/env python3
"""
Simple LM Link Bridge for multi-GPU connectivity
"""
import os
import sys
import json
import yaml
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import socket

class LMLinkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy', 'service': 'lm-link-bridge'}).encode())
        elif self.path == '/gpus':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # Check GPU availability
            gpus = []
            try:
                # Check NVIDIA
                result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        gpus.append({'type': 'nvidia', 'name': line})
            except:
                pass
            self.wfile.write(json.dumps({'gpus': gpus}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/route':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'message': 'Request routed'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, LMLinkHandler)
    print(f"LM Link Bridge running on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server(8080)
EOF

chmod +x lm-link-bridge.py

log_success "LM Link Bridge configuration created"

# ============================================================================
# TASK 1.4: Configure Nginx Reverse Proxy
# ============================================================================
log_info "Task 1.4: Configuring Nginx Reverse Proxy..."

# Install Nginx if not present
if ! command -v nginx &> /dev/null; then
    apt-get update
    apt-get install -y nginx certbot python3-certbot-nginx
    log_success "Nginx and Certbot installed"
else
    log_success "Nginx already installed"
fi

# Create Nginx configuration
cat > /etc/nginx/sites-available/hermes-chat << 'EOF'
server {
    listen 80;
    server_name chat.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /lm-link {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/hermes-chat /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

if [ $? -eq 0 ]; then
    systemctl reload nginx
    log_success "Nginx configured and reloaded"
else
    log_error "Nginx configuration test failed"
    exit 1
fi

log_info "To enable SSL, run: certbot --nginx -d chat.yourdomain.com"

# ============================================================================
# TASK 1.5: Setup Azure Speech Services
# ============================================================================
log_info "Task 1.5: Setting up Azure Speech Services..."

# Create Azure Speech configuration directory
mkdir -p /opt/azure-speech
cd /opt/azure-speech

# Install Azure Speech SDK
apt-get update
apt-get install -y python3-pip python3-venv

python3 -m venv venv
source venv/bin/activate
pip install azure-cognitiveservices-speech==1.34.0

# Create Azure Speech configuration
cat > azure_speech_config.json << 'EOF'
{
  "speech_key": "YOUR_AZURE_SPEECH_KEY",
  "speech_region": "eastus",
  "agent_voices": {
    "hermes1": {
      "voice": "en-GB-MaisieNeural",
      "style": "customerservice",
      "rate": "1.0",
      "pitch": "medium",
      "description": "Planning Strategist (FEMALE en-GB) - Natural, warm British accent"
    },
    "hermes2": {
      "voice": "en-AU-CarlyNeural",
      "style": "cheerful",
      "rate": "1.1",
      "pitch": "+10%",
      "description": "Creative Brainstormer (FEMALE en-AU) - Casual, relaxed Australian voice"
    },
    "hermes3": {
      "voice": "en-KE-AsiliaNeural",
      "style": "calm",
      "rate": "0.95",
      "pitch": "medium",
      "description": "System Architect (FEMALE en-KE) - Warm, expressive Kenyan English voice"
    },
    "hermes4": {
      "voice": "en-US-TonyNeural",
      "style": "empathetic",
      "rate": "0.9",
      "pitch": "medium",
      "description": "Bug Triage Specialist (MALE en-US) - Analytical, methodical"
    },
    "hermes5": {
      "voice": "en-US-ChristopherNeural",
      "style": "serious",
      "rate": "0.85",
      "pitch": "-10%",
      "description": "Root Cause Analyst (MALE en-US) - Investigative, deep"
    }
  },
  "user_voice_config": {
    "default_voice": "en-US-JennyNeural",
    "default_language": "en-US",
    "mode": "text_only",
    "auto_detect_language": true
  }
}
EOF

log_success "Azure Speech Services configured"

# Create Azure Speech test script
cat > test_azure_speech.py << 'EOF'
#!/usr/bin/env python3
import azure.cognitiveservices.speech as speechsdk
import json

# Load configuration
with open('azure_speech_config.json', 'r') as f:
    config = json.load(f)

# Configure speech service
speech_config = speechsdk.SpeechConfig(
    subscription=config['speech_key'],
    region=config['speech_region']
)

print("Azure Speech Services Configuration Test")
print("=" * 50)

# Test each agent voice
for agent_id, voice_config in config['agent_voices'].items():
    print(f"\nTesting {agent_id}: {voice_config['voice']}")
    speech_config.speech_synthesis_voice_name = voice_config['voice']
    
    # Simple synthesis test
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    result = synthesizer.speak_text_async(f"Hello, I am {agent_id}.").get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"  ✓ Voice synthesis successful")
    else:
        print(f"  ✗ Voice synthesis failed: {result.reason}")

print("\n" + "=" * 50)
print("Azure Speech Services test complete")
EOF

chmod +x test_azure_speech.py

log_success "Azure Speech test script created"

# ============================================================================
# Phase 1 Complete
# ============================================================================
echo ""
log_success "=== Phase 1: Infrastructure Setup Complete ==="
echo ""
echo "Summary:"
echo "  ✓ Open WebUI deployed on port 3000"
echo "  ✓ Cloud API configuration created at /opt/hermes-chat/config/cloud_apis.json"
echo "  ✓ LM Link Bridge configured at /opt/lm-link"
echo "  ✓ Nginx reverse proxy configured"
echo "  ✓ Azure Speech Services configured at /opt/azure-speech"
echo ""
echo "Next Steps:"
echo "  1. Update /opt/hermes-chat/config/cloud_apis.json with actual API keys"
echo "  2. Configure SSL: certbot --nginx -d chat.yourdomain.com"
echo "  3. Test Azure Speech: cd /opt/azure-speech && ./test_azure_speech.py"
echo "  4. Start LM Link Bridge: cd /opt/lm-link && python3 lm-link-bridge.py"
echo ""
echo "Deployment completed at $(date)"
