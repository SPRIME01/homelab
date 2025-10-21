#!/bin/bash

# Shell logging helper for homelab structured logging
# Provides functions: log_info, log_warn, log_error, log_debug
# Emits JSON output with the same schema as Node and Python loggers
# Supports formatted text output with emojis when HOMELAB_LOG_TARGET=stdout and TTY is present

# Global variables for logging configuration
HOMELAB_EVENT_ID_COUNTER=0
HOMELAB_LOG_CONFIG_LOADED=false

# Load configuration and initialize logger
__log_init() {
    if [ "$HOMELAB_LOG_CONFIG_LOADED" = true ]; then
        return 0
    fi

    # Set default values from environment variables
    HOMELAB_SERVICE="${HOMELAB_SERVICE:-unknown-service}"
    HOMELAB_ENVIRONMENT="${HOMELAB_ENVIRONMENT:-development}"
    HOMELAB_LOG_TARGET="${HOMELAB_LOG_TARGET:-vector}"
    HOMELAB_LOG_LEVEL="${HOMELAB_LOG_LEVEL:-info}"

    # Get version from package.json or pyproject.toml
    HOMELAB_VERSION="$(__log_get_version)"

    # Determine if we should use pretty printing
    if [ "$HOMELAB_LOG_TARGET" = "stdout" ]; then
        # Check if stdout is a TTY or if we're forcing pretty output
        if [ -t 1 ] || [ "${HOMELAB_FORCE_PRETTY:-false}" = "true" ]; then
            HOMELAB_USE_PRETTY_PRINT=true
        else
            HOMELAB_USE_PRETTY_PRINT=false
        fi
    else
        HOMELAB_USE_PRETTY_PRINT=false
    fi

    HOMELAB_LOG_CONFIG_LOADED=true
}

# Get version from package.json or pyproject.toml
__log_get_version() {
    # Try package.json first
    if [ -f "package.json" ]; then
        if command -v jq >/dev/null 2>&1; then
            version=$(jq -r '.version // "0.0.0"' package.json 2>/dev/null)
            if [ "$version" != "null" ] && [ -n "$version" ]; then
                echo "$version"
                return 0
            fi
        else
            # Fallback to grep/sed if jq is not available
            version=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' package.json | sed -E 's/.*"([^"]*)".*/\1/' 2>/dev/null)
            if [ -n "$version" ]; then
                echo "$version"
                return 0
            fi
        fi
    fi

    # Try pyproject.toml
    if [ -f "pyproject.toml" ]; then
        version=$(grep -E '^version[[:space:]]*=' pyproject.toml | sed -E 's/.*=[[:space:]]*["\x27]?([^"\x27]+)["\x27]?.*/\1/' 2>/dev/null)
        if [ -n "$version" ]; then
            echo "$version"
            return 0
        fi
    fi

    echo "0.0.0"
}

# Generate a monotonic event ID
__log_generate_event_id() {
    HOMELAB_EVENT_ID_COUNTER=$((HOMELAB_EVENT_ID_COUNTER + 1))
    timestamp_ms=$(date +%s%3N)
    echo "evt_${timestamp_ms}_${HOMELAB_EVENT_ID_COUNTER}"
}

# Get ISO-8601 UTC timestamp
__log_get_timestamp() {
    # Try Python for UTC ISO8601 with milliseconds first
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")' 2>/dev/null && return 0
    fi

    # Fallback to date command
    # Try to use date with GNU format, fallback to BSD format
    if date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null; then
        return 0
    else
        # BSD date format (macOS) - safe ISO8601 without milliseconds
        date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null
    fi
}

# Escape JSON string
__log_json_escape() {
    local str="$1"

    # Try jq first (most reliable)
    if command -v jq >/dev/null 2>&1; then
        echo -n "$str" | jq -Rs . 2>/dev/null | sed 's/^"//;s/"$//' && return 0
    fi

    # Try python3 next
    if command -v python3 >/dev/null 2>&1; then
        echo -n "$str" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()), end="")' 2>/dev/null | sed 's/^"//;s/"$//' && return 0
    fi

    # Fallback to comprehensive sed/perl escape
    # Escape backslashes first, then quotes, then control characters
    echo -n "$str" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed 's/$/\\n/' | tr -d '\r' | sed 's/\\n$//' | \
    sed 's/\t/\\t/g; s/\b/\\b/g; s/\f/\\f/g; s/\r/\\r/g'
}

# Build JSON log entry
__log_build_json() {
    local level="$1"
    local message="$2"
    local event_id="$3"
    shift 3
    local additional_fields=("$@")

    local timestamp="$(__log_get_timestamp)"
    local json_message="$(__log_json_escape "$message")"

    # Start building JSON
    local json="{"
    json+="\"timestamp\":\"$timestamp\","
    json+="\"level\":\"$level\","
    json+="\"message\":\"$json_message\","
    json+="\"service\":\"$HOMELAB_SERVICE\","
    json+="\"environment\":\"$HOMELAB_ENVIRONMENT\","
    json+="\"version\":\"$HOMELAB_VERSION\","
    json+="\"category\":\"application\","
    json+="\"event_id\":\"$event_id\","
    json+="\"context\":{}"

    # Parse additional fields
    local context_started=false
    for field in "${additional_fields[@]}"; do
        if [[ "$field" == *"="* ]]; then
            local key="${field%%=*}"
            local value="${field#*=}"

            # Check if this is a root-level field
            case "$key" in
                request_id|user_hash|source|duration_ms|status_code|tags|trace_id|span_id|category)
                    json+=",\"$key\":\"$(__log_json_escape "$value")\""
                    ;;
                *)
                    # Add to context
                    if [ "$context_started" = false ]; then
                        json+=",\"context\":{"
                        context_started=true
                    else
                        json+=","
                    fi
                    json+="\"$key\":\"$(__log_json_escape "$value")\""
                    ;;
            esac
        fi
    done

    if [ "$context_started" = true ]; then
        json+="}"
    fi

    json+="}"
    echo "$json"
}

# Build pretty text log entry
__log_build_pretty() {
    local level="$1"
    local message="$2"
    local event_id="$3"
    shift 3
    local additional_fields=("$@")

    local timestamp="$(__log_get_timestamp)"
    local formatted_time=$(echo "$timestamp" | sed 's/.*T\([0-9:]*\)\..*/\1/' | sed 's/Z/ UTC/')

    # Level-specific colors and emojis
    case "$level" in
        "debug")
            local color="\033[36m"  # Cyan
            local emoji="🔍"
            ;;
        "info")
            local color="\033[32m"  # Green
            local emoji="ℹ️"
            ;;
        "warn")
            local color="\033[33m"  # Yellow
            local emoji="⚠️"
            ;;
        "error")
            local color="\033[31m"  # Red
            local emoji="❌"
            ;;
        *)
            local color="\033[0m"   # Default
            local emoji="📝"
            ;;
    esac

    local reset="\033[0m"
    local dim="\033[2m"

    # Build the log line
    local line="${dim}${formatted_time}${reset} ${color}${level^^}${reset} ${emoji} ${message}"

    # Add trace info if present
    for field in "${additional_fields[@]}"; do
        if [[ "$field" == "trace_id="* ]]; then
            local trace_id="${field#*=}"
            line+=" [${trace_id:0:8}...]"
        fi
    done

    # Add duration if present
    for field in "${additional_fields[@]}"; do
        if [[ "$field" == "duration_ms="* ]]; then
            local duration="${field#*=}"
            line+=" (${duration}ms)"
        fi
    done

    echo -e "$line"
}

# Core logging function
__log() {
    local level="$1"
    local message="$2"
    shift 2
    local additional_fields=("$@")

    # Initialize if not already done
    __log_init

    # Check log level
    case "$HOMELAB_LOG_LEVEL" in
        "error")
            if [ "$level" != "error" ]; then return 0; fi
            ;;
        "warn")
            if [ "$level" = "debug" ] || [ "$level" = "info" ]; then return 0; fi
            ;;
        "info")
            if [ "$level" = "debug" ]; then return 0; fi
            ;;
        # "debug" or anything else allows all levels
    esac

    # Generate event ID
    local event_id="$(__log_generate_event_id)"

    # Output based on target
    if [ "$HOMELAB_USE_PRETTY_PRINT" = true ]; then
        __log_build_pretty "$level" "$message" "$event_id" "${additional_fields[@]}"
    else
        __log_build_json "$level" "$message" "$event_id" "${additional_fields[@]}"
    fi

    # Route to Vector if needed
    if [ "$HOMELAB_LOG_TARGET" = "vector" ]; then
        local json_output="$(__log_build_json "$level" "$message" "$event_id" "${additional_fields[@]}")"
        # Try to send to Vector, fail gracefully
        if command -v curl >/dev/null 2>&1; then
            # Use configurable endpoint with sensible timeout/exit-on-failure flags
            local vector_endpoint="${HOMELAB_VECTOR_ENDPOINT:-http://localhost:8682/ingest}"
            echo "$json_output" | curl -sS --connect-timeout 5 --max-time 10 --fail -X POST -H "Content-Type: application/json" -d @- "$vector_endpoint" 2>&1 || {
                # Log the failure but don't exit
                echo "Warning: Failed to send log to Vector at $vector_endpoint" >&2
            } &
        fi
    fi
}

# Public logging functions
log_info() {
    __log "info" "$@"
}

log_warn() {
    __log "warn" "$@"
}

log_error() {
    __log "error" "$@"
}

log_debug() {
    __log "debug" "$@"
}

# Helper utilities
log_metric() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_unit="${3:-count}"
    shift 3
    local additional_fields=("$@")

    __log "info" "Metric: $metric_name" "metric_name=$metric_name" "metric_value=$metric_value" "metric_unit=$metric_unit" "${additional_fields[@]}"
}

log_span() {
    local operation="$1"
    local trace_id="$2"
    local span_id="$3"
    shift 3
    local additional_fields=("$@")

    __log "info" "Span: $operation" "trace_id=$trace_id" "span_id=$span_id" "operation=$operation" "${additional_fields[@]}"
}

# Create a logger with a specific category
log_with_category() {
    local category="$1"
    shift
    __log "info" "$@" "category=$category"
}

# Create a logger with trace context
log_with_trace() {
    local trace_id="$1"
    local span_id="$2"
    shift 2
    __log "info" "$@" "trace_id=$trace_id" "span_id=$span_id"
}

# Create a logger with request context
log_with_request() {
    local request_id="$1"
    local user_hash="$2"
    shift 2
    __log "info" "$@" "request_id=$request_id" "user_hash=$user_hash"
}

# Log HTTP request
log_request() {
    local method="$1"
    local url="$2"
    shift 2
    local additional_fields=("$@")

    __log "info" "HTTP Request" "method=$method" "url=$url" "${additional_fields[@]}"
}

# Log HTTP response
log_response() {
    local method="$1"
    local url="$2"
    local status_code="$3"
    local duration_ms="$4"
    shift 4
    local additional_fields=("$@")

    __log "info" "HTTP Response" "method=$method" "url=$url" "status_code=$status_code" "duration_ms=$duration_ms" "${additional_fields[@]}"
}

# Log error with context
log_error_with_context() {
    local error_message="$1"
    local error_type="$2"
    shift 2
    local additional_fields=("$@")

    __log "error" "$error_message" "error_type=$error_type" "${additional_fields[@]}"
}

# Initialize logging when the script is sourced
__log_init
