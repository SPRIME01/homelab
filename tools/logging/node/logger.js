const fs = require('fs');
const path = require('path');
const { Writable } = require('stream');
const pino = require('pino');

// -----------------------------------------------------------------------------
// Configuration helpers
// -----------------------------------------------------------------------------

let eventIdCounter = 0;

function generateEventId() {
  eventIdCounter += 1;
  return `evt_${Date.now()}_${eventIdCounter}`;
}

function getVersion() {
  try {
    const packageJsonPath = path.resolve(process.cwd(), 'package.json');
    if (fs.existsSync(packageJsonPath)) {
      const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
      return packageJson.version || '0.0.0';
    }
  } catch (error) {
    // Ignore and fall back to default version
  }
  return '0.0.0';
}

const config = {
  service: process.env.HOMELAB_SERVICE || 'unknown-service',
  environment: process.env.HOMELAB_ENVIRONMENT || 'development',
  logTarget: (process.env.HOMELAB_LOG_TARGET || 'stdout').toLowerCase(),
  logLevel: (process.env.HOMELAB_LOG_LEVEL || 'info').toLowerCase(),
  forcePretty: String(process.env.HOMELAB_FORCE_PRETTY || '').toLowerCase() === 'true',
  version: getVersion()
};

const usePrettyPrint =
  config.logTarget === 'stdout'
    ? (config.forcePretty || process.stdout.isTTY)
    : false;

const OPTIONAL_ROOT_FIELDS = [
  'request_id',
  'user_hash',
  'source',
  'duration_ms',
  'status_code',
  'tags',
  'trace_id',
  'span_id'
];

const RESERVED_FIELDS = new Set([
  'level',
  'msg',
  'message',
  'timestamp',
  'service',
  'environment',
  'version',
  'category',
  'event_id',
  'trace_id',
  'span_id',
  'context',
  'time',
  'pid',
  'hostname',
  'req',
  'res',
  'err',
  ...OPTIONAL_ROOT_FIELDS
]);

const MESSAGE_FIELD = '__structured_message';
RESERVED_FIELDS.add(MESSAGE_FIELD);
const METHOD_WRAPPED_FLAG = Symbol('structuredLoggerMethodWrapped');

// -----------------------------------------------------------------------------
// Formatting helpers
// -----------------------------------------------------------------------------

function serializeError(error) {
  if (!error) {
    return null;
  }

  const serialized = {
    name: error.name || 'Error',
    message: error.message || String(error),
    stack: error.stack
  };

  for (const key of Object.keys(error)) {
    if (!(key in serialized)) {
      serialized[key] = error[key];
    }
  }

  return serialized;
}

function buildLogEntry(object) {
  const messageValue =
    object.msg !== undefined
      ? object.msg
      : object.message !== undefined
        ? object.message
        : object[MESSAGE_FIELD];

  const entry = {
    timestamp: new Date().toISOString(),
    level: object.level,
    message: messageValue !== undefined ? messageValue : '',
    service: object.service || config.service,
    environment: object.environment || config.environment,
    version: object.version || config.version,
    category: object.category || 'application',
    event_id: object.event_id || generateEventId(),
    trace_id: object.trace_id,
    span_id: object.span_id,
    context: {}
  };

  for (const field of OPTIONAL_ROOT_FIELDS) {
    if (object[field] !== undefined) {
      entry[field] = object[field];
    }
  }

  if (object.context && typeof object.context === 'object') {
    entry.context = { ...object.context };
  }

  for (const key of Object.keys(object)) {
    if (RESERVED_FIELDS.has(key)) {
      continue;
    }
    const value = object[key];
    if (value !== undefined) {
      entry.context[key] = value;
    }
  }

  if (!entry.context || Object.keys(entry.context).length === 0) {
    entry.context = {};
  }

  if (entry.trace_id === undefined) {
    delete entry.trace_id;
  }
  if (entry.span_id === undefined) {
    delete entry.span_id;
  }

  return entry;
}

const LEVEL_COLORS = {
  debug: '\x1b[36m',
  info: '\x1b[32m',
  warn: '\x1b[33m',
  error: '\x1b[31m'
};

const COLOR_RESET = '\x1b[0m';
const COLOR_DIM = '\x1b[2m';
const COLOR_BOLD = '\x1b[1m';

function formatPrettyEntry(entry, colorize) {
  const timestamp = entry.timestamp
    ? new Date(entry.timestamp).toISOString().substring(11, 19)
    : '';
  const level = (entry.level || 'info').toUpperCase();
  const service = entry.service || '';
  const category =
    entry.category && entry.category !== 'application' ? entry.category : '';

  const levelColor = LEVEL_COLORS[entry.level] || '';
  const color = (value, code) => (colorize && code ? `${code}${value}${COLOR_RESET}` : value);

  const parts = [
    timestamp ? color(timestamp, COLOR_DIM) : '',
    color(level, levelColor),
    color(service, COLOR_BOLD),
    category
  ];

  if (entry.trace_id) {
    parts.push(`[${String(entry.trace_id).substring(0, 8)}...]`);
  }

  if (entry.duration_ms !== undefined) {
    parts.push(`(${entry.duration_ms}ms)`);
  }

  parts.push('-');
  parts.push(entry.message);

  const line = parts.filter(Boolean).join(' ');
  const contextString =
    entry.context && Object.keys(entry.context).length > 0
      ? `\n${color(JSON.stringify(entry.context, null, 2), COLOR_DIM)}`
      : '';

  return `${line}${contextString}`;
}

class JsonStream extends Writable {
  constructor(targetStream) {
    super();
    this.target = targetStream;
  }

  _write(chunk, encoding, callback) {
    try {
      this.target.write(chunk, encoding);
      callback();
    } catch (error) {
      callback(error);
    }
  }
}

class PrettyStream extends Writable {
  constructor(targetStream, colorize) {
    super();
    this.target = targetStream;
    this.colorize = colorize;
    this.buffer = '';
  }

  _write(chunk, encoding, callback) {
    try {
      this.buffer += chunk.toString();

      let newlineIndex = this.buffer.indexOf('\n');
      while (newlineIndex !== -1) {
        const line = this.buffer.slice(0, newlineIndex);
        this.buffer = this.buffer.slice(newlineIndex + 1);

        if (line.trim().length > 0) {
          const parsed = JSON.parse(line);
          const formatted = formatPrettyEntry(parsed, this.colorize);
          this.target.write(`${formatted}\n`);
        }

        newlineIndex = this.buffer.indexOf('\n');
      }
      callback();
    } catch (error) {
      callback(error);
    }
  }
}

function wrapLogMethods(pinoLogger) {
  const levels = ['debug', 'info', 'warn', 'error'];

  levels.forEach((level) => {
    const method = pinoLogger[level];
    if (typeof method !== 'function') {
      return;
    }

    if (method[METHOD_WRAPPED_FLAG]) {
      return;
    }

    const original = method.bind(pinoLogger);

    const wrapped = (arg1, arg2) => {
      const bindings = typeof pinoLogger.bindings === 'function'
        ? pinoLogger.bindings()
        : {};

      const isObjectArg =
        arg1 !== null &&
        typeof arg1 === 'object' &&
        !Array.isArray(arg1) &&
        !(arg1 instanceof Date);

      if (typeof arg1 === 'string') {
        const baseContext =
          arg2 && typeof arg2 === 'object' && arg2 !== null ? arg2 : {};
        const payload = {
          ...bindings,
          ...baseContext,
          [MESSAGE_FIELD]: arg1
        };
        return original(payload, arg1);
      }

      if (isObjectArg) {
        const message = typeof arg2 === 'string' ? arg2 : '';
        const payload = {
          ...bindings,
          ...arg1,
          [MESSAGE_FIELD]: message
        };
        return original(payload, message);
      }

      const fallbackMessage =
        arg1 === undefined ? '' : (typeof arg1 === 'string' ? arg1 : String(arg1));
      return original({ ...bindings, [MESSAGE_FIELD]: fallbackMessage }, fallbackMessage);
    };

    wrapped[METHOD_WRAPPED_FLAG] = true;
    pinoLogger[level] = wrapped;
  });
}

// -----------------------------------------------------------------------------
// Logger creation and utilities
// -----------------------------------------------------------------------------

const destination = usePrettyPrint
  ? new PrettyStream(process.stdout, process.stdout.isTTY)
  : new JsonStream(process.stdout);

const baseLogger = pino(
  {
    level: config.logLevel,
    base: null,
    timestamp: false,
    formatters: {
      level: (label) => ({ level: label }),
      bindings: () => ({}),
      log: (object) => buildLogEntry(object)
    }
  },
  destination
);

function createLoggerUtils(currentLogger) {
  return {
    createLogger(options = {}) {
      const childBindings = {
        service: options.service || config.service,
        environment: options.environment || config.environment,
        version: options.version || config.version,
        category: options.category || 'application'
      };
      return buildLogger(currentLogger.child(childBindings));
    },

    withCategory(category) {
      return buildLogger(currentLogger.child({ category }));
    },

    withTrace(traceId, spanId) {
      return buildLogger(
        currentLogger.child({
          trace_id: traceId,
          span_id: spanId
        })
      );
    },

    withRequest(requestId, userHash) {
      return buildLogger(
        currentLogger.child({
          request_id: requestId,
          user_hash: userHash
        })
      );
    },

    withSpan(spanContext = {}, fn) {
      if (typeof fn !== 'function') {
        return undefined;
      }
      const { traceId, spanId } = spanContext;
      const spanLogger = buildLogger(
        currentLogger.child({
          trace_id: traceId,
          span_id: spanId
        })
      );
      return fn(spanLogger);
    },

    logRequest(req = {}, additionalContext = {}) {
      const headers = req.headers || {};
      const requestId = req.id || headers['x-request-id'] || headers['X-Request-Id'];
      currentLogger.info(
        {
          request_id: requestId,
          context: {
            method: req.method,
            url: req.url,
            userAgent: headers['user-agent'] || headers['User-Agent'],
            ...additionalContext
          }
        },
        'HTTP Request'
      );
    },

    logResponse(req = {}, res = {}, durationMs, additionalContext = {}) {
      const headers = req.headers || {};
      const requestId = req.id || headers['x-request-id'] || headers['X-Request-Id'];
      currentLogger.info(
        {
          request_id: requestId,
          status_code: res.statusCode,
          duration_ms: durationMs,
          context: {
            method: req.method,
            url: req.url,
            ...additionalContext
          }
        },
        'HTTP Response'
      );
    },

    logError(error, additionalContext = {}) {
      const errContext = serializeError(error);
      currentLogger.error(
        {
          context: {
            ...additionalContext,
            ...(errContext ? { err: errContext } : {})
          }
        },
        (error && error.message) || 'Error occurred'
      );
    }
  };
}

function buildLogger(pinoLogger) {
  wrapLogMethods(pinoLogger);

  const originalChild = pinoLogger.child.bind(pinoLogger);
  pinoLogger.child = (bindings = {}) => buildLogger(originalChild(bindings));

  return Object.assign(pinoLogger, createLoggerUtils(pinoLogger));
}

const logger = buildLogger(
  baseLogger.child({
    service: config.service,
    environment: config.environment,
    version: config.version
  })
);

// -----------------------------------------------------------------------------
// Exports
// -----------------------------------------------------------------------------

logger.serializeError = serializeError;
logger.generateEventId = generateEventId;
logger.config = config;

module.exports = Object.assign(logger, {
  logger,
  serializeError,
  generateEventId,
  config
});
