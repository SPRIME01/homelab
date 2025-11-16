#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Migration helper: v1 -> v2

This helper prints steps to migrate from v1.x -> v2.x where breaking changes are expected.

Steps you should manually perform:

1) Update .envrc to export REQUIRE_TAILSCALE=1 if your infra requires Tailscale.
2) Update any references to enable_pulumi -> features_pulumi if your template uses the new naming convention.
3) Run `just ci-validate` and fix failing guard tests.
4) Manually review `justfile` and `tests/` for guard changes and ensure your CI still passes.

EOF
