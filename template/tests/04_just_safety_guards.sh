#!/usr/bin/env bash
set -euo pipefail

# Skip if `just` isn't installed in the environment
if ! command -v just >/dev/null 2>&1; then
  echo "skipping: just not found"
  exit 2
fi

echo "Validating Justfile syntax with 'just --dump'..."
just --dump >/dev/null

echo "Testing deploy fails when HOMELAB=0"
if HOMELAB=0 just deploy >/dev/null 2>&1; then
  echo "deploy unexpectedly succeeded with HOMELAB=0"
  exit 1
fi

echo "Testing deploy succeeds when HOMELAB=1 and DEPLOY_CONFIRM=yes"
if ! HOMELAB=1 DEPLOY_CONFIRM=yes just deploy | grep -q "Infra deploy allowed"; then
  echo "deploy did not succeed with HOMELAB=1 and DEPLOY_CONFIRM=yes"
  exit 1
fi

echo "Just safety guards tests passed"
exit 0
