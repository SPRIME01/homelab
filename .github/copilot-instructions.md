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

### Running Tests
```bash
bash tests/run-tests.sh  # Runs all tests; treats exit code 2 as "skipped"
just ci-validate         # CI target: syntax check + tests
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

## Key Documentation References

- **`docs/Secrets Management.md`** — SOPS/age workflow, backup, rotation
- **`docs/Tailscale.md`** — Complete Tailscale SSH setup walkthrough
- **`docs/Automation.md`** — Justfile guard patterns, HOMELAB detection
- **`justfile`** — All recipes with embedded guard logic
- **`.envrc`** — Auto-detection of homelab environment
- **`.sops.yaml`** — Encryption rules for `infra/` files

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
