# Setup Pulumi

Configure Pulumi with typed stacks, encrypted credentials, and the XDG-friendly backend paths used throughout the repo.

## Prerequisites

- `HOMELAB=1` exported (direnv will do this if your age key exists).
- Tools installed via `mise install` (Pulumi 3.207.0, Bun 1.2.36).
- Age key at `~/.config/sops/age/keys.txt` so you can encrypt secrets.

## Steps

1. **Choose a backend**
   - *Local (default)*:
     ```bash
     export PULUMI_LOCAL_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/pulumi"
     mkdir -p "$PULUMI_LOCAL_STATE"
     export PULUMI_BACKEND_URL="file://$PULUMI_LOCAL_STATE"
     ```
   - *Pulumi Cloud*:
     - Create an org/account at https://app.pulumi.com and generate an access token.
     - `export PULUMI_ACCESS_TOKEN="pul-..." && pulumi login`.
   - *S3-compatible*:
     ```bash
     export PULUMI_BACKEND_URL="s3://my-pulumi-state"
     ```
2. **Install dependencies**
   ```bash
   cd infra/pulumi-bootstrap
   bun install
   ```
3. **Initialize or select a stack**
   ```bash
   HOMELAB=1 STACK_NAME=dev just pulumi-stack-init
   # or
   pulumi stack select dev
   ```
4. **Configure typed secrets** using the provided template:
   ```bash
   cp docs/Reference/example.pulumi.env infra/pulumi.env
   $EDITOR infra/pulumi.env
   sops --encrypt --input-type dotenv --output-type dotenv \
     --age "$(age-keygen -y ~/.config/sops/age/keys.txt)" \
     infra/pulumi.env > infra/pulumi.env.sops
   shred -u infra/pulumi.env
   ```
5. **Preview and apply**
   ```bash
   just pulumi-preview
   HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-up
   ```

## Validation

- Pulumi commands should log the backend URL they are talking to (file:// path by default).
- The TypeScript program in `infra/pulumi-bootstrap/index.ts` uses branded types, so TypeScript must compile cleanly (`bunx tsc --noEmit`).
- `just pulumi-up` refuses to run unless both `HOMELAB=1` and a confirmation token are provided.

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
