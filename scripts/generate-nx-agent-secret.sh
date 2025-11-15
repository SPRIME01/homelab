#!/usr/bin/env bash
# Generate secure random secret for Nx distributed agents
# Usage: bash scripts/generate-nx-agent-secret.sh

set -euo pipefail

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: openssl not found (required for secure random generation)" >&2
  exit 1
fi

# Generate 256-bit (32 byte) random hex string
NX_SHARED_SECRET=$(openssl rand -hex 32)

echo "Generated Nx agent shared secret (store in infra/nx-agents.env, then encrypt):"
echo ""
echo "NX_SHARED_SECRET=${NX_SHARED_SECRET}"
echo ""
echo "IMPORTANT: This secret authorizes agents to join the distributed execution cluster."
echo "  1. Copy this to infra/nx-agents.env"
echo "  2. Add NX_AGENT_IPS=100.64.0.10,100.64.0.11 (your Tailscale IPs)"
echo "  3. Encrypt with: just nx-encrypt-config"
echo "  4. Delete plaintext infra/nx-agents.env"
echo ""
echo "For migration to per-agent keypairs, see docs/Nx Agent Migration.md"
