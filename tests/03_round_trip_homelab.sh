#!/usr/bin/env bash
set -euo pipefail

# Test: encryption round-trip succeeds on homelab node with private identity present
KEYFILE="$HOME/.config/sops/age/keys.txt"
if [ ! -f "$KEYFILE" ]; then
  echo "SKIP: homelab private identity not found at $KEYFILE" >&2
  exit 2
fi

PUB=$(grep '^# public key:' "$KEYFILE" | sed 's/^# public key: //')
if [ -z "$PUB" ]; then
  echo "FAIL: could not extract public key from $KEYFILE" >&2
  exit 1
fi

TMP_ENC=/tmp/test_example.env.sops
TMP_DEC=/tmp/decrypted_example.env

echo "Encrypting infra/example.env -> $TMP_ENC"
SOPS_CONFIG=/dev/null sops --encrypt --input-type dotenv --output-type dotenv --age "$PUB" infra/example.env > "$TMP_ENC"

echo "Decrypting $TMP_ENC"
sops --input-type dotenv --output-type dotenv -d "$TMP_ENC" > "$TMP_DEC"

if diff -u infra/example.env "$TMP_DEC" >/dev/null 2>&1; then
  echo "PASS: round-trip OK"
  rm -f "$TMP_DEC" "$TMP_ENC"
  exit 0
else
  echo "FAIL: decrypted contents differ" >&2
  echo "Decrypted file is at $TMP_DEC for inspection"
  exit 1
fi
