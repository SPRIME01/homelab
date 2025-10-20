#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load the structured logging system
if [[ -f "${ROOT_DIR}/lib/logging.sh" ]]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/lib/logging.sh"
else
    echo "ERROR: Could not find logging.sh at ${ROOT_DIR}/lib/logging.sh" >&2
    exit 1
fi

# Set service name for this script
export HOMELAB_SERVICE="doctor"

log_info "Running homelab doctor checks..." "script=doctor.sh" "action=start"

required_bins=(direnv devbox mise pnpm npx just)

for bin in "${required_bins[@]}"; do
  if ! command -v "${bin}" >/dev/null 2>&1; then
    log_error "Missing dependency: ${bin}" "component=dependency_check" "dependency=${bin}" "status=missing"
    exit 1
  else
    log_debug "Found dependency: ${bin}" "component=dependency_check" "dependency=${bin}" "status=found"
  fi
done

if [[ ! -f "${ROOT_DIR}/lib/env-loader.sh" ]]; then
  log_error "Missing lib/env-loader.sh" "component=file_check" "file=lib/env-loader.sh" "status=missing"
  exit 1
else
  log_debug "Found lib/env-loader.sh" "component=file_check" "file=lib/env-loader.sh" "status=found"
fi

if [[ ! -f "${ROOT_DIR}/devbox.json" ]]; then
  log_error "Missing devbox.json" "component=file_check" "file=devbox.json" "status=missing"
  exit 1
else
  log_debug "Found devbox.json" "component=file_check" "file=devbox.json" "status=found"
fi

if [[ ! -f "${ROOT_DIR}/.mise.toml" ]]; then
  log_error "Missing .mise.toml" "component=file_check" "file=.mise.toml" "status=missing"
  exit 1
else
  log_debug "Found .mise.toml" "component=file_check" "file=.mise.toml" "status=found"
fi

log_info "Environment prerequisites detected." "component=doctor" "status=complete"
