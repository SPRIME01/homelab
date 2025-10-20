# Vector Configuration

This directory contains the Vector configuration for collecting, transforming, and forwarding logs and metrics according to the ADR specifications.

## Overview

Vector is configured to:
- Listen for OTLP logs on localhost (ports 4317 for gRPC and 4318 for HTTP)
- Parse JSON logs
- Apply redaction transforms for PII (email addresses, access tokens, session identifiers)
- Forward events to OpenObserve through OTLP
- Emit Prometheus-compatible metrics to GreptimeDB
- Provide local stdout tailing

## Configuration

The main configuration is in [`vector.toml`](./vector.toml), which includes:

### Sources
- **OTLP gRPC**: Listens on `0.0.0.0:4317` for gRPC OTLP logs
- **OTLP HTTP**: Listens on `0.0.0.0:4318` for HTTP OTLP logs

### Transforms
- **JSON Parsing**: Parses log messages as JSON
- **PII Redaction**: Redacts sensitive information including:
  - Email addresses
  - Access tokens
  - API keys
  - Session identifiers
  - Any field containing 'token', 'key', 'secret', or 'password'
- **Metadata Addition**: Adds source, environment, and timestamp metadata
- **Metrics Extraction**: Extracts metrics from log data

### Sinks
- **OpenObserve**: Forwards logs to OpenObserve via OTLP
- **GreptimeDB**: Sends metrics to GreptimeDB via Prometheus remote write
- **Console**: Outputs logs to stdout for local tailing
- **File**: Optionally stores logs to local files with daily rotation

## Running Vector Locally

### Using Devbox

The project includes Vector as a Devbox package and provides convenient scripts:

1. Start Vector with the configuration:
   ```bash
   devbox run vector
   ```

2. Tail logs in real-time:
   ```bash
   devbox run log-tail
   ```

### Manual Installation

If you prefer to install Vector manually:

1. Install Vector following the [official installation guide](https://vector.dev/docs/setup/installation/)

2. Run Vector with the configuration:
   ```bash
   vector --config ops/vector/vector.toml
   ```

3. To tap into the log stream:
   ```bash
   vector tap --config ops/vector/vector.toml
   ```

## Environment Variables

Vector will use the following environment variable if set:
- `ENVIRONMENT`: Sets the environment tag (defaults to "development")

## Dependencies

Vector expects the following services to be running:
- **OpenObserve**: HTTP endpoint on `localhost:5080`
- **GreptimeDB**: Prometheus remote write endpoint on `localhost:4000`

## Testing

To test the Vector configuration:

1. Start Vector:
   ```bash
   devbox run vector
   ```

2. Send a test log using curl:
   ```bash
   curl -X POST http://localhost:4318/v1/logs \
     -H "Content-Type: application/json" \
     -d '{
       "resourceLogs": [{
         "resource": {},
         "scopeLogs": [{
           "scope": {},
           "logRecords": [{
             "timeUnixNano": "1640995200000000000",
             "severityNumber": 9,
             "severityText": "INFO",
             "body": {
               "stringValue": "{\"message\": \"Test log\", \"email\": \"test@example.com\", \"access_token\": \"secret123\"}"
             }
           }]
         }]
       }]
     }'
   ```

3. Check the console output to see the redacted log:
   ```bash
   devbox run log-tail
   ```

## Troubleshooting

- If Vector fails to start, check the configuration syntax with:
  ```bash
  vector validate ops/vector/vector.toml
  ```

- For more verbose output, run with:
  ```bash
  vector --config ops/vector/vector.toml --verbose
  ```

- Check that OpenObserve and GreptimeDB are accessible from Vector.
