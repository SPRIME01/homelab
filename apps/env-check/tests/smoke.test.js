#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const { resolve } = require("node:path");

const projectRoot = resolve(__dirname, "..");
const script = resolve(projectRoot, "src/index.js");

const child = spawnSync("node", [script, "test"], {
  stdio: "inherit",
  env: { ...process.env, NODE_ENV: process.env.NODE_ENV || "test" },
});

if (child.status !== 0) {
  console.error("❌ env-check smoke test failed.");
  process.exit(child.status ?? 1);
}

console.log("✅ env-check smoke test passed.");
