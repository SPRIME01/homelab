# Template Updates and Safe Update Paths

This document describes how to safely update projects generated from the Copier template. It covers three update categories — configuration-only, guard rail updates (manual review), and breaking changes — and provides checklists and recommended commands for each.

## Safe update paths

### Scenario A: Config-Only Updates (Safe)
- Tool version bumps in `.mise.toml`
- Documentation improvements
- New example files
- Dependency updates in `package.json`

Update process:
```bash
copier update
# Review changes, accept/reject individually
just ci-validate  # Verify nothing broke
```

### Scenario B: Guard Rail Updates (Manual Review Required)
Examples:
- Changes to `justfile` recipes
- Modifications to tests (`tests/*.sh`)
- New `HOMELAB` checks or confirmation prompts
- Updates to `DEPLOY_CONFIRM`, `DRY_RUN`, `REQUIRE_TAILSCALE` logic

Update process:
```bash
copier update --vcs-ref=v1.1.0  # Specific version
git diff justfile tests/  # Review guard changes carefully

# Re-run specific guard validation tests
bash tests/04_just_safety_guards.sh
bash tests/08_infra_guards.sh

# Full validation
just ci-validate
```

Critical review checklist:
- [ ] No guard patterns bypassed or weakened
- [ ] All `HOMELAB=1` checks still present
- [ ] Confirmation prompts still require explicit consent
- [ ] DRY_RUN mode still supported for all destructive operations
- [ ] Test suite still validates guard behavior

### Scenario C: Breaking Changes (Migration Steps Required)
Examples:
- New mandatory variables in `copier.yml`
- Dropped features or renamed options
- Changed file structure requiring manual moves
- New security requirements

Update process:
```bash
# Read CHANGELOG.md for migration steps
cat CHANGELOG.md | grep -A 20 "v2.0.0"

# Apply update with conflict resolution
copier update --vcs-ref=v2.0.0 --conflict=rej

# Follow migration guide
cat docs/Reference/Migration-v1-to-v2.md
```

Versioning strategy:
- Patch (`v1.x.x`) - Bug fixes, docs
- Minor (`v1.x.x`) - New optional features
- Major (`v2.x.x`) - Guard rail changes requiring review

## Testing Generated Projects

Generated projects include:
- `pytest.ini` — Configures Python import paths (sets `pythonpath = .`)
- `tests/04_just_safety_guards.sh` — Validates justfile guard patterns
- `tests/08_infra_guards.sh` — Validates infrastructure recipe guards (Pulumi/Ansible)
- `tests/python/` — Unit tests for validators and hooks

# Quick checks for updates
- Launch generated project in a test directory and run `just ci-validate`
- Verify `pytest.ini` is present and configured correctly
- Check for `.rej` files created by copier and manually inspect
- Validate pre-commit hooks and guard tests
- Ensure Python tests can import from `extensions/` and `hooks/` packages

# Releasing template versions
- Tag template branch with `git tag -a vX.Y.Z -m "Message"`
- Push tags: `git push origin --tags`

Include migration notes and changelogs for major versions to help users update safely.
