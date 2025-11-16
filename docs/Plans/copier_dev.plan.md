# Plan: Convert Homelab to Copier Template with Template Branch

Transform the homelab repository into a Copier template on a `template` branch, enabling users to generate customized homelab projects while preserving all security guards. Includes pre-generation validation, safe update paths for guard rails, and comprehensive update documentation.

## Steps

### 1. Create `template` branch with Copier structure

Branch from `main`, reorganize as `copier.yml` (root), `template/` (all current files), `hooks/` (pre/post generation scripts), `extensions/` (validators.py). Add `copier.yml` with 15+ variables (project identity, tool versions, feature flags), `_exclude` for `.git|node_modules|*.sops|pnpm-lock.yaml`, `_templates_suffix: .j2`, validation tasks checking mise/direnv installation.

**Variables to include:**
- **Project Identity**: `project_name`, `project_description`, `admin_email`, `github_owner`
- **Tool Versions**: `node_version`, `python_version`, `pulumi_version`, `pnpm_version`, `nx_version`
- **Optional Features**: `enable_pulumi`, `enable_ansible`, `enable_nx_distributed`
- **Tailscale Config**: `tailnet_name`, `tailscale_tag`
- **NPM Scope**: `npm_scope` (optional, must start with `@` if provided)

**Exclusions:**
```yaml
_exclude:
  - .git
  - .nx
  - node_modules
  - dist
  - tmp
  - "*.sops"
  - .copier-answers.yml
  - pnpm-lock.yaml
```

**Validation tasks:**
```yaml
_tasks:
  - "command -v mise >/dev/null 2>&1 || echo 'WARNING: mise not installed'"
  - "command -v direnv >/dev/null 2>&1 || echo 'WARNING: direnv not installed'"
```

### 2. Implement `hooks/pre_copy.py` with validators

Validate all user inputs before generation to prevent common mistakes:

**Validation rules:**
- `project_name`: Matches `^[a-z0-9\-_]+$` pattern (lowercase alphanumeric, hyphens, underscores only)
- `admin_email`: Contains `@` and valid TLD pattern (`.com`, `.org`, `.net`, etc.)
- `npm_scope`: If provided, starts with `@` and matches `^@[a-z0-9\-_]+$`
- Tool versions: Match semver pattern `^\d+\.\d+\.\d+$`
- Feature flags: Boolean validation

**Error handling:**
- Exit with error code 1 and descriptive message on validation failure
- Provide helpful suggestions (e.g., "project_name must be lowercase, got 'MyProject', try 'my-project'")

### 3. Template 40+ files with `.j2` suffix

**Core configuration files:**
- `.envrc.j2` - Add project/admin comment header
- `.mise.toml.j2` - Parameterize tool versions
- `devbox.json.j2` - Allow package customization
- `package.json.j2` - Project name, description, optional npm scope
- `tsconfig.base.json.j2` - Path mappings with npm scope
- `README.md.j2` - Project metadata, GitHub links

**Documentation files (25+ files):**
- All `docs/Explanations/*.md` → Replace hardcoded examples with `{{ admin_email }}`, `{{ project_name }}`
- All `docs/Howto/*.md` → Template example commands with user's context
- All `docs/Tutorials/*.md` → Personalize walkthrough steps
- All `docs/Reference/*.md` → Template variable names and examples
 - `docs/Reference/example.envrc.j2` → Template admin_email
 - `docs/Reference/example.tailscale-acl.json.j2` → Template admin_email, tags

**Package files:**
 - `packages/homelab-types/package.json.j2` → npm scope
 - `packages/pulumi-bootstrap/package.json.j2` → npm scope, project name
 - `packages/pulumi-bootstrap/index.ts.j2` → Project-specific resource names (optional)

**Files to keep as-is (universal patterns):**
- `justfile` - Guard patterns are universal
- All `tests/*.sh` - Validate architecture, not project-specific
- All `scripts/*.sh` - Generic tooling
- `.sops.yaml` - User updates after keygen
- `.gitignore` - Already comprehensive

### 4. Create `hooks/post_copy.sh` security checklist

Print comprehensive setup instructions immediately after generation:

**8-step security setup:**

1. **Generate age keypair**
   ```bash
   mkdir -p ~/.config/sops/age
   age-keygen -o ~/.config/sops/age/keys.txt
   chmod 600 ~/.config/sops/age/keys.txt
   ```

2. **Extract public recipient**
   ```bash
   age-keygen -y ~/.config/sops/age/keys.txt
   # Copy this value for next step
   ```

3. **Update `.sops.yaml` with real recipient**
   ```bash
   # Edit .sops.yaml and replace placeholder with your public key
   vim .sops.yaml
   ```

4. **Create and encrypt secrets**
   ```bash
   # For each example file in docs/Reference/
   cp docs/Reference/example.tailscale.env infra/tailscale.env
   vim infra/tailscale.env  # Fill with real values
   export AGE_RECIPIENT="age1..."  # Your public key
   just tailscale-encrypt
   ```

5. **Obtain Tailscale auth key**
   - Visit Tailscale admin console
   - Generate new auth key (ephemeral, reusable)
   - Store in `infra/tailscale.env` before encryption

6. **Configure Tailscale ACL tags**
   - In admin console, create tags: `tag:homelab-wsl2`, `tag:homelab-server`
   - Assign admin_email as tagOwner
   - Configure SSH access rules

7. **Run validation suite**
   ```bash
   just ci-validate
   # All tests should pass or skip (exit code 0 or 2)
   ```

8. **Follow first deployment tutorial**
   ```bash
   cat docs/Tutorials/Your-First-Deployment.md
   ```

**3 prominent warnings:**
```
⚠️  NEVER commit plaintext secrets to git!
⚠️  Store age private key in password manager (backup recovery)
⚠️  Verify all guard tests pass before first deploy
```

### 5. Document safe update paths in `docs/Reference/Template-Updates.md`

Create comprehensive update strategy documentation covering 3 scenarios:

#### Scenario A: Config-Only Updates (Safe)
- Tool version bumps in `.mise.toml`
- Documentation improvements
- New example files
- Dependency updates in `package.json`

**Update process:**
```bash
copier update
# Review changes, accept/reject individually
just ci-validate  # Verify nothing broke
```

#### Scenario B: Guard Rail Updates (Manual Review Required)
- Changes to `justfile` recipes
- Modifications to test files (`tests/*.sh`)
- New `HOMELAB` checks or confirmation prompts
- Updates to `DEPLOY_CONFIRM`, `DRY_RUN`, `REQUIRE_TAILSCALE` logic

**Update process:**
```bash
copier update --vcs-ref=v1.1.0  # Specific version
git diff justfile tests/  # Review guard changes carefully

# Re-run specific guard validation tests
bash tests/04_just_safety_guards.sh
bash tests/08_infra_guards.sh

# Full validation
just ci-validate
```

**Critical review checklist:**
- [ ] No guard patterns bypassed or weakened
- [ ] All `HOMELAB=1` checks still present
- [ ] Confirmation prompts still require explicit consent
- [ ] DRY_RUN mode still supported for all destructive operations
- [ ] Test suite still validates guard behavior

#### Scenario C: Breaking Changes (Migration Steps Required)
- New mandatory variables in `copier.yml`
- Dropped features or renamed options
- Changed file structure requiring manual moves
- New security requirements

**Update process:**
```bash
# Read CHANGELOG.md for migration steps
cat CHANGELOG.md | grep -A 20 "v2.0.0"

# Apply update with conflict resolution
copier update --vcs-ref=v2.0.0 --conflict=rej

# Follow migration guide
cat docs/Reference/Migration-v1-to-v2.md
```

**Version tagging convention:**
- `v1.x.x` - Patch/minor (backward-compatible)
- `v2.x.x` - Major (guard rail changes, manual review)
- `v3.x.x` - Breaking (migration required)

**CHANGELOG.md format:**
```markdown
## [2.0.0] - 2025-11-16

### Breaking Changes
- Added `REQUIRE_TAILSCALE=1` default to all infra recipes
- Renamed `enable_pulumi` → `features_pulumi`

### Migration Steps
1. Update `.envrc` to export `REQUIRE_TAILSCALE=1`
2. Update Tailscale connection before running `just deploy`
3. Re-run `copier update` to apply variable renames

### Guard Rail Changes
- `justfile`: Added Tailscale check to ansible-deploy recipe
- `tests/08_infra_guards.sh`: New test validates REQUIRE_TAILSCALE behavior
```

### 6. Add conditional feature exclusion via Jinja2 ✅ IMPLEMENTED

**When `enable_pulumi=false`, exclude:**
- `packages/pulumi-bootstrap/` (entire directory) — ✅ via `_exclude` in copier.yml
- `infra/pulumi-bootstrap/` (symlink) — ✅ via `_exclude` in copier.yml
- `tests/06_pulumi_project_validation.sh` — ✅ via `_exclude` in copier.yml
- Pulumi recipes from `justfile` — ✅ **IMPLEMENTED** via `{% if enable_pulumi %}` in template/justfile.j2:
  - `pulumi-preview`
  - `pulumi-up`
  - `pulumi-destroy`
  - `pulumi-stack-init`
- Pulumi dependencies from `package.json` — ⏳ TODO (currently included unconditionally)

**When `enable_ansible=false`, skip:**
- `infra/ansible-bootstrap/` (entire directory) — ✅ via `_exclude` in copier.yml
- `tests/07_ansible_molecule_validation.sh` — ✅ via `_exclude` in copier.yml
- Ansible recipes from `justfile` — ✅ **IMPLEMENTED** via `{% if enable_ansible %}` in template/justfile.j2:
  - `ansible-ping`
  - `ansible-deploy`
  - `ansible-check`
  - `ansible-molecule-test`
  - `ansible-molecule-converge`
  - `ansible-molecule-verify`
  - `ansible-molecule-destroy`
  - `ansible-molecule-*` recipes

**When `enable_nx_distributed=false`, skip:**
- `scripts/nx-*.sh` (agent scripts)
- `docs/Explanations/Nx-Distributed-Architecture.md`
- Nx recipes from `justfile` (lines 83-105):
  - `nx-init`
  - `nx-encrypt-config`
  - `nx-start-agent`
  - `nx-distributed-build`
- Prune `@nx/*` packages from `package.json`:
  - `@nx/js`
  - `@nx/workspace`
  - `nx`

**Update test runner:**
Modify `tests/run-tests.sh` to conditionally skip disabled feature tests:
```bash
# Generated by Copier based on enabled features
tests=(
  "01_non_homelab_decrypt.sh"
  "02_sops_yaml_schema.sh"
  "03_round_trip_homelab.sh"
  "04_just_safety_guards.sh"
  "05_tailscale_ssh_guards.sh"
{% if enable_pulumi %}
  "06_pulumi_project_validation.sh"
{% endif %}
{% if enable_ansible %}
  "07_ansible_molecule_validation.sh"
{% endif %}
  "08_infra_guards.sh"
  "09_tailscale_ssh_verification.sh"
{% if enable_nx_distributed %}
  "10_nx_distributed_validation.sh"
{% endif %}
)
```

## Further Considerations

### 1. CI/CD for template branch

**GitHub Actions Should validate `copier.yml` syntax, test template generation in ephemeral directory, and verify all guard tests pass in generated project**

**Benefits:**
- Catches Jinja2 syntax errors before users hit them
- Verifies generated projects actually work (guards pass)
- Prevents regressions in template variables
- Validates conditional feature exclusion logic

**Proposed workflow** (`.github/workflows/template-validation.yml`):
```yaml
name: Validate Template

on:
  push:
    branches: [template]
  pull_request:
    branches: [template]

jobs:
  validate-template:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install copier
        run: pipx install copier

      - name: Validate copier.yml syntax
        run: copier --help-all  # Validates schema

      - name: Generate test project (all features)
        run: |
          copier copy --vcs-ref=HEAD . /tmp/test-all \
            -d project_name=test-homelab \
            -d admin_email=test@example.com \
            -d enable_pulumi=true \
            -d enable_ansible=true \
            -d enable_nx_distributed=true

      - name: Generate test project (minimal features)
        run: |
          copier copy --vcs-ref=HEAD . /tmp/test-minimal \
            -d project_name=minimal-lab \
            -d admin_email=test@example.com \
            -d enable_pulumi=false \
            -d enable_ansible=false \
            -d enable_nx_distributed=false

      - name: Run guard tests in generated projects
        run: |
          cd /tmp/test-all
          # Mock HOMELAB=0 environment
          bash tests/04_just_safety_guards.sh
          bash tests/08_infra_guards.sh

          cd /tmp/test-minimal
          bash tests/04_just_safety_guards.sh
```

**Decision: YES** - Include CI validation for template branch to catch issues early.

### 2. Template versioning strategy

**Use semantic versioning with migration docs - `v1.x.x` for backward-compatible (config/docs changes), `v2.x.x` for guard rail changes requiring manual review, `v3.x.x` for breaking changes (new mandatory variables, dropped features)?**

**Versioning strategy:**
- **Patch** (`v1.0.1`): Bug fixes, typo corrections, doc clarifications
- **Minor** (`v1.1.0`): New optional features, tool version updates, new example files
- **Major** (`v2.0.0`): Guard rail changes, new required variables, structural changes

**Include `copier.yml` constraints:**
```yaml
_min_copier_version: "9.0.0"
_envops:
  keep_trailing_newline: true
```

**Git tagging convention:**
```bash
# On template branch
git tag -a v1.0.0 -m "Initial template release"
git tag -a v1.1.0 -m "Add Nx distributed builds support"
git tag -a v2.0.0 -m "BREAKING: Add REQUIRE_TAILSCALE default"
git push origin --tags
```

**Users specify version when updating:**
```bash
copier update --vcs-ref=v1.1.0  # Specific version
copier update                   # Latest (risky for major versions)
```

**Decision: YES** - Use semver with explicit migration docs for v2+ updates.

### 3. Interactive mode for sensitive values

**Should `copier.yml` include `type: str, secret: true` for optional fields like `tailscale_authkey_preview` (just first 8 chars for confirmation, not stored), then guide user to proper encryption workflow in post_copy?**

**Problem:** Accidentally storing secrets in `.copier-answers.yml` defeats entire security model.

**Proposed solution:**
```yaml
# In copier.yml
tailscale_authkey_preview:
  type: str
  secret: true  # Won't be stored in .copier-answers.yml
  help: "First 8 characters of Tailscale auth key (for confirmation only)"
  default: "tskey-au"
  validator: "{% if tailscale_authkey_preview|length > 12 %}Enter only first 8-12 chars{% endif %}"
```

**In post_copy.sh:**
```bash
echo "You provided auth key preview: ${TAILSCALE_AUTHKEY_PREVIEW}"
echo "Complete setup by:"
echo "  1. Paste full auth key into infra/tailscale.env"
echo "  2. Run: just tailscale-encrypt"
echo ""
echo "⚠️  The preview is NOT stored in .copier-answers.yml for security"
```

**Alternative: Skip sensitive prompts entirely**
Just document in post_copy.sh that users MUST obtain keys manually:
```bash
echo "SECURITY: Copier intentionally does NOT prompt for secrets"
echo "Obtain these values manually:"
echo "  - Tailscale auth key (admin console)"
echo "  - Age keypair (age-keygen)"
echo "  - Cloud provider tokens"
```

**Decision: NO** - Don't prompt for any sensitive values. Keep template generation fully non-privileged, guide users through secure manual steps in post_copy.sh. This prevents accidental leaks and keeps `.copier-answers.yml` safe to commit (if users choose).

## Implementation Order

1. Create `template` branch from `main`
2. Implement `hooks/pre_copy.py` validators (test locally)
3. Create `copier.yml` with all variables and constraints
4. Template 10 core files first (`.envrc`, `.mise.toml`, `package.json`, `README.md`, etc.)
5. Verify basic generation works: `copier copy . /tmp/test-basic`
6. Template all documentation files (25+ files)
7. Add conditional feature exclusion (Jinja2 `{% if %}` blocks)
8. Create `hooks/post_copy.sh` with security checklist
9. Write `docs/Reference/Template-Updates.md`
10. Add GitHub Actions workflow for template validation
11. Tag initial release: `git tag v1.0.0`
12. Update main branch `README.md` with "Generate from template" instructions

## Success Criteria

- [ ] `copier copy` generates working homelab project with custom name/email
- [ ] All guard tests pass in generated project (`just ci-validate`)
- [ ] Feature flags correctly exclude unwanted components
- [ ] `copier update` successfully applies config changes
- [ ] Guard rail updates are clearly documented with review checklist
- [ ] No secrets ever prompted or stored in `.copier-answers.yml`
- [ ] Template CI validates generation and tests on every push
- [ ] Users can choose template version via `--vcs-ref=v1.0.0`
- [ ] Comprehensive documentation for first-time users and update paths



## Current Status

### ✅ Completed
- Replaced .jinja with .j2 in the template and docs
- Added core templated files and feature toggles
- Added unit tests for extensions.validators and hooks.pre_copy (unit test framework added to CI)
- Implemented migrations scaffolding and CHANGELOG.md
- **Added conditional Pulumi and Ansible recipes to `template/justfile.j2`** using `{% if enable_pulumi %}` and `{% if enable_ansible %}` blocks
- **Fixed Python import issues in generated projects** by adding `template/pytest.ini` with `pythonpath = .` configuration
- **Added `__init__.py` to template packages** (`hooks/` and `extensions/`) to make them proper Python packages
- **Updated ValidationFilters** to allow instantiation without Jinja environment for unit testing
- **All tests passing**: Repository tests (11/11), generated project shell tests, and generated project Python tests (9/9)

### ✅ Validated
- Template generation works with all feature combinations (enable_pulumi, enable_ansible, enable_nx_distributed)
- Guard tests pass in generated projects (04_just_safety_guards.sh, 08_infra_guards.sh)
- Python imports work correctly in generated projects via pytest.ini configuration
- Conditional recipe inclusion works as expected

### 🔄 Next recommended items (optional enhancements):
- Template the remaining files (40+ files in the plan): .mise.toml.j2, tsconfig.base.json.j2, docs/Howto/Tutorials pages
- Add more template-specific tests for migrations and conditional exclusions
- Consider adding a pre-commit hook for .rej files
- Expand CI matrix to test more feature combinations
