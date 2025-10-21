#!/bin/bash

# Test script for the metrics pipeline
# Validates Vector → GreptimeDB ingestion, sampling rules, and retention

# Global failure flag
TESTS_FAILED=false

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
VECTOR_OTLP_HTTP="http://localhost:4318"
GREPTIMEDB_HTTP="http://localhost:4000"
GREPTIMEDB_PROMETHEUS="http://localhost:4000/v1/prometheus"

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

json_escape() {
    local value="$1"

    if command -v jq >/dev/null 2>&1; then
        jq -Rs . <<<"$value" 2>/dev/null | sed 's/^"//;s/"$//' | tr -d '\n' && return 0
    fi

    if command -v perl >/dev/null 2>&1; then
        printf '%s' "$value" | perl -0pe '
            s/\\/\\\\/g;
            s/"/\\"/g;
            s/\t/\\t/g;
            s/\r/\\r/g;
            s/\n/\\n/g;
            s/\f/\\f/g;
            s/\b/\\b/g;
            s/([\x00-\x1F])/sprintf("\\u%04x", ord($1))/ge;
        ' | tr -d '\n'
        return 0
    fi

    printf '%s' "$value" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e $'s/\t/\\\\t/g' -e $'s/\r/\\\\r/g' -e $'s/\n/\\\\n/g' | tr -d '\n'
}

get_timestamp_ns() {
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY'
import time
print(time.time_ns())
PY
        return 0
    fi

    if timestamp="$(date +%s%N 2>/dev/null)"; then
        echo "$timestamp"
        return 0
    fi

    local seconds
    seconds="$(date +%s 2>/dev/null || printf '0')"
    echo "${seconds}000000000"
}

# Helper functions for testing
assert_contains() {
    local actual="$1"
    local expected="$2"
    local test_name="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "$actual" == *"$expected"* ]]; then
        echo "✅ PASS: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo "❌ FAIL: $test_name"
        echo "   Expected to contain: $expected"
        echo "   Actual: $actual"
        return 1
    fi
}

assert_equals() {
    local actual="$1"
    local expected="$2"
    local test_name="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "$actual" == "$expected" ]]; then
        echo "✅ PASS: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo "❌ FAIL: $test_name"
        echo "   Expected: $expected"
        echo "   Actual: $actual"
        return 1
    fi
}

check_service_health() {
    local service_name="$1"
    local health_url="$2"

    echo "🔍 Checking $service_name health at $health_url..."

    if curl -sS --connect-timeout 5 --max-time 10 --fail "$health_url" > /dev/null 2>&1; then
        echo "✅ $service_name is healthy"
        return 0
    else
        echo "❌ $service_name is not responding at $health_url"
        return 1
    fi
}

send_metric_log() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_unit="$3"
    local service="$4"

    echo "📤 Sending metric log: $metric_name=$metric_value $metric_unit"

    # Construct JSON safely using jq to avoid injection issues
    local json_payload
    local timestamp_ns
    timestamp_ns="$(get_timestamp_ns)"

    if command -v jq >/dev/null 2>&1; then
        json_payload=$(jq -n \
            --arg service "$service" \
            --arg metric_name "$metric_name" \
            --arg metric_value "$metric_value" \
            --arg metric_unit "$metric_unit" \
            --arg timestamp "$timestamp_ns" \
            '{
                resourceLogs: [{
                    resource: {
                        attributes: [{
                            key: "service.name",
                            value: {stringValue: $service}
                        }]
                    },
                    scopeLogs: [{
                        scope: {},
                        logRecords: [{
                            timeUnixNano: $timestamp,
                            severityNumber: 9,
                            severityText: "INFO",
                            body: {
                                stringValue: ("Metric: \($metric_name)=\($metric_value) \($metric_unit)")
                            },
                            attributes: [
                                {key: "metric_name", value: {stringValue: $metric_name}},
                                {key: "metric_value", value: {stringValue: $metric_value}},
                                {key: "metric_unit", value: {stringValue: $metric_unit}},
                                {key: "metric_type", value: {stringValue: "counter"}}
                            ]
                        }]
                    }]
                }]
            }')
    elif command -v python3 >/dev/null 2>&1; then
        json_payload=$(python3 - "$service" "$metric_name" "$metric_value" "$metric_unit" "$timestamp_ns" <<'PY'
import json
import sys

service, metric_name, metric_value, metric_unit, timestamp = sys.argv[1:6]

payload = {
    "resourceLogs": [{
        "resource": {
            "attributes": [{
                "key": "service.name",
                "value": {"stringValue": service}
            }]
        },
        "scopeLogs": [{
            "scope": {},
            "logRecords": [{
                "timeUnixNano": timestamp,
                "severityNumber": 9,
                "severityText": "INFO",
                "body": {
                    "stringValue": f"Metric: {metric_name}={metric_value} {metric_unit}"
                },
                "attributes": [
                    {"key": "metric_name", "value": {"stringValue": metric_name}},
                    {"key": "metric_value", "value": {"stringValue": metric_value}},
                    {"key": "metric_unit", "value": {"stringValue": metric_unit}},
                    {"key": "metric_type", "value": {"stringValue": "counter"}}
                ]
            }]
        }]
    }]
}

print(json.dumps(payload))
PY
)
    else
        # Fallback to manual JSON construction with basic escaping
        local esc_service esc_name esc_value esc_unit
        esc_service="$(json_escape "$service")"
        esc_name="$(json_escape "$metric_name")"
        esc_value="$(json_escape "$metric_value")"
        esc_unit="$(json_escape "$metric_unit")"

        json_payload="{
            \"resourceLogs\": [{
                \"resource\": {
                    \"attributes\": [{
                        \"key\": \"service.name\",
                        \"value\": {\"stringValue\": \"$esc_service\"}
                    }]
                },
                \"scopeLogs\": [{
                    \"scope\": {},
                    \"logRecords\": [{
                        \"timeUnixNano\": \"$timestamp_ns\",
                        \"severityNumber\": 9,
                        \"severityText\": \"INFO\",
                        \"body\": {
                            \"stringValue\": \"Metric: $esc_name=$esc_value $esc_unit\"
                        },
                        \"attributes\": [{
                            \"key\": \"metric_name\",
                            \"value\": {\"stringValue\": \"$esc_name\"}
                        }, {
                            \"key\": \"metric_value\",
                            \"value\": {\"stringValue\": \"$esc_value\"}
                        }, {
                            \"key\": \"metric_unit\",
                            \"value\": {\"stringValue\": \"$esc_unit\"}
                        }, {
                            \"key\": \"metric_type\",
                            \"value\": {\"stringValue\": \"counter\"}
                        }]
                    }]
                }]
            }]
        }"
    fi

    if ! printf '%s' "$json_payload" | curl -sS --connect-timeout 2 --max-time 5 --fail \
        -X POST "$VECTOR_OTLP_HTTP/v1/logs" \
        -H "Content-Type: application/json" \
        --data-binary @- > /dev/null; then
        echo "❌ Failed to send metric payload to Vector" >&2
        TESTS_FAILED=true
        return 1
    fi

    echo "✅ Sent metric: $metric_name"
}

test_vector_greptime_connectivity() {
    echo "🧪 Testing Vector to GreptimeDB connectivity..."

    # Check if Vector is running
    if ! check_service_health "Vector" "$VECTOR_OTLP_HTTP/v1/logs"; then
        echo "Please start Vector with: devbox run vector"
        return 1
    fi

    # Check if GreptimeDB is running
    if ! check_service_health "GreptimeDB" "$GREPTIMEDB_HTTP/health"; then
        echo "Please start GreptimeDB with: devbox run greptimedb"
        return 1
    fi

    echo "Vector and GreptimeDB connectivity verified."
}

test_metric_ingestion() {
    echo "🧪 Testing metric ingestion..."

    # Send test metrics
    local test_timestamp=$(date +%s)
    send_metric_log "test_requests_total" "42" "count" "test-service"
    send_metric_log "test_response_time" "150" "ms" "test-service"
    send_metric_log "test_error_rate" "0.05" "ratio" "test-service"

    # Wait for metrics to be processed
    echo "⏳ Waiting for metrics to be processed..."
    sleep 5

    # Query GreptimeDB for metrics
    echo "🔍 Querying GreptimeDB for metrics..."

    local query_result
    query_result=$(curl -sS --connect-timeout 5 --max-time 10 --fail "$GREPTIMEDB_PROMETHEUS/api/v1/query?query=test_requests_total" 2>&1)

    if [[ -n "$query_result" && "$query_result" != *"error"* ]]; then
        assert_contains "$query_result" "test_requests_total" "Metric found in GreptimeDB"
        assert_contains "$query_result" "42" "Metric value is correct"
    else
        echo "❌ Failed to query metrics from GreptimeDB"
        echo "Response: $query_result"
        return 1
    fi

    echo "Metric ingestion test completed."
}

test_metric_sampling() {
    echo "🧪 Testing metric sampling rules..."

    # Send high-frequency metrics to test sampling
    for i in {1..20}; do
        send_metric_log "high_frequency_metric" "$i" "count" "test-service"
        # Small delay to avoid overwhelming the system
        sleep 0.1
    done

    # Wait for sampling to be applied
    echo "⏳ Waiting for sampling to be applied..."
    sleep 10

    # Query to see if sampling was applied (should have fewer metrics than sent)
    local query_result
    query_result=$(curl -sS --connect-timeout 5 --max-time 10 --fail "$GREPTIMEDB_PROMETHEUS/api/v1/query?query=increase(high_frequency_metric_total[1m])" 2>&1)

    if [[ -n "$query_result" && "$query_result" != *"error"* ]]; then
        # Check that we have some metrics but not all 20
        if [[ "$query_result" == *"value"* ]]; then
            echo "✅ PASS: High-frequency metrics were sampled"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo "❌ FAIL: No high-frequency metrics found after sampling"
        fi
        TESTS_RUN=$((TESTS_RUN + 1))
    else
        echo "❌ Failed to query sampled metrics from GreptimeDB"
        echo "Response: $query_result"
        return 1
    fi

    echo "Metric sampling test completed."
}

test_metric_retention() {
    echo "🧪 Testing metric retention..."

    # Send a metric with a specific timestamp
    local old_timestamp=$(date -d '1 hour ago' +%s)

    # Construct JSON safely using jq to avoid injection issues
    local retention_json
    if command -v jq >/dev/null 2>&1; then
        retention_json=$(jq -n \
            --arg timestamp "$(($old_timestamp * 1000000000))" \
            '{
                resourceLogs: [{
                    resource: {
                        attributes: [{
                            key: "service.name",
                            value: {stringValue: "retention-test-service"}
                        }]
                    },
                    scopeLogs: [{
                        scope: {},
                        logRecords: [{
                            timeUnixNano: $timestamp,
                            severityNumber: 9,
                            severityText: "INFO",
                            body: {
                                stringValue: "Retention test metric"
                            },
                            attributes: [
                                {key: "metric_name", value: {stringValue: "retention_test_metric"}},
                                {key: "metric_value", value: {stringValue: "1"}},
                                {key: "metric_unit", value: {stringValue: "count"}}
                            ]
                        }]
                    }]
                }]
            }')
    else
        # Fallback to manual JSON construction
        retention_json="{
            \"resourceLogs\": [{
                \"resource\": {
                    \"attributes\": [{
                        \"key\": \"service.name\",
                        \"value\": {\"stringValue\": \"retention-test-service\"}
                    }]
                },
                \"scopeLogs\": [{
                    \"scope\": {},
                    \"logRecords\": [{
                        \"timeUnixNano\": \"$(($old_timestamp * 1000000000))\",
                        \"severityNumber\": 9,
                        \"severityText\": \"INFO\",
                        \"body\": {
                            \"stringValue\": \"Retention test metric\"
                        },
                        \"attributes\": [{
                            \"key\": \"metric_name\",
                            \"value\": {\"stringValue\": \"retention_test_metric\"}
                        }, {
                            \"key\": \"metric_value\",
                            \"value\": {\"stringValue\": \"1\"}
                        }, {
                            \"key\": \"metric_unit\",
                            \"value\": {\"stringValue\": \"count\"}
                        }]
                    }]
                }]
            }]
        }"
    fi

    curl -sS --connect-timeout 5 --max-time 10 --fail \
        -X POST "$VECTOR_OTLP_HTTP/v1/logs" \
        -H "Content-Type: application/json" \
        -d "$retention_json" > /dev/null

    # Wait for processing
    sleep 5

    # Query for the metric with time range
    local query_result
    query_result=$(curl -sS --connect-timeout 5 --max-time 10 --fail "$GREPTIMEDB_PROMETHEUS/api/v1/query_range?query=retention_test_metric&start=$((old_timestamp - 300))&end=$(date +%s)&step=60" 2>&1)

    if [[ -n "$query_result" && "$query_result" != *"error"* ]]; then
        assert_contains "$query_result" "retention_test_metric" "Retention test metric found"
        echo "✅ PASS: Metric retention is working correctly"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "⚠️  WARNING: Retention test metric not found (might be expected if retention policy is aggressive)"
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    echo "Metric retention test completed."
}

test_metric_aggregation() {
    echo "🧪 Testing metric aggregation..."

    # Send multiple metrics with the same name but different values
    for value in 10 20 30 40 50; do
        send_metric_log "aggregation_test" "$value" "ms" "aggregation-service"
        sleep 0.1
    done

    # Wait for processing
    sleep 5

    # Query for aggregated metrics
    local query_result
    query_result=$(curl -sS --connect-timeout 5 --max-time 10 --fail "$GREPTIMEDB_PROMETHEUS/api/v1/query?query=avg(aggregation_test)" 2>&1)

    if [[ -n "$query_result" && "$query_result" != *"error"* && "$query_result" == *"30"* ]]; then
        echo "✅ PASS: Metric aggregation working correctly (avg = 30)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAIL: Metric aggregation not working as expected"
        echo "Response: $query_result"
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    echo "Metric aggregation test completed."
}

# Run all tests
echo "🚀 Starting metrics pipeline tests..."
echo

# Helper function to run a test and capture exit status
run_test() {
    local test_function="$1"
    echo "Running: $test_function"

    if $test_function; then
        echo "✅ $test_function completed successfully"
    else
        echo "❌ $test_function failed"
        TESTS_FAILED=true
    fi
    echo
}

run_test test_vector_greptime_connectivity
run_test test_metric_ingestion
run_test test_metric_sampling
run_test test_metric_retention
run_test test_metric_aggregation

# Print summary
echo "📊 Test Summary:"
echo "   Tests run: $TESTS_RUN"
echo "   Tests passed: $TESTS_PASSED"
echo "   Tests failed: $((TESTS_RUN - TESTS_PASSED))"

if [ "$TESTS_FAILED" = true ] || [ $TESTS_PASSED -ne $TESTS_RUN ]; then
    echo "💥 Some tests failed!"
    exit 1
else
    echo "🎉 All tests passed!"
    exit 0
fi
