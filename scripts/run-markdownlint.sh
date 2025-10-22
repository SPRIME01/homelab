#!/usr/bin/env bash
set -euo pipefail

# Run markdownlint (node-based) if available; otherwise print a message and exit 0
if command -v markdownlint >/dev/null 2>&1; then
  exec markdownlint "$@"
else
  echo "markdownlint not found; skipping markdown lint (install with npm i -g markdownlint-cli)"
  exit 0
fi
