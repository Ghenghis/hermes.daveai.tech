#!/usr/bin/env bash
# Repair broken postfix + verify installed tools
set +e

echo "=== Purging broken postfix ==="
DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y postfix 2>&1 | tail -3
apt-get install -y -f 2>&1 | tail -3
apt-get autoremove -y 2>&1 | tail -2

echo ""
echo "=== Tool verification ==="
FAILED=0
for t in ssh git gh curl wget jq rsync zip unzip tar rg fd python3 pip3 node npm docker pwsh; do
  if command -v "$t" >/dev/null; then
    V=$("$t" --version 2>&1 | head -1 | cut -c1-60)
    printf "  [OK]      %-10s %s\n" "$t" "$V"
  else
    printf "  [MISSING] %s\n" "$t"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "=== Result: $FAILED tools missing ==="
