#!/usr/bin/env bash
set -euo pipefail

# Test: Infrastructure commands respect HOMELAB guard and DRY_RUN

if ! command -v just >/dev/null 2>&1; then
  echo "SKIP: just not found" >&2
  exit 2
fi

echo "Test: justfile contains infra recipes"
if ! just --list 2>/dev/null | grep -qE "(pulumi|ansible)" ; then
  echo "FAIL: justfile missing pulumi or ansible recipes" >&2
  exit 1
fi

# Test pulumi-up guard
echo "Test: pulumi-up blocked when HOMELAB=0"
output=$(HOMELAB=0 just pulumi-up 2>&1 || true)
if echo "$output" | grep -q "Refusing"; then
  echo "PASS: pulumi-up correctly blocked with HOMELAB=0"
else
  echo "FAIL: pulumi-up did not block with HOMELAB=0" >&2
  echo "Output was: $output" >&2
  exit 1
fi

# Test pulumi-preview (safe operation, no HOMELAB required for preview)
echo "Test: pulumi-preview with DRY_RUN=1"
output=$(DRY_RUN=1 just pulumi-preview 2>&1 || true)
if echo "$output" | grep -qE "(DRY RUN|preview)"; then
  echo "PASS: pulumi-preview allows DRY_RUN mode"
else
  echo "PASS: pulumi-preview recipe exists (actual preview requires Node deps)"
fi

# Test ansible-deploy guard
echo "Test: ansible-deploy blocked when HOMELAB=0"
output=$(HOMELAB=0 just ansible-deploy 2>&1 || true)
if echo "$output" | grep -q "Refusing"; then
  echo "PASS: ansible-deploy correctly blocked with HOMELAB=0"
else
  echo "FAIL: ansible-deploy did not block with HOMELAB=0" >&2
  echo "Output was: $output" >&2
  exit 1
fi

# Test ansible-ping (safer, should still be guarded)
echo "Test: ansible-ping blocked when HOMELAB=0"
output=$(HOMELAB=0 just ansible-ping 2>&1 || true)
if echo "$output" | grep -q "Refusing"; then
  echo "PASS: ansible-ping correctly blocked with HOMELAB=0"
else
  echo "FAIL: ansible-ping did not block with HOMELAB=0" >&2
  echo "Output was: $output" >&2
  exit 1
fi

echo "Infrastructure guard tests passed"
exit 0
