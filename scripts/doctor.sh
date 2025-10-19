#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🔍 Running homelab doctor checks..."

required_bins=(direnv devbox mise pnpm npx just)

for bin in "${required_bins[@]}"; do
  if ! command -v "${bin}" >/dev/null 2>&1; then
    echo "❌ Missing dependency: ${bin}" >&2
    exit 1
  fi
done

if [[ ! -f "${ROOT_DIR}/lib/env-loader.sh" ]]; then
  echo "❌ Missing lib/env-loader.sh" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/devbox.json" ]]; then
  echo "❌ Missing devbox.json" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/.mise.toml" ]]; then
  echo "❌ Missing .mise.toml" >&2
  exit 1
fi

echo "✅ Environment prerequisites detected."
