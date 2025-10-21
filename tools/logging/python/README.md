# Python Logger

A dependency-free structured logging implementation that follows the homelab project's common logging schema.

## Installation

No additional packages are required—`logger.py` works with the Python standard library. Simply ensure the module is on your `PYTHONPATH` (the end-to-end tests run with `PYTHONPATH=python` from the `tools/logging` directory).

## Usage

```python
from logger import logger, LoggerUtils

# Basic logging
logger.info("Application started")
logger.warn("Something unexpected happened")
logger.error("An error occurred")

# Logging with context
logger.info("User action", user_id="123", action="login")

# Using categories
auth_logger = logger.with_category("auth")
auth_logger.info("User authenticated", user_id="123")

# Adding trace context
trace_logger = LoggerUtils.bind_trace("trace-123", "span-456")
trace_logger.info("Operation completed")

# Adding request context
request_logger = LoggerUtils.with_request("req-789", "user-hash")
request_logger.info("Request processed")

# HTTP logging
LoggerUtils.log_request("GET", "/api/users", "req-123", "Mozilla/5.0")
LoggerUtils.log_response("GET", "/api/users", 200, 150, "req-123")

# Error logging
try:
    # Some operation that might fail
    raise ValueError("Invalid input")
except Exception as e:
    LoggerUtils.log_error(e, input_value="test")
```

## Configuration

The logger reads configuration from environment variables:

- `HOMELAB_SERVICE`: Service name (default: "unknown-service")
- `HOMELAB_ENVIRONMENT`: Environment (default: "development")
- `HOMELAB_LOG_TARGET`: Log target (default: "stdout")
- `HOMELAB_LOG_LEVEL`: Log level (default: "info")

## Output Format

### JSON Output (default)

```json
{
  "timestamp": "2023-10-20T02:45:16.818Z",
  "level": "info",
  "message": "User authenticated",
  "service": "auth-service",
  "environment": "production",
  "version": "1.0.0",
  "category": "auth",
  "event_id": "evt_1697795116818_1",
  "trace_id": "trace-123",
  "span_id": "span-456",
  "request_id": "req-789",
  "context": {
    "user_id": "123"
  }
}
```

### Console Output (when HOMELAB_LOG_TARGET=stdout and TTY is present)

```
02:45:16 INFO auth-service auth [trace-12...] - User authenticated
{
  "user_id": "123"
}
```

## Schema

### Required Fields

- `timestamp`: ISO-8601 UTC timestamp
- `level`: Log level (error, warn, info, debug)
- `message`: Log message
- `service`: Service name
- `environment`: Environment (development, staging, production)
- `version`: Service version from pyproject.toml
- `category`: Log category (default: "application")
- `event_id`: Monotonic event ID (auto-generated)
- `context`: Additional context object

### Optional Fields

- `request_id`: Request ID
- `user_hash`: User identifier hash
- `source`: Source identifier
- `duration_ms`: Duration in milliseconds
- `status_code`: HTTP status code
- `tags`: Array of tags
- `trace_id`: OpenTelemetry trace identifier for distributed tracing
- `span_id`: OpenTelemetry span identifier for distributed tracing

## OpenTelemetry Integration

The logger is prepared for OpenTelemetry integration. The `bind_trace` function can be used to associate logs with OpenTelemetry traces:

```python
# With OpenTelemetry
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("operation") as span:
    trace_id = format(span.get_span_context().trace_id, "032x")
    span_id = format(span.get_span_context().span_id, "016x")

    trace_logger = LoggerUtils.bind_trace(trace_id, span_id)
    trace_logger.info("Operation in progress")
