#!/usr/bin/env bash
set -euo pipefail

# Decrypt infra/tailscale.env.sops (with sops) into a temp file and run
# `tailscale up --authkey=<key>` when tailscale binary exists. This is
# intended for machines that should run tailscaled (homelab servers).

if ! command -v sops >/dev/null 2>&1; then
  echo "sops not found; cannot decrypt infra/tailscale.env.sops" >&2
  exit 2
fi

if [ ! -f infra/tailscale.env.sops ]; then
  echo "infra/tailscale.env.sops not found; create and encrypt infra/tailscale.env first" >&2
  exit 2
fi

TMP=$(mktemp)
cleanup(){ rm -f "$TMP"; }
trap cleanup EXIT

echo "Decrypting infra/tailscale.env.sops to temporary file..."
sops -d --input-type dotenv --output-type dotenv infra/tailscale.env.sops > "$TMP"

# shellcheck disable=SC1090
source "$TMP"

if [ -z "${TAILSCALE_AUTHKEY-}" ]; then
  echo "TAILSCALE_AUTHKEY not found in decrypted file" >&2
  exit 1
fi

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale CLI not found. If you are on WSL2 and using Windows host's Tailscale, do NOT run this script in WSL2."
  echo "This script is intended to be run on machines that will run tailscaled (homelab servers)." >&2
  exit 2
fi

echo "Bringing tailscale up with authkey (mockable):"
echo "tailscale up --authkey=***REDACTED***"
tailscale up --authkey="$TAILSCALE_AUTHKEY"

echo "Tailscale join complete. Run 'tailscale status' to verify."

exit 0
