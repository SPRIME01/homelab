#!/usr/bin/env bash
set -euo pipefail

echo "Running tests..."

tests=(
  "01_non_homelab_decrypt.sh"
  "02_sops_yaml_schema.sh"
  "03_round_trip_homelab.sh"
  "04_just_safety_guards.sh"
  "05_tailscale_ssh_guards.sh"
)

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

fail=0
for t in "${tests[@]}"; do
  echo
  echo "--- Running $t ---"
  rc=0
  bash "tests/$t" || rc=$?
  if [ "$rc" -eq 2 ]; then
    echo "Test $t skipped"
    continue
  elif [ "$rc" -ne 0 ]; then
    echo "Test $t failed"
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo
  echo "One or more tests failed" >&2
  exit 1
else
  echo
  echo "All tests passed (or were skipped as appropriate)"
  exit 0
fi
