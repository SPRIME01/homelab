# Security Model

The homelab treats every machine as untrusted until it proves it holds the correct age key **and** is on the tailnet. All automation inherits five defense layers that intentionally fail closed.

## Defense-in-Depth Layers

| Layer | Control | Implementation | Result |
| --- | --- | --- | --- |
| 1 | Key-based identity | `.envrc` looks for `~/.config/sops/age/keys.txt` and exports `HOMELAB=1` | Only machines with the private key can even attempt a deploy |
| 2 | Explicit confirmation | `DEPLOY_CONFIRM` prompts or env var + typed words (`deploy`, `destroy`, `build`) | Prevents stray CI jobs or scripts from mutating infra silently |
| 3 | Dry-run preview | `DRY_RUN=1` branches in just recipes and IaC code | Ensures every destructive workflow can be rehearsed without impact |
| 4 | Network verification | `REQUIRE_TAILSCALE=1` forces the Tailscale CLI to report a healthy connection | Blocks operations when off the tailnet or before ACL tags are applied |
| 5 | Runtime guard rails | Pulumi/Ansible/Nx code re-check `HOMELAB` and secrets presence | Even if a script bug slips in, the runtime layer still refuses execution |

## Threat Model Matrix

| Threat | Mitigation | Residual Risk |
| --- | --- | --- |
| Accidental deploy from coffee shop Wi-Fi | `HOMELAB=1` never set because age key stays on secure host | If key is copied to laptop intentionally, user assumes the risk |
| Secrets leaked via git | Only `.sops` files committed; references to plaintext files are gitignored; docs emphasize age encryption steps | Compromise is still possible if a developer dumps decrypted env to logs |
| Compromised Nx agent | Agents connect through Tailscale ACL tags and use shared secret from encrypted `infra/nx-agents.env.sops`; runs limited commands | If shared secret leaks, rotate via `docs/Howto/Generate-And-Rotate-Keys.md` |
| Supply chain tampering | `.mise.toml` pins versions and references Context7/GitHub lookup dates; `devbox.json` defines minimal packages | Dependence on upstream release integrity remains |
| Unauthorized SSH | `just tailscale-ssh-enable` enforces HOMELAB and Tailscale CLI, ACLs restrict who can connect | Someone with admin portal access could still change ACLs, so audit Tailscale admin logs |

## Operating Principles

- **Least privilege**: Always prefer Tailnet-restricted SSH (`tag:homelab-wsl2`, `tag:homelab-server`) and keep nodes headless.
- **Auditability**: Run `just ci-validate` + targeted Nx builds before every deploy so logs show the guard checks.
- **Zero trust**: Nothing assumes "developer laptop" is safe; credentials live in `.sops` files, never in shell history.
- **Fast rotation**: Keys, tokens, and Nx shared secrets have documented rotation paths (`Generate-And-Rotate-Keys`, `Encrypt-New-Secrets`).

Review this file whenever you add a new integration. If it skips any layer above, the design is incomplete.
