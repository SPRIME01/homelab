# System Architecture

The homelab stack layers devbox, mise, and direnv on top of strict guard rails so every privileged action is traced back to a trusted identity. The diagram below shows the workflow from an interactive shell to the automation tools.

```mermaid
flowchart TD
  A[Developer Shell] -->|enter project| B(devbox shell)
  B --> C[mise activate]
  C --> D[.envrc]
  D --> E{HOMELAB detection}
  E -->|HOMELAB=1| F[just recipes]
  E -->|HOMELAB=0| G[Fail closed]
  F --> H[Pulumi CLI]
  F --> I[Ansible + Molecule]
  F --> J[Nx Distributed Tasks]
  D --> K[XDG paths (state/cache/config)]
  K --> L[SOPS/age key lookup]
  L --> E
```

## Tool Chain

- **Devbox**: Creates a reproducible base image (packages like git, jq, curl) but leaves activation explicit. Use `devbox shell` when you want system packages plus mise-managed tools.
- **Mise**: Pins versions defined in `.mise.toml` (bun 1.2.36, python 3.13.9, pulumi 3.207.0, etc.) and places them on `PATH` automatically once `.envrc` activates mise.
- **direnv / .envrc**: Detects `~/.config/sops/age/keys.txt` and exports `HOMELAB=1` only on trusted machines. It also sets `PULUMI_LOCAL_STATE` and `XDG_STATE_HOME` friendly defaults so Pulumi, Nx cache, and logs never spill into the repo.
- **just**: Central dispatcher for guarded workflows. Every recipe follows the `HOMELAB` + `DEPLOY_CONFIRM` + `DRY_RUN` + `REQUIRE_TAILSCALE` guard pattern defined in `.github/copilot-instructions.md`.

## Data Flow and XDG Paths

- Secrets and credentials live under `infra/*.env.sops` and are decrypted only when recipes run with `HOMELAB=1`.
- Pulumi local state defaults to `${XDG_STATE_HOME:-$HOME/.local/state}/pulumi` and Nx cache uses `${XDG_STATE_HOME:-$HOME/.local/state}/nx-cache`.
- Scripts import helper functions from `lib/env-loader.sh` (the replacement for the deprecated `scripts/load_env.sh`). Always prefer XDG-friendly paths so multiple developers can share the repo safely.

## Guard Layers

1. `.envrc` only exports `HOMELAB=1` when the private age key exists locally.
2. Just recipes enforce `HOMELAB=1` and interactive confirmations before running.
3. Infrastructure commands check for `REQUIRE_TAILSCALE=1` to ensure the tailnet session is active.
4. Pulumi and Ansible code repeat the same guard logic at runtime (fail-safe default).
5. Tests in `tests/*.sh` verify the guard rails before CI accepts a change.

Treat the architecture as a chain: if any link is missing, infrastructure commands must stop rather than guessing.
