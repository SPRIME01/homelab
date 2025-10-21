# Quick environment setup (homelab)

This file contains the minimal copy-paste commands to get a development shell matching CI.

1) Install Devbox tools (one-time):

```bash
devbox install --tidy-lockfile
```

2) Allow direnv (local only):

```bash
direnv allow
```

3) Create a project `.venv` (uv-managed if available):

```bash
# If devbox+uv are available inside your shell
devbox run bash -lc "uv python install 3.12 || true; uv venv .venv --python 3.12 || python3 -m venv .venv"
# or fallback
python3 -m venv .venv
source .venv/bin/activate
```

4) Run a quick smoke check (lint + tests):

```bash
just env-check
```

Notes:
- CI uses `./lib/env-loader.sh ci` (no direnv). Workflows persist the venv via `$GITHUB_ENV` / `$GITHUB_PATH` so subsequent steps inherit the environment.
- Avoid auto-spawning `devbox shell` from `.envrc`; we evaluate devbox's direnv snippet into the current shell instead.

## Environment Override Patterns for Debugging

### Logging Overrides

The observability stack can be controlled using environment variables for debugging and offline development:

#### Disable Observability

To disable log forwarding to OpenObserve and metrics collection:

```bash
# Disable observability for a single command
HOMELAB_OBSERVE=0 npx nx run env-check:test

# Disable observability for the current shell session
export HOMELAB_OBSERVE=0
npx nx run env-check:test
```

#### Change Log Target

To force logs to stdout instead of Vector:

```bash
# Force stdout logging for a single command
HOMELAB_LOG_TARGET=stdout npx nx run env-check:test

# Force stdout logging for the current shell session
export HOMELAB_LOG_TARGET=stdout
npx nx run env-check:test
```

#### Adjust Log Levels

To control log verbosity:

```bash
# Set debug level logging
HOMELAB_LOG_LEVEL=debug npx nx run env-check:test

# Set error level only
HOMELAB_LOG_LEVEL=error npx nx run env-check:test
```

#### Sampling Controls

To control log sampling in production-like environments:

```bash
# Sample 25% of debug logs
HOMELAB_LOG_SAMPLE_DEBUG=0.25 npx nx run env-check:test

# Sample 50% of info logs
HOMELAB_LOG_SAMPLE_INFO=0.5 npx nx run env-check:test

# Disable sampling for all logs
HOMELAB_LOG_SAMPLE_DEBUG=1.0 HOMELAB_LOG_SAMPLE_INFO=1.0 npx nx run env-check:test
```

### Development Overrides

#### Service Identity

To override default service identification:

```bash
# Set custom service name
HOMELAB_SERVICE=my-service npx nx run env-check:test

# Set custom environment
HOMELAB_ENVIRONMENT=local-dev npx nx run env-check:test

# Set custom version
HOMELAB_VERSION=1.2.3 npx nx run env-check:test
```

#### Endpoint Overrides

To point to different observability endpoints:

```bash
# Override OpenObserve endpoint
OPENOBSERVE_ENDPOINT=http://localhost:6080 npx nx run env-check:test

# Override GreptimeDB endpoint
GREPTIMEDB_ENDPOINT=http://localhost:5000 npx nx run env-check:test

# Override Vector ports
VECTOR_OTLP_GRPC_PORT=5317 VECTOR_OTLP_HTTP_PORT=5318 npx nx run env-check:test
```

### Common Debugging Scenarios

#### Offline Development

For development without network connectivity:

```bash
# Disable observability and force local output
HOMELAB_OBSERVE=0 HOMELAB_LOG_TARGET=stdout npx nx run env-check:test

# Or using the Just command
just env-check-offline
```

#### Log Inspection

To inspect logs without forwarding:

```bash
# Enable verbose logging to stdout
HOMELAB_LOG_LEVEL=debug HOMELAB_LOG_TARGET=stdout npx nx run env-check:test | jq .

# Tail logs with pretty formatting
devbox run log-tail
```

#### Performance Testing

To test performance without observability overhead:

```bash
# Disable all logging features
HOMELAB_OBSERVE=0 HOMELAB_LOG_LEVEL=error npx nx run env-check:test

# Or with minimal logging
HOMELAB_OBSERVE=0 HOMELAB_LOG_LEVEL=warn npx nx run env-check:test
```

#### Integration Testing

To test with specific observability configurations:

```bash
# Test with staging endpoints
HOMELAB_ENVIRONMENT=staging \
OPENOBSERVE_ENDPOINT=https://logs-staging.example.com \
GREPTIMEDB_ENDPOINT=https://metrics-staging.example.com \
npx nx run env-check:test

# Test with debug sampling
HOMELAB_LOG_SAMPLE_DEBUG=1.0 HOMELAB_LOG_SAMPLE_INFO=1.0 npx nx run env-check:test
```

### Just Command Shortcuts

The project includes convenient Just commands for common debugging scenarios:

```bash
# Run env-check with observability disabled
just env-check-offline

# Run env-check with debug logging
just env-check-debug

# Run env-check with stdout logging
just env-check-stdout

# Run full observability stack test
just observability-test

# Tail Vector logs
just log-tail

# Validate Vector configuration
just vector-validate
```

### Environment Precedence

Environment variables are evaluated in the following order (highest to lowest priority):

1. Command-line environment variables (e.g., `HOMELAB_OBSERVE=0 command`)
2. Shell environment variables (e.g., `export HOMELAB_OBSERVE=0`)
3. `.env` files in the project directory
4. Default values in `lib/env-loader.sh`

### Troubleshooting

#### Verify Current Settings

To check the current environment settings:

```bash
# Show all HOMELAB_* variables
env | grep HOMELAB_

# Show logging configuration
env | grep -E "(HOMELAB_LOG|VECTOR|OPENOBSERVE|GREPTIME)"

# Check if Vector is running
pgrep -f vector || echo "Vector is not running"
```

#### Reset to Defaults

To reset environment to default values:

```bash
# Clear all HOMELAB_* variables
for var in $(env | grep HOMELAB_ | cut -d= -f1); do
  unset "$var"
done

# Reload environment
source lib/env-loader.sh
```

#### Test Observability Flow

To test the complete observability flow:

```bash
# Start observability stack
just observability-start

# Run test with logging
npx nx run env-check:test

# Check logs in OpenObserve
curl -s "http://localhost:5080/api/search?q=service:env-check" | jq .

# Check metrics in GreptimeDB
curl -s "http://localhost:4000/v1/sql" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM metrics WHERE name = \"response_time\" LIMIT 10"}' | jq .

# Stop observability stack
just observability-stop
```
