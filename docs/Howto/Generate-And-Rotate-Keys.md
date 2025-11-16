# Generate and Rotate Keys

Use this runbook to create new cryptographic material and rotate existing keys without leaving plaintext artifacts in git history.

## Age / SOPS Keys

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
age-keygen -y ~/.config/sops/age/keys.txt   # prints public recipient
```

Update `.sops.yaml` recipients if you introduce a new key for teammates or CI. Re-encrypt existing secrets with `sops updatekeys file.sops`.

## Tailscale Auth Keys

1. Generate a reusable auth key in the Tailscale admin console (scoped to your tailnet, ideally reusable key with expiry).
2. Run `just tailscale-rotate-key` (enforces `HOMELAB=1`).
3. Update `infra/tailscale.env`, then encrypt using `just tailscale-encrypt` (requires `AGE_RECIPIENT`).

## Nx Shared Secret

1. Decrypt the agent config:
   ```bash
   sops -d --input-type dotenv --output-type dotenv infra/nx-agents.env.sops > /tmp/nx.env
   ```
2. Replace `NX_SHARED_SECRET` with a new random value (`openssl rand -hex 32`).
3. Re-encrypt and shred the plaintext:
   ```bash
   sops --encrypt --input-type dotenv --output-type dotenv \
     --age "$(age-keygen -y ~/.config/sops/age/keys.txt)" \
     /tmp/nx.env > infra/nx-agents.env.sops
   shred -u /tmp/nx.env
   ```

## Pulumi Stack Secrets Provider

If you switch from the default provider to a cloud KMS, run:
```bash
cd infra/pulumi-bootstrap
pulumi stack change-secrets-provider "awskms://alias/pulumi-secrets?region=us-east-1"
```

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
