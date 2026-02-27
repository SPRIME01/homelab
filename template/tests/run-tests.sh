#!/usr/bin/env bash
set -euo pipefail

echo "Running tests..."

tests=(
  "01_non_homelab_decrypt.sh"
  "02_sops_yaml_schema.sh"
  "03_round_trip_homelab.sh"
  "04_just_safety_guards.sh"
  "05_tailscale_ssh_guards.sh"
  "06_pulumi_project_validation.sh"
  "07_ansible_molecule_validation.sh"
  "08_infra_guards.sh"
  "09_tailscale_ssh_verification.sh"
  "10_nx_distributed_validation.sh"
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
