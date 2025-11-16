# Environment Variables

| Variable | Type | Default | Purpose | Required For |
| --- | --- | --- | --- | --- |
| `HOMELAB` | `'0'` or `'1'` | `0` | Gates every privileged command and script | Pulumi/Ansible/Nx recipes, tests |
| `DEPLOY_CONFIRM` | string (`yes`, interactive prompt) | _(unset)_ | Prevents unattended deploys; must equal `yes` for non-interactive runs | `just deploy`, `pulumi-up`, `ansible-deploy`, `nx-distributed-build` |
| `DRY_RUN` | `'0'` or `'1'` | `0` | Enables no-op preview mode in just recipes | All guarded recipes that support rehearsal |
| `REQUIRE_TAILSCALE` | `'0'` or `'1'` | `0` | Forces scripts to validate Tailscale CLI and active session | High-sensitivity Pulumi/Ansible/Nx runs |
| `AGE_RECIPIENT` | age public key `age1...` | _(required when encrypting)_ | Recipient for SOPS encryption | `just tailscale-encrypt`, `just nx-encrypt-config`, manual `sops` commands |
| `PULUMI_LOCAL_STATE` | filesystem path | `${XDG_STATE_HOME:-$HOME/.local/state}/pulumi` | Local backend storage | Pulumi previews/up/destroy when not using cloud backend |
| `PULUMI_BACKEND_URL` | URI (`file://` or `s3://` or `https://app.pulumi.com/...`) | Derived from `PULUMI_LOCAL_STATE` | Points Pulumi CLI at the correct backend | Pulumi CLI & just recipes |
| `PULUMI_ACCESS_TOKEN` | Pulumi cloud token | _(unset)_ | Authenticates to Pulumi Cloud when using hosted backend | Pulumi login on hosted backend |
| `STACK_NAME` | string | `dev` | Selects stack for `just pulumi-stack-init` | Pulumi stack initialization |
| `NX_SHARED_SECRET` | random string | _(stored in `infra/nx-agents.env.sops`)_ | Auth token for Nx Cloud agents | `just nx-start-agent`, distributed builds |
| `NX_AGENT_IPS` | comma-separated IP list | _(stored in secrets)_ | Documented list of agent addresses for orchestration | Nx distributed workflows |
| `TAILSCALE_AUTHKEY` | secret string | _(stored in secrets)_ | Joins nodes to tailnet programmatically | `just tailscale-encrypt`, onboarding nodes |
| `TAILSCALE_WINDOWS_IP` | IPv4 string | _(optional)_ | Records host IP when using WSL2 + Windows Tailscale | References in scripts connecting to Windows daemon |
| `TAILNET` | string | _(optional)_ | Human-friendly name of the tailnet | Logging/diagnostics |
| `CACHE_DIR` | path | `${XDG_STATE_HOME:-$HOME/.local/state}/nx-cache` | Nx cache storage | `just nx-cache-*` recipes |

Use `docs/Reference/example.*` files as templates when creating plaintext `.env` files before encryption.
