# Setup Development Environment

Bring a workstation online with the exact tool versions and guard rails expected by the homelab project.

## Prerequisites

- `direnv`, `devbox`, and `mise` installed and on `PATH`.
- Ability to install the pinned versions listed in `.mise.toml`.
- Optional: Python 3.11+ for the bootstrap unit tests.

## Procedure

1. **Initialize devbox and mise** (already checked in, but rerun if files drift):
   ```bash
   devbox init --force                # regenerates devbox.json if schema updates
   mise use                           # ensures local installation matches .mise.toml pins
   mise install
   ```
2. **Approve `.envrc`** to activate mise automatically and expose helper notes about devbox usage:
   ```bash
   direnv allow
   direnv status | grep 'Found RC allowed'
   ```
3. **Verify pinned versions** using the bootstrap tests:
   ```bash
   python3 -m unittest discover -v .tests/bootstrap
   mise ls --current
   ```
4. **Run diagnostics** to confirm guard rails:
   ```bash
   just check
   just detect-homelab
   ```

## Notes

- `.envrc` intentionally does **not** auto-start devbox; follow its comment and run `devbox shell` when you need the Nix-like environment.
- Devbox installs portable tooling (git, curl, jq, postgresql client) without touching the host, while mise handles higher-level CLIs such as Pulumi and pnpm.
- Keep `.tests/bootstrap/*.py` up to date when you add new dev tooling so CI continues to validate the onboarding flow.

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
