# Homelab Node.js Logger

A structured logging helper for Node.js applications in the Homelab ecosystem, built on top of Pino.

## Features

- Structured logging with Pino
- Standardized log schema with required fields
- Automatic event ID generation
- Environment-based configuration
- Pretty printing in development
- Trace and span context support
- HTTP request/response logging helpers
- Error serialization
- OpenTelemetry preparation

## Installation

```bash
npm install pino pino-pretty
```

## Usage

```javascript
const { logger } = require('./tools/logging/node/logger');

// Basic logging
logger.info('Application started');
logger.error('Something went wrong', { context: { userId: 123 } });

// With category
const dbLogger = logger.withCategory('database');
dbLogger.info('Connected to database');

// With trace context
const traceLogger = logger.withTrace('trace-123', 'span-456');
traceLogger.info('Operation completed');

// With request context
const requestLogger = logger.withRequest('req-789', 'user-hash');
requestLogger.info('User action performed');

// Using withSpan for automatic trace context
logger.withSpan(
  { traceId: 'trace-123', spanId: 'span-456' },
  (spanLogger) => {
    spanLogger.info('This log includes trace context');
  }
);

// HTTP request/response logging
app.use((req, res, next) => {
  const start = Date.now();

  logger.logRequest(req);

  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.logResponse(req, res, duration);
  });

  next();
});

// Error logging
try {
  // Some operation that might fail
} catch (error) {
  logger.logError(error, { operation: 'database-query' });
}
```

## Configuration

The logger reads configuration from the following environment variables:

- `HOMELAB_SERVICE`: The service name (default: 'unknown-service')
- `HOMELAB_ENVIRONMENT`: The environment (default: 'development')
- `HOMELAB_LOG_TARGET`: The log target (default: 'stdout')
- `HOMELAB_LOG_LEVEL`: The log level (default: 'info')

## Log Schema

All log entries include the following required fields:

- `timestamp`: ISO-8601 UTC timestamp
- `level`: Log level (error, warn, info, debug)
- `message`: Log message
- `service`: Service name
- `environment`: Environment name
- `version`: Application version from package.json
- `category`: Log category (default: 'application')
- `event_id`: Monotonically increasing event ID
- `trace_id`: Trace ID for distributed tracing
- `span_id`: Span ID for distributed tracing
- `context`: Additional context object

Optional fields:

- `request_id`: Request ID
- `user_hash`: Hashed user identifier
- `source`: Log source
- `duration_ms`: Operation duration in milliseconds
- `status_code`: HTTP status code
- `tags`: Array of tags
