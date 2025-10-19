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

case "${MODE}" in
  local)
    export HOMELAB_ENV_TARGET="developer-shell"
    ;;
  shell)
    export HOMELAB_ENV_TARGET="devbox-shell"
    ;;
  ci)
    export HOMELAB_ENV_TARGET="ci-pipeline"
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
