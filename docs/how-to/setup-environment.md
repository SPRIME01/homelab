Here is the correct **implementation sequence**, de-duplicated, dependency-ordered, and optimized to avoid technical debt.

---

## 🧱 Implementation Sequence (Best-Practice Order)

|    #   | Step                                           | Purpose                                                                                                          | Depends On                   |
| :----: | :--------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- | :--------------------------- |
|  **1** | **Initialize Git repository and branch rules** | Establish `main`/`stage`/`dev`, add branch protections, and wire default PR templates.                           | —                            |
|  **2** | **Install direnv and template `.envrc`**       | Provide local-only env activation that delegates to `lib/env-loader.sh` and documents the `direnv allow` flow.   | Git init                     |
|  **3** | **Create base `devbox.json`**                  | Define OS-level dependencies (pnpm, uv, mise, just, sops, volta, cargo).                                         | direnv `.envrc` in place     |
|  **4** | **Configure `.mise.toml`**                     | Pin global runtime versions (Node, Python, Rust) and configure tool-specific defaults.                           | Devbox                       |
|  **5** | **Integrate Volta**                            | Manage Node/TypeScript toolchain binaries (npm, pnpm, yarn).                                                     | mise                         |
|  **6** | **Integrate Cargo**                            | Manage Rust dependencies and crate builds.                                                                       | mise                         |
|  **7** | **Create `nx.json` and `workspace.json`**      | Define monorepo structure, default targets, caching, and plugin setup.                                           | Volta + Cargo                |
|  **8** | **Update Nx plugin configuration**             | Add executors for Cargo, Python, and Volta-managed Node projects.                                                | nx.json                      |
|  **9** | **Write `Justfile` recipes**                   | Define workflow commands (`setup`, `build`, `test`, `lint`, `deploy`, `doctor`, `promote-*`).                     | Nx config                    |
| **10** | **Add all config files to Chezmoi**            | Track dotfiles (`.envrc`, `.mise.toml`, `.volta`, `devbox.json`, `Justfile`, etc.) for reproducibility.          | All local configs exist      |
| **11** | **Test local reproducibility**                 | Run `direnv allow` → Devbox shell → mise → Volta → Nx → Just to confirm deterministic setup.                     | Chezmoi                      |
| **12** | **Wire into GitHub Actions CI/CD**             | Author workflow matrix for `dev`/`stage`/`main`; bootstrap with `./lib/env-loader.sh ci` (no `direnv`).           | Verified local setup         |
| **13** | **Add optional SOPS integration to CI**        | Secure secrets for builds and deployments.                                                                       | CI/CD active                 |

---

## 🔁 Simplified Workflow

```mermaid
flowchart TD
    A[Initialize Git + Branch Guards] --> B[direnv + .envrc (local shells)]
    A --> C[lib/env-loader.sh (CI bootstrap)]
    B --> D[Devbox.json]
    C --> D
    D --> E[mise + Volta + Cargo Configs]
    E --> F[Nx Workspace Setup]
    F --> G[Justfile Tasks]
    G --> H[Chezmoi Dotfile Tracking]
    H --> I[Local Test Matrix]
    I --> J[GitHub Actions Integration]
    J --> K[SOPS CI Secrets]
```

---

## ⚙️ Resulting System Integrity

* **Single source of truth:** Chezmoi deploys `.envrc`, tool configs, and secrets scaffolding.
* **Zero-drift environments:** direnv (local) + Devbox + mise ensure parity without manual exports. For Python, prefer `uv` to manage interpreters and virtual environments; CI jobs should install or make `uv` available (Devbox packaging or pipx fallback) and create/activate a `.venv` pinned to Python 3.12 during bootstrap.

### Recommended `.envrc` (safe, non-blocking)

Use the following pattern in `.envrc` to eval Devbox's environment into your current shell rather than spawning an interactive `devbox shell` automatically. This keeps editor/CI behavior predictable while providing Devbox's PATH and init-hook effects.

```bash
# Local-only environment composition — do not use in CI/CD.
if [[ -f "./lib/env-loader.sh" ]]; then
  # shellcheck disable=SC1091
  source ./lib/env-loader.sh local
fi

# Safely eval Devbox's direnv snippet (non-blocking)
if command -v devbox >/dev/null 2>&1; then
  _HOMELAB_SAVED_OPTS="$(set +o)"
  set +u
  eval "$(devbox generate direnv --print-envrc 2>/dev/null)" || true
  eval "$_HOMELAB_SAVED_OPTS" || true
  unset _HOMELAB_SAVED_OPTS
fi

if command -v mise >/dev/null 2>&1; then
  eval "$(mise direnv activate 2>/dev/null)" || true
  if command -v use >/dev/null 2>&1; then
    use mise 2>/dev/null || true
  fi
fi

export NODE_ENV=${NODE_ENV:-development}
export NX_DAEMON=${NX_DAEMON:-false}
export RUST_LOG=${RUST_LOG:-info}
export PYTHONPATH="$PWD"
export UV_CACHE_DIR="$PWD/.cache/uv"
export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}"
export PATH="$PNPM_HOME:$HOME/.volta/bin:$HOME/.cargo/bin:$PATH"
```
* **Polyglot builds:** Nx handles Node, Python, and Rust seamlessly.
* **Idempotent automation:** CI/CD shells call `./lib/env-loader.sh` directly; Just targets remain reusable everywhere.
* **Secure reproducibility:** SOPS manages all secrets, no plaintext leakage.
* **Branch clarity:** `dev` → `stage` → `main` promotion path baked into recipes and workflows.

---

### ✓ Completed → Next:

Set up:

1. `.envrc` template that shells out to `lib/env-loader.sh` and document `direnv allow`.
2. `devbox.json` (with all required binaries).
3. `.mise.toml` (Node, Python, Rust versions).
4. `.volta` and Cargo project scaffolds.

→ Say **“devbox and mise baseline”** to generate those configuration files next.

---

Correct. Each tool should first initialize its own configuration to ensure correct defaults and avoid hand-rolled config drift. Below is the proper **sequence**, the **commands to run**, and **file contents** for a clean, reproducible monorepo setup.

---

## 🧩 Correct Setup Sequence

| Step | Purpose                                  | Command(s)                                              | Notes                                                  |
| ---- | ---------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| 1    | Initialize Git                           | `git init && git branch -m main`                        | Create `dev`/`stage` branches immediately after.       |
| 2    | Initialize Nx workspace                  | `npx create-nx-workspace@latest . --preset=empty`       | Empty workspace for polyglot monorepo                  |
| 3    | Initialize Devbox                        | `devbox init`                                           | Creates `devbox.json`                                  |
| 4    | Initialize Mise                          | `mise init > .mise.toml` (manual edit after)            | Manages runtime versions                               |
| 5    | Initialize Just                          | `touch Justfile`                                        | Create and fill recipes                                |
| 6    | Initialize Volta (Node toolchain)        | `volta setup`                                           | Installs `~/.volta`, pins Node/pnpm for Nx             |
| 7    | Initialize Cargo                         | `cargo init --vcs none`                                 | Adds `Cargo.toml` if Rust adapters exist               |
| 8    | Add Chezmoi management                   | `chezmoi init --source=~/dotfiles`                      | Manage reproducible local config                       |
| 9    | Configure direnv for environment loading | `cat <<'EOF' > .envrc` … `direnv allow`                 | Local-only; delegates to `lib/env-loader.sh`           |
| 10   | Initialize CI                            | `gh workflow init` or copy prebuilt GitHub Actions YAML | Call `./lib/env-loader.sh ci` instead of `direnv`      |

---

## ⚙️ `.envrc`

```bash
# .envrc
# Local-only environment composition — do not use in CI/CD.
if [[ -f "./lib/env-loader.sh" ]]; then
  # shellcheck disable=SC1091
  source ./lib/env-loader.sh local
fi

use devbox
eval "$(mise activate direnv)"

export NODE_ENV=${NODE_ENV:-development}
export NX_DAEMON=${NX_DAEMON:-false}
export RUST_LOG=${RUST_LOG:-info}
export PYTHONPATH="$PWD"
export UV_CACHE_DIR="$PWD/.cache/uv"
export PNPM_HOME="$HOME/.local/share/pnpm"
export PATH="$PNPM_HOME:$HOME/.volta/bin:$HOME/.cargo/bin:$PATH"
```

---

## 🧠 Example `devbox.json`

```json
{
  "packages": [
    "nodejs@lts",
    "pnpm",
    "python@3.11",
    "rustup",
    "direnv",
    "just",
    "mise",
    "sops"
  ],
  "shell": {
    "init_hook": [
      "if [ -f ./lib/env-loader.sh ]; then source ./lib/env-loader.sh shell; fi",
      "eval \"$(mise activate bash)\"",
      "export PATH=\"$HOME/.cargo/bin:$HOME/.volta/bin:$PATH\""
    ]
  }
}
```

---

## 🧩 Example `.mise.toml`

```toml
[tools]
node = "lts"
python = "3.11"
rust = "stable"

[env]
RUST_LOG = "info"
UV_CACHE_DIR = ".cache/uv"
```

---

## 🧱 Example `Justfile`

```makefile
# Justfile
default:
    @just --list

build:
    npx nx run-many --target=build --all

test:
    npx nx run-many --target=test --all

lint:
    npx nx run-many --target=lint --all

deploy:
    npx nx run-many --target=deploy --all

clean:
    rm -rf dist .cache

doctor:
    ./scripts/doctor.sh

promote-stage:
    git push origin HEAD:stage

promote-main:
    git push origin stage:main

ci-bootstrap:
    ./lib/env-loader.sh ci
    npx nx run-many --target=lint --all
```

---

## 🗂️ `nx.json` (minimal base)

```json
{
  "extends": "nx/presets/core.json",
  "npmScope": "ainativepdk",
  "affected": { "defaultBase": "main" },
  "tasksRunnerOptions": {
    "default": {
      "runner": "nx/tasks-runners/default",
      "options": { "cacheableOperations": ["build", "lint", "test"] }
    }
  }
}
```

---

## 🧩 Example `workspace.json`

```json
{
  "version": 2,
  "projects": {}
}
```

---

## ✅ Next 3 Actions

1. Run the 10 commands in sequence above to scaffold tooling.
2. Copy `.envrc`, `devbox.json`, `.mise.toml`, `Justfile` into root and commit with Chezmoi.
3. Run `direnv allow`, `just doctor`, and `just build`; then execute `just ci-bootstrap` (no direnv) to validate CI parity.

---

## 🔀 Branch Workflow Playbook

- **dev branch:** Default integration branch. Feature branches target `dev` and trigger lightweight CI (`just ci-bootstrap`).
- **stage branch:** Receives promotion from `dev` after review. Runs full integration tests, smoke deploys, and artifact certification.
- **main branch:** Production-ready. Only merge from `stage` once checks and approvals succeed. Tags originate here.
- **Promotion commands:** Use `just promote-stage` to push the current HEAD to `stage`, and `just promote-main` after staging sign-off.
- **Hotfix handling:** Branch from `main`, run full CI, then merge back into both `main` and `stage` to keep them in sync.
