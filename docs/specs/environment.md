# 🧩 Home Lab Environment Specification
**Purpose:** Unified, reproducible development environment for multi-language (Node, Python, Rust, TypeScript) projects orchestrated with Nx.

---

## 🔁 System Overview (Mermaid Diagram)

```mermaid
flowchart TD
    A[Chezmoi<br>Dotfile + State Manager] --> A1[direnv<br>Directory-Aware Env Guard]
    A1 --> A2[lib/env-loader.sh<br>Environment Composition]
    A2 --> B[Devbox<br>Toolchain Isolation]
    B --> C[mise<br>Runtime Version Manager]
    C --> D1[Volta<br>Node Toolchain Manager]
    C --> D2[SOPS<br>Secrets Management]
    D2 --> E[Just<br>Task Orchestration]
    E --> F[Nx<br>Monorepo & Build Orchestrator]
    F --> G1[pnpm<br>Node Package Manager]
    F --> G2[uv<br>Python Env Manager]
    F --> G3[Cargo<br>Rust Package Manager]
    G1 --> H[Applications / Services]
    G2 --> H
    G3 --> H
````

**Flow Summary:**
Chezmoi bootstraps the host configuration → direnv evaluates `.envrc` and runs `lib/env-loader.sh` to compose secrets and runtime hooks → Devbox provides isolated system toolchains → mise manages language runtimes → Volta ensures deterministic Node/TypeScript toolchains → SOPS handles secrets → Just runs developer commands → Nx orchestrates builds/tests → pnpm, uv, and Cargo handle per-language dependency management.

---

## ⚙️ Layered Environment Strategy

| Layer | Tool                  | Primary Function                                  |
| :---- | :-------------------- | :------------------------------------------------ |
| 0     | **Chezmoi**           | Dotfile and state management                      |
| 0a    | **direnv**            | Per-directory environment activation via `lib/env-loader.sh` |
| 1     | **Devbox**            | Toolchain isolation                               |
| 2     | **mise**              | Runtime version management (Node, Python, Rust)   |
| 2a    | **Volta**             | Node toolchain pinning (npm, pnpm, yarn)          |
| 3     | **SOPS**              | Secrets encryption/decryption                     |
| 4     | **Just**              | Task orchestration and entrypoints                |
| 5     | **Nx**                | Monorepo orchestration, dependency graph, caching |
| 6     | **pnpm / uv / Cargo** | Package and environment management                |

---

## 🧱 Tool Role Specifications

### 1. Chezmoi — Host/User Configuration Layer

| Function                  | Description                                                             | Integration Points                                                          |
| :------------------------ | :---------------------------------------------------------------------- | :-------------------------------------------------------------------------- |
| **Dotfile deployment**    | Manages reproducible configuration across hosts.                        | Deploys `devbox.json`, `.mise.toml`, `.volta`, `.justfile`, `nx.json`, etc. |
| **Secret key deployment** | Places private keys for SOPS securely in `~/.config/sops/age/keys.txt`. | Enables SOPS decryption.                                                    |
| **Bootstrap automation**  | Installs base toolchain configs and environment files.                  | Prepares environment before Devbox initialization.                          |

---

### 1a. direnv — Automatic Environment Activation Layer

| Function                        | Description                                                                 | Integration Points                                                                |
| :------------------------------ | :-------------------------------------------------------------------------- | :-------------------------------------------------------------------------------- |
| **Policy enforcement**          | Uses `.envrc` allowlist to gate environment loading for trusted directories | Chezmoi installs the managed `.envrc` template and updates the allow list.        |
| **Environment composition**     | Executes `lib/env-loader.sh` to merge secrets, `.env` overlays, and runtime hooks | Ensures Devbox, mise, and Just commands see a consistent environment.             |
| **Developer ergonomics**        | Auto-loads/unloads project variables when entering/leaving the repo         | Keeps local shells in sync with Just/Nx workflows without manual sourcing.       |
| **CI/CD bypass**                | Documented as a local-only helper; pipelines call `lib/env-loader.sh` directly | GitHub Actions and other CI jobs bootstrap without `direnv` dependencies.        |
| **Fallback compatibility guard**| Warns when deprecated `scripts/load_env.sh` is invoked                       | Highlights migration path toward the new loader for legacy scripts.              |

---

### 2. Devbox — OS-Level Toolchain Isolation

| Function                  | Description                                                      | Integration Points                                                   |
| :------------------------ | :--------------------------------------------------------------- | :------------------------------------------------------------------- |
| **Isolated environments** | Provides per-project sandbox with pinned toolchains.             | Runs mise, Volta, pnpm, uv, Cargo, and Nx inside a consistent shell. |
| **Reproducible builds**   | Declares OS-level dependencies in `devbox.json`.                 | Chezmoi deploys and updates this file.                               |
| **Environment parity**    | Ensures consistent setups for local, CI, and remote development. | Nx and Just tasks depend on Devbox isolation.                        |

---

### 3. mise — Runtime Version Management

| Function                 | Description                                                    | Integration Points                                           |
| :----------------------- | :------------------------------------------------------------- | :----------------------------------------------------------- |
| **Runtime pinning**      | Locks Node, Python, and Rust versions via `.mise.toml`.        | Ensures compatible interpreters for pnpm, uv, Cargo, and Nx. |
| **Runtime switching**    | Automatically activates correct runtimes inside Devbox shells. | Provides runtime context to Volta and Nx executors.          |
| **Language unification** | Centralizes runtime versions for polyglot projects.            | Maintains compatibility across all toolchains.               |

---

### 3a. Volta — Node Toolchain Manager

| Function                    | Description                                                  | Integration Points                                           |
| :-------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **Tool pinning**            | Pins Node, npm, pnpm, and Yarn versions per project.         | Ensures consistent JS/TS toolchain versions across machines. |
| **Binary shims**            | Provides fast, local binary resolution.                      | Nx executors call Volta-managed binaries for Node tasks.     |
| **Complementary with mise** | Volta handles Node tools, mise handles Node runtime version. | Ensures complete reproducibility.                            |

---

### 4. SOPS — Encrypted Secrets Management

| Function                         | Description                                     | Integration Points                            |
| :------------------------------- | :---------------------------------------------- | :-------------------------------------------- |
| **Secret encryption/decryption** | Encrypts `.env.sops` and other sensitive files. | Just and Nx tasks decrypt secrets at runtime. |
| **Key management**               | Uses Age or GPG keys deployed by Chezmoi.       | Enables automated secret access.              |
| **Security integration**         | Keeps secrets version-controlled but protected. | Works alongside Nx deploy workflows.          |

---

### 5. Just — Task Orchestration Layer

| Function                | Description                                                     | Integration Points                                   |
| :---------------------- | :-------------------------------------------------------------- | :--------------------------------------------------- |
| **Command abstraction** | Simplifies developer commands into readable recipes.            | Wraps Nx commands and environment tasks.             |
| **Task sequencing**     | Defines workflows like `just setup`, `just build`, `just test`. | Invokes Nx CLI, SOPS decryption, or Devbox commands. |
| **Consistency layer**   | Provides uniform CLI interface across environments.             | Works with mise and Devbox shells.                   |

---

### 6. Nx — Monorepo and Build Orchestrator

| Function                   | Description                                                      | Integration Points                        |
| :------------------------- | :--------------------------------------------------------------- | :---------------------------------------- |
| **Project orchestration**  | Manages multiple apps, services, and libraries across languages. | Integrates pnpm, uv, Cargo, and Volta.    |
| **Task graph + caching**   | Builds dependency graphs and caches results.                     | Used by Just tasks and CI/CD.             |
| **Code generation**        | Scaffolds code via plugins or generators.                        | Controlled by Just or directly via CLI.   |
| **Distributed builds**     | Optional Nx Cloud or self-hosted cache.                          | Integrates with Devbox or GitHub Actions. |
| **Cross-language support** | Manages Node, Python, and Rust workflows under one workspace.    | mise and Volta ensure correct runtimes.   |

---

### 7. pnpm / uv / Cargo — Package and Environment Managers

| Function                           | Description                                              | Integration Points             |
| :--------------------------------- | :------------------------------------------------------- | :----------------------------- |
| **Language dependency management** | Handles package installs for Node, Python, and Rust.     | Called via Nx tasks.           |
| **Environment isolation**          | uv and Cargo manage per-project virtual envs and crates. | Activated inside Devbox shell. |
| **Reproducibility**                | Lockfiles ensure deterministic builds.                   | Controlled under Nx monorepo.  |

---

## 🧩 Example Execution Flow

1. **Chezmoi** deploys environment config (`devbox.json`, `.mise.toml`, `.volta`, `.justfile`, etc.).
2. **direnv** evaluates `.envrc` and runs `lib/env-loader.sh` to compose environment variables.
3. **Devbox** initializes an isolated development shell.
4. **mise** activates Node, Python, and Rust runtimes.
5. **Volta** provides pinned Node/TS toolchains (npm, pnpm, yarn).
6. **SOPS** decrypts secrets for builds or local tasks.
7. **Just** runs orchestration commands (`just build`, `just deploy`, etc.).
8. **Nx** executes builds/tests using dependency graph and caching.
9. **pnpm / uv / Cargo** resolve and install dependencies.

> **Automation Note:** CI/CD pipelines skip `direnv` and invoke `./lib/env-loader.sh` directly before running Just or Nx commands, ensuring non-interactive jobs have deterministic environments without additional dependencies.

---

## 🧭 Branch & Promotion Strategy

- **main:** Production-ready branch. Protected; only merges from `stage` after validation. Tagged releases deploy from here.
- **stage:** Pre-production validation. GitHub Actions runs full integration suites, destroys test infrastructure after approval, and promotes to `main` when green.
- **dev:** Integration sandbox for feature branches. Lightweight checks (lint, unit tests) run on push, promoting to `stage` via pull request once features stabilize.
- **Feature branches:** Short-lived branches forked from `dev`. Rebase frequently, rely on `just doctor` to verify local readiness, and open PRs targeting `dev`.
- **Hotfix workflow:** Branch from `main`, apply targeted changes, run full CI, then merge back into both `main` and `stage` to keep branches aligned.

---

## 🔒 CI/CD Environment Loading Playbook

1. Check out repo and restore cached Devbox/mise artifacts if available.
2. Run `./lib/env-loader.sh ci` (idempotent mode) to export secrets and runtime variables without `direnv`.
    - CI should ensure a Python runtime is available and prefer `uv` for interpreter management. Best practice: install `uv` (via Devbox packaging or pipx fallback), use `uv python install 3.12` and create/activate a `.venv` pinned to Python 3.12 before running build/test steps.
    - Locally, prefer evaluating Devbox's direnv snippet into your current shell rather than auto-spawning `devbox shell`. Use `devbox generate direnv --print-envrc` inside `.envrc` with a temporary `set +u` guard (see repo's `.envrc`) so Devbox's init hooks are applied non-interactively.
    - CI should ensure a Python runtime is available and prefer `uv` for interpreter management. Best practice: install `uv` (via Devbox packaging or pipx fallback), use `uv python install 3.12` and create/activate a `.venv` pinned to Python 3.12 before running build/test steps.
3. Launch Devbox or containerized shell for builds (`devbox run -- just build`), ensuring parity with local tooling.
4. Execute Nx/Just targets with cache warming and artifact uploads enabled.
5. On success, publish promotion artifacts (manifests, container images) and trigger next-branch workflows.

---

## ✅ Next Steps

1. Template a Chezmoi-managed `.envrc` that delegates to `lib/env-loader.sh` and registers safe direnv permissions (local-only).
2. Add Volta and Cargo configs to Chezmoi templates.
3. Extend `.mise.toml` to include Node, Python, and Rust toolchains.
4. Update `nx.json` and `workspace.json` to recognize Cargo projects and Volta-managed Node builds.
5. Create Just recipes wrapping Nx workflows (`build`, `test`, `lint`, `deploy`), including branch-aware commands (`just promote-stage`, `just promote-main`).
6. Include Volta and Cargo setup in `devbox.json` for reproducible environments.
7. Author GitHub Actions workflows for `dev`, `stage`, and `main`, each using `lib/env-loader.sh` instead of `direnv`.
