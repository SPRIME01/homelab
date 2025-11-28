#!/usr/bin/env bash
set -euo pipefail

# Test: Pulumi project structure and configuration validation

if ! command -v node >/dev/null 2>&1; then
  echo "SKIP: node not installed" >&2
  exit 2
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "SKIP: npm not installed" >&2
  exit 2
fi

echo "Test: Pulumi project files exist"
if [ ! -f "infra/pulumi-bootstrap/Pulumi.yaml" ]; then
  echo "FAIL: infra/pulumi-bootstrap/Pulumi.yaml not found" >&2
  exit 1
fi

if [ ! -f "infra/pulumi-bootstrap/package.json" ]; then
  echo "FAIL: infra/pulumi-bootstrap/package.json not found" >&2
  exit 1
fi

if [ ! -f "infra/pulumi-bootstrap/tsconfig.json" ]; then
  echo "FAIL: infra/pulumi-bootstrap/tsconfig.json not found" >&2
  exit 1
fi

if [ ! -f "infra/pulumi-bootstrap/index.ts" ]; then
  echo "FAIL: infra/pulumi-bootstrap/index.ts not found" >&2
  exit 1
fi

echo "Test: Pulumi.yaml contains required keys"
if ! grep -q "^name:" infra/pulumi-bootstrap/Pulumi.yaml; then
  echo "FAIL: Pulumi.yaml missing 'name' key" >&2
  exit 1
fi

if ! grep -q "^runtime:" infra/pulumi-bootstrap/Pulumi.yaml; then
  echo "FAIL: Pulumi.yaml missing 'runtime' key" >&2
  exit 1
fi

echo "Test: package.json is valid JSON"
if ! jq empty infra/pulumi-bootstrap/package.json >/dev/null 2>&1; then
  echo "FAIL: package.json is not valid JSON" >&2
  exit 1
fi

echo "Test: tsconfig.json enables strict mode"
if ! grep -q '"strict": true' infra/pulumi-bootstrap/tsconfig.json; then
  echo "FAIL: tsconfig.json must enable strict mode" >&2
  exit 1
fi

echo "Test: index.ts contains HOMELAB guard"
if ! grep -q "HOMELAB" infra/pulumi-bootstrap/index.ts; then
  echo "FAIL: index.ts missing HOMELAB guard" >&2
  exit 1
fi

if ! grep -q "validateHomelabAccess" infra/pulumi-bootstrap/index.ts; then
  echo "FAIL: index.ts missing validateHomelabAccess function" >&2
  exit 1
fi

echo "Test: index.ts uses branded types"
if ! grep -q "readonly __brand" infra/pulumi-bootstrap/index.ts; then
  echo "FAIL: index.ts missing branded types" >&2
  exit 1
fi

echo "Pulumi project validation tests passed"
exit 0
