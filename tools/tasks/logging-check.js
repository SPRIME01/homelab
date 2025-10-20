#!/usr/bin/env node

const { existsSync, readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { execSync } = require("node:child_process");

const PROJECT_ROOT = process.cwd();
const REQUIRED_FILES = [
  // Core logging infrastructure
  resolve(PROJECT_ROOT, "lib/logging.sh"),
  resolve(PROJECT_ROOT, "lib/env-loader.sh"),

  // Language-specific loggers
  resolve(PROJECT_ROOT, "tools/logging/node/logger.js"),
  resolve(PROJECT_ROOT, "tools/logging/python/logger.py"),

  // Test files to verify functionality
  resolve(PROJECT_ROOT, "tools/logging/test_node_logger.js"),
  resolve(PROJECT_ROOT, "tools/logging/test_structlog.py"),
  resolve(PROJECT_ROOT, "tools/logging/test_shell_logger.sh"),
];

const REQUIRED_SCHEMA_FIELDS = [
  "timestamp",
  "level",
  "message",
  "service",
  "environment",
  "version",
  "category",
  "event_id",
  "context"
];

const OPTIONAL_ROOT_FIELDS = [
  "request_id",
  "user_hash",
  "source",
  "duration_ms",
  "status_code",
  "tags",
  "trace_id",
  "span_id"
];

let errors = [];

function checkRequiredFiles() {
  console.log("🔍 Checking required logging files...");

  const missing = REQUIRED_FILES.filter((file) => !existsSync(file));

  if (missing.length > 0) {
    errors.push(`Missing required files: ${missing.join(", ")}`);
    return false;
  }

  console.log("✅ All required logging files present");
  return true;
}

function checkNodeLogger() {
  console.log("🔍 Checking Node.js logger schema...");

  try {
    // Test that the Node logger can be loaded
    const loggerPath = resolve(PROJECT_ROOT, "tools/logging/node/logger.js");
    const loggerDir = resolve(PROJECT_ROOT, "tools/logging/node");

    // Change to node logger directory to ensure relative paths work
    const originalCwd = process.cwd();
    process.chdir(loggerDir);

    // Load and test the logger
    const logger = require(loggerPath);

    // Create a test logger and verify output structure
    const testLogger = logger.createLogger({ category: "test" });

    // Capture output by temporarily hijacking console.log
    const originalWrite = process.stdout.write;
    let logOutput = "";
    process.stdout.write = (chunk) => {
      logOutput += chunk.toString();
      return true;
    };

    // Log a test message
    testLogger.info("Test message", { test_field: "test_value" });

    // Restore stdout
    process.stdout.write = originalWrite;

    // Restore original working directory
    process.chdir(originalCwd);

    // Parse the JSON output to verify schema
    const logEntry = JSON.parse(logOutput);

    // Check required fields
    for (const field of REQUIRED_SCHEMA_FIELDS) {
      if (!(field in logEntry)) {
        errors.push(`Node.js logger missing required field: ${field}`);
        return false;
      }
    }

    console.log("✅ Node.js logger schema verification passed");
    return true;

  } catch (error) {
    errors.push(`Node.js logger schema verification failed: ${error.message}`);
    return false;
  }
}

function checkPythonLogger() {
  console.log("🔍 Checking Python logger schema...");

  try {
    const inlineScript = `from logger import logger\nlogger.info('Test message', test_field='test_value')`;
    const output = execSync(`python3 -c "${inlineScript}"`, {
      cwd: resolve(PROJECT_ROOT, "tools/logging"),
      encoding: 'utf8',
      env: {
        ...process.env,
        HOMELAB_LOG_TARGET: 'vector',
        PYTHONPATH: resolve(PROJECT_ROOT, "tools/logging/python")
      }
    });

    const jsonLine = output.trim().split('\n').find(line => line.startsWith('{'));
    if (!jsonLine) {
      errors.push("Python logger test did not produce valid JSON output");
      return false;
    }

    const logEntry = JSON.parse(jsonLine);

    for (const field of REQUIRED_SCHEMA_FIELDS) {
      if (!(field in logEntry)) {
        errors.push(`Python logger missing required field: ${field}`);
        return false;
      }
    }

    console.log("✅ Python logger schema verification passed");
    return true;

  } catch (error) {
    errors.push(`Python logger schema verification failed: ${error.message}`);
    return false;
  }
}

function checkShellLogger() {
  console.log("🔍 Checking Shell logger schema...");

  try {
    const testScriptPath = resolve(PROJECT_ROOT, "tools/logging/test_shell_logger.sh");

    // Run the shell test script to verify the logger
    const output = execSync(`bash -c "source ./lib/logging.sh && log_info 'Test message' 'test_field=value'"`, {
      cwd: PROJECT_ROOT,
      encoding: 'utf8',
      env: {
        ...process.env,
        HOMELAB_LOG_TARGET: 'vector'
      }
    });

    const jsonLine = output.trim().split('\n').find(line => line.startsWith('{'));
    if (!jsonLine) {
      errors.push("Shell logger test did not produce valid JSON output");
      return false;
    }

    const logEntry = JSON.parse(jsonLine);

    for (const field of REQUIRED_SCHEMA_FIELDS) {
      if (!(field in logEntry)) {
        errors.push(`Shell logger missing required field: ${field}`);
        return false;
      }
    }

    console.log("✅ Shell logger schema verification passed");
    return true;

  } catch (error) {
    errors.push(`Shell logger schema verification failed: ${error.message}`);
    return false;
  }
}

function checkEnvironmentBootstrap() {
  console.log("🔍 Checking environment bootstrap...");

  try {
    // Test that env-loader.sh can be sourced and sets required variables
    const output = execSync(`bash -c '. ./lib/env-loader.sh ci && env | grep HOMELAB_'`, {
      cwd: PROJECT_ROOT,
      encoding: 'utf8'
    });

    const requiredEnvVars = [
      "HOMELAB_ENV_MODE",
      "HOMELAB_ENV_TARGET",
      "HOMELAB_SERVICE",
      "HOMELAB_ENVIRONMENT",
      "HOMELAB_LOG_TARGET"
    ];

    for (const envVar of requiredEnvVars) {
      if (!output.includes(envVar)) {
        errors.push(`Environment bootstrap missing required variable: ${envVar}`);
        return false;
      }
    }

    console.log("✅ Environment bootstrap verification passed");
    return true;

  } catch (error) {
    errors.push(`Environment bootstrap verification failed: ${error.message}`);
    return false;
  }
}

function main() {
  console.log("🚀 Starting logging infrastructure checks...\n");

  let allPassed = true;

  // Run all checks
  allPassed = checkRequiredFiles() && allPassed;
  allPassed = checkNodeLogger() && allPassed;
  allPassed = checkPythonLogger() && allPassed;
  allPassed = checkShellLogger() && allPassed;
  allPassed = checkEnvironmentBootstrap() && allPassed;

  console.log("\n" + "=".repeat(50));

  if (allPassed && errors.length === 0) {
    console.log("✅ All logging checks passed!");
    process.exit(0);
  } else {
    console.log("❌ Logging checks failed with the following errors:");
    errors.forEach((error, index) => {
      console.log(`  ${index + 1}. ${error}`);
    });
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  checkRequiredFiles,
  checkNodeLogger,
  checkPythonLogger,
  checkShellLogger,
  checkEnvironmentBootstrap,
  REQUIRED_SCHEMA_FIELDS,
  OPTIONAL_ROOT_FIELDS
};
