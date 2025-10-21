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
    local timestamp_ms=""

    if command -v python3 >/dev/null 2>&1; then
        timestamp_ms="$(python3 -c 'import time; print(int(time.time() * 1000))' 2>/dev/null)"
    fi

    if [ -z "$timestamp_ms" ]; then
        if timestamp_ms="$(date +%s%3N 2>/dev/null)"; then
            :
        else
            local seconds
            seconds="$(date +%s 2>/dev/null || printf '0')"
            timestamp_ms="$((seconds * 1000))"
        fi
    fi

    echo "evt_${timestamp_ms}_${HOMELAB_EVENT_ID_COUNTER}"
}

# Get ISO-8601 UTC timestamp
__log_get_timestamp() {
    local gnu_timestamp
    if gnu_timestamp="$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null)"; then
        echo "$gnu_timestamp"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")' 2>/dev/null && return 0
    fi

    date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null
}

# Escape JSON string
__log_json_escape() {
    local str="$1"

    # Try jq first (most reliable)
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "$str" | jq -Rs . 2>/dev/null | sed 's/^"//;s/"$//' | tr -d '\n' && return 0
    fi

    # Try python3 next
    if command -v python3 >/dev/null 2>&1; then
        printf '%s' "$str" | python3 - 2>/dev/null <<'PY'
import json
import sys

value = sys.stdin.read()
encoded = json.dumps(value, ensure_ascii=False)
sys.stdout.write(encoded[1:-1])
PY
        return 0
    fi

    # Fallback: use perl for comprehensive escaping of control characters
    if command -v perl >/dev/null 2>&1; then
        printf '%s' "$str" | perl -C -0pe '
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

    # Last resort: minimal POSIX escaping
    printf '%s' "$str" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e $'s/\t/\\\\t/g' -e $'s/\r/\\\\r/g' -e $'s/\n/\\\\n/g' | tr -d '\n'
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

    local escaped_service="$(__log_json_escape "$HOMELAB_SERVICE")"
    local escaped_environment="$(__log_json_escape "$HOMELAB_ENVIRONMENT")"
    local escaped_version="$(__log_json_escape "$HOMELAB_VERSION")"

    local root_fields=(
        "\"timestamp\":\"$timestamp\""
        "\"level\":\"$level\""
        "\"message\":\"$json_message\""
        "\"service\":\"$escaped_service\""
        "\"environment\":\"$escaped_environment\""
        "\"version\":\"$escaped_version\""
        "\"category\":\"application\""
        "\"event_id\":\"$event_id\""
    )

    local context_entries=()

    for field in "${additional_fields[@]}"; do
        if [[ "$field" == *"="* ]]; then
            local key="${field%%=*}"
            local value="${field#*=}"

            # Check if this is a root-level field
            case "$key" in
                category)
                    local escaped_value="$(__log_json_escape "$value")"
                    local replaced=false
                    for i in "${!root_fields[@]}"; do
                        if [[ "${root_fields[$i]}" == "\"category\":"* ]]; then
                            root_fields[$i]="\"category\":\"$escaped_value\""
                            replaced=true
                            break
                        fi
                    done
                    if [ "$replaced" = false ]; then
                        root_fields+=("\"category\":\"$escaped_value\"")
                    fi
                    ;;
                request_id|user_hash|source|duration_ms|status_code|tags|trace_id|span_id)
                    root_fields+=("\"$key\":\"$(__log_json_escape "$value")\"")
                    ;;
                *)
                    context_entries+=("\"$key\":\"$(__log_json_escape "$value")\"")
                    ;;
            esac
        fi
    done

    if [ "${#context_entries[@]}" -gt 0 ]; then
        local context_body
        context_body="$(IFS=,; echo "${context_entries[*]}")"
        root_fields+=("\"context\":{${context_body}}")
    else
        root_fields+=("\"context\":{}")
    fi

    local json="{"
    json+="$(IFS=,; echo "${root_fields[*]}")"
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

# Build OTLP minimal JSON payload for a single log record.
# Arguments:
# 1: timeUnixNano
# 2: severityNumber
# 3: severityText
# 4: body_string_value (escaped JSON string)
__log_build_otlp_payload() {
    local time_unix_nano="$1"
    local severity_number="$2"
    local severity_text="$3"
    local body_string_value="$4"

    # Construct the JSON payload without external dependencies.
    printf '%s' "{\"resourceLogs\":[{\"resource\":{},\"scopeLogs\":[{\"scope\":{},\"logRecords\":[{\"timeUnixNano\":\"${time_unix_nano}\",\"severityNumber\":${severity_number},\"severityText\":\"${severity_text}\",\"body\":{\"stringValue\":\"${body_string_value}\"}}]}]}]}"
}

# Map log level to OTLP severity number
severity_number() {
    case "$1" in
        "debug") echo "5" ;;
        "info") echo "9" ;;
        "warn") echo "13" ;;
        "error") echo "17" ;;
        *) echo "9" ;;
    esac
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

    local json_output="$(__log_build_json "$level" "$message" "$event_id" "${additional_fields[@]}")"

    # Output based on target
    if [ "$HOMELAB_USE_PRETTY_PRINT" = true ]; then
        __log_build_pretty "$level" "$message" "$event_id" "${additional_fields[@]}"
    else
        echo "$json_output"
    fi

    # Route to Vector if needed
    if [ "$HOMELAB_LOG_TARGET" = "vector" ]; then
        # Try to send to Vector, fail gracefully
        if command -v curl >/dev/null 2>&1; then
            # Use configurable endpoint with sensible timeout/exit-on-failure flags
            # Default to Vector's OTLP HTTP logs endpoint. Allow override via HOMELAB_VECTOR_ENDPOINT.
            # We construct a minimal OTLP JSON payload (resourceLogs -> scopeLogs -> logRecords)
            # and put the structured log JSON as a string in body.stringValue. This matches
            # the transforms in ops/vector/vector.toml which look for .message or .body.
            local vector_endpoint="${HOMELAB_VECTOR_ENDPOINT:-http://localhost:4318/v1/logs}"
            local curl_output=""

            # Prepare timeUnixNano (portable fallback to python3 when needed)
            local time_unix_nano
            if time_unix_nano="$(date +%s%N 2>/dev/null)" && [ -n "$time_unix_nano" ]; then
                :
            elif command -v python3 >/dev/null 2>&1; then
                time_unix_nano="$(python3 -c 'import time; print(int(time.time() * 1e9))' 2>/dev/null)"
            else
                # Fallback: seconds -> nanoseconds
                local secs
                secs="$(date +%s 2>/dev/null || printf '0')"
                time_unix_nano="$((secs * 1000000000))"
            fi

            # Escape the structured JSON so it can be placed into a JSON string
            local escaped_payload
            escaped_payload="$(__log_json_escape "$json_output")"

            # Build minimal OTLP JSON payload without depending on jq
            local otlp_payload
            otlp_payload="$(__log_build_otlp_payload "$time_unix_nano" "$(severity_number "$level")" "$level" "$escaped_payload")"

            if ! curl_output="$(printf '%s' "$otlp_payload" | curl --silent --show-error --fail --connect-timeout 2 --max-time 5 -X POST -H "Content-Type: application/json" -d @- "$vector_endpoint" 2>&1)"; then
                echo "Warning: Failed to send log to Vector at $vector_endpoint" >&2
                if [ -n "$curl_output" ]; then
                    echo "$curl_output" >&2
                fi
            fi
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
