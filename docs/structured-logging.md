# Structured Logging System

## Overview

This document describes the structured logging system implemented for the homelab project. The system provides a unified logging approach across Node.js, Python, and Shell environments, with consistent schema and output formatting.

## Architecture

The structured logging system consists of the following components:

1. **Language-specific loggers**:
   - Node.js logger (`tools/logging/node/logger.js`)
   - Python logger (`tools/logging/python/logger.py`)
   - Shell logger (`lib/logging.sh`)

2. **Environment bootstrap**:
   - Environment loader (`lib/env-loader.sh`)
   - Configuration management

3. **Log processing**:
   - Vector configuration (`ops/vector/vector.toml`)
   - PII redaction and transformations

4. **CI/CD integration**:
   - Logging check script (`tools/tasks/logging-check.js`)
   - Justfile integration

## Schema

All log entries follow a common schema with the following fields:

### Required Fields
- `timestamp`: ISO-8601 UTC timestamp
- `level`: Log level (debug, info, warn, error)
- `message`: Log message
- `service`: Service name
- `environment`: Environment (development, staging, production)
- `version`: Application version
- `category`: Log category (application, audit, etc.)
- `event_id`: Unique event identifier
- `context`: Additional context data

### Optional Root Fields
- `request_id`: Request identifier
- `user_hash`: Hashed user identifier
- `source`: Log source
- `duration_ms`: Duration in milliseconds
- `status_code`: HTTP status code
- `tags`: Array of tags
- `trace_id`: Distributed trace identifier
- `span_id`: Span identifier

## Usage

### Node.js

```javascript
const { logger } = require('../../../tools/logging/node/logger');

// Basic logging
logger.info('Application started');

// Logging with context
logger.info('User action', {
  userId: '123',
  action: 'login'
});

// Using utility methods
logger.logRequest(req);
logger.logResponse(req, res, 150);
logger.logError(error);
```

### Python

```python
from logger import logger

# Basic logging
logger.info("Application started")

# Logging with context
logger.info("User action", user_id="123", action="login")

# Using utility methods
LoggerUtils.log_request("GET", "/api/users", "req-123", "test-agent")
LoggerUtils.log_response("GET", "/api/users", 200, 150, "req-123")
LoggerUtils.log_error(error, operation="test")
```

### Shell

```bash
# Source the logging system
source lib/logging.sh

# Basic logging
log_info "Application started"

# Logging with context
log_info "User action" "user_id=123" "action=login"

# Using utility methods
log_request "GET" "/api/users" "user_agent=test"
log_response "GET" "/api/users" "200" "150"
log_error_with_context "Database error" "ConnectionError" "host=db.example.com"
```

## Configuration

### Environment Variables

- `HOMELAB_SERVICE`: Service name (default: unknown-service)
- `HOMELAB_ENVIRONMENT`: Environment (default: development)
- `HOMELAB_LOG_TARGET`: Log target (stdout, vector, default: vector)
- `HOMELAB_LOG_LEVEL`: Log level (debug, info, warn, error, default: info)
- `HOMELAB_FORCE_PRETTY`: Force pretty printing (true/false, default: false)

### Environment Bootstrap

The environment bootstrap system loads the appropriate configuration based on the mode:

```bash
# Local development
source lib/env-loader.sh local

# CI environment
source lib/env-loader.sh ci

# Shell environment
source lib/env-loader.sh shell
```

## Vector Integration

Logs are processed by Vector for transformation and routing:

1. **Sources**: OTLP endpoints receive logs from applications
2. **Transforms**: JSON parsing, PII redaction, metadata addition
3. **Sinks**: OpenObserve for log storage, GreptimeDB for metrics

### PII Redaction

Vector automatically redacts sensitive information:
- Email addresses: `user@example.com` → `REDACTED_EMAIL`
- Access tokens: `token123` → `REDACTED_TOKEN`
- API keys: `key123` → `REDACTED_KEY`
- Session identifiers: `sess123` → `REDACTED_SESSION`

## Testing

### End-to-End Tests

Run the comprehensive test suite:

```bash
./tests/e2e/test_logging_pipeline.sh
```

### Individual Logger Tests

Test each logger implementation:

```bash
# Node.js
cd tools/logging/node && node test_node_logger.js

# Python
cd tools/logging/python && python test_structlog.py

# Shell
cd tools/logging && bash test_shell_logger.sh
```

### CI/CD Integration

Run the logging check as part of CI/CD:

```bash
# Using Just
just logging

# Direct execution
node tools/tasks/logging-check.js
```

## Troubleshooting

### Common Issues

1. **Node.js module not found**:
   - Ensure the require path is correct: `./node/logger`
   - Check that you're in the correct directory

2. **Python logger issues**:
   - Ensure Python 3.12+ is available—the logger has no third-party dependencies
   - Check PYTHONPATH includes the logger directory

3. **Shell logger not found**:
   - Ensure `lib/logging.sh` is sourced before use
   - Check that the script is executable

4. **Vector configuration issues**:
   - Validate configuration: `vector validate ops/vector/vector.toml`
   - Check that Vector is running and accessible

### Debug Mode

Enable debug logging for troubleshooting:

```bash
export HOMELAB_LOG_LEVEL=debug
export HOMELAB_LOG_TARGET=stdout
export HOMELAB_FORCE_PRETTY=true
```

## Best Practices

1. **Use structured logging consistently** across all applications
2. **Include relevant context** with log messages
3. **Use appropriate log levels** for different types of messages
4. **Avoid logging sensitive information** (PII redaction helps but prevention is better)
5. **Test logging output** to ensure schema compliance
6. **Monitor log aggregation** to detect issues early

## Migration Guide

### From Unstructured to Structured Logging

1. Replace console.log/logger.info with structured logger calls
2. Add context information to log messages
3. Update error handling to use structured error logging
4. Configure environment variables for proper log targeting
5. Update CI/CD pipelines to include logging checks

### Example Migration

**Before:**
```javascript
console.log('User logged in:', userId);
```

**After:**
```javascript
logger.info('User logged in', { userId });
```

## References

- [Vector Documentation](https://vector.dev/docs/)
- [OpenTelemetry Logging](https://opentelemetry.io/docs/specs/otel/logs/)
