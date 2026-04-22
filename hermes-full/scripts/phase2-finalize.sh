#!/usr/bin/env bash
# Run as fnice — finalize PATH and verify
set +e

BASHRC="$HOME/.bashrc"
if ! grep -q 'HOME/.local/bin' "$BASHRC"; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$BASHRC"
  echo "[+] added ~/.local/bin to PATH"
fi

# Source and verify
export PATH="$HOME/.local/bin:$PATH"

echo ""
echo "=== Phase 2 final tool check ==="
FAILED=0
for t in ssh git gh curl wget jq rsync zip unzip tar rg fd python3 pip3 node npm docker pwsh; do
  if command -v "$t" >/dev/null; then
    printf "  [OK]  %-8s  %s\n" "$t" "$(command -v "$t")"
  else
    printf "  [XX]  %s\n" "$t"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "=== Python packages check ==="
python3 -c "import httpx, aiohttp, requests, bs4, paramiko, yaml, dotenv, rich, typer, click; print('[OK] all python modules import')" \
  || echo "[XX] python modules failed"

echo ""
echo "=== Docker connectivity ==="
docker ps --format '{{.Names}}' 2>&1 | head -3

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "=== PHASE 2 COMPLETE ==="
else
  echo "=== $FAILED tools still missing ==="
fi
