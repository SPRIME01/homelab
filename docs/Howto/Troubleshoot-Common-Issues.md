# Troubleshoot Common Issues

This guide covers the five failure modes called out in `.github/copilot-instructions.md` and shows the quickest diagnostic commands for each.

## 1. SOPS fails with "invalid character"

**Cause**: Encrypting `.env` files without telling SOPS to treat the file as dotenv.

**Fix**:
```bash
sops --encrypt --input-type dotenv --output-type dotenv \
  --age "$AGE_RECIPIENT" infra/my.env > infra/my.env.sops
```

## 2. Tests hang in CI

**Cause**: A bash test waits for a tool that is not installed instead of exiting `2` (skip).

**Diagnose**:
```bash
bash tests/run-tests.sh | tail -n 20
```

Ensure each suite follows the pattern:
```bash
if ! command -v tailscale >/dev/null 2>&1; then
  echo "SKIP: tailscale CLI missing" >&2
  exit 2
fi
```

## 3. `just deploy` blocked

**Cause**: `HOMELAB`, `DEPLOY_CONFIRM`, or `REQUIRE_TAILSCALE` not satisfied.

**Diagnose**:
```bash
just detect-homelab
env | grep -E 'HOMELAB|DEPLOY_CONFIRM|REQUIRE_TAILSCALE'
```

**Fix**:
```bash
export HOMELAB=1
export DEPLOY_CONFIRM=yes
export REQUIRE_TAILSCALE=1  # optional guard
```

## 4. Encrypted file will not decrypt

**Cause**: Missing `~/.config/sops/age/keys.txt`, wrong permissions, or recipients mismatch.

**Diagnose**:
```bash
ls -l ~/.config/sops/age/keys.txt
sops -d --input-type dotenv --output-type dotenv infra/example.env.sops | head -n 5
```

**Fix**: Ensure `chmod 600` on the key file and that the recipient matches `.sops.yaml`.

## 5. Tailscale commands fail (especially on WSL2)

**Cause**: Linux environment lacks a running tailscaled; WSL2 must talk to Windows host.

**Diagnose**:
```bash
command -v tailscale || echo "Install tailscale binary"
wsl.exe tailscale status || powershell.exe tailscale status
```

**Fix**: Start Tailscale on Windows host, then use `wsl-tailscale-ip` or `tailscale status --json` inside WSL to confirm connectivity.

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
