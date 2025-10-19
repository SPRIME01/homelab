#!/usr/bin/env node

const { existsSync } = require("node:fs");
const { resolve } = require("node:path");

const requiredFiles = [
  resolve(process.cwd(), "lib/env-loader.sh"),
  resolve(process.cwd(), "Justfile"),
  resolve(process.cwd(), "devbox.json"),
  resolve(process.cwd(), ".mise.toml"),
];

const missing = requiredFiles.filter((file) => !existsSync(file));

if (missing.length > 0) {
  console.error(`❌ Lint failed: missing files ${missing.join(", ")}`);
  process.exit(1);
}

console.log("✅ Lint stub passed (required files present).");
