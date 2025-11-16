# Tutorial: Your First Deployment

**Audience**: Beginner (30 minutes)

## Goal

Generate age keys, join the tailnet, encrypt your first secret, and perform a guarded dry-run deployment end to end.

## Prerequisites

- Laptop with `direnv`, `mise`, `pnpm`, and `sops` installed.
- Access to the Tailscale admin console.
- Ability to install the pinned versions via `mise install`.

## Steps

1. **Install toolchain**
   ```bash
   mise install
   pnpm install
   ```
2. **Create age key**
   ```bash
   mkdir -p ~/.config/sops/age
   age-keygen -o ~/.config/sops/age/keys.txt
   chmod 600 ~/.config/sops/age/keys.txt
   direnv allow
   just detect-homelab   # should report HOMELAB=1 now
   ```
3. **Join Tailscale**
   ```bash
   tailscale up --authkey tskey-...
   tailscale status
   ```
4. **Encrypt a secret**
   ```bash
   cp docs/Reference/example.env infra/bootstrap.env
   $EDITOR infra/bootstrap.env
   AGE_RECIPIENT=$(age-keygen -y ~/.config/sops/age/keys.txt)
   sops --encrypt --input-type dotenv --output-type dotenv \
     --age "$AGE_RECIPIENT" infra/bootstrap.env > infra/bootstrap.env.sops
   shred -u infra/bootstrap.env
   ```
5. **Run guarded deploy (dry run)**
   ```bash
   HOMELAB=1 DRY_RUN=1 DEPLOY_CONFIRM=yes just deploy
   HOMELAB=1 DRY_RUN=1 DEPLOY_CONFIRM=yes just pulumi-up
   HOMELAB=1 DRY_RUN=1 REQUIRE_TAILSCALE=1 just ansible-deploy
   ```
6. **Validate test suite**
   ```bash
   just ci-validate
   ```

## Success Criteria

- `just detect-homelab` prints "HOMELAB detected".
- `tailscale status` lists your machine with the expected tag.
- `sops -d --input-type dotenv infra/bootstrap.env.sops | head -n 3` shows decrypted content without errors.
- `HOMELAB=1 DRY_RUN=1 DEPLOY_CONFIRM=yes just deploy` exits `0` with a "DRY RUN" message.
- `just ci-validate` exits `0` (skipped tests may output exit code `2` for individual suites but the runner should pass).

Complete this tutorial before moving on to `docs/Howto/Setup-Pulumi.md`.
