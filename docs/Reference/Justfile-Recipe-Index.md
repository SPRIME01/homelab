# Justfile Recipe Index

## Diagnostics

| Recipe | Description | Guards | Example |
| --- | --- | --- | --- |
| `check` | Runs `mise doctor` and `devbox doctor` | None | `just check` |
| `env` | Prints sorted environment variables | None | `just env` |
| `detect-homelab` | Reports whether the age key exists and how to export `HOMELAB=1` | None (read-only) | `just detect-homelab` |
| `ci-validate` | Dumps justfile for syntax errors then runs `tests/run-tests.sh` | None (tests mock guards) | `just ci-validate` |

## Deployment Entry Point

| Recipe | Description | Guards | Example |
| --- | --- | --- | --- |
| `deploy` | Composite guard that verifies `HOMELAB`, confirmations, DRY_RUN, and optional Tailscale before allowing infra workflows | `HOMELAB=1`, confirmation prompts, optional `REQUIRE_TAILSCALE=1` | `HOMELAB=1 DEPLOY_CONFIRM=yes just deploy` |

## Tailscale Helpers

| Recipe | Description | Guards | Example |
| --- | --- | --- | --- |
| `tailscale-status` | Shows tailnet status; safe to run anywhere | None | `just tailscale-status` |
| `tailscale-join` | Delegates to `scripts/tailscale-join.sh` | Indirect guard inside script | `just tailscale-join` |
| `tailscale-ssh-enable` | Enables Tailscale SSH on the current node | `HOMELAB=1`, tailscale CLI present | `HOMELAB=1 just tailscale-ssh-enable` |
| `tailscale-ssh-disable` | Disables SSH and leaves Tailscale up | `HOMELAB=1` | `HOMELAB=1 just tailscale-ssh-disable` |
| `tailscale-rotate-key` | Describes how to rotate auth keys securely | `HOMELAB=1` | `HOMELAB=1 just tailscale-rotate-key` |
| `tailscale-encrypt` | Encrypts `infra/tailscale.env` with SOPS; shred plaintext | Requires `AGE_RECIPIENT` and `TAILSCALE_AUTHKEY` | `AGE_RECIPIENT=age1... TAILSCALE_AUTHKEY=tskey- just tailscale-encrypt` |

## Pulumi Recipes

| Recipe | Description | Guards | Example |
| --- | --- | --- | --- |
| `pulumi-preview` | Installs deps, configures local backend, runs `pulumi preview` | Honors `DRY_RUN=1` to short-circuit | `just pulumi-preview` |
| `pulumi-up` | Full deployment with HOMELAB + confirmation + optional DRY_RUN | `HOMELAB=1`, confirmation, optional `DRY_RUN` | `HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-up` |
| `pulumi-destroy` | Destroys stack with "destroy" confirmation prompt | `HOMELAB=1`, typed confirmation, optional `DRY_RUN` | `HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-destroy` |
| `pulumi-stack-init` | Initializes a named stack using local backend defaults | `HOMELAB=1` | `HOMELAB=1 STACK_NAME=dev just pulumi-stack-init` |

## Ansible Recipes

| Recipe | Description | Guards | Example |
| --- | --- | --- | --- |
| `ansible-ping` | Tests inventory over Tailscale SSH | `HOMELAB=1`, optional `REQUIRE_TAILSCALE=1` | `HOMELAB=1 just ansible-ping` |
| `ansible-deploy` | Applies playbooks with confirmation and optional DRY_RUN | `HOMELAB=1`, confirmation, optional `REQUIRE_TAILSCALE`, optional `DRY_RUN` | `HOMELAB=1 REQUIRE_TAILSCALE=1 DEPLOY_CONFIRM=yes just ansible-deploy` |
| `ansible-check` | Runs playbooks in check mode with Tailscale guard | `HOMELAB=1`, optional `REQUIRE_TAILSCALE` | `HOMELAB=1 just ansible-check` |
| `ansible-molecule-test` | Runs Molecule test suite end-to-end | None (Docker only) | `just ansible-molecule-test` |
| `ansible-molecule-converge` | Applies Molecule role | None | `just ansible-molecule-converge` |
| `ansible-molecule-verify` | Runs Molecule verification phase | None | `just ansible-molecule-verify` |
| `ansible-molecule-destroy` | Tears down Molecule instances | None | `just ansible-molecule-destroy` |

## Nx Distributed Execution

| Recipe | Description | Guards | Example |
| --- | --- | --- | --- |
| `nx-init` | Installs pnpm deps, validates `nx.json` | `HOMELAB=1` | `HOMELAB=1 just nx-init` |
| `nx-encrypt-config` | Encrypts `infra/nx-agents.env` | Requires `AGE_RECIPIENT`, plaintext file present | `AGE_RECIPIENT=age1... just nx-encrypt-config` |
| `nx-start-agent` | Decrypts agent config and starts Nx Cloud agent (per machine) | `HOMELAB=1`, `REQUIRE_TAILSCALE` default `1`, requires sops key | `HOMELAB=1 just nx-start-agent` |
| `nx-distributed-build` | Runs distributed build with confirmation + DRY_RUN support | `HOMELAB=1`, confirmation, optional `DRY_RUN` | `HOMELAB=1 DEPLOY_CONFIRM=yes just nx-distributed-build` |
| `nx-test` | Executes `nx run-many --target=test --all` | Optional `DRY_RUN` | `just nx-test` |
| `nx-affected-build` | Runs affected build versus `main` | Optional `DRY_RUN` | `just nx-affected-build` |
| `nx-cache-prune` | Deletes cache entries older than 7 days (or prints what would happen) | Optional `DRY_RUN` | `DRY_RUN=1 just nx-cache-prune` |
| `nx-cache-server-start` | Launches HTTP cache server bound to Tailscale IP | `HOMELAB=1`, tailscale CLI required | `HOMELAB=1 just nx-cache-server-start` |
| `nx-cache-server-stop` | Stops the cache server or cleans stale processes | None | `just nx-cache-server-stop` |
| `nx-cache-health` | Checks cache HTTP endpoint | None (warns if curl missing) | `just nx-cache-health` |
| `nx-discover-agents` | Lists candidate tailnet machines via Tailscale | `HOMELAB=1` | `HOMELAB=1 just nx-discover-agents` |

Use these tables when deciding which recipe best matches your desired workflow and whether you must export additional guard variables before execution.
