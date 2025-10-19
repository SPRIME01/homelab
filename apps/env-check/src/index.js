#!/usr/bin/env node

const mode = process.argv[2] || "run";

const requiredVars = ["NODE_ENV", "UV_CACHE_DIR", "PNPM_HOME"];

function checkEnv() {
  const missing = requiredVars.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    console.error(`❌ Missing environment variables: ${missing.join(", ")}`);
    process.exit(1);
  }
  console.log("✅ Environment variables are present.");
}

function main() {
  console.log(`env-check: mode=${mode}`);
  checkEnv();
  if (mode === "deploy") {
    console.log("🚀 Deploy placeholder completed.");
  }
}

main();
