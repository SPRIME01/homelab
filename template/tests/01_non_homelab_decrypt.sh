#!/usr/bin/env bash
set -euo pipefail

# Test: secret cannot be decrypted on non-homelab machines
# This test expects there to be no $HOME/.config/sops/age/keys.txt present.

KEYFILE="$HOME/.config/sops/age/keys.txt"
if [ -f "$KEYFILE" ]; then
  echo "SKIP: $KEYFILE exists. Move or remove it to run this test on a non-homelab machine." >&2
  exit 2
fi

if sops --input-type dotenv --output-type dotenv -d infra/example.env.sops >/dev/null 2>&1; then
  echo "FAIL: file decrypted without local homelab key" >&2
  exit 1
else
  echo "PASS: decryption failed as expected on non-homelab machine"
fi
