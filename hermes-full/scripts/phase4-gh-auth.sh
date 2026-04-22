#!/usr/bin/env bash
# Phase 4: gh auth token push to VPS containers
set -e

GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
VPS="root@YOUR_VPS_IP"

echo "=== Phase 4: Push gh token to VPS containers ==="
echo "Token: ${GITHUB_TOKEN:0:20}..."

# Push token to VPS (using SSH keys already set up)
echo "Pushing token to VPS..."
echo "$GITHUB_TOKEN" | ssh -o StrictHostKeyChecking=no "$VPS" "cat > /tmp/gh-token.txt && chmod 600 /tmp/gh-token.txt"

# Authenticate gh in all 5 containers
echo ""
echo "Authenticating gh in containers..."
for c in hermes1 hermes2 hermes3 hermes4 hermes5; do
  echo "  $c:"
  ssh -o StrictHostKeyChecking=no "$VPS" \
    "docker exec -i $c bash -c 'gh auth login --with-token' < /tmp/gh-token.txt" 2>/dev/null
  STATUS=$(ssh -o StrictHostKeyChecking=no "$VPS" \
    "docker exec $c gh auth status 2>&1 | head -2")
  echo "    $STATUS"
done

# Cleanup
ssh -o StrictHostKeyChecking=no "$VPS" "rm /tmp/gh-token.txt"

echo ""
echo "=== Phase 4 COMPLETE ==="
