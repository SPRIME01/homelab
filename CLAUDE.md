# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **security-hardened homelab infrastructure** repository that serves dual purposes:
1. **Working Infrastructure**: Production automation for managing a personal homelab
2. **Copier Template**: Reusable template for generating customized homelab projects

The project uses a fail-safe security model where all privileged operations require `HOMELAB=1` environment variable (auto-detected from `~/.config/sops/age/keys.txt` presence).

## Common Development Commands

### Testing (Dual Test System)

**Bash infrastructure tests** (exit code 2 = skip):
```bash
just ci-validate              # Justfile syntax + all bash tests
bash tests/run-tests.sh        # Run all 10 bash tests directly
```

**Python template tests** (requires devbox shell):
```bash
devbox shell                   # Activate Python 3.13.9 environment
pytest tests/python -q         # Run 4 Python test modules
exit                           # Leave devbox shell
```

**Full validation**:
```bash
just verify-all                # Runs bash + Python + Molecule tests
```

### Build Commands

```bash
# Nx monorepo builds
pnpm exec nx build homelab-types      # Build types library
pnpm exec nx build pulumi-bootstrap   # Build Pulumi infra
just nx-affected-build                # Build changed projects only
just nx-distributed-build             # Distributed build (requires HOMELAB=1 + agents)

# Pulumi operations
just pulumi-preview                   # Preview changes
HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-up    # Deploy (requires confirmation)
```

### Lint/Validate Commands

```bash
just --justfile --check              # Validate justfile syntax
just sops-validate                   # Check .sops.yaml schema
just nx-validate                     # Workspace validation
pnpm exec nx graph                   # Visualize task graph
just ansible-lint                    # Lint Ansible playbooks
```

### Environment Setup

```bash
mise install                         # Install pinned tools (node 22.17.0, python 3.13.9, etc.)
pnpm install                         # Prepare monorepo packages
direnv allow                         # Trust .envrc for HOMELAB auto-detection
just detect-homelab                  # Confirm SOPS/age key detection
```

## High-Level Architecture

### Security Guard Pattern (Everywhere)

All privileged operations follow this pattern:

```bash
if [ "${HOMELAB:-0}" != "1" ]; then
  echo "Refusing to <action>: HOMELAB != 1" >&2
  exit 1
fi
```

**Auto-detection** (.envrc): Sets `HOMELAB=1` when `~/.config/sops/age/keys.txt` exists. Defaults to `HOMELAB=0` on dev machines.

**Deployment confirmation**:
- Interactive: Type "deploy" when prompted
- Non-interactive: `DEPLOY_CONFIRM=yes`
- Dry-run: `DRY_RUN=1` (preview without execution)

### Directory Structure

```
homelab/
├── docs/                    # Diataxis-framed documentation (28 files)
│   ├── Explanations/        # Architecture, security model concepts
│   ├── Howto/              # Step-by-step guides (11 guides)
│   ├── Reference/          # Tables, APIs, environment variables
│   └── Tutorials/          # Progressive learning paths
│
├── infra/                   # Infrastructure code and encrypted secrets
│   ├── ansible-bootstrap/  # Ansible playbooks, inventory, roles, molecule tests
│   ├── pulumi-bootstrap → # Symlink to packages/pulumi-bootstrap
│   └── *.sops             # Encrypted secrets (tailscale.env.sops, etc.)
│
├── packages/                # Nx monorepo packages
│   ├── homelab-types/      # Branded types library (@homelab/types)
│   └── pulumi-bootstrap/   # Pulumi infrastructure code
│
├── tests/                   # Test suites (bash + Python)
│   ├── *.sh                # 10 bash infrastructure tests
│   ├── run-tests.sh        # Test runner (exit 2 = skip)
│   └── python/             # 4 pytest test modules
│
├── scripts/                 # Bootstrap and utility scripts
├── hooks/                   # Copier template hooks
├── extensions/              # Jinja2 template extensions
├── justfile                 # 61 recipes for all operations
├── copier.yml              # Template definition with 23 validators
└── nx.json                 # Nx monorepo configuration
```

### Key Architectural Patterns

**Branded Types** (TypeScript/Python): Type-safe strings for security-sensitive values
```typescript
type AgeRecipient = string & { readonly __brand: 'AgeRecipient' };
type TailscaleIP = string & { readonly __brand: 'TailscaleIP' };
type SOPSFilePath = string & { readonly __brand: 'SOPSFilePath' };
```

**Dual Test System**:
- Bash: Infrastructure guards (exit code 2 = skip when deps missing)
- Python: Template validation (pytest-based)

**Tool Version Pinning** (.mise.toml): All tool versions are pinned (node 22.17.0, python 3.13.9, pulumi 3.207.0, nx 22.0.3, pnpm 10.22.0)

**Template-Project Duality**: The repository is both working infrastructure and a Copier template. The `template/` directory symlinks to root for generation.

**Nx Monorepo**: Cache in `~/.local/state/nx-cache`, parallel=3, daemon enabled. Distributed agents across Tailscale network with encrypted config.

**SOPS Encryption**: Encrypted secrets in `*.sops` files with double recipient setup (CI + personal). Path regex matching in `.sops.yaml`.

### Critical Guards (Never Bypass)

1. **HOMELAB environment**: All destructive operations require `HOMELAB=1`
2. **Deployment confirmation**: `DEPLOY_CONFIRM=yes` or interactive typing
3. **Dry-run support**: `DRY_RUN=1` for preview without execution
4. **Tailscale verification**: `REQUIRE_TAILSCALE=1` enforces VPN connectivity

### Test Exit Code Convention

- `0` = pass
- `1` = fail
- `2` = **skip** (allows CI to pass when optional deps missing)

Example skip pattern:
```bash
if [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then
  echo "SKIP: no homelab key" >&2
  exit 2
fi
```

### SOPS Encryption Pattern

```bash
# Encrypt (always use --input-type/--output-type for .env files)
sops --encrypt --input-type dotenv --output-type dotenv --age "$AGE_RECIPIENT" \
  infra/example.env > infra/example.env.sops

# Decrypt (requires ~/.config/sops/age/keys.txt)
sops --decrypt --input-type dotenv --output-type dotenv infra/example.env.sops

# Edit in-place (decrypts → $EDITOR → re-encrypts)
sops infra/example.env.sops
```

### Copier Template System

Generate new projects:
```bash
pip install copier
copier copy gh:SPRIME01/homelab my-homelab \
  -d project_name=my-homelab \
  -d admin_email=you@example.com \
  -d enable_pulumi=true \
  -d enable_ansible=true \
  -d enable_nx_distributed=false
```

Key files: `copier.yml` (23 validators), `hooks/pre_copy.py`, `hooks/post_copy.sh`, `extensions/validators.py`

### Adding New Infrastructure

1. Add guarded `just` recipe with `HOMELAB` check and `DRY_RUN` support
2. Create TDD test in `tests/` validating guard behavior (mock external deps)
3. Document required secrets in `infra/example.<tool>.env` (encrypt to `.sops`)
4. Update `.sops.yaml` with path regex for new encrypted files
5. Add documentation in appropriate `docs/` section

### Important Constraints

- Never bypass the guard pattern `if [ "${HOMELAB:-0}" != "1" ]; then ...; fi`
- Mock external dependencies (Tailscale, Pulumi backends, Nx agents) in tests
- Run both test systems before PRs: `just ci-validate` and `devbox shell && pytest tests/python -q`
- When modifying Copier template, update validators in `copier.yml` AND `hooks/pre_copy.py`
- Document workflows in appropriate Diataxis section (Tutorial/How-to/Reference/Explanation)
