# Setup Ansible

Prepare Ansible to manage homelab nodes via Tailscale SSH with Molecule-backed testing.

## Prerequisites

- `HOMELAB=1` and active Tailscale session if you plan to reach real nodes.
- Python tooling installed from `.mise.toml` (`ansible-core 2.18.1`, `molecule 5.1.0`).
- Docker available for Molecule tests (optional but recommended).

## Steps

1. **Install Ansible dependencies with `uv`**

   Tool versions are pinned in `.mise.toml` (authoritative source via Context7 MCP).

   Enter a reproducible dev environment first (either `mise activate` or `devbox shell`):
   ```zsh
   # Option A: use mise (auto-activated via .envrc)
   direnv allow

   # Option B: use devbox (manual entry)
   devbox shell
   ```

   Then install Python tools with `uv` using the pinned Python from `.mise.toml`:
   ```zsh
   cd infra/ansible-bootstrap

   # Create venv via uv and activate it
   uv venv
   source .venv/bin/activate

   # Install deps (versions are specified in requirements.txt)
   uv pip install -r requirements.txt

   # Verify installations
   ansible --version    # should show 2.18.x
   molecule --version   # should show 5.1.x
   pytest --version     # should show 8.x
   ```

   **Note:** Always run these installs inside `devbox shell` or after `mise activate` so `uv` and the pinned Python version from `.mise.toml` are used.
2. **Configure inventory**
   ```bash
   cp docs/Reference/example.ansible.env infra/ansible.env
   sops --encrypt --input-type dotenv --output-type dotenv \
     --age "$(age-keygen -y ~/.config/sops/age/keys.txt)" \
     infra/ansible.env > infra/ansible.env.sops
   shred -u infra/ansible.env

   $EDITOR infra/ansible-bootstrap/inventory/homelab.yml
   # Add entries referencing Tailscale IPs and ACL tags
   ```
3. **Verify Tailscale SSH transport**
   ```bash
   HOMELAB=1 REQUIRE_TAILSCALE=1 just ansible-ping
   ```
4. **Practice runs**
   ```bash
   HOMELAB=1 just ansible-check          # dry-run playbook
   HOMELAB=1 DEPLOY_CONFIRM=yes just ansible-deploy
   ```
5. **Test roles with Molecule**
   ```bash
   just ansible-molecule-test            # create → converge → verify → destroy
   ```

## Validation Checklist

- `ansible.cfg` should reference `inventory/` and `transport = ssh`.
- All playbooks must reference hosts by Tailscale IP or `ssh://` alias, never raw LAN IPs.
- Molecule logs should prove your roles work before touching physical nodes.

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
