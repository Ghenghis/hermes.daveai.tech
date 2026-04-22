# Hermes Universal Access Roadmap

**Goal:** give Hermes real, unrestricted, **dynamic** access to every surface it might need to operate on — local Windows/Linux filesystems, *newly added drives*, *new folder locations*, remote VPS/servers/cloud, Android devices, GitHub, Docker, MCP endpoints, and HTTP APIs — through a uniform, auto-healing tooling + auth layer.

**The four things Hermes needs to be complete:**

1. **Path access** — every drive, mount, or folder the user registers, reachable without translation friction.
2. **CLI tools installed** — a consistent, re-runnable bundle available in every surface Hermes runs in.
3. **Auth / keys / tokens** — SSH, GitHub, cloud, Docker, all stored once and reused everywhere.
4. **A command runner that picks the right OS/backend** — one abstraction, 12 backends underneath.

**Context:** current deployment = 5 Discord bots in Debian containers on VPS `YOUR_VPS_IP`. They can reach the VPS filesystem + Shiba memory, but they can't see Windows drives, Android devices, or arbitrary new hosts. This roadmap adds a **local WSL2 runtime**, a **registry-based path system** for adding new drives/locations at runtime, and a **12-backend access layer** so any surface works the same way from Hermes' point of view.

---

## 0. Architecture Decision

Three deployment surfaces — Hermes runs in all three and stays in sync via git + Shiba memory.

| Surface                      | Role                                   | Filesystem Access                           | Priority              |
| ---------------------------- | -------------------------------------- | ------------------------------------------- | --------------------- |
| **WSL2 Ubuntu on Windows**   | Local dev, full access to `C:\`, `G:\` | `/mnt/c`, `/mnt/g` native                   | **P0 — set up first** |
| **Docker Desktop container** | Reproducible sandboxed Hermes          | Bind mounts for chosen folders only         | P1                    |
| **VPS Debian containers**    | 24/7 Discord bots, remote ops          | VPS-only; can SSH back to WSL via Tailscale | Already live          |

The WSL2 surface is the single most valuable addition because it solves the Windows-path problem at zero cost.

---

## 1. Phase 1 — WSL2 Local Runtime (P0)

**Outcome:** Hermes runs in an Ubuntu shell that reads and writes `C:\Users\Admin\...` and `G:\Github\...` with zero translation.

### 1.1 Enable WSL2

```powershell
# In an elevated PowerShell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
wsl --update
```

Reboot once. Launch `ubuntu` from Start Menu and complete first-run setup.

### 1.2 Verify Windows drive mounts

```bash
ls /mnt/c/Users/Admin/Downloads/VPS
ls /mnt/g/Github
ls /mnt/g/hermes_master_combined_reviewed_kit
```

If these list, filesystem access is solved.

### 1.3 Optional symlinks for ergonomics

```bash
mkdir -p ~/work
ln -s /mnt/c/Users/Admin/Downloads/VPS        ~/work/vps
ln -s /mnt/g/Github                            ~/work/github
ln -s /mnt/g/hermes_master_combined_reviewed_kit ~/work/hermes-kit
```

---

## 2. Phase 2 — Core Tool Bundle (P0)

**Single command to install everything Hermes needs.** Run inside WSL Ubuntu. Also applicable to Debian VPS containers.

### 2.1 Base install script

Save as `~/work/setup-hermes-tools.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "== Updating apt =="
sudo apt update

echo "== Core CLI bundle =="
sudo apt install -y \
  openssh-client git curl wget jq rsync zip unzip tar \
  ripgrep fd-find bat \
  python3 python3-pip python3-venv \
  build-essential pkg-config

echo "== Node.js 20 (via NodeSource) =="
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

echo "== GitHub CLI =="
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install -y gh

echo "== Docker CE + compose plugin =="
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"

echo "== PowerShell 7 =="
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
  | sudo gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/$(. /etc/os-release && echo $VERSION_ID)/prod $(. /etc/os-release && echo $VERSION_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/microsoft-prod.list > /dev/null
sudo apt update && sudo apt install -y powershell

echo "== Symlinks =="
sudo ln -sf "$(command -v fdfind)" /usr/local/bin/fd 2>/dev/null || true
sudo ln -sf "$(command -v batcat)" /usr/local/bin/bat 2>/dev/null || true

echo "== Python packages (core) =="
pip3 install --break-system-packages --user \
  requests httpx aiohttp beautifulsoup4 lxml pyyaml \
  paramiko python-dotenv rich typer click

echo "== Done =="
```

Run once:

```bash
chmod +x ~/work/setup-hermes-tools.sh
~/work/setup-hermes-tools.sh
```

Log out of WSL and back in for docker group membership to apply.

### 2.2 Verification

```bash
for t in ssh git gh curl wget jq rsync zip unzip tar rg fd python3 pip3 node npm docker pwsh; do
  printf "%-10s " "$t"; command -v "$t" >/dev/null && echo "OK" || echo "MISSING"
done
```

Target: all rows show `OK`.

---

## 3. Phase 3 — Authentication & Keys (P0)

### 3.1 SSH to VPS

```bash
ssh-keygen -t ed25519 -C "hermes-local-wsl" -f ~/.ssh/id_ed25519 -N ""
ssh-copy-id root@YOUR_VPS_IP
ssh root@YOUR_VPS_IP 'echo ok'   # should print ok
```

### 3.2 GitHub (required — currently missing on VPS too)

Interactive login (copy the 8-char code, paste at github.com/login/device):

```bash
gh auth login --git-protocol https --web
gh auth status
```

Export the token to reuse on VPS containers:

```bash
gh auth token > ~/gh-token.txt
chmod 600 ~/gh-token.txt
scp ~/gh-token.txt root@YOUR_VPS_IP:/root/gh-token.txt
ssh root@YOUR_VPS_IP 'for c in hermes1 hermes2 hermes3 hermes4 hermes5; do \
   docker exec -i $c bash -c "gh auth login --with-token" < /root/gh-token.txt; \
done; rm /root/gh-token.txt'
```

This closes the last ❌ from the VPS audit.

### 3.3 Docker socket (WSL)

`newgrp docker` then `docker ps` — if it lists containers, you're in.

---

## 4. Phase 4 — Local Hermes Agent (P1)

### 4.1 Clone & install

```bash
cd ~/work/github
git clone https://github.com/Ghenghis/hermes-agent-2026.4.13.git hermes-local
cd hermes-local/hermes-agent-2026.4.13
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 4.2 Config — reuse VPS env, point paths at WSL

Create `~/.hermes-local/.env`:

```
SILICONFLOW_API_KEY=<same as VPS>
MINIMAX_API_KEY=<same as VPS>
SHIBA_BASE_URL=http://YOUR_VPS_IP:18789
SHIBA_API_KEY=shiba-hermes-2026
HERMES_DATA_DIR=/home/$USER/work
HERMES_SKILLS_EXTERNAL=/mnt/g/hermes_master_combined_reviewed_kit/skills
```

### 4.3 First run

```bash
hermes gateway run --platform cli
```

Test that it reads `/mnt/c/...` and `/mnt/g/...` without error.

---

## 5. Phase 5 — Docker Desktop Alternative (P2)

If user prefers isolation over WSL:

```bash
docker run -d --name hermes-local \
  --restart unless-stopped \
  -v "C:/Users/Admin/Downloads/VPS:/workspace/vps" \
  -v "G:/Github:/workspace/github" \
  -v "G:/hermes_master_combined_reviewed_kit:/workspace/hermes-kit" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file ~/.hermes-local/.env \
  nousresearch/hermes-agent:latest gateway run
```

Path translation (`C:\` → `/workspace/vps`) happens at the bind-mount boundary.

---

## 6. Phase 6 — VPS ↔ Local Bridge (P2, optional but powerful)

Let VPS Hermes bots reach the local Windows machine for cross-environment tasks.

**Recommended:** Tailscale (zero config, NAT-traversing, free tier).

### 6.1 Install Tailscale

On WSL Ubuntu:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```

On VPS:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```

Both now appear in `tailscale status` with `100.x.y.z` IPs. VPS bots can `ssh <tailscale-ip>` into the Windows WSL host and read `/mnt/c/...`.

---

## 7. Verification Checklist

Single end-to-end test. Run from WSL after all phases:

```bash
# Tooling
for t in ssh git gh curl jq rsync rg fd python3 node docker pwsh; do
  command -v "$t" >/dev/null && echo "[OK] $t" || echo "[MISSING] $t"
done

# Filesystem
test -d /mnt/c/Users/Admin/Downloads/VPS          && echo "[OK] C: mount"
test -d /mnt/g/Github                              && echo "[OK] G: mount"

# Remote
ssh -o BatchMode=yes root@YOUR_VPS_IP 'hostname' && echo "[OK] VPS SSH"

# GitHub
gh auth status 2>&1 | grep -q "Logged in"          && echo "[OK] gh auth"

# Docker
docker ps >/dev/null                               && echo "[OK] docker"

# Shiba (VPS)
curl -s --max-time 4 http://YOUR_VPS_IP:18789/health \
  -H "X-Shiba-Key: shiba-hermes-2026" | grep -q '"status":"ok"' \
  && echo "[OK] Shiba memory"

# Hermes local
source ~/work/github/hermes-local/hermes-agent-2026.4.13/.venv/bin/activate \
  && hermes --version && echo "[OK] Hermes CLI"
```

All 8 lines must print `[OK]`.

---

## 8. Priority Order (condensed)

1. **Enable WSL2 + install Ubuntu-24.04** *(5 min)*
2. **Run `setup-hermes-tools.sh`** *(10–15 min)*
3. **`gh auth login` + `ssh-copy-id`** *(5 min)* — also pushes token to VPS, fixing the last ❌
4. **Verify checklist § 7** *(2 min)*
5. **Clone hermes-agent repo into WSL and install locally** *(10 min)*
6. *(Later)* Tailscale bridge, Docker Desktop variant

Total hands-on time: **~45 min**. After that, Hermes can read `C:\`, `G:\`, your VPS, Docker, GitHub, everything.

---

## 9. What This Fixes

| Problem                                           | Fix                                     |
| ------------------------------------------------- | --------------------------------------- |
| `C:\...` / `G:\...` paths fail in Linux container | WSL `/mnt/c`, `/mnt/g` mounts (Phase 1) |
| VPS bots missing `gh auth`                        | Token copy in Phase 3.2                 |
| No local Hermes runtime                           | Phase 4 clone + venv                    |
| No cross-environment reach                        | Phase 6 Tailscale                       |
| Missing CLI tools after reboots                   | Re-runnable `setup-hermes-tools.sh`     |

---

## 10. Open Questions (decide before Phase 4)

- **Skills source of truth** — keep on `G:\hermes_master_combined_reviewed_kit\skills` (Windows canonical) and have VPS `rsync` pull, or flip it?
- **Which Discord platform does local Hermes use?** — probably `cli` only; leave Discord to VPS bots to avoid double-responses.
- **Telegram tokens** — local Hermes should not reuse VPS Telegram tokens (would duplicate replies). Leave `TELEGRAM_BOT_TOKEN` unset locally.

---

*Last updated: 2026-04-18 — VPS audit state: all 5 bots up, 0 restarts, Shiba reachable, gh auth is the last outstanding item and gets closed in Phase 3.2.*

---

## 11. Access Backends — the 12-backend model

Every command Hermes runs passes through **one** of these backends. The runner auto-selects based on the target (`file://`, `ssh://`, `http://`, `adb://`, `mcp://`, etc.).

| #   | Backend          | What it talks to                                             | Transport                       | Example target                      |
| --- | ---------------- | ------------------------------------------------------------ | ------------------------------- | ----------------------------------- |
| 1   | `local-shell`    | Host's default shell (bash/zsh/sh on Linux, pwsh on Windows) | spawn                           | `run("ls", cwd="/mnt/g/Github")`    |
| 2   | `windows-shell`  | PowerShell 7 / cmd.exe                                       | spawn via WSL interop or native | `run("Get-ChildItem C:\\")`         |
| 3   | `linux-shell`    | bash inside WSL or on Linux host                             | spawn                           | `run("apt list --installed")`       |
| 4   | `ssh-remote`     | Any remote SSH endpoint                                      | OpenSSH                         | `run("uptime", host="vps.tailnet")` |
| 5   | `scp-sftp`       | File transfer over SSH                                       | OpenSSH                         | `put(local, remote)`                |
| 6   | `rsync`          | Efficient folder sync                                        | SSH or local                    | `sync(src, dst, delete=True)`       |
| 7   | `http-api`       | Any HTTP/S endpoint                                          | `httpx` / `curl`                | `GET https://api.example.com/v1/x`  |
| 8   | `container-exec` | Docker/Podman container stdin/stdout                         | Docker socket                   | `run("ls", container="hermes1")`    |
| 9   | `mcp-local`      | Local MCP server (stdio)                                     | MCP SDK                         | `call("filesystem.read", ...)`      |
| 10  | `mcp-remote`     | Remote MCP server                                            | WebSocket/SSE                   | `call("github.search", ...)`        |
| 11  | `android-termux` | Termux on Android via SSH                                    | SSH                             | `run("ls ~/storage/shared")`        |
| 12  | `adb-bridge`     | Android via ADB from host                                    | `adb` CLI                       | `run("shell input tap 100 200")`    |

**Uniform API:**

```python
from hermes.access import run, put, get, sync, call

# Auto-picks backend from URI scheme
run("ls", target="file:///mnt/g/Github")             # → local-shell
run("uptime", target="ssh://root@vps.tailnet")       # → ssh-remote
run("ls", target="docker://hermes1")                 # → container-exec
run("ls", target="adb://emulator-5554")              # → adb-bridge
run("ls", target="termux://phone.tailnet:8022")      # → android-termux + ssh
call("repos.list", target="mcp://github")            # → mcp-remote
```

Each backend is a thin adapter over an existing tool (`ssh`, `docker exec`, `adb`, `httpx`, etc.) — no reinventing.

---

## 12. Dynamic Path Registry — add drives & locations at runtime

**Problem:** roadmap can't hard-code every path the user will ever add (new USB drive, new project folder, new network share).

**Solution:** YAML registry at `~/.hermes/paths.yml`, edited by CLI commands or the Access & Tooling UI. Hermes reads it on every request and knows about every registered location.

### 12.1 Registry format

```yaml
# ~/.hermes/paths.yml
paths:
  # Single root — Hermes will traverse it on demand
  - id: c-drive
    label: "Windows C:"
    os: windows
    windows_path: "C:\\"
    wsl_path: "/mnt/c"
    container_mount: "/workspace/c"       # used when running in Docker
    read_only: false
    tags: [system, primary]

  - id: g-drive
    label: "Windows G: (projects)"
    os: windows
    windows_path: "G:\\"
    wsl_path: "/mnt/g"
    container_mount: "/workspace/g"
    tags: [projects, primary]

  - id: vps-data
    label: "VPS /opt/data (hermes)"
    os: linux
    ssh_host: root@YOUR_VPS_IP
    remote_path: /opt/data
    tags: [remote, production]

  - id: phone-termux
    label: "Android Termux storage"
    os: android
    termux_host: user@phone.tailnet:8022
    remote_path: ~/storage/shared
    tags: [mobile]

drives:
  # Mountable/removable drives — auto-detected + manually addable
  - id: usb-ext-1
    label: "External backup drive"
    detect: "/dev/disk/by-label/BACKUP"
    mount_point: /mnt/backup
    auto_mount: true
    tags: [removable, backup]

mcp:
  - id: github-mcp
    label: "GitHub MCP server"
    url: "https://mcp.github.com"
    auth: env:GITHUB_TOKEN

  - id: local-fs-mcp
    label: "Local filesystem MCP"
    command: "npx -y @modelcontextprotocol/server-filesystem"
    args: ["/mnt/g", "/mnt/c/Users/Admin"]
```

### 12.2 CLI commands to manage it

```bash
# Add a brand-new drive or folder — registers it everywhere Hermes runs
hermes path add --id new-ssd --label "2TB NVMe" \
    --windows "D:\\" --wsl /mnt/d --container /workspace/d

# Add a remote SSH target
hermes path add --id training-box --label "GPU rig" \
    --ssh user@gpu.example.com --remote /home/user/work

# Add an Android/Termux target
hermes path add --id phone --label "Pixel" \
    --termux u0_a123@100.64.1.5:8022 --remote ~/storage/shared

# List everything Hermes can reach
hermes path list

# Verify all registered paths are actually accessible right now
hermes path verify

# Remove
hermes path remove --id new-ssd

# Reload (after editing the YAML by hand)
hermes path reload
```

### 12.3 Auto-detection

On startup and on-demand, Hermes runs:

- `lsblk -J` (Linux/WSL) → find new block devices, offer to register
- `Get-PSDrive -PSProvider FileSystem` (Windows) → find new drives
- `tailscale status` → find new tailnet peers
- `adb devices` → find new Android devices
- `docker ps --format '{{.Names}}'` → find new containers

Anything new is queued for the user with a one-click "Register?" prompt (CLI or UI).

---

## 13. Per-OS Tool Bundles (complete)

### 13.1 Windows host — native side

Run in elevated PowerShell:

```powershell
# winget-driven, fully non-interactive
$pkgs = @(
  "Git.Git",
  "GitHub.cli",
  "Microsoft.PowerShell",
  "OpenJS.NodeJS.LTS",
  "Python.Python.3.12",
  "Microsoft.OpenSSH.Beta",
  "Docker.DockerDesktop",
  "Microsoft.WindowsTerminal",
  "7zip.7zip",
  "BurntSushi.ripgrep.MSVC",
  "sharkdp.fd",
  "jqlang.jq"
)
foreach ($p in $pkgs) { winget install --silent --accept-source-agreements --accept-package-agreements $p }

# Enable WSL (if not already)
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
```

### 13.2 Linux (Debian/Ubuntu) — WSL or native or VPS

Already covered in § 2.1 `setup-hermes-tools.sh`. That script is the canonical Linux bundle.

### 13.3 Android (Termux) — mobile surface

Install F-Droid → install Termux + Termux:API from F-Droid (Play Store version is outdated).

Inside Termux:

```bash
pkg update -y && pkg upgrade -y
pkg install -y openssh git curl wget jq python nodejs rsync tar zip unzip termux-api
termux-setup-storage           # grants access to ~/storage/shared → /sdcard
sshd                            # start SSH daemon
passwd                          # set a password
whoami                          # note the u0_aXXX user
ifconfig wlan0 | grep inet      # note the IP
```

Connect from Hermes host:

```bash
ssh -p 8022 u0_aXXX@<phone-ip>
```

Register in path registry (see § 12.2).

### 13.4 Remote Linux / VPS / cloud

Same as § 13.2. Pushed via SSH + `apt-get`.

### 13.5 Training / GPU hosts

Base § 13.2 bundle **plus**:

```bash
sudo apt install -y git-lfs
pip install --user torch torchvision transformers datasets accelerate bitsandbytes
nvidia-smi                      # verify NVIDIA driver
# CUDA toolkit only if the training code actually links against it
```

---

## 14. Settings UI — "Access & Tooling" panel

Single panel, six sections, real actions only. Add to `webview-ui/src/components/settings/AccessTab.tsx`.

### 14.1 Layout

```
┌─ Access & Tooling ──────────────────────────────────────┐
│                                                         │
│  ▸ Paths & Drives             [+ Add] [⟳ Auto-detect]  │
│    • C:\ (C:)           wsl=/mnt/c      ✅ reachable    │
│    • G:\ (G:)           wsl=/mnt/g      ✅ reachable    │
│    • VPS /opt/data      ssh=root@...    ✅ reachable    │
│    • Pixel /storage     termux=u0_a...  ❌ unreachable  │
│                                                         │
│  ▸ Remote Hosts (SSH)         [+ Add] [Test All]       │
│                                                         │
│  ▸ GitHub / Repos             [Login] [Status] [Copy]  │
│                                                         │
│  ▸ Containers & Docker        [Start] [Stop] [Shell]   │
│                                                         │
│  ▸ MCP Endpoints              [+ Add] [Reload]         │
│                                                         │
│  ▸ Runtimes & Tools                                     │
│    Windows:   [Install] [Verify] [Repair]               │
│    Linux:     [Install] [Verify] [Repair]               │
│    Android:   [Install] [Verify] [Repair]               │
│    GPU/ML:    [Install] [Verify] [Repair]               │
│                                                         │
│  [ Verify All Access ]  [ Repair Missing ]  [ Logs ]   │
└─────────────────────────────────────────────────────────┘
```

### 14.2 Button actions — every one wired to a real operation

| Button              | Calls                                                             |
| ------------------- | ----------------------------------------------------------------- |
| `Install` (per OS)  | `hermes tools install --os=<os>` → runs the bundle script         |
| `Verify` (per OS)   | `hermes tools verify --os=<os>` → § 15 checklist                  |
| `Repair` (per OS)   | `hermes tools repair --os=<os>` → reinstalls only missing         |
| `+ Add` (Paths)     | Opens dialog, writes to `~/.hermes/paths.yml`                     |
| `Auto-detect`       | Runs `lsblk` / `Get-PSDrive` / `tailscale status` / `adb devices` |
| `Test All`          | Parallel connectivity check across every registered target        |
| `Verify All Access` | Runs § 15 end-to-end checklist, shows pass/fail matrix            |
| `Repair Missing`    | For every ❌, runs the specific remediation                        |
| `Logs`              | Opens `~/.hermes/logs/access.log` tail                            |

**No dead buttons. No decoration.** Every control maps to a concrete `hermes ...` CLI invocation.

---

## 15. Verify-All-Access Checklist (end-to-end)

Single script, runs in under 60 seconds, produces a matrix.

```bash
#!/usr/bin/env bash
# ~/.hermes/bin/verify-all

set +e
pass() { echo "[✅] $1"; }
fail() { echo "[❌] $1 — $2"; }

# ── Tools ────────────────────────────────────────────────
for t in ssh scp sftp rsync git gh curl wget jq rg fd python3 pip3 node npm docker pwsh adb; do
  command -v "$t" >/dev/null && pass "tool: $t" || fail "tool: $t" "not in PATH"
done

# ── Paths ────────────────────────────────────────────────
yq '.paths[] | .id + " " + (.wsl_path // .windows_path // .remote_path // "?")' \
  ~/.hermes/paths.yml | while read id path; do
  if [[ "$path" =~ ^/ ]]; then
    test -e "$path" && pass "path: $id ($path)" || fail "path: $id" "$path missing"
  fi
done

# ── SSH hosts ────────────────────────────────────────────
yq '.paths[] | select(.ssh_host) | .id + " " + .ssh_host' ~/.hermes/paths.yml | \
while read id host; do
  ssh -o BatchMode=yes -o ConnectTimeout=4 "$host" 'echo ok' >/dev/null 2>&1 \
    && pass "ssh: $id" || fail "ssh: $id" "unreachable"
done

# ── GitHub ───────────────────────────────────────────────
gh auth status 2>&1 | grep -q "Logged in" && pass "gh auth" || fail "gh auth" "not logged in"

# ── Docker ───────────────────────────────────────────────
docker ps >/dev/null 2>&1 && pass "docker" || fail "docker" "socket unreachable"

# ── ADB (if any Android in registry) ─────────────────────
if yq '.paths[] | select(.os == "android")' ~/.hermes/paths.yml | grep -q .; then
  adb devices | grep -q "device$" && pass "adb" || fail "adb" "no devices"
fi

# ── HTTP (sample) ────────────────────────────────────────
curl -s --max-time 4 https://api.github.com/zen >/dev/null \
  && pass "http" || fail "http" "outbound blocked"

# ── Shiba memory (VPS) ───────────────────────────────────
curl -s --max-time 4 http://YOUR_VPS_IP:18789/health \
  -H "X-Shiba-Key: shiba-hermes-2026" | grep -q '"status":"ok"' \
  && pass "shiba" || fail "shiba" "unreachable"

# ── MCP endpoints ────────────────────────────────────────
yq '.mcp[].id' ~/.hermes/paths.yml | while read id; do
  hermes mcp ping --id "$id" >/dev/null 2>&1 \
    && pass "mcp: $id" || fail "mcp: $id" "ping failed"
done
```

`hermes access verify` wraps this and prints a single pass/fail summary.

---

## 16. Auto-Repair — when something fails

Each failure category has a deterministic fix:

| Failure                     | Auto-repair action                                                                       |
| --------------------------- | ---------------------------------------------------------------------------------------- |
| `tool: X not in PATH`       | `apt install X` (Linux/WSL) or `winget install X` (Windows) or `pkg install X` (Termux)  |
| `path: X missing`           | Re-check mount (`mount \| grep`), attempt `mount` if removable, else prompt user         |
| `ssh: X unreachable`        | `ssh-keygen -R host`, retry; if still fails, prompt for password to re-run `ssh-copy-id` |
| `gh auth not logged in`     | Launch `gh auth login --web` in new terminal                                             |
| `docker socket unreachable` | `sudo systemctl start docker` + `usermod -aG docker $USER`                               |
| `adb: no devices`           | `adb kill-server && adb start-server`, prompt user to enable USB debugging               |
| `http outbound blocked`     | Surface in UI (network/firewall issue — can't auto-fix)                                  |
| `shiba unreachable`         | Re-apply iptables rule (already persisted via `/etc/rc.local`)                           |
| `mcp: X ping failed`        | Restart MCP process if local (`stdio`), else surface                                     |

Exposed as `hermes access repair` — runs through every ❌ and applies the matching fix, then re-verifies.

---

## 17. Priority Order (updated, full)

| Phase | What                                                           | Time   | Outcome                                |
| ----- | -------------------------------------------------------------- | ------ | -------------------------------------- |
| 1     | WSL2 + Ubuntu-24.04 install                                    | 5 min  | `/mnt/c`, `/mnt/g` available           |
| 2     | `setup-hermes-tools.sh` (Linux bundle)                         | 15 min | All Linux tools in WSL                 |
| 3     | Windows-side `winget` bundle (§ 13.1)                          | 10 min | Docker Desktop, native gh, pwsh 7      |
| 4     | `gh auth login` + `ssh-copy-id` + token push to VPS            | 5 min  | GitHub works everywhere, VPS ❌ cleared |
| 5     | Path registry (`~/.hermes/paths.yml`) populated with C, G, VPS | 3 min  | Hermes knows the 3 starter paths       |
| 6     | `hermes access verify` passes all rows                         | 2 min  | Baseline confirmed                     |
| 7     | Clone hermes-agent into WSL, install locally                   | 10 min | Local Hermes runs                      |
| 8     | Tailscale on WSL + VPS                                         | 5 min  | VPS bots can reach local machine       |
| 9     | *(optional)* Termux on Android, register in path registry      | 15 min | Mobile surface                         |
| 10    | *(optional)* GPU/training host via SSH + register              | 10 min | ML workloads reachable                 |

**P0 total (1-6): ~40 min.** After that, every new drive, folder, server, phone, or container just needs `hermes path add ...` — no more roadmaps.

---

## 18. What "complete" really means

Hermes is complete when **all of these are one command away**:

- ☐ Open any registered Windows path (`C:\`, `G:\`, newly-added drives)
- ☐ Open any registered Linux path (local or via SSH)
- ☐ Open any registered Android path (via Termux SSH)
- ☐ SSH into any registered remote host
- ☐ Move files with `scp` / `sftp` / `rsync` to any registered target
- ☐ Run `git` / `gh` authenticated as the user
- ☐ Run `python` / `node` / `pip` / `npm` in every surface
- ☐ Run `docker` / `docker compose` locally and on VPS
- ☐ Call any HTTP/S API with proper auth
- ☐ Use Android via Termux shell or ADB bridge
- ☐ Reach training/cloud/GPU boxes identically to any Linux host
- ☐ Talk to any local or remote MCP endpoint
- ☐ Register **new** paths/drives/hosts at runtime without code changes

Every checkbox maps to one of the 12 backends in § 11 + one registry entry in § 12.

---

## 19. Condensed package list (the "short final list")

### Must-have everywhere
`git` · `curl` · `wget` · `jq` · `zip` · `unzip` · `tar` · `ripgrep` · `fd`

### Remote access
`openssh-client` · `openssh-server` (optional) · `rsync` · `scp` · `sftp`

### Runtimes
`python3` · `python3-pip` · `nodejs` · `npm` · `npx`

### Repo / GitHub
`gh`

### Containers
`docker` · `docker compose` (v2 plugin)

### Windows bridge
`powershell` / `pwsh` · access to `cmd.exe` · WSL · Git Bash

### Android (Termux)
`openssh` · `git` · `curl` · `wget` · `python` · `nodejs` · `rsync` · `tar` · `zip` · `unzip` · `jq` · `termux-api`

### Training / GPU
`git-lfs` · `python3-venv` · `nvidia-smi` · optional CUDA/cuDNN · optional `docker`

All of the above are installed/verified/repaired via the single `hermes tools {install|verify|repair} --os=<os>` command.

---

*Roadmap v2 — expanded from single-WSL focus to full universal-access model. Registry-driven, backend-abstracted, auto-healing.*

