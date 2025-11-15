# Infrastructure Toolkit

This document lists the **manual setup steps** required to complete the infrastructure toolkit configuration. The repository provides secure, type-safe infrastructure-as-code tooling with strict `HOMELAB=1` guards and Tailscale SSH integration.

---

## Overview

The homelab infrastructure toolkit includes:
- **Pulumi TypeScript**: Modern IaC with strict typing, branded types, and HOMELAB guards
- **Ansible**: Configuration management with Tailscale SSH transport and Python typing (Protocols, TypedDict, NewType)
- **Molecule**: Full testing framework with Docker driver for Ansible role validation
- **TDD validation**: Comprehensive test suite ensuring security boundaries

All privileged operations require `HOMELAB=1` or active Tailscale SSH connectivity.

---

## Prerequisites

1. **Age encryption keypair** at `~/.config/sops/age/keys.txt` (see [Secrets Management.md](Secrets Management.md))
2. **Tailscale installed and joined** to your tailnet (see [Tailscale.md](Tailscale.md))
3. **HOMELAB=1 environment variable** set on trusted machines (auto-detected in `.envrc`)
4. **Docker installed** for Molecule testing (optional, for testing only)

---

## Quick Start

### 1. Install Infrastructure Tools

```bash
# Install mise-managed tools (includes Pulumi, Ansible, Node, Python)
mise install

# Verify installations
pulumi version         # Should show 3.207.0
ansible --version      # Should show 2.18.x
molecule --version     # Should show 5.1.0
node --version         # Should show v22.17.0
python --version       # Should show 3.13.9
```

### 2. Configure Pulumi Backend

**Option A: Pulumi Cloud (recommended for teams)**

1. Create a free account at https://app.pulumi.com
2. Generate an access token: https://app.pulumi.com/account/tokens
3. Store token in encrypted secrets (see step 4 below)

**Option B: Local File Backend (no cloud account needed)**

```bash
# Set backend to local filesystem
export PULUMI_BACKEND_URL="file://~/.pulumi"

# Or add to infra/.envrc:
echo 'export PULUMI_BACKEND_URL="file://~/.pulumi"' >> infra/.envrc
direnv allow infra/
```

**Option C: S3 Backend (for self-hosted teams)**

```bash
# Set backend to S3 bucket
export PULUMI_BACKEND_URL="s3://my-pulumi-state-bucket"
```

### 3. Initialize Pulumi Stack

```bash
# Requires HOMELAB=1
export HOMELAB=1

# Initialize the default "dev" stack
cd infra/pulumi-bootstrap
npm install
pulumi stack init dev

# Or use justfile recipe:
HOMELAB=1 STACK_NAME=dev just pulumi-stack-init
```

### 4. Encrypt Cloud Provider Credentials

**For Pulumi:**

```bash
# Copy example env file
cp infra/example.pulumi.env infra/pulumi.env

# Edit with your credentials
$EDITOR infra/pulumi.env

# Encrypt with SOPS (requires age key)
sops --encrypt --input-type dotenv --output-type dotenv \
  --age "$(age-keygen -y ~/.config/sops/age/keys.txt)" \
  infra/pulumi.env > infra/pulumi.env.sops

# Securely delete plaintext
shred -u infra/pulumi.env
```

**For Ansible:**

```bash
# Copy example env file
cp infra/example.ansible.env infra/ansible.env

# Edit with your credentials
$EDITOR infra/ansible.env

# Encrypt with SOPS
sops --encrypt --input-type dotenv --output-type dotenv \
  --age "$(age-keygen -y ~/.config/sops/age/keys.txt)" \
  infra/ansible.env > infra/ansible.env.sops

# Securely delete plaintext
shred -u infra/ansible.env
```

### 5. Configure Ansible Inventory

```bash
# Edit inventory with your Tailscale node IPs
$EDITOR infra/ansible-bootstrap/inventory/homelab.yml

# Example entry:
# node1:
#   ansible_host: 100.64.0.10  # Tailscale IP
#   tags:
#     - tag:homelab-wsl2

# Test connectivity (requires HOMELAB=1 and Tailscale)
HOMELAB=1 just ansible-ping
```

### 6. Set Up Environment File (Optional)

```bash
# Copy example envrc
cp infra/example.envrc infra/.envrc

# Edit and uncomment secrets loading
$EDITOR infra/.envrc

# Allow direnv for infra directory
direnv allow infra/
```

---

## Usage Examples

### Pulumi Workflows

```bash
# Preview infrastructure changes (safe, read-only)
just pulumi-preview

# Apply changes (requires HOMELAB=1 + confirmation)
HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-up

# Dry-run mode (preview without applying)
HOMELAB=1 DRY_RUN=1 just pulumi-up

# Destroy infrastructure (requires HOMELAB=1 + "destroy" confirmation)
HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-destroy
```

### Ansible Workflows

```bash
# Ping all inventory hosts (requires HOMELAB=1)
HOMELAB=1 just ansible-ping

# Run deployment playbook (requires HOMELAB=1 + confirmation)
HOMELAB=1 DEPLOY_CONFIRM=yes just ansible-deploy

# Check mode (dry-run, no changes)
HOMELAB=1 just ansible-check

# Require Tailscale connectivity
HOMELAB=1 REQUIRE_TAILSCALE=1 DEPLOY_CONFIRM=yes just ansible-deploy
```

### Molecule Testing (No HOMELAB Required)

```bash
# Full test sequence (create, converge, verify, destroy)
just ansible-molecule-test

# Incremental testing
just ansible-molecule-converge  # Apply role
just ansible-molecule-verify    # Run tests
just ansible-molecule-destroy   # Clean up
```

---

## Security Best Practices

### Guard Rails Summary

| Environment Variable | Purpose | Required For |
|---------------------|---------|--------------|
| `HOMELAB=1` | Gates all privileged infrastructure operations | Pulumi up/destroy, Ansible deploy/ping |
| `DEPLOY_CONFIRM=yes` | Non-interactive confirmation | CI/CD pipelines |
| `DRY_RUN=1` | Preview mode without side effects | Testing recipes |
| `REQUIRE_TAILSCALE=1` | Enforce active Tailscale connection | High-security deploys |

### Credential Storage

✅ **DO:**
- Store credentials in SOPS-encrypted `.env.sops` files
- Use dedicated age keypairs for infrastructure secrets
- Rotate credentials regularly (90-day maximum)
- Audit access to `~/.config/sops/age/keys.txt`

❌ **DON'T:**
- Commit plaintext credentials to git (even in private repos)
- Share age private keys via email/chat
- Use the same age key for homelab and CI
- Set `HOMELAB=1` on dev laptops (use Tailscale SSH instead)

### Tailscale SSH Benefits

- **Zero trust**: All SSH traffic routed through Tailscale VPN
- **ACL enforcement**: Only `tag:homelab-wsl2` nodes accept SSH
- **Automatic failover**: Connections fail if Tailscale disconnected (fail-secure)
- **Audit logs**: Tailscale admin console tracks all SSH sessions

---

## Type Safety Features

### TypeScript (Pulumi)

**Branded types for security-sensitive values:**
```typescript
type StackName = string & { readonly __brand: 'StackName' };
type ResourceID = string & { readonly __brand: 'ResourceID' };
```

**Discriminated unions for result handling:**
```typescript
type CommandResult<T> =
  | { readonly status: 'success'; readonly data: T }
  | { readonly status: 'error'; readonly error: Error; readonly exitCode: number }
  | { readonly status: 'skipped'; readonly reason: string };
```

**Strict mode enabled** (`tsconfig.json`):
- `strict: true` (all strict checks)
- `noImplicitReturns: true`
- `noFallthroughCasesInSwitch: true`

### Python (Ansible)

**Modern typing with Protocols and TypedDict:**
```python
from typing import Protocol, TypedDict, NewType, TypeGuard

TailscaleIP = NewType('TailscaleIP', str)

class AnsibleHost(TypedDict, total=True):
    ansible_host: Required[TailscaleIP]
    ansible_user: Required[str]
    tags: Required[list[str]]

class InventoryProvider(Protocol):
    def get_hosts(self) -> dict[str, AnsibleHost]: ...
    def verify_connectivity(self) -> bool: ...
```

**Type guards for runtime validation:**
```python
def is_tailscale_ip(value: str) -> TypeGuard[TailscaleIP]:
    parts = value.split('.')
    return int(parts[0]) == 100 and all(0 <= int(p) <= 255 for p in parts[1:])
```

---

## Testing

### Run All Tests

```bash
# Full test suite (includes Pulumi, Ansible, guards)
just ci-validate

# Individual test suites
bash tests/06_pulumi_project_validation.sh
bash tests/07_ansible_molecule_validation.sh
bash tests/08_infra_guards.sh
bash tests/09_tailscale_ssh_verification.sh
```

### Molecule Test Workflow

```bash
# Full test cycle (Docker-based, no homelab required)
cd infra/ansible-bootstrap
molecule test

# Incremental development workflow
molecule create              # Spin up Docker containers
molecule converge            # Apply role
molecule login               # SSH into test container
molecule verify              # Run pytest tests
molecule destroy             # Clean up
```

---

## Troubleshooting

### "Refusing to run: HOMELAB != 1"

**Cause:** Infrastructure command executed without `HOMELAB=1`.

**Fix:**
```bash
# Check HOMELAB detection
just detect-homelab

# If key exists but HOMELAB not set:
export HOMELAB=1

# Or add to shell rc:
echo 'export HOMELAB=1' >> ~/.bashrc
source ~/.bashrc
```

### Pulumi Backend Errors

**Error:** "error: could not login to backend"

**Fix for local backend:**
```bash
export PULUMI_BACKEND_URL="file://~/.pulumi"
pulumi login --local
```

**Fix for cloud backend:**
```bash
# Generate token at https://app.pulumi.com/account/tokens
export PULUMI_ACCESS_TOKEN="pul-..."
pulumi login
```

### Ansible Tailscale SSH Failures

**Error:** "Failed to connect via tailscale ssh"

**Check:**
```bash
# Verify Tailscale is running
tailscale status

# Verify target node has Tailscale SSH enabled
tailscale status | grep "tag:homelab-wsl2"

# Verify ACL allows SSH to your user
# Check https://login.tailscale.com/admin/acls
```

**Fix:**
```bash
# On target node (requires HOMELAB=1):
HOMELAB=1 just tailscale-ssh-enable
```

### Molecule Docker Permission Errors

**Error:** "permission denied while trying to connect to Docker daemon"

**Fix (Linux):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or use rootless Docker (preferred):
dockerd-rootless-setuptool.sh install
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Infrastructure Validation
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install mise
        run: |
          curl https://mise.run | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install tools
        run: mise install

      - name: Run tests (no HOMELAB required)
        run: just ci-validate

      - name: Molecule tests
        run: |
          cd infra/ansible-bootstrap
          molecule test
```

**Note:** CI does NOT require `HOMELAB=1` for testing. Guard validation uses mocked environments.

---

## File Structure Reference

```
infra/
├── pulumi-bootstrap/
│   ├── index.ts              # Main Pulumi program with HOMELAB guards
│   ├── package.json          # Node dependencies
│   ├── tsconfig.json         # TypeScript strict mode config
│   ├── Pulumi.yaml           # Project metadata + backend config
│   ├── Pulumi.dev.yaml       # Dev stack config (encrypted with Pulumi)
│   └── .gitignore            # Exclude node_modules, bin/
│
├── ansible-bootstrap/
│   ├── ansible.cfg           # Forces Tailscale SSH transport
│   ├── requirements.txt      # Python dependencies (ansible-core, molecule)
│   ├── inventory/
│   │   └── homelab.yml       # Tailscale IP-based inventory
│   ├── playbooks/
│   │   └── deploy.yml        # Example deployment with HOMELAB guard
│   ├── library/
│   │   └── inventory_utils.py # Typed inventory utilities (Protocols, TypedDict)
│   ├── molecule/
│   │   └── default/
│   │       ├── molecule.yml   # Molecule config (Docker driver)
│   │       ├── converge.yml   # Role application playbook
│   │       ├── verify.yml     # Ansible-based verification
│   │       ├── prepare.yml    # Pre-converge setup
│   │       └── tests/
│   │           └── test_default.py  # Pytest tests
│   ├── .yamllint             # YAML linting config
│   └── .ansible-lint         # Ansible linting config
│
├── example.pulumi.env        # Template for Pulumi credentials
├── example.ansible.env       # Template for Ansible credentials
└── example.envrc             # Template for direnv configuration
```

---

## Additional Resources

- **Pulumi Documentation**: https://www.pulumi.com/docs/
- **Pulumi TypeScript API**: https://www.pulumi.com/docs/reference/pkg/nodejs/pulumi/pulumi/
- **Ansible Documentation**: https://docs.ansible.com/
- **Molecule Documentation**: https://molecule.readthedocs.io/
- **Tailscale SSH Guide**: https://tailscale.com/kb/1193/tailscale-ssh/
- **SOPS Documentation**: https://github.com/mozilla/sops

---

## Next Steps

1. **Generate infrastructure-specific age keys** (separate from homelab keys):
   ```bash
   age-keygen -o ~/.config/sops/age/infra-keys.txt
   chmod 600 ~/.config/sops/age/infra-keys.txt
   ```

2. **Add Pulumi state encryption** (if using Pulumi Cloud):
   ```bash
   cd infra/pulumi-bootstrap
   pulumi stack change-secrets-provider \
     "awskms://alias/pulumi-secrets?region=us-east-1"
   ```

3. **Configure ACLs for infrastructure nodes** (Tailscale admin console):
   - Add `tag:infra-node` for dedicated infrastructure runners
   - Restrict SSH access to specific admin users only

4. **Set up automated secret rotation** (90-day schedule):
   - Pulumi Cloud tokens
   - Cloud provider API keys
   - Ansible vault passwords

5. **Implement GitOps workflows** (optional):
   - Use Pulumi Automation API for PR-based deploys
   - Integrate Ansible Tower/AWX for centralized execution

---

**Questions or issues?** Review the troubleshooting section, check test output with `just ci-validate`, and verify guard behavior with `just detect-homelab`.
