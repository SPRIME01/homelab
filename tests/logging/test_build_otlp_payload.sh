#!/usr/bin/env bash
set -euo pipefail

# Simple test for lib/logging.sh OTLP payload builder
ROOT_DIR=$(cd "$(dirname "$0")/../../" && pwd)
source "$ROOT_DIR/lib/logging.sh"

# Create a sample message
HOMELAB_SERVICE="test-service"
HOMELAB_ENVIRONMENT="test"
HOMELAB_VERSION="0.0.1"

# Build a JSON log entry
json_entry="$(__log_build_json "info" "unit test" "evt_test_1" "key1=value1")"

# Escape then build OTLP payload using helper
escaped_payload="$(__log_json_escape "$json_entry")"
now_ns="$(date +%s%N 2>/dev/null || echo $(( $(date +%s) * 1000000000 )))"
otlp_payload="$(__log_build_otlp_payload "$now_ns" "9" "info" "$escaped_payload")"

# Basic assertions
if ! printf '%s' "$otlp_payload" | grep -q 'resourceLogs'; then
  echo "FAIL: payload missing resourceLogs"
  exit 2
fi

if ! printf '%s' "$otlp_payload" | grep -q 'logRecords'; then
  echo "FAIL: payload missing logRecords"
  exit 2
fi

if ! printf '%s' "$otlp_payload" | grep -q 'stringValue'; then
  echo "FAIL: payload missing body.stringValue"
  exit 2
fi

# Validate that the escaped JSON is present (a heuristic: check for the event_id key inside the stringValue)
if ! printf '%s' "$otlp_payload" | grep -q 'event_id'; then
  echo "FAIL: payload does not include event_id in body"
  exit 2
fi

printf 'PASS: OTLP payload looks valid\n'
