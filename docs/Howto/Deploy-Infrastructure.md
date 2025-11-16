# Deploy Infrastructure

Execute infrastructure changes safely by chaining Pulumi previews with Ansible playbooks and honoring every guard variable.

## Pre-flight Checks

1. `HOMELAB=1` exported (verify with `just detect-homelab`).
2. `DEPLOY_CONFIRM=yes` set for automation or plan to confirm interactively.
3. `REQUIRE_TAILSCALE=1` when operating across the tailnet.
4. Secrets decrypted only in memory (`sops -d --input-type dotenv --output-type dotenv infra/*.sops`).

## Workflow

1. **Preview Pulumi changes**
   ```bash
   just pulumi-preview
   ```
2. **Apply Pulumi stack**
   ```bash
   HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-up
   # Use DRY_RUN=1 for rehearsals
   HOMELAB=1 DRY_RUN=1 just pulumi-up
   ```
3. **Run Ansible check mode**
   ```bash
   HOMELAB=1 REQUIRE_TAILSCALE=1 just ansible-check
   ```
4. **Deploy with Ansible**
   ```bash
   HOMELAB=1 REQUIRE_TAILSCALE=1 DEPLOY_CONFIRM=yes just ansible-deploy
   ```
5. **Coordinate Nx distributed builds** (optional)
   ```bash
   HOMELAB=1 DEPLOY_CONFIRM=yes just nx-distributed-build
   ```

## Rollback Strategy

- **Pulumi**: `HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-destroy` removes resources tied to the selected stack.
- **Ansible**: add `state=absent` tasks or dedicated rollback playbooks, then run them with `just ansible-deploy`.
- **Nx Agents**: restart via `scripts/nx-agent-restart.sh` or disable cache servers with `just nx-cache-server-stop` if new builds misbehave.

## Observability

- Monitor Pulumi output; failures leave the stack in a safe state but may require `pulumi cancel`.
- Ansible logs show which hosts enforced `REQUIRE_TAILSCALE`.
- Nx commands print which agents accepted work; verify they match `infra/nx-agents.env.sops`.

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
