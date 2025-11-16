# Add New Homelab Node

Onboard another machine (physical or VM) into the secure Tailscale + Ansible workflow.

## Steps

1. **Prepare the node**
   - Install the Tailscale client.
   - Install system dependencies (Docker, systemd timers) as needed by your roles.
2. **Join the tailnet**
   ```bash
   sudo tailscale up --authkey ${TAILSCALE_AUTHKEY} --hostname <hostname> --advertise-tags=tag:homelab-server
   ```
   Approve the node in the Tailscale admin console and ensure ACL tags match your policy.
3. **Label the inventory**
   ```bash
   $EDITOR infra/ansible-bootstrap/inventory/homelab.yml
   # Add host entry referencing the node's tailscale IP
   ```
4. **Verify SSH connectivity**
   ```bash
   HOMELAB=1 just ansible-ping --limit <hostname>
   ```
5. **Deploy base configuration**
   ```bash
   HOMELAB=1 DEPLOY_CONFIRM=yes just ansible-deploy -- --limit <hostname>
   ```
6. **Enroll in Nx distributed builds (optional)**
   - Install Node/pnpm via mise or devbox.
   - Run `scripts/nx-agent-restart.sh` to register the agent with the shared secret.

## Validation

- `tailscale status` should list the node with the correct tag.
- `just ansible-check -- --limit <hostname>` must succeed before you run destructive playbooks.
- Nx agent logs should appear in `~/.local/state/nx-cache-server.log` if you configured the cache server.

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
