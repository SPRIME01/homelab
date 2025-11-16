# Migration v1 → v2

This document describes the migration steps required when updating a generated project from `v1.x.x` to `v2.x.x` of the template. The migration includes changes to guard rails and may require manual updates.

## Breaking changes in v2.0.0
- `REQUIRE_TAILSCALE=1` now defaults to true for infra-related recipes.
- Variable rename: `enable_pulumi` -> `features_pulumi`

## Migration steps
1. Update `.envrc` to export `REQUIRE_TAILSCALE=1` where appropriate.
2. Replace variable names in `copier.yml` answers if required and re-run `copier update` with `--vcs-ref=v2.0.0`.
3. Run `just ci-validate` and fix any failing guard tests.
4. Review `justfile` and `tests/` for guard logic changes.

If you are upgrading multiple workspaces, test a single project with `copier update --vcs-ref=v2.0.0` first and resolve issues before performing repeated updates.
