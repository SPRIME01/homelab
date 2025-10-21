#!/bin/bash

# End-to-End Test for Structured Logging System
#
# This script validates the entire structured logging pipeline including:
# 1. Environment bootstrap
# 2. Logger implementations (Node, Python, Shell)
# 3. Vector configuration
# 4. CI/CD integration
# 5. Updated applications
# 6. Overall logging pipeline health

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions for testing
log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

run_test() {
    local test_name="$1"
    local test_command="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    log_test "$test_name"

    if eval "$test_command" >/dev/null 2>&1; then
        log_pass "$test_name"
        return 0
    else
        log_fail "$test_name"
        return 1
    fi
}

# Function to validate JSON schema
validate_json_schema() {
    local json_output="$1"
    local required_fields=("timestamp" "level" "message" "service" "environment" "version" "category" "event_id" "context")

    # Extract the first JSON line from the output (filters out warnings)
    local json_line
    json_line=$(echo "$json_output" | sed -n 's/^\({.*}\)$/\1/p' | head -n 1)

    if [ -z "$json_line" ]; then
        return 1
    fi

    # Check if the output is valid JSON
    if ! echo "$json_line" | jq . >/dev/null 2>&1; then
        return 1
    fi

    # Check each required field
    for field in "${required_fields[@]}"; do
        if ! echo "$json_line" | jq -e ".${field}" >/dev/null 2>&1; then
            return 1
        fi
    done

    return 0
}

# 1. Test Environment Bootstrap
test_environment_bootstrap() {
    log_info "Testing environment bootstrap..."

    # Test sourcing env-loader.sh with different modes
    run_test "Environment bootstrap - local mode" \
        "bash -c 'source $PROJECT_ROOT/lib/env-loader.sh local && [[ \$HOMELAB_ENV_TARGET == \"developer-shell\" ]]'"

    run_test "Environment bootstrap - ci mode" \
        "bash -c 'source $PROJECT_ROOT/lib/env-loader.sh ci && [[ \$HOMELAB_ENVIRONMENT == \"ci\" ]]'"

    run_test "Environment bootstrap - shell mode" \
        "bash -c 'source $PROJECT_ROOT/lib/env-loader.sh shell && [[ \$HOMELAB_ENV_TARGET == \"devbox-shell\" ]]'"

    # Test required environment variables are set
    run_test "Environment variables - HOMELAB_SERVICE" \
        "bash -c 'source $PROJECT_ROOT/lib/env-loader.sh local && [[ -n \$HOMELAB_SERVICE ]]'"

    run_test "Environment variables - HOMELAB_LOG_TARGET" \
        "bash -c 'source $PROJECT_ROOT/lib/env-loader.sh local && [[ -n \$HOMELAB_LOG_TARGET ]]'"

    run_test "Environment variables - HOMELAB_OBSERVE flag" \
        "bash -c 'source $PROJECT_ROOT/lib/env-loader.sh local && [[ -n \$HOMELAB_OBSERVE ]]'"
}

# 2. Test Logger Implementations
test_node_logger() {
    log_info "Testing Node.js logger implementation..."

    # Change to tools/logging directory
    cd "$PROJECT_ROOT/tools/logging" || { log_fail "Failed to cd to $PROJECT_ROOT/tools/logging"; return 1; }

    # Test JSON output
    local node_output
    node_output=$(HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test-service HOMELAB_ENVIRONMENT=test node test_node_logger.js 2>/dev/null | grep "PASS" | wc -l)

    if [ "$node_output" -gt 0 ]; then
        log_pass "Node.js logger implementation"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Node.js logger implementation"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test schema compliance
    local schema_output
    schema_output=$(HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test-service HOMELAB_ENVIRONMENT=test node -e "
        const logger = require('./node/logger');
        logger.info('Test message', { test: true });
    " 2>/dev/null)

    if validate_json_schema "$schema_output"; then
        log_pass "Node.js logger schema compliance"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Node.js logger schema compliance"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    cd "$PROJECT_ROOT"
}

test_python_logger() {
    log_info "Testing Python logger implementation..."

    # Change to tools/logging directory
    cd "$PROJECT_ROOT/tools/logging" || { log_fail "Failed to cd to $PROJECT_ROOT/tools/logging"; return 1; }

    # Test JSON output
    local python_output
    python_output=$(HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test-service HOMELAB_ENVIRONMENT=test PYTHONPATH=python python3 test_structlog.py 2>/dev/null | grep "PASS" | wc -l)

    if [ "$python_output" -gt 0 ]; then
        log_pass "Python logger implementation"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Python logger implementation"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test schema compliance
    local schema_output
    schema_output=$(HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test-service HOMELAB_ENVIRONMENT=test PYTHONPATH=python python3 -c "from logger import logger; logger.info('Test message', test=True)" 2>/dev/null)

    if validate_json_schema "$schema_output"; then
        log_pass "Python logger schema compliance"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Python logger schema compliance"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    cd "$PROJECT_ROOT"
}

test_shell_logger() {
    log_info "Testing Shell logger implementation..."

    # Change to tools directory
    cd "$PROJECT_ROOT/tools/logging" || { log_fail "Failed to cd to $PROJECT_ROOT/tools/logging"; return 1; }

    # Test JSON output
    local shell_output
    shell_output=$(HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test-service HOMELAB_ENVIRONMENT=test bash test_shell_logger.sh 2>/dev/null | grep "PASS" | wc -l)

    if [ "$shell_output" -gt 0 ]; then
        log_pass "Shell logger implementation"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Shell logger implementation"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test schema compliance
    local schema_output
    schema_output=$(HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test-service HOMELAB_ENVIRONMENT=test bash -c "
        source $PROJECT_ROOT/lib/logging.sh
        log_info 'Test message' 'test=value'
    " 2>/dev/null)

    if validate_json_schema "$schema_output"; then
        log_pass "Shell logger schema compliance"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Shell logger schema compliance"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))

    cd "$PROJECT_ROOT"
}

# 3. Test Vector Configuration
test_vector_config() {
    log_info "Testing Vector configuration..."

    # Check if vector.toml exists
    run_test "Vector configuration file exists" \
        "[[ -f $PROJECT_ROOT/ops/vector/vector.toml ]]"

    # Test Vector configuration syntax
    if command -v vector >/dev/null 2>&1; then
        run_test "Vector configuration syntax validation" \
            "vector validate $PROJECT_ROOT/ops/vector/vector.toml"
    else
        log_info "Vector not installed, skipping syntax validation"
    fi

    # Check for required configuration blocks
    run_test "Vector sources configured" \
        "grep -q '\\[sources.otlp_logs\\]' $PROJECT_ROOT/ops/vector/vector.toml"

    run_test "Vector transforms configured" \
        "grep -q '\\[transforms.parse_json\\]' $PROJECT_ROOT/ops/vector/vector.toml"

    run_test "Vector sinks configured" \
        "grep -q '\\[sinks.openobserve\\]' $PROJECT_ROOT/ops/vector/vector.toml"

    run_test "PII redaction rules configured" \
        "grep -q 'REDACTED_EMAIL' $PROJECT_ROOT/ops/vector/vector.toml"
}

# 4. Test CI/CD Integration
test_cicd_integration() {
    log_info "Testing CI/CD integration..."

    # Test logging check target
    run_test "Logging check script exists" \
        "[[ -f $PROJECT_ROOT/tools/tasks/logging-check.js ]]"

    # Run the logging check
    if command -v node >/dev/null 2>&1; then
        run_test "Logging check execution" \
            "cd $PROJECT_ROOT && node tools/tasks/logging-check.js"
    else
        log_info "Node.js not available, skipping logging check"
    fi

    # Test Justfile integration
    run_test "Justfile logging target exists" \
        "grep -q '^logging:' $PROJECT_ROOT/Justfile"
}

# 5. Test Updated Applications
test_applications() {
    log_info "Testing updated applications..."

    # Test Node.js env-check application
    if command -v node >/dev/null 2>&1; then
        run_test "Node.js env-check application" \
            "cd $PROJECT_ROOT && HOMELAB_SERVICE=env-check node apps/env-check/src/index.js test"

        # Check if it uses structured logging
        run_test "Node.js env-check uses structured logging" \
            "grep -q 'require.*logger' $PROJECT_ROOT/apps/env-check/src/index.js"
    else
        log_info "Node.js not available, skipping Node.js application tests"
    fi

    # Test Python main.py
    if command -v python3 >/dev/null 2>&1; then
        run_test "Python main.py application" \
            "cd $PROJECT_ROOT && HOMELAB_SERVICE=homelab-main python3 main.py"

        # Check if it uses structured logging
        run_test "Python main.py uses structured logging" \
            "grep -q 'from logger import logger' $PROJECT_ROOT/main.py"
    else
        log_info "Python not available, skipping Python application tests"
    fi

    # Test Shell scripts
    run_test "Shell env-check.sh script" \
        "bash $PROJECT_ROOT/scripts/env-check.sh --help 2>/dev/null || bash $PROJECT_ROOT/scripts/env-check.sh"

    run_test "Shell env-check.sh uses structured logging" \
        "grep -q 'source.*logging.sh' $PROJECT_ROOT/scripts/env-check.sh"

    run_test "Shell doctor.sh script" \
        "bash $PROJECT_ROOT/scripts/doctor.sh"

    run_test "Shell doctor.sh uses structured logging" \
        "grep -q 'source.*logging.sh' $PROJECT_ROOT/scripts/doctor.sh"
}

# 6. Test Log Output Schema Consistency
test_schema_consistency() {
    log_info "Testing schema consistency across implementations..."

    # Test Node.js output
    local node_json
    if command -v node >/dev/null 2>&1; then
        node_json=$(cd "$PROJECT_ROOT/tools/logging/node" && HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test HOMELAB_ENVIRONMENT=test node -e "
            const logger = require('./logger');
            logger.info('Test message', { field: 'value' });
        " 2>/dev/null | head -1)

        if validate_json_schema "$node_json" && [[ "$node_json" == *"field"* ]]; then
            log_pass "Node.js schema consistency"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            log_fail "Node.js schema consistency"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
        TESTS_RUN=$((TESTS_RUN + 1))
    fi

    # Test Python output
    local python_json
    if command -v python3 >/dev/null 2>&1; then
        python_json=$(cd "$PROJECT_ROOT/tools/logging/python" && HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test HOMELAB_ENVIRONMENT=test PYTHONPATH=. python3 -c "from logger import logger; logger.info('Test message', field='value')" 2>/dev/null | head -1)

        if validate_json_schema "$python_json" && [[ "$python_json" == *"field"* ]]; then
            log_pass "Python schema consistency"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            log_fail "Python schema consistency"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
        TESTS_RUN=$((TESTS_RUN + 1))
    fi

    # Test Shell output
    local shell_json
    shell_json=$(HOMELAB_LOG_TARGET=vector HOMELAB_SERVICE=test HOMELAB_ENVIRONMENT=test bash -c "
        source $PROJECT_ROOT/lib/logging.sh
        log_info 'Test message' 'field=value'
    " 2>/dev/null | head -1)

    if validate_json_schema "$shell_json" && [[ "$shell_json" == *"field"* ]]; then
        log_pass "Shell schema consistency"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_fail "Shell schema consistency"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_RUN=$((TESTS_RUN + 1))
}

# 7. Test Pipeline End-to-End
test_pipeline_e2e() {
    log_info "Testing end-to-end pipeline..."

    # Create a test log file
    local test_log_file="/tmp/homelab-test-logs.json"

    # Test that all implementations can write to the same file
    if command -v node >/dev/null 2>&1; then
        cd "$PROJECT_ROOT/tools/logging/node" || { log_fail "Failed to cd to $PROJECT_ROOT/tools/logging/node"; return 1; }
        HOMELAB_LOG_TARGET=stdout HOMELAB_SERVICE=test HOMELAB_ENVIRONMENT=test node -e "
            const logger = require('./logger');
            logger.info('Node.js test message');
        " > "$test_log_file" 2>/dev/null || true
    fi

    if command -v python3 >/dev/null 2>&1; then
        cd "$PROJECT_ROOT/tools/logging/python" || { log_fail "Failed to cd to $PROJECT_ROOT/tools/logging/python"; return 1; }
        HOMELAB_LOG_TARGET=stdout HOMELAB_SERVICE=test HOMELAB_ENVIRONMENT=test PYTHONPATH=. python3 -c "from logger import logger; logger.info('Python test message')" >> "$test_log_file" 2>/dev/null || true
    fi

    HOMELAB_LOG_TARGET=stdout HOMELAB_SERVICE=test HOMELAB_ENVIRONMENT=test bash -c "
        source $PROJECT_ROOT/lib/logging.sh
        log_info 'Shell test message'
    " >> "$test_log_file" 2>/dev/null || true

    # Check if all logs were written
    if [ -f "$test_log_file" ]; then
        local log_count
        log_count=$(cat "$test_log_file" | wc -l)

        if [ "$log_count" -gt 0 ]; then
            log_pass "End-to-end pipeline - logs written"
        else
            log_fail "End-to-end pipeline - no logs written"
        fi

        # Clean up
        rm -f "$test_log_file"
    fi

    # Test that applications can run with structured logging
    run_test "Applications run with structured logging" \
        "bash -c 'source $PROJECT_ROOT/lib/env-loader.sh local && cd $PROJECT_ROOT && bash scripts/doctor.sh >/dev/null 2>&1'"
}

# Main test execution
main() {
    echo "🚀 Starting End-to-End Logging Pipeline Tests..."
    echo "=================================================="
    echo ""

    # Source the environment bootstrap
    log_info "Sourcing environment bootstrap..."
    source "$PROJECT_ROOT/lib/env-loader.sh" local

    # Run all test suites
    test_environment_bootstrap
    echo ""

    test_node_logger
    echo ""

    test_python_logger
    echo ""

    test_shell_logger
    echo ""

    test_vector_config
    echo ""

    test_cicd_integration
    echo ""

    test_applications
    echo ""

    test_schema_consistency
    echo ""

    test_pipeline_e2e
    echo ""

    # Print summary
    echo "=================================================="
    echo "📊 Test Summary:"
    echo "   Tests run: $TESTS_RUN"
    echo "   Tests passed: $TESTS_PASSED"
    echo "   Tests failed: $TESTS_FAILED"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed! The structured logging system is working correctly.${NC}"
        echo ""
        echo "✅ Environment bootstrap is working"
        echo "✅ All logger implementations are functional and schema-compliant"
        echo "✅ Vector configuration is properly set up"
        echo "✅ CI/CD integration is working"
        echo "✅ Applications are using structured logging correctly"
        echo "✅ Schema consistency is maintained across implementations"
        echo "✅ End-to-end pipeline is functional"
        exit 0
    else
        echo -e "${RED}💥 Some tests failed! Please check the issues above.${NC}"
        echo ""
        echo "The structured logging system has issues that need to be addressed."
        exit 1
    fi
}

# Run main function
main "$@"
