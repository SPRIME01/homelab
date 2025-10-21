#!/bin/bash

# Test script for the shell logging helper
# Verifies JSON output, pretty printing, and schema compliance

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source the logging helper
source "$PROJECT_ROOT/lib/logging.sh"

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

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

# Test functions
test_json_output() {
    echo "🧪 Testing JSON output..."

    # Set environment to force JSON output
    export HOMELAB_LOG_TARGET=vector
    export HOMELAB_SERVICE=test-service
    export HOMELAB_ENVIRONMENT=test
    export HOMELAB_LOG_LEVEL=debug

    # Reset the logging config to pick up new values
    HOMELAB_LOG_CONFIG_LOADED=false

    # Capture log output
    local output
    output=$(log_info "Test message" "key=value" 2>&1)

    # Verify JSON structure
    assert_contains "$output" '"timestamp"' "JSON contains timestamp"
    assert_contains "$output" '"level":"info"' "JSON contains correct level"
    assert_contains "$output" '"message":"Test message"' "JSON contains message"
    assert_contains "$output" '"service":"test-service"' "JSON contains service"
    assert_contains "$output" '"environment":"test"' "JSON contains environment"
    assert_contains "$output" '"version":"' "JSON contains version"
    assert_contains "$output" '"category":"application"' "JSON contains category"
    assert_contains "$output" '"event_id":"evt_' "JSON contains event_id"
    assert_contains "$output" '"context":' "JSON contains context"
    assert_contains "$output" '"key":"value"' "JSON contains custom field in context"

    # Test with optional root-level fields
    output=$(log_info "Test with request" "request_id=req-123" "trace_id=trace-456" "duration_ms=100" 2>&1)
    assert_contains "$output" '"request_id":"req-123"' "JSON contains request_id at root"
    assert_contains "$output" '"trace_id":"trace-456"' "JSON contains trace_id at root"
    assert_contains "$output" '"duration_ms":"100"' "JSON contains duration_ms at root"

    echo "JSON output tests completed."
}

test_pretty_output() {
    echo "🧪 Testing pretty output..."

    # Set environment to force pretty output
    export HOMELAB_LOG_TARGET=stdout
    export HOMELAB_FORCE_PRETTY=true

    # Reset the logging config to pick up new values
    HOMELAB_LOG_CONFIG_LOADED=false

    # Test info level
    local output
    output=$(log_info "Test message" 2>&1)
    assert_contains "$output" "INFO" "Pretty output contains INFO level"
    assert_contains "$output" "ℹ️" "Pretty output contains info emoji"
    assert_contains "$output" "Test message" "Pretty output contains message"

    # Test warn level
    output=$(log_warn "Warning message" 2>&1)
    assert_contains "$output" "WARN" "Pretty output contains WARN level"
    assert_contains "$output" "⚠️" "Pretty output contains warning emoji"

    # Test error level
    output=$(log_error "Error message" 2>&1)
    assert_contains "$output" "ERROR" "Pretty output contains ERROR level"
    assert_contains "$output" "❌" "Pretty output contains error emoji"

    # Test debug level
    output=$(log_debug "Debug message" 2>&1)
    assert_contains "$output" "DEBUG" "Pretty output contains DEBUG level"
    assert_contains "$output" "🔍" "Pretty output contains debug emoji"

    # Test with trace and duration
    output=$(log_info "Test with trace" "trace_id=trace-12345678" "duration_ms=250" 2>&1)
    assert_contains "$output" "[trace-12...]" "Pretty output contains truncated trace ID"
    assert_contains "$output" "(250ms)" "Pretty output contains duration"

    echo "Pretty output tests completed."
}

test_log_levels() {
    echo "🧪 Testing log levels..."

    # Test error level - should show all levels
    export HOMELAB_LOG_LEVEL=error
    HOMELAB_LOG_CONFIG_LOADED=false

    local output
    output=$(log_error "Error message" 2>&1)
    assert_contains "$output" "Error message" "Error level shows error messages"

    output=$(log_warn "Warning message" 2>&1 || true)
    if [[ -n "$output" ]]; then
        echo "❌ FAIL: Error level should not show warning messages"
        return 1
    else
        echo "✅ PASS: Error level does not show warning messages"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test warn level - should show warn and error
    export HOMELAB_LOG_LEVEL=warn
    HOMELAB_LOG_CONFIG_LOADED=false

    output=$(log_warn "Warning message" 2>&1)
    assert_contains "$output" "Warning message" "Warn level shows warning messages"

    output=$(log_error "Error message" 2>&1)
    assert_contains "$output" "Error message" "Warn level shows error messages"

    output=$(log_info "Info message" 2>&1 || true)
    if [[ -n "$output" ]]; then
        echo "❌ FAIL: Warn level should not show info messages"
        return 1
    else
        echo "✅ PASS: Warn level does not show info messages"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test info level - should show info, warn, and error
    export HOMELAB_LOG_LEVEL=info
    HOMELAB_LOG_CONFIG_LOADED=false

    output=$(log_info "Info message" 2>&1)
    assert_contains "$output" "Info message" "Info level shows info messages"

    output=$(log_warn "Warning message" 2>&1)
    assert_contains "$output" "Warning message" "Info level shows warning messages"

    output=$(log_error "Error message" 2>&1)
    assert_contains "$output" "Error message" "Info level shows error messages"

    # Test debug level - should show all levels
    export HOMELAB_LOG_LEVEL=debug
    HOMELAB_LOG_CONFIG_LOADED=false

    output=$(log_debug "Debug message" 2>&1)
    assert_contains "$output" "Debug message" "Debug level shows debug messages"

    echo "Log level tests completed."
}

test_helper_functions() {
    echo "🧪 Testing helper functions..."

    # Set to JSON output for easier verification
    export HOMELAB_LOG_TARGET=vector
    HOMELAB_LOG_CONFIG_LOADED=false

    # Test log_metric
    local output
    output=$(log_metric "test_counter" "42" "count" "service=api" 2>&1)
    assert_contains "$output" '"metric_name":"test_counter"' "log_metric includes metric_name"
    assert_contains "$output" '"metric_value":"42"' "log_metric includes metric_value"
    assert_contains "$output" '"metric_unit":"count"' "log_metric includes metric_unit"
    assert_contains "$output" '"service":"api"' "log_metric includes custom fields"

    # Test log_span
    output=$(log_span "database_query" "trace-123" "span-456" "query=SELECT" 2>&1)
    assert_contains "$output" '"trace_id":"trace-123"' "log_span includes trace_id"
    assert_contains "$output" '"span_id":"span-456"' "log_span includes span_id"
    assert_contains "$output" '"operation":"database_query"' "log_span includes operation"
    assert_contains "$output" '"query":"SELECT"' "log_span includes custom fields"

    # Test log_with_category
    output=$(log_with_category "audit" "User login" "user_hash=abc123" 2>&1)
    assert_contains "$output" '"category":"audit"' "log_with_category sets category"
    assert_contains "$output" '"user_hash":"abc123"' "log_with_category includes custom fields"

    # Test log_with_trace
    output=$(log_with_trace "trace-789" "span-012" "Operation in trace" 2>&1)
    assert_contains "$output" '"trace_id":"trace-789"' "log_with_trace includes trace_id"
    assert_contains "$output" '"span_id":"span-012"' "log_with_trace includes span_id"

    # Test log_with_request
    output=$(log_with_request "req-345" "user-def" "Processing request" 2>&1)
    assert_contains "$output" '"request_id":"req-345"' "log_with_request includes request_id"
    assert_contains "$output" '"user_hash":"user-def"' "log_with_request includes user_hash"

    # Test log_request
    output=$(log_request "GET" "/api/users" "user_agent=test" 2>&1)
    assert_contains "$output" '"method":"GET"' "log_request includes method"
    assert_contains "$output" '"url":"/api/users"' "log_request includes url"
    assert_contains "$output" '"user_agent":"test"' "log_request includes custom fields"

    # Test log_response
    output=$(log_response "GET" "/api/users" "200" "150" "bytes=1024" 2>&1)
    assert_contains "$output" '"method":"GET"' "log_response includes method"
    assert_contains "$output" '"url":"/api/users"' "log_response includes url"
    assert_contains "$output" '"status_code":"200"' "log_response includes status_code"
    assert_contains "$output" '"duration_ms":"150"' "log_response includes duration_ms"
    assert_contains "$output" '"bytes":"1024"' "log_response includes custom fields"

    # Test log_error_with_context
    output=$(log_error_with_context "Database connection failed" "ConnectionError" "host=db.example.com" 2>&1)
    assert_contains "$output" '"level":"error"' "log_error_with_context has error level"
    assert_contains "$output" '"error_type":"ConnectionError"' "log_error_with_context includes error_type"
    assert_contains "$output" '"host":"db.example.com"' "log_error_with_context includes custom fields"

    echo "Helper function tests completed."
}

test_version_detection() {
    echo "🧪 Testing version detection..."

    # Test with package.json
    cd "$PROJECT_ROOT"
    export HOMELAB_LOG_TARGET=vector
    HOMELAB_LOG_CONFIG_LOADED=false

    local output
    output=$(log_info "Version test" 2>&1)

    # Get the expected version dynamically from package.json
    local expected_version="0.0.0"
    if [ -f "$PROJECT_ROOT/package.json" ]; then
        if command -v jq >/dev/null 2>&1; then
            expected_version=$(jq -r '.version // "0.0.0"' "$PROJECT_ROOT/package.json" 2>/dev/null)
        else
            # Fallback to grep/sed if jq is not available
            expected_version=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$PROJECT_ROOT/package.json" | sed -E 's/.*"([^"]*)".*/\1/' 2>/dev/null)
            if [ -z "$expected_version" ]; then
                expected_version="0.0.0"
            fi
        fi
    fi

    # Should detect version from package.json
    assert_contains "$output" "\"version\":\"$expected_version\"" "Detects version from package.json"

    echo "Version detection tests completed."
}

test_event_id_generation() {
    echo "🧪 Testing event ID generation..."

    export HOMELAB_LOG_TARGET=vector
    HOMELAB_LOG_CONFIG_LOADED=false

    # Generate two events and verify they have different event IDs
    local output1 output2
    output1=$(log_info "First event" 2>&1)
    output2=$(log_info "Second event" 2>&1)

    # Extract event IDs
    local event_id1 event_id2
    event_id1=$(echo "$output1" | grep -o '"event_id":"evt_[^"]*"' | sed 's/"event_id":"\([^"]*\)"/\1/')
    event_id2=$(echo "$output2" | grep -o '"event_id":"evt_[^"]*"' | sed 's/"event_id":"\([^"]*\)"/\1/')

    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$event_id1" != "$event_id2" ]]; then
        echo "✅ PASS: Event IDs are unique"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAIL: Event IDs should be unique"
        echo "   First: $event_id1"
        echo "   Second: $event_id2"
    fi

    # Verify event ID format
    TESTS_RUN=$((TESTS_RUN + 1))
    if [[ "$event_id1" =~ ^evt_[0-9]+_[0-9]+$ ]]; then
        echo "✅ PASS: Event ID has correct format"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAIL: Event ID has incorrect format: $event_id1"
    fi

    echo "Event ID generation tests completed."
}

# Run all tests
echo "🚀 Starting shell logger tests..."
echo

test_json_output
echo
test_pretty_output
echo
test_log_levels
echo
test_helper_functions
echo
test_version_detection
echo
test_event_id_generation
echo

# Print summary
echo "📊 Test Summary:"
echo "   Tests run: $TESTS_RUN"
echo "   Tests passed: $TESTS_PASSED"
echo "   Tests failed: $((TESTS_RUN - TESTS_PASSED))"

if [ $TESTS_PASSED -eq $TESTS_RUN ]; then
    echo "🎉 All tests passed!"
    exit 0
else
    echo "💥 Some tests failed!"
    exit 1
fi
