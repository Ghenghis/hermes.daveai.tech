#!/usr/bin/env bash
# Hermes universal tool bundle — Linux/WSL/VPS
# Re-runnable, idempotent. Run as root (or with sudo).
set -euo pipefail

log() { echo ""; echo "[$(date +%H:%M:%S)] === $* ==="; }

# Determine the non-root user (passed via env or auto-detect)
TARGET_USER="${TARGET_USER:-${SUDO_USER:-fnice}}"
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6 || echo "/home/$TARGET_USER")

log "Target user: $TARGET_USER (home: $TARGET_HOME)"

log "Updating apt index"
apt-get update -qq

log "Core CLI bundle"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
  openssh-client git curl wget jq rsync zip unzip tar \
  ripgrep fd-find bat \
  python3 python3-pip python3-venv python3-full \
  build-essential pkg-config ca-certificates gnupg lsb-release \
  apt-transport-https software-properties-common

log "Node.js 20 via NodeSource"
NODE_MAJOR=0
if command -v node >/dev/null; then
  NODE_MAJOR=$(node -v | cut -d. -f1 | tr -d v)
fi
if [ "$NODE_MAJOR" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -q nodejs
fi

log "GitHub CLI"
if ! command -v gh >/dev/null; then
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
  echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update -qq
  apt-get install -y -q gh
fi

log "Docker CE + compose plugin"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
usermod -aG docker "$TARGET_USER" 2>/dev/null || true

log "PowerShell 7"
if ! command -v pwsh >/dev/null; then
  mkdir -p /etc/apt/keyrings
  curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg 2>/dev/null || true
  UBU_VER=$(. /etc/os-release && echo "$VERSION_ID")
  CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/${UBU_VER}/prod ${CODENAME} main" \
    > /etc/apt/sources.list.d/microsoft-prod.list
  apt-get update -qq
  apt-get install -y -q powershell || echo "[warn] powershell install failed (non-fatal)"
fi

log "Symlinks for fdfind/batcat"
[ -x /usr/bin/fdfind ] && ln -sf /usr/bin/fdfind /usr/local/bin/fd
[ -x /usr/bin/batcat ] && ln -sf /usr/bin/batcat /usr/local/bin/bat

log "Python packages (user-level)"
sudo -u "$TARGET_USER" -H pip3 install --break-system-packages --user -q \
  requests httpx aiohttp beautifulsoup4 lxml pyyaml \
  paramiko python-dotenv rich typer click

log "Verification"
FAILED=0
for t in ssh git gh curl wget jq rsync zip unzip tar rg fd python3 pip3 node npm docker pwsh; do
  if command -v "$t" >/dev/null; then
    printf "  [OK]      %-10s %s\n" "$t" "$(command -v "$t")"
  else
    printf "  [MISSING] %s\n" "$t"
    FAILED=$((FAILED + 1))
  fi
done

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo "[!] $FAILED tools missing — rerun this script or install manually"
  exit 1
fi

echo ""
echo "[✓] All tools installed. Log out of WSL and back in for docker group membership to apply."
