# Encrypt New Secrets

Use SOPS + age to protect any new credential files before committing them.

## Steps

1. **Start from a template**
   ```bash
   cp docs/Reference/example.env infra/my-service.env
   ```
2. **Fill values**
   - Use `EDITOR=vim` or your preferred editor.
   - Avoid quotes; keep `KEY=value` pairs per dotenv semantics.
3. **Encrypt**
   ```bash
   AGE_RECIPIENT=$(age-keygen -y ~/.config/sops/age/keys.txt)
   sops --encrypt --input-type dotenv --output-type dotenv \
     --age "$AGE_RECIPIENT" infra/my-service.env > infra/my-service.env.sops
   shred -u infra/my-service.env
   ```
4. **Verify**
   ```bash
   sops -d --input-type dotenv --output-type dotenv infra/my-service.env.sops | head -n 5
   ```
5. **Load at runtime**
   - Source the file like `eval "$(sops -d ... infra/my-service.env.sops)"` inside guarded scripts.
   - Never `cat` plaintext to the console when screen sharing.

## Tips

- Keep `.sops` entries out of `.gitignore` (only plaintext env files are ignored).
- Rotate recipients via `sops updatekeys` after onboarding teammates.
- Store AGE recipients in password managers for offline reference.

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
