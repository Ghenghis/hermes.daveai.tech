#!/usr/bin/env bash
# Phase 6: Hermes Access Verification (local-only)
# Checks all local wiring without requiring VPS SSH

set +e

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "  [PASS] $name"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Phase 6: Hermes Access Verification (Local) ==="
echo ""

echo "=== WSL Environment ==="
check "WSL Ubuntu running" "wsl -d Ubuntu -- echo ok"
check "C: drive mounted" "wsl -d Ubuntu -- test -d /mnt/c"
check "G: drive mounted" "wsl -d Ubuntu -- test -d /mnt/g"

echo ""
echo "=== WSL Symlinks ==="
check "work/vps symlink" "wsl -d Ubuntu -- test -L ~/work/vps"
check "work/github symlink" "wsl -d Ubuntu -- test -L ~/work/github"
check "work/hermes-kit symlink" "wsl -d Ubuntu -- test -L ~/work/hermes-kit"

echo ""
echo "=== paths.yml Registry ==="
check "~/.hermes directory exists" "wsl -d Ubuntu -- test -d ~/.hermes"
check "paths.yml exists" "wsl -d Ubuntu -- test -f ~/.hermes/paths.yml"
check "paths.yml valid YAML" "wsl -d Ubuntu -- python3 -c 'import yaml; yaml.safe_load(open(\"/home/fnice/.hermes/paths.yml\"))'"

echo ""
echo "=== WSL Tools (18) ==="
wsl -d Ubuntu -- bash -c "
  for t in ssh git gh curl wget jq rsync zip unzip tar rg fd python3 pip3 node npm docker pwsh; do
    if command -v \$t >/dev/null 2>&1; then
      echo '  [PASS] \$t'
    else
      echo '  [FAIL] \$t'
    fi
  done
" | while read line; do
  if [[ $line == *PASS* ]]; then PASS=$((PASS + 1)); fi
  if [[ $line == *FAIL* ]]; then FAIL=$((FAIL + 1)); fi
  echo "$line"
done

echo ""
echo "=== Windows Tools (12) ==="
powershell -Command "
  \$tools = @('git','gh','pwsh','node','npm','python','pip','docker','rg','fd','jq')
  foreach(\$t in \$tools) {
    if(Get-Command \$t -ErrorAction SilentlyContinue) { Write-Host \"  [PASS] \$t\" } else { Write-Host \"[FAIL] \$t\" }
  }
" 2>&1 | while read line; do
  if [[ $line == *PASS* ]]; then PASS=$((PASS + 1)); fi
  if [[ $line == *FAIL* ]]; then FAIL=$((FAIL + 1)); fi
  echo "$line"
done

echo ""
echo "=== Python Packages ==="
wsl -d Ubuntu -- python3 -c "
  import sys
  pkgs = ['httpx','aiohttp','requests','bs4','paramiko','yaml','dotenv','rich','typer','click']
  for p in pkgs:
    try:
      __import__(p)
      print(f'  [PASS] {p}')
    except ImportError:
      print(f'  [FAIL] {p}')
" | while read line; do
  if [[ $line == *PASS* ]]; then PASS=$((PASS + 1)); fi
  if [[ $line == *FAIL* ]]; then FAIL=$((FAIL + 1)); fi
  echo "$line"
done

echo ""
echo "=== Docker Connectivity ==="
if docker ps >/dev/null 2>&1; then
  echo "  [PASS] Docker daemon responding"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] Docker daemon not responding (start Docker Desktop)"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Phase 6 Result ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
if [ $FAIL -eq 0 ]; then
  echo "  [OK] All local checks passed"
  exit 0
else
  echo "  [WARN] $FAIL checks failed"
  exit 1
fi
