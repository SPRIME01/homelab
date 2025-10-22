#!/usr/bin/env bash

set -euo pipefail

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  _ENV_LOADER_PREV_SHELL_OPTS="$(set +o)"
  trap 'eval "${_ENV_LOADER_PREV_SHELL_OPTS}"' RETURN
fi

MODE="${1:-local}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

load_env_file() {
  local file="$1"
  [[ -f "${file}" ]] || return 0

  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    if [[ "${line}" == *"="* ]]; then
      local key="${line%%=*}"
      local value="${line#*=}"
      value="${value%$'\r'}"
      export "${key}"="${value}"
    fi
  done < "${file}"
}

load_sops_env() {
  local file="$1"
  [[ -f "${file}" && -x "$(command -v sops || true)" ]] || return 0

  local tmp
  tmp="$(mktemp "${PROJECT_ROOT}/.sops.XXXXXX")"
  if sops -d "${file}" > "${tmp}"; then
    load_env_file "${tmp}"
  else
    echo "Warning: failed to decrypt ${file}" >&2
  fi
  rm -f "${tmp}"
}

export HOMELAB_ENV_MODE="${MODE}"

# Set HOMELAB_OBSERVE flag (default to 1, but allow override)
export HOMELAB_OBSERVE="${HOMELAB_OBSERVE:-1}"

# Set HOMELAB_LOG_TARGET based on HOMELAB_OBSERVE flag
if [[ -z "${HOMELAB_LOG_TARGET:-}" ]]; then
    # If HOMELAB_LOG_TARGET is unset, test HOMELAB_OBSERVE explicitly for the string "1"
    if [[ "${HOMELAB_OBSERVE}" == "1" ]]; then
        export HOMELAB_LOG_TARGET="vector"
    else
        export HOMELAB_LOG_TARGET="stdout"
    fi
fi

case "${MODE}" in
  local)
    export HOMELAB_ENV_TARGET="developer-shell"
    export HOMELAB_SERVICE="homelab"
    export HOMELAB_ENVIRONMENT="development"
    ;;
  shell)
    export HOMELAB_ENV_TARGET="devbox-shell"
    export HOMELAB_SERVICE="homelab"
    export HOMELAB_ENVIRONMENT="development"
    ;;
  ci)
    export HOMELAB_ENV_TARGET="ci-pipeline"
    export HOMELAB_SERVICE="homelab"
    export HOMELAB_ENVIRONMENT="ci"
    export CI=true
    ;;
  *)
    echo "Unknown env-loader mode: ${MODE}" >&2
    exit 1
    ;;
esac

# Legacy compatibility warning
if [[ -n "${SCRIPTS_LOAD_ENV_SH_WARNING:-}" ]]; then
  echo "Warning: scripts/load_env.sh is deprecated. Please use lib/env-loader.sh instead."
fi

load_env_file "${PROJECT_ROOT}/.env"
load_env_file "${PROJECT_ROOT}/.env.local"
load_sops_env "${PROJECT_ROOT}/.env.sops"

export PATH="${PROJECT_ROOT}/node_modules/.bin:${PATH}"
export UV_CACHE_DIR="${PROJECT_ROOT}/.cache/uv"
mkdir -p "${UV_CACHE_DIR}"
