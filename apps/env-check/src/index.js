#!/usr/bin/env node

const { logger } = require('../../../tools/logging/node/logger');

const mode = process.argv[2] || "run";

const requiredVars = ["NODE_ENV", "UV_CACHE_DIR", "PNPM_HOME"];

function checkEnv() {
  const missing = requiredVars.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    logger.error({
      context: {
        missingVars: missing,
        requiredVars: requiredVars
      }
    }, `❌ Missing environment variables: ${missing.join(", ")}`);
    process.exit(1);
  }
  logger.info({
    context: {
      checkedVars: requiredVars,
      mode: mode
    }
  }, "✅ Environment variables are present.");
}

function main() {
  logger.info({
    context: {
      mode: mode,
      requiredVars: requiredVars
    }
  }, `env-check: mode=${mode}`);

  checkEnv();

  if (mode === "deploy") {
    logger.info({
      context: {
        mode: mode
      }
    }, "🚀 Deploy placeholder completed.");
  }
}

main();
