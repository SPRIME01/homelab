<!-- .github/copilot-instructions.md -->

# Copilot / AI agent instructions — homelab

Purpose: help an AI coding agent become productive quickly in this repository by describing the high-level architecture, critical developer workflows, project-specific conventions, and the precise files and commands you should read or run.

Keep this short and actionable. If you change a workflow or canonical file, update this document.

## Big picture
- Polyglot monorepo orchestrated with Nx. Languages/tools: Node (pnpm/Volta), Python (uv + .venv), Rust (cargo), and Just for task recipes.
- Devbox provides reproducible OS-level toolchains; direnv + `./lib/env-loader.sh` compose runtime variables locally. CI bypasses direnv and calls `./lib/env-loader.sh ci`.
- Goal: local developer shells match CI with idempotent bootstrapping (uv manages Python interpreters; `.venv` is per-project virtualenv).

## Key files to read first
- `.envrc` — direnv entrypoint. It evaluates `devbox generate direnv --print-envrc` safely and activates `mise` if present. Look for set/unset guards.
- `lib/env-loader.sh` — canonical loader used locally and in CI (shell export rules, sops decryption). Read how it is sourced (shell/local/ci modes).
- `devbox.json` & `devbox.lock` — OS-level packages and `shell.init_hook` (uv + .venv handling lives here).
- `.github/workflows/*.yml` — CI bootstrapping. CI now persists venv info using `$GITHUB_ENV` / `$GITHUB_PATH`.
- `docs/*` — setup and spec docs describe intended workflow. Use them to generate in-repo guidance.

## Developer workflows (commands you can run)
- Set up toolchain and install packages: `devbox install --tidy-lockfile`
- Generate direnv snippet: `devbox generate direnv --print-envrc`
- Activate environment locally (direnv): `direnv allow` (after updating `.envrc`).
- Use uv to list/install Python: `uv python list`; `uv python install 3.12`
- Create venv locally (idempotent): `uv venv .venv --python 3.12` (fallback: `python -m venv .venv`).
- Run tests/lint via Nx: `npx nx run-many --target=test --all` and `npx nx run-many --target=lint --all` (CI uses these targets).

## Project-specific conventions and patterns
- Do NOT spawn interactive subshells from `.envrc` (avoid `devbox shell` in `.envrc`). Instead eval devbox's direnv snippet into the current shell so PATH and env vars propagate.
- Guard `set -u` (nounset) when evaluating external/generated shell snippets. The repo uses a pattern like:

```bash
_SAVED_OPTS="$(set +o)"; set +u
eval "$(devbox generate direnv --print-envrc 2>/dev/null)" || true
eval "$_SAVED_OPTS" || true
unset _SAVED_OPTS
```

- CI bootstrapping uses `./lib/env-loader.sh ci` (no direnv). If adding Python setup in workflows, write `VIRTUAL_ENV` and venv bin path into `$GITHUB_ENV` / `$GITHUB_PATH` so subsequent steps inherit the venv.

## Integration points & external dependencies
- Devbox (devbox CLI): generates shell snippets, installs OS-level packages. Check `devbox.json` for list of packages (pnpm, uv, mise, direnv, just, sops, rustup, nodejs@20).
- uv: Python interpreter manager. Used to pin Python 3.12 and create `.venv`.
- mise: runtime manager — `.envrc` evals `mise direnv activate` when present.
- GitHub Actions: CI runs `./lib/env-loader.sh ci` then uses Node/Nx tasks; workflows were updated to ensure uv/pipx/vvenv are prepared and exported.

## Common pitfalls & troubleshooting
- direnv blocked / `direnv allow` fails: inspect `.envrc` and `devbox generate direnv --print-envrc`. Ensure `.envrc` temporarily disables nounset before eval.
- `pop_var_context` or unbound variable errors: these are caused by `set -u` being active when evaling generated scripts — add guard as above.
- uv CLI mismatches: use `uv venv .venv --python 3.12` (creation) and `source .venv/bin/activate` for activation; do not expect `uv venv activate .venv` to exist.
- CI venv activation: sourcing a venv in a single step does not persist — write VIRTUAL_ENV and prepend the venv bin to PATH via `$GITHUB_ENV` and `$GITHUB_PATH`.

## If you change environment bootstrapping
- Update `devbox.json` (shell.init_hook) for interactive shells, and `.github/workflows/*` for CI. Keep both idempotent and non-fatal (use `|| true`).
- Update `docs/how-to/setup-environment.md` and `docs/specs/environment.md` to reflect any changes in the bootstrapping pattern.

## Example edits an AI agent might perform
- Fix uv usage: replace `uv venv create .venv --python 3.12` with `uv venv .venv --python 3.12` and replace `uv venv activate .venv` with `source .venv/bin/activate`.
- Persist venv in CI: after creating `.venv`, append `echo "VIRTUAL_ENV=$PWD/.venv" >> "$GITHUB_ENV"` and `echo "$PWD/.venv/bin" >> "$GITHUB_PATH"`.

## Quick checklist before making a PR
- Run `devbox install` locally and `direnv allow` to ensure `.envrc` changes don't break loading.
- Run `npx nx run-many --target=lint --all` and `npx nx run-many --target=test --all` as smoke checks.
- Update docs in `docs/` to explain any user-facing change.

---

If anything here is unclear or you'd like additional repo-specific rules (e.g., preferred commit messages, branching policy details), tell me what to add and I'll update this file.
