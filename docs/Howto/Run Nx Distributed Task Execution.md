**Nx Distributed Agents**
- **Purpose**: Describe how to run Nx distributed task execution (agents) across Tailscale-connected machines in this homelab, securely and incrementally.

**Tutorial:**
- **Prereqs**: `HOMELAB=1` (SOPS age key present), `tailscale` CLI installed, `pnpm` v10.22.0, `sops` installed.
- **Bootstrap (orchestrator machine)**:
  - Generate agent secret:

```
bash scripts/generate-nx-agent-secret.sh
```

  - Create `infra/nx-agents.env` using `docs/Reference/example.nx-agents.env` and paste `NX_SHARED_SECRET` and `NX_AGENT_IPS`.
  - Encrypt config:

```
export AGE_RECIPIENT="<age-recipient>"
just nx-encrypt-config
```

  - Initialize workspace:

```
just nx-init
```

- **Start cache server (recommended local HTTP initially)**:

```
just nx-cache-server-start
```

- **Start agents (on each agent machine)**:
  - Ensure `HOMELAB=1` and `sops` keys available.
  - Decrypt and start agent via `just nx-start-agent` or run `scripts/nx-agent-restart.sh`.

- **Run distributed build (orchestrator)**:

```
DEPLOY_CONFIRM=yes DRY_RUN=1 just nx-distributed-build  # test
DEPLOY_CONFIRM=yes just nx-distributed-build            # run
```

**How-to: add new agent (static list)**
- Use `just nx-discover-agents` on a homelab machine to list candidate Tailscale IPs.
- Edit `infra/nx-agents.env` locally, append IPs to `NX_AGENT_IPS`, encrypt with `just nx-encrypt-config`, and distribute `.sops` file to agents.

**Scaling to multiple machines**
- Start additional agents with `just nx-start-agent` on each machine.
- For >10 agents, consider moving cache backend to an NFS or object store (S3-compatible) and update `nx.json` `cacheDirectory`/cache config.

**Subnet routing (Tailscale)**
- If agents are behind a subnet router, ensure the router exposes the cache server port (3333) and tailscale ACLs permit the agent tag to reach the cache server.
- Example ACL entry: allow `tag:homelab-wsl2` between the two agent subnets on port 3333.

**Securing agent tokens**
- Short-term: share a single SOPS-encrypted `NX_SHARED_SECRET` (fast bootstrap).
- Best practice for scale: migrate to per-agent keypairs and use `.sops.yaml` multiple recipients so each agent has its own recipient key.
  - Procedure:
    1. Add new recipients to `.sops.yaml` `age` list for per-agent recipients.
    2. Re-encrypt `infra/nx-agents.env.sops` with the extended recipient list.
    3. Rotate secrets and remove old recipient when all agents upgraded.

**Fallback behavior**
- If Tailscale is unavailable or agents unreachable, Nx will fall back to local execution for affected tasks per its normal semantics; orchestrator logs will indicate fallback.

**Monitoring & Self-Healing**
- `scripts/nx-agent-health-monitor.sh` can be run as a cron or systemd user timer; it checks `tailscale` connectivity, cache server health, and agent process presence and attempts restarts via `just`.
- `scripts/nx-agent-restart.sh` is an idempotent restart helper for agents.
- Systemd user unit for cache is provided at `scripts/nx-cache.service`; install with `systemctl --user enable --now /path/to/scripts/nx-cache.service` after adjusting ExecStart path.

**CI considerations**
- CI uses validation-only runs (no distributed agents) by default. See `.github/workflows/nx-validate.yml` for the Nx validation workflow.
- To migrate CI to use homelab agents, add self-hosted runners joined to your tailnet and update workflows to use `runs-on: [self-hosted, linux]` and start ephemeral agents with `npx nx-cloud start-agent`.

**Reference**
- `nx.json` tasksRunnerOptions: `cacheDirectory: ~/.local/state/nx-cache`, `cacheableOperations: ["build","test","lint"]`.
- Default cache HTTP port: `3333`.

**Troubleshooting**
- If agent won't start: check `~/.local/state/nx-agent.log`, ensure `sops` keys present, verify `tailscale status`.
- If cache unreachable: check `tailscale ip -4` output and firewall/ACLs; run `just nx-cache-server-start` on the cache host.

**Appendix: migration to per-agent keys**
- See docs/Nx Agent Migration.md (example and step-by-step) for full migration.
