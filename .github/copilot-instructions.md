# Copilot Instructions for Homelab Project

## Project Architecture

This is a **security-hardened homelab infrastructure** with strict access controls. The core principle: **all privileged operations require `HOMELAB=1` environment variable** (auto-detected from `~/.config/sops/age/keys.txt` presence) or active Tailscale SSH connectivity.

**Key directories:**
- `infra/` — encrypted secrets (`.sops` files), Tailscale ACL configs
- `scripts/` — bootstrap helpers for age/SOPS/Tailscale setup
- `tests/` — bash-based TDD tests with exit code `2` = skip
- `docs/` — comprehensive setup guides (Tailscale, SOPS, Automation)

**Guard rail pattern (enforced everywhere):**
```bash
if [ "${HOMELAB:-0}" != "1" ]; then
  echo "Refusing to <action>: HOMELAB != 1" >&2
  exit 1
fi
```

## Critical Developer Workflows

### Running Tests (Dual Test System)
This project has **two complementary test systems**:

**1. Bash-based infrastructure tests** (for guards, SOPS, Tailscale):
```bash
bash tests/run-tests.sh  # Runs all bash tests; treats exit code 2 as "skipped"
just ci-validate         # CI target: validates justfile syntax + runs bash tests
```

**2. Python-based template tests** (for Copier template validation):
```bash
devbox shell             # Activates reproducible Python 3.13.9 + pytest env
pytest tests/python -q   # Runs Python tests for hooks/validators/template generation
exit                     # Leaves devbox shell
```

**VSCode tasks available**:
- "Verify JS tests" → `pnpm vitest` (runs vitest for TypeScript packages)
- "Verify Python tests" → `pytest tests/python` (runs Python template tests)
- "Verify Molecule" → `HOMELAB=1 just ansible-molecule-test` (Ansible validation)
- "Verify All" → Runs all three test suites in sequence

**Test structure (10 bash + 4 Python test suites):**
```
tests/
# Bash infrastructure tests (exit codes: 0=pass, 1=fail, 2=skip)
├── 01_non_homelab_decrypt.sh          # SOPS guard behavior (HOMELAB=0)
├── 02_sops_yaml_schema.sh             # .sops.yaml validation
├── 03_round_trip_homelab.sh           # Encrypt/decrypt cycle
├── 04_just_safety_guards.sh           # Justfile guard validation
├── 05_tailscale_ssh_guards.sh         # Tailscale SSH transport (mocked)
├── 06_pulumi_project_validation.sh    # Pulumi strict mode, branded types
├── 07_ansible_molecule_validation.sh  # Ansible structure validation
├── 08_infra_guards.sh                 # Infra recipe guards
├── 09_tailscale_ssh_verification.sh   # SSH config validation
├── 10_nx_distributed_validation.sh    # Nx monorepo structure, guards
└── run-tests.sh                       # Test runner (treats exit 2 as skip)

# Python template tests (pytest-based, run via devbox shell)
└── python/
    ├── conftest.py                    # Pytest configuration & fixtures
    ├── test_pre_copy.py               # Validates hooks/pre_copy.py validators
    ├── test_validators.py             # Validates extensions/validators.py filters
    └── test_template_generation.py    # End-to-end Copier template generation
```

**Exit code convention:**
- `0` = pass (green in CI)
- `1` = fail (red, blocks merge)
- `2` = **skip** (yellow, allows CI to pass when optional deps missing)

**Example skip pattern (for tests requiring homelab keys):**
```bash
if [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then
  echo "SKIP: no homelab key, cannot test decryption" >&2
  exit 2
fi
```

**Mock external deps in tests:**
```bash
# tests/05_tailscale_ssh_guards.sh pattern:
TMPDIR="$(mktemp -d)"
cat > "$TMPDIR/tailscale" << 'MOCK'
#!/usr/bin/env bash
echo "100.64.0.10"  # Fake Tailscale IP
MOCK
chmod +x "$TMPDIR/tailscale"
export PATH="$TMPDIR:$PATH"  # Mock tailscale CLI
```

### Secrets Management (SOPS + age)
```bash
# Encrypt (always use --input-type/--output-type for .env files)
sops --encrypt --input-type dotenv --output-type dotenv --age "$AGE_RECIPIENT" infra/example.env > infra/example.env.sops

# Decrypt (requires ~/.config/sops/age/keys.txt)
sops --decrypt --input-type dotenv --output-type dotenv infra/example.env.sops

# Test pattern: skip if no homelab key
if [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then
  echo "SKIP: ..." >&2
  exit 2
fi
```

**Never commit plaintext secrets.** Only `.sops` encrypted files belong in the repo.

### Justfile Recipes (all guarded)
```bash
just deploy                    # Interactive confirmation required + HOMELAB=1
DEPLOY_CONFIRM=yes just deploy # Non-interactive (CI/scripts)
DRY_RUN=1 just deploy          # Preview without execution

just tailscale-ssh-enable      # Requires HOMELAB=1
just tailscale-join            # Decrypts infra/tailscale.env.sops and joins tailnet
```

### Environment Detection
`.envrc` (via direnv) auto-sets `HOMELAB=1` when `~/.config/sops/age/keys.txt` exists. Run `direnv allow` after modifying `.envrc`.

> **Devbox note:** the current `.envrc` only marks Devbox as available and exposes `devbox-shell`; you still need to run `devbox shell` manually before using Devbox-managed tools (pytest, `uv` installs, etc.), so the host shell stays predictable.

## Project-Specific Conventions

### Test Exit Codes
- `0` = pass
- `1` = fail
- `2` = **skip** (tool not installed, or homelab key missing)

Exit 2 allows CI to pass when optional deps aren't present.

### SOPS Path Regex Matching
`.sops.yaml` `path_regex` matches against the **filename passed to SOPS**, not absolute paths. Pattern:
```yaml
path_regex: '.*infra/.*\.(yaml|json|env)\.sops$'
```

### Tailscale SSH Transport
- **WSL2**: Uses Windows host's Tailscale instance (no local daemon)
- **Homelab nodes**: Run `tailscaled` and enable SSH via `just tailscale-ssh-enable`
- **Dev machines**: Join tailnet for connectivity only (no SSH server)

### Shell Strictness
All bash scripts and `justfile` recipes use `set -euo pipefail` for fail-fast behavior. Never suppress errors with `|| true` unless explicitly safe.

## Integration Points & External Dependencies

### Tool Pinning (.mise.toml)
Versions are **pinned from Context7 MCP lookups** or GitHub releases API:
- `node = "22.17.0"`
- `python = "3.13.9"`
- `pulumi = "3.207.0"`

When adding tools, query Context7 MCP for authoritative versions before pinning.

### GitHub Actions CI
- `.github/workflows/ci-validate.yml` — validates `just` syntax + runs tests
- `.github/workflows/sops-ci.yml` — decrypts secrets using `SOPS_AGE_KEY` secret

CI private key is stored in GitHub secret `SOPS_AGE_KEY`. Restore it with:
```yaml
mkdir -p "$HOME/.config/sops/age"
echo "${{ secrets.SOPS_AGE_KEY }}" > "$HOME/.config/sops/age/keys.txt"
chmod 600 "$HOME/.config/sops/age/keys.txt"
```

### No Sudo Policy
**Only exception:** Installing `tailscaled` system service on Windows host or homelab nodes. Everything else is user-local (`$HOME/.local/bin`).

### Generating Config Files
Use tool-specific init commands to generate config files, then modify as needed. For example:

```bash mise config generate > .mise.toml
mise config generate > .mise.toml
devbox init > devbox.json
```
Generate all config files using tool inti command to limit the surface for halucination then modify the generated files as needed.

## Common Pitfalls

1. **SOPS fails with "invalid character"**: Add `--input-type dotenv --output-type dotenv` for `.env` files
2. **Test hangs in CI**: Check if test exits 2 (skip) properly when deps missing
3. **`just deploy` blocked**: Ensure `HOMELAB=1` and `DEPLOY_CONFIRM=yes` are set
4. **Encrypted file won't decrypt**: Verify `~/.config/sops/age/keys.txt` exists with `chmod 600` and matches `.sops.yaml` recipients
5. **Tailscale commands fail**: In WSL2, ensure Windows host has Tailscale running; use `wsl-tailscale-ip` to discover IP

## Infrastructure-as-Code Patterns (Pulumi/Ansible)

### Pulumi (TypeScript)
**Required structure:**
```typescript
// infra/pulumi-bootstrap/index.ts
import * as pulumi from "@pulumi/pulumi";

// MUST use branded types for all resource identifiers
type StackName = string & { readonly __brand: 'StackName' };
type ResourceID = string & { readonly __brand: 'ResourceID' };

// ALWAYS gate privileged operations
const config = new pulumi.Config();
const homelabFlag = config.get("homelab") || "0";
if (homelabFlag !== "1") {
  throw new Error("Refusing Pulumi operations: HOMELAB != 1");
}

// Export typed outputs (no raw strings)
export const outputs: Record<string, pulumi.Output<string>> = {
  clusterEndpoint: cluster.endpoint,
  kubeconfig: cluster.kubeconfig,
};
```

**Mandatory conventions:**
- All stack configs in `infra/<project>/Pulumi.<stack>.yaml` encrypted via SOPS
- No hardcoded credentials (use `pulumi.Config.requireSecret()`)
- DRY_RUN simulation via `pulumi preview` (never deploy without preview)
- Tag all resources with `homelab:managed=true`

### Ansible (Python inventory plugins + Tailscale SSH)
**Required `ansible.cfg`:**
```ini
[defaults]
transport = ssh
inventory = inventory/
roles_path = roles/
host_key_checking = False

[ssh_connection]
# Force Tailscale SSH (must fail if Tailscale unavailable)
ssh_executable = tailscale ssh
pipelining = True
```

**Inventory structure** (must use `inventory/` dir, not flat files):
```yaml
# inventory/homelab.yml (encrypted via SOPS)
all:
  vars:
    ansible_user: "{{ lookup('env', 'USER') }}"
    homelab_flag: "{{ lookup('env', 'HOMELAB') }}"
  children:
    homelab_nodes:
      hosts:
        node1:
          ansible_host: 100.64.0.10  # Tailscale IP only
          tags: ['tag:homelab-wsl2']
```

**Playbook safety pattern:**
```yaml
# playbooks/deploy.yml
- name: Verify HOMELAB guard before ANY task
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Check HOMELAB environment variable
      fail:
        msg: "Refusing to run: HOMELAB != 1"
      when: lookup('env', 'HOMELAB') != '1'

    - name: Verify Tailscale connectivity
      command: tailscale status --json
      register: tailscale_status
      failed_when: tailscale_status.rc != 0
      changed_when: false
```

**Python inventory plugins (typed):**
```python
# inventory/plugins/homelab_nodes.py
from typing import Protocol, NewType
from ansible.plugins.inventory import BaseInventoryPlugin

TailscaleIP = NewType('TailscaleIP', str)

class TailscaleNode(Protocol):
    hostname: str
    tailscale_ip: TailscaleIP
    tags: list[str]

class HomelabInventoryPlugin(BaseInventoryPlugin):
    NAME = 'homelab_nodes'

    def verify_file(self, path: str) -> bool:
        # Only load if HOMELAB=1
        import os
        return os.environ.get('HOMELAB') == '1'
```

## When Adding New Infrastructure

1. **Add guarded `just` recipe** with `HOMELAB` check and `DRY_RUN` support
2. **Create TDD test** in `tests/` validating guard behavior (use mocked shims like `tests/05_tailscale_ssh_guards.sh`)
3. **Document required secrets** in `infra/example.<tool>.env` (encrypt to `.sops`)
4. **Update `.sops.yaml`** with path regex for new encrypted files
5. **Add to `docs/Infra Toolkit.md`** with manual setup steps for humans
6. **For Pulumi**: Add stack-specific config encryption rules, test preview mode
7. **For Ansible**: Add molecule tests (if applicable), verify Tailscale SSH transport

## Example: Adding a New Guarded Command

```bash
# In justfile:
my-infra-action:
	bash -lc 'set -euo pipefail; \
	if [ "${HOMELAB:-0}" != "1" ]; then \
	  echo "Refusing: HOMELAB != 1" >&2; exit 1; \
	fi; \
	if [ "${DRY_RUN:-0}" = "1" ]; then \
	  echo "DRY RUN: would run action"; exit 0; \
	fi; \
	echo "Running real action"'

# Test in tests/06_my_infra_guards.sh:
if HOMELAB=0 just my-infra-action >/dev/null 2>&1; then
  echo "FAIL: succeeded with HOMELAB=0" >&2; exit 1
fi

if ! HOMELAB=1 DRY_RUN=1 just my-infra-action | grep -q "DRY RUN"; then
  echo "FAIL: DRY_RUN not respected" >&2; exit 1
fi
```

## Nx Monorepo & Distributed Builds

This project uses **Nx 22.0.3 + pnpm 10.22.0** for distributed task execution across Tailscale-networked machines.

### Architecture
```
packages/
├── homelab-types/       # Branded types library (@homelab/types)
│   ├── src/index.ts     # TailscaleIP, SOPSFilePath, AgeRecipient, HomelabFlag
│   └── project.json     # Nx project config (@nx/js:tsc executor)
└── pulumi-bootstrap/    # Migrated from infra/ (symlinked for compat)
    ├── index.ts         # Infrastructure code importing @homelab/types
    └── project.json     # Nx build target
```

**Key files:**
- `nx.json` — Cache in `~/.local/state/nx-cache` (XDG_STATE_HOME pattern), parallel=3, daemon enabled
- `pnpm-workspace.yaml` — Packages: `['packages/*', 'infra/*']` (allows legacy infra/ projects)
- `tsconfig.base.json` — Strict mode + path mappings for `@homelab/*` packages
- `.nxignore` — Excludes `**/*.sops`, `**/*.env`, `.envrc` from task graph

### Build Commands
```bash
# Build specific project
pnpm exec nx build homelab-types
pnpm exec nx build pulumi-bootstrap

# Build all affected by changes
just nx-affected-build

# Distributed build (requires HOMELAB=1 + agents configured)
DEPLOY_CONFIRM=yes just nx-distributed-build
```

### Distributed Agent Workflow
**Bootstrap (one-time setup):**
```bash
# Generate shared secret (256-bit)
bash scripts/generate-nx-agent-secret.sh

# Configure agents (copy from docs/Reference/example.nx-agents.env)
# infra/nx-agents.env:
#   NX_SHARED_SECRET=<hex-token>
#   NX_AGENT_IPS=100.64.0.10,100.64.0.11  # Tailscale IPs

# Encrypt config
export AGE_RECIPIENT="age1ml9z356pnzxgjs8x96ngtzycfvxr4yuxq7qnqs5f2eperevgfupsvue8jl"
just nx-encrypt-config

# Start cache server (HTTP on port 3333)
just nx-cache-server-start

# Start agent on each machine
just nx-start-agent  # Decrypts infra/nx-agents.env.sops, starts background agent
```

**Critical patterns:**
- **Agent discovery**: Static list via `NX_AGENT_IPS` in encrypted config (see `just nx-discover-agents` for Tailscale IP detection)
- **Cache backend**: Local HTTP initially (`npx http-server ~/.local/state/nx-cache --port 3333`), migrate to NFS/S3 for >10 agents
- **Fallback behavior**: Nx automatically falls back to local execution if agents unreachable
- **Health monitoring**: `scripts/nx-agent-health-monitor.sh` checks Tailscale/cache/agent, restarts via `scripts/nx-agent-restart.sh`
- **Systemd integration**: `scripts/nx-cache.service` for persistent cache server (`systemctl --user enable`)

**Adding new projects to monorepo:**
1. Create `packages/<name>/project.json` with `@nx/js:tsc` executor
2. Add `tsconfig.json` (extends `../../tsconfig.base.json`) and `tsconfig.lib.json` (compilation)
3. Update `tsconfig.base.json` paths: `"@homelab/<name>": ["packages/<name>/src/index.ts"]`
4. Set `outDir: ../../dist/packages/<name>` in `tsconfig.lib.json` for task outputs
5. Build with `nx build <name>` (never use `tsc` directly)

### Migration Pattern (infra/ → packages/)
When moving legacy projects into Nx:
1. **Create packages/<name>** with proper Nx project structure
2. **Symlink old location**: `ln -s ../packages/<name> infra/<name>` (backward compatibility)
3. **Update imports**: Change relative paths to `@homelab/<name>` aliases
4. **Validate builds**: Run `nx build <name>` and ensure dist/ outputs correct
5. **Update justfile recipes**: Keep existing recipes working via symlink

**Example from this repo:**
```bash
# Pulumi was migrated from infra/pulumi-bootstrap → packages/pulumi-bootstrap
# Old path still works via symlink for gradual migration
ls -la infra/pulumi-bootstrap  # → ../packages/pulumi-bootstrap
```

## Copier Template System

This repository **doubles as a Copier template** for generating customized homelab projects. Key files:

**Template definition:**
- `copier.yml` — Template metadata, questions (23 validators), conditional exclusions, post-gen tasks
- `template/` — Source files with `.j2` Jinja templates (renders to target project)
- `hooks/pre_copy.py` — Pre-generation validation (project_name, email, semver, npm_scope)
- `hooks/post_copy.sh` — Post-generation setup (chmod +x scripts, create placeholders)
- `extensions/validators.py` — Custom Jinja filters for template validation

**Critical patterns:**
- All user-facing prompts have **inline validators** in `copier.yml` (regex-based)
- Python hooks provide **secondary validation** via `hooks/pre_copy.py` (runs before file copy)
- Conditional exclusions based on feature flags: `enable_pulumi`, `enable_ansible`, `enable_nx_distributed`
- Template testing via `pytest tests/python/test_template_generation.py` (requires devbox shell)

**Generate a new project from this template:**
```bash
pip install copier
copier copy gh:SPRIME01/homelab my-homelab \
  -d project_name=my-homelab \
  -d admin_email=you@example.com \
  -d enable_pulumi=true \
  -d enable_ansible=true \
  -d enable_nx_distributed=false
```

**Modifying the template (workflow):**
1. Edit files in `template/` (use `.j2` suffix for Jinja templates)
2. Add validators to `copier.yml` or `hooks/pre_copy.py` for new questions
3. Test with `devbox shell && pytest tests/python -q` (validates hooks + generation)
4. Test generated project with `just copier-validate` (full end-to-end)
5. Update `README.md` and `docs/Reference/Template-Testing.md`

## Key Documentation References

- **`docs/Secrets Management.md`** — SOPS/age workflow, backup, rotation
- **`docs/Tailscale.md`** — Complete Tailscale SSH setup walkthrough
- **`docs/Automation.md`** — Justfile guard patterns, HOMELAB detection
- **`docs/Nx Distributed Agents.md`** — Distributed builds, agent setup, troubleshooting
- **`justfile`** — All recipes with embedded guard logic (33 recipes: 21 infra + 12 Nx)
- **`.envrc`** — Auto-detection of homelab environment
- **`.sops.yaml`** — Encryption rules for `infra/` files (includes `infra/nx.*\.sops$`)
- **`copier.yml`** — Template definition with 23 inline validators
- **`pytest.ini`** — Python test configuration (testpaths, maxfail, warnings)

## Type Safety Requirements (Strict)

### TypeScript (tsconfig.json: strict mode required)
**Mandatory patterns:**
- **Branded types for all security-sensitive strings** (age keys, auth tokens, file paths):
  ```typescript
  type AgeRecipient = string & { readonly __brand: 'AgeRecipient' };
  type SOPSFilePath = string & { readonly __brand: 'SOPSFilePath' };
  type TailscaleAuthKey = string & { readonly __brand: 'TailscaleAuthKey' };

  function validateAgeRecipient(raw: string): AgeRecipient {
    if (!/^age1[a-z0-9]{58}$/.test(raw)) {
      throw new Error(`Invalid age recipient: ${raw}`);
    }
    return raw as AgeRecipient;
  }
  ```
- **Discriminated unions for command results**:
  ```typescript
  type CommandResult<T> =
    | { status: 'success'; data: T }
    | { status: 'error'; error: Error; exitCode: number }
    | { status: 'skipped'; reason: string };
  ```
- **Readonly by default**: Use `readonly` for all array/object properties unless mutation is required
- **No `any` or `unknown` without explicit type guards**: Every `unknown` must have a runtime validator

### Python (3.11+, use typing.Protocol and TypeGuard)
**Mandatory patterns:**
- **NewType for security-sensitive values**:
  ```python
  from typing import NewType, TypeGuard, Literal

  AgeRecipient = NewType('AgeRecipient', str)
  SOPSFilePath = NewType('SOPSFilePath', str)

  def is_age_recipient(value: str) -> TypeGuard[AgeRecipient]:
      import re
      return bool(re.match(r'^age1[a-z0-9]{58}$', value))

  def validate_age_recipient(raw: str) -> AgeRecipient:
      if not is_age_recipient(raw):
          raise ValueError(f"Invalid age recipient: {raw}")
      return AgeRecipient(raw)
  ```
- **Protocols for structural typing**:
  ```python
  from typing import Protocol

  class Encryptable(Protocol):
      def encrypt(self, recipient: AgeRecipient) -> bytes: ...
      def decrypt(self, identity_path: SOPSFilePath) -> bytes: ...
  ```
- **TypedDict with total=True for configs**:
  ```python
  from typing import TypedDict, Required, NotRequired

  class SOPSConfig(TypedDict, total=True):
      path_regex: Required[str]
      age: Required[list[str]]
      encrypted_suffix: NotRequired[str]  # Optional with explicit marker
  ```
- **Literal types for enums/constants**:
  ```python
  ExitCode = Literal[0, 1, 2]  # pass, fail, skip
  HomelabFlag = Literal[0, 1]
  ```

**Forbidden:**
- ❌ Raw `str` for file paths, secrets, or credentials
- ❌ `Any` type (use `object` or explicit unions)
- ❌ Mutable default arguments (`def func(items: list = [])`)
- ❌ Type comments (`# type: ignore`) without JIRA ticket reference

## Day-to-Day Development Patterns

### Adding a New TypeScript Package
```bash
# 1. Create package structure
mkdir -p packages/my-package/src
cd packages/my-package

# 2. Create project.json (Nx config)
cat > project.json << 'EOF'
{
  "name": "my-package",
  "sourceRoot": "packages/my-package/src",
  "projectType": "library",
  "targets": {
    "build": {
      "executor": "@nx/js:tsc",
      "outputs": ["{options.outputPath}"],
      "options": {
        "outputPath": "dist/packages/my-package",
        "main": "packages/my-package/src/index.ts",
        "tsConfig": "packages/my-package/tsconfig.lib.json"
      }
    }
  }
}
EOF

# 3. Create tsconfig files (extend root, set outDir)
# tsconfig.json references tsconfig.lib.json
# tsconfig.lib.json extends ../../tsconfig.base.json with outDir: ../../dist/packages/my-package

# 4. Update tsconfig.base.json paths
# Add: "@homelab/my-package": ["packages/my-package/src/index.ts"]

# 5. Build and validate
pnpm exec nx build my-package
just ci-validate
```

### Working with Encrypted Secrets
```bash
# View encrypted file (requires HOMELAB=1)
sops -d --input-type dotenv --output-type dotenv infra/tailscale.env.sops

# Edit in-place (decrypts → $EDITOR → re-encrypts)
sops infra/tailscale.env.sops

# Add new encrypted file
cp docs/Reference/example.env infra/my-service.env
vim infra/my-service.env  # Fill values
export AGE_RECIPIENT="age1ml9z356pnzxgjs8x96ngtzycfvxr4yuxq7qnqs5f2eperevgfupsvue8jl"
sops --encrypt --input-type dotenv --output-type dotenv \
  --age "$AGE_RECIPIENT" infra/my-service.env > infra/my-service.env.sops
rm infra/my-service.env  # Never commit plaintext
git add infra/my-service.env.sops
```

### Debugging Infrastructure Changes
```bash
# 1. Always preview first (DRY_RUN or tool-native preview)
HOMELAB=1 DRY_RUN=1 just pulumi-up        # Shows intended changes
HOMELAB=1 just pulumi-preview             # Pulumi native preview

# 2. Test with single-node subset first
HOMELAB=1 DEPLOY_CONFIRM=yes just ansible-ping  # Validate connectivity

# 3. Apply incrementally with check mode
HOMELAB=1 just ansible-check              # Ansible dry-run

# 4. Full deploy only after validation
HOMELAB=1 DEPLOY_CONFIRM=yes just ansible-deploy

# 5. Verify with distributed build
DEPLOY_CONFIRM=yes just nx-affected-build  # Only changed projects
```

### Common TDD Workflow (Adding New Feature)
```bash
# 1. Create test file first
cat > tests/11_my_feature.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "Test: my-feature requires HOMELAB=1"
if HOMELAB=0 just my-feature >/dev/null 2>&1; then
  echo "FAIL: succeeded with HOMELAB=0" >&2
  exit 1
fi

echo "Test: my-feature supports DRY_RUN"
if ! HOMELAB=1 DRY_RUN=1 just my-feature | grep -q "DRY RUN"; then
  echo "FAIL: DRY_RUN not respected" >&2
  exit 1
fi

echo "my-feature validation passed"
exit 0
EOF
chmod +x tests/11_my_feature.sh

# 2. Add to test runner
# Edit tests/run-tests.sh: add "11_my_feature.sh" to tests array

# 3. Implement feature (test will fail first - RED)
# Edit justfile: add my-feature recipe with guards

# 4. Validate implementation (GREEN)
bash tests/11_my_feature.sh
just ci-validate

# 5. Document in appropriate docs/ file
```

## Quick Start for AI Agents

1. **Check context**: Is `HOMELAB=1` set? Are you on a trusted machine?
2. **Read the docs first**: Always check `docs/` for workflow details before modifying
3. **Use TDD**: Write tests in `tests/` before implementing features
4. **Mock external deps**: Use shims like `tests/05_tailscale_ssh_guards.sh` for network-dependent commands
5. **Preserve guard patterns**: Never bypass `HOMELAB` checks or remove `DRY_RUN` support
6. **Validate with `just ci-validate`** before committing

---

## Security Philosophy (Non-Negotiable)

This project operates under **zero-trust principles** for infrastructure automation:

### **Defense in Depth (Multiple Guard Layers)**
1. **Environment detection** (`.envrc` auto-sets `HOMELAB=1` only when `~/.config/sops/age/keys.txt` present)
2. **Explicit confirmation** (`DEPLOY_CONFIRM=yes` required for non-interactive)
3. **Dry-run validation** (`DRY_RUN=1` shows intended actions before execution)
4. **Network verification** (`REQUIRE_TAILSCALE=1` enforces VPN connectivity)

### **Fail-Safe Defaults**
- ❌ **No implicit trust**: Commands fail closed (error if `HOMELAB!=1`)
- ❌ **No silent failures**: Every error must be visible (`set -euo pipefail`)
- ❌ **No secrets in plaintext**: Only `.sops` encrypted files in repo
- ❌ **No sudo except Tailscale system service**: Everything else user-local
- ✅ **Explicit is better than implicit**: Require typed confirmation for destructive ops

### **Threat Model**
**Primary risks this design mitigates:**
1. Accidental deployment from dev laptop on public WiFi
2. Secrets leaked via git history or CI logs
3. Privilege escalation via compromised dependencies
4. Supply chain attacks (pinned versions, checksums required)
5. Lateral movement if one node compromised (ACL tags + least privilege)

**What this design does NOT protect against:**
- Physical access to homelab nodes (assume physical security)
- Compromise of the `~/.config/sops/age/keys.txt` private key itself
- Malicious code in pinned tool versions (trust GitHub/Context7 sources)

### **When Implementing Features**
**Ask yourself:**
1. Can this fail gracefully if `HOMELAB!=1`? (Test with `HOMELAB=0`)
2. Can this be previewed without side effects? (Implement `DRY_RUN=1`)
3. Can this be audited later? (Log actions, emit structured output)
4. Can this be recovered from failure? (Idempotent, retryable)
5. Can this be tested without live credentials? (Mock external services)

**If the answer to ANY of these is "no", the design is incomplete.**

---

**Remember:** This project prioritizes **security and fail-safety** over convenience. Every destructive action must be gated, tested, and documented. Convenience features that reduce safety are rejected by design.
