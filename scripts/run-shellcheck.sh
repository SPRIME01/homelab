#!/usr/bin/env bash
set -euo pipefail

# Wrapper: run shellcheck if present, otherwise perform a basic 'bash -n' syntax check.
if command -v shellcheck >/dev/null 2>&1; then
  exec shellcheck "$@"
else
  echo "shellcheck not found; falling back to 'bash -n' for syntax checks"
  exit_code=0
  for f in "$@"; do
    if [[ -f "$f" ]]; then
      if ! bash -n "$f"; then
        echo "Syntax error in $f"
        exit_code=1
      fi
    fi
  done
  exit $exit_code
fi
