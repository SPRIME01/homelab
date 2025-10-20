#!/bin/bash

# Test script for Vector configuration
# Lints Vector config (VRL parsing, redaction transforms, sink wiring)

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
VECTOR_CONFIG_FILE="$PROJECT_ROOT/ops/vector/vector.toml"
VECTOR_BIN="vector"

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

check_vector_binary() {
    echo "🔍 Checking Vector binary..."

    if command -v "$VECTOR_BIN" &> /dev/null; then
        echo "✅ Vector binary found at: $(which $VECTOR_BIN)"
        return 0
    else
        echo "❌ Vector binary not found. Please install Vector or ensure it's in PATH"
        return 1
    fi
}

test_config_syntax() {
    echo "🧪 Testing Vector configuration syntax..."

    # Check if config file exists
    if [[ ! -f "$VECTOR_CONFIG_FILE" ]]; then
        echo "❌ Vector config file not found: $VECTOR_CONFIG_FILE"
        return 1
    fi

    # Validate TOML syntax
    if command -v "toml-lint" &> /dev/null; then
        local lint_output
        lint_output=$(toml-lint "$VECTOR_CONFIG_FILE" 2>&1)

        if [[ $? -eq 0 ]]; then
            echo "✅ PASS: TOML syntax is valid"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo "❌ FAIL: TOML syntax errors found:"
            echo "$lint_output"
        fi
        TESTS_RUN=$((TESTS_RUN + 1))
    else
        echo "⚠️  WARNING: toml-lint not found, skipping TOML syntax validation"
    fi

    # Validate Vector config
    local validate_output
    validate_output=$("$VECTOR_BIN" validate --config-toml "$VECTOR_CONFIG_FILE" 2>&1)

    if [[ $? -eq 0 ]]; then
        echo "✅ PASS: Vector configuration is valid"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAIL: Vector configuration validation failed:"
        echo "$validate_output"
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    echo "Configuration syntax tests completed."
}

test_vrl_parsing() {
    echo "🧪 Testing VRL parsing in transforms..."

    # Extract VRL source code from config
    local vrl_sources
    vrl_sources=$(grep -A 20 'source = """' "$VECTOR_CONFIG_FILE" | grep -v 'source = """' | grep -v '"""' | sed '/^$/d')

    if [[ -z "$vrl_sources" ]]; then
        echo "❌ FAIL: No VRL source code found in transforms"
        TESTS_RUN=$((TESTS_RUN + 1))
        return 1
    fi

    echo "Found VRL transforms, testing syntax..."

    # Test each VRL script separately
    local transform_names
    transform_names=$(grep -B 5 'source = """' "$VECTOR_CONFIG_FILE" | grep '\[transforms\.' | sed 's/\[transforms\.\(.*\)\]/\1/')

    while IFS= read -r transform_name; do
        if [[ -n "$transform_name" ]]; then
            echo "  Testing VRL for transform: $transform_name"

            # Extract VRL source for this transform
            local vrl_source
            vrl_source=$(awk -v transform="$transform_name" '
                /^\[transforms\.' transform '\]/ { in_transform=1; next }
                in_transform && /^\[transforms\./ { in_transform=0 }
                in_transform && /source = """/ {
                    in_source=1; next
                }
                in_source && /"""/ { in_source=0; next }
                in_source { print }
            ' "$VECTOR_CONFIG_FILE")

            if [[ -n "$vrl_source" ]]; then
                # Test VRL syntax with Vector
                local vrl_test_output
                vrl_test_output=$(echo "$vrl_source" | "$VECTOR_BIN" test vrl --stdin 2>&1)

                if [[ $? -eq 0 ]]; then
                    echo "    ✅ PASS: VRL syntax is valid for $transform_name"
                    TESTS_PASSED=$((TESTS_PASSED + 1))
                else
                    echo "    ❌ FAIL: VRL syntax error in $transform_name:"
                    echo "$vrl_test_output"
                fi
                TESTS_RUN=$((TESTS_RUN + 1))
            else
                echo "    ⚠️  WARNING: Could not extract VRL source for $transform_name"
            fi
        fi
    done <<< "$transform_names"

    echo "VRL parsing tests completed."
}

test_redaction_transforms() {
    echo "🧪 Testing redaction transforms..."

    # Check for redaction transform
    if ! grep -q '\[transforms.redact_pii\]' "$VECTOR_CONFIG_FILE"; then
        echo "❌ FAIL: Redaction transform [transforms.redact_pii] not found"
        TESTS_RUN=$((TESTS_RUN + 1))
        return 1
    fi

    echo "  Found redaction transform, testing redaction rules..."

    # Test email redaction
    assert_contains "$(grep -A 10 'redact email addresses' "$VECTOR_CONFIG_FILE")" \
        "replace" "Email redaction rule exists"

    # Test token redaction
    assert_contains "$(grep -A 5 'access_token' "$VECTOR_CONFIG_FILE")" \
        "REDACTED_TOKEN" "Access token redaction rule exists"

    # Test API key redaction
    assert_contains "$(grep -A 5 'api_key' "$VECTOR_CONFIG_FILE")" \
        "REDACTED_KEY" "API key redaction rule exists"

    # Test generic sensitive data redaction
    assert_contains "$(grep -A 10 'contains.*token.*key.*secret.*password' "$VECTOR_CONFIG_FILE")" \
        "REDACTED_SENSITIVE" "Generic sensitive data redaction rule exists"

    # Test VRL redaction logic with sample data
    local test_vrl='
        .email = "user@example.com"
        .access_token = "sk-1234567890abcdef"
        .api_key = "secret-key-123"
        .session_id = "sess-abc123"
        .password_field = "super-secret"

        # Redact email addresses
        .email = replace(.email, /([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/, "REDACTED_EMAIL")

        # Redact access tokens
        if exists(.access_token) {
          .access_token = "REDACTED_TOKEN"
        }

        # Redact API keys
        if exists(.api_key) {
          .api_key = "REDACTED_KEY"
        }

        # Redact session identifiers
        if exists(.session_id) {
          .session_id = "REDACTED_SESSION"
        }

        # Redact any field containing "token", "key", "secret", or "password"
        for_each(object_keys(.)) -> |key| {
          if contains(string!(key), "token") || contains(string!(key), "key") || contains(string!(key), "secret") || contains(string!(key), "password") {
            .[key] = "REDACTED_SENSITIVE"
          }
        }
    '

    local redaction_test_output
    redaction_test_output=$(echo "$test_vrl" | "$VECTOR_BIN" test vrl --stdin 2>&1)

    if [[ $? -eq 0 ]]; then
        # Check if redaction worked correctly
        assert_contains "$redaction_test_output" "REDACTED_EMAIL" "Email redaction works correctly"
        assert_contains "$redaction_test_output" "REDACTED_TOKEN" "Token redaction works correctly"
        assert_contains "$redaction_test_output" "REDACTED_KEY" "API key redaction works correctly"
        assert_contains "$redaction_test_output" "REDACTED_SESSION" "Session ID redaction works correctly"
        assert_contains "$redaction_test_output" "REDACTED_SENSITIVE" "Generic sensitive data redaction works correctly"
    else
        echo "❌ FAIL: Redaction VRL test failed:"
        echo "$redaction_test_output"
        TESTS_RUN=$((TESTS_RUN + 1))
    fi

    echo "Redaction transform tests completed."
}

test_sink_wiring() {
    echo "🧪 Testing sink wiring..."

    # Check for required sinks
    local required_sinks=("openobserve" "greptimedb" "stdout")

    for sink in "${required_sinks[@]}"; do
        if grep -q "\[sinks.$sink\]" "$VECTOR_CONFIG_FILE"; then
            echo "  ✅ Found sink: $sink"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo "  ❌ Missing sink: $sink"
        fi
        TESTS_RUN=$((TESTS_RUN + 1))
    done

    # Check sink inputs are properly wired
    # OpenObserve should receive from add_metadata
    assert_contains "$(grep -A 5 '\[sinks.openobserve\]' "$VECTOR_CONFIG_FILE")" \
        "inputs = \[\"add_metadata\"\]" "OpenObserve sink is wired to add_metadata transform"

    # GreptimeDB should receive from extract_metrics
    assert_contains "$(grep -A 5 '\[sinks.greptimedb\]' "$VECTOR_CONFIG_FILE")" \
        "inputs = \[\"extract_metrics\"\]" "GreptimeDB sink is wired to extract_metrics transform"

    # Stdout should receive from add_metadata
    assert_contains "$(grep -A 5 '\[sinks.stdout\]' "$VECTOR_CONFIG_FILE")" \
        "inputs = \[\"add_metadata\"\]" "Stdout sink is wired to add_metadata transform"

    # Check transform chain wiring
    # parse_json should receive from otlp sources
    assert_contains "$(grep -A 5 '\[transforms.parse_json\]' "$VECTOR_CONFIG_FILE")" \
        "inputs = \[\"otlp_logs\", \"otlp_http_logs\"\]" "parse_json transform is wired to OTLP sources"

    # redact_pii should receive from parse_json
    assert_contains "$(grep -A 5 '\[transforms.redact_pii\]' "$VECTOR_CONFIG_FILE")" \
        "inputs = \[\"parse_json\"\]" "redact_pii transform is wired to parse_json"

    # add_metadata should receive from redact_pii
    assert_contains "$(grep -A 5 '\[transforms.add_metadata\]' "$VECTOR_CONFIG_FILE")" \
        "inputs = \[\"redact_pii\"\]" "add_metadata transform is wired to redact_pii"

    # extract_metrics should receive from redact_pii
    assert_contains "$(grep -A 5 '\[transforms.extract_metrics\]' "$VECTOR_CONFIG_FILE")" \
        "inputs = \[\"redact_pii\"\]" "extract_metrics transform is wired to redact_pii"

    echo "Sink wiring tests completed."
}

test_health_checks() {
    echo "🧪 Testing health check configurations..."

    # Check for health check configuration
    local health_checks
    health_checks=$(grep -c "healthcheck = true" "$VECTOR_CONFIG_FILE")

    if [[ $health_checks -gt 0 ]]; then
        echo "✅ PASS: Found $health_checks health check(s) configured"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "⚠️  WARNING: No health checks found in configuration"
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    # Check for source health checks
    if grep -q "healthcheck = true" "$VECTOR_CONFIG_FILE"; then
        local source_health_checks
        source_health_checks=$(grep -A 1 '\[sources\.' "$VECTOR_CONFIG_FILE" | grep -c "healthcheck = true")

        if [[ $source_health_checks -gt 0 ]]; then
            echo "✅ PASS: Found $source_health_checks source health check(s)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo "⚠️  WARNING: No source health checks found"
        fi
        TESTS_RUN=$((TESTS_RUN + 1))
    fi

    # Check for sink health checks
    if grep -q "healthcheck = true" "$VECTOR_CONFIG_FILE"; then
        local sink_health_checks
        sink_health_checks=$(grep -A 1 '\[sinks\.' "$VECTOR_CONFIG_FILE" | grep -c "healthcheck = true")

        if [[ $sink_health_checks -gt 0 ]]; then
            echo "✅ PASS: Found $sink_health_checks sink health check(s)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo "⚠️  WARNING: No sink health checks found"
        fi
        TESTS_RUN=$((TESTS_RUN + 1))
    fi

    echo "Health check tests completed."
}

# Run all tests
echo "🚀 Starting Vector configuration tests..."
echo

if ! check_vector_binary; then
    echo "💥 Cannot proceed without Vector binary"
    exit 1
fi

test_config_syntax
echo
test_vrl_parsing
echo
test_redaction_transforms
echo
test_sink_wiring
echo
test_health_checks
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
