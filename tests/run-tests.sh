#!/usr/bin/env bash
set -euo pipefail

echo "Running tests..."

tests=(
  "01_non_homelab_decrypt.sh"
  "02_sops_yaml_schema.sh"
  "03_round_trip_homelab.sh"
)

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

fail=0
for t in "${tests[@]}"; do
  echo
  echo "--- Running $t ---"
  bash "tests/$t" || { echo "Test $t failed"; fail=1; }
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
