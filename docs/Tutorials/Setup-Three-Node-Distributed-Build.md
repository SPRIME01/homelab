# Tutorial: Setup a Three-Node Distributed Build

**Audience**: Advanced operators expanding distributed Nx capacity.

## Goal

Bring up one orchestrator and three agents connected over Tailscale, share a cache server, and confirm distributed `nx run-many` logs show remote execution.

## Steps

1. **Prepare orchestrator**
   ```bash
   HOMELAB=1 direnv allow
   pnpm install
   scripts/generate-nx-agent-secret.sh
   cp docs/Reference/example.nx-agents.env infra/nx-agents.env
   $EDITOR infra/nx-agents.env   # set NX_SHARED_SECRET and three agent IPs
   AGE_RECIPIENT=$(age-keygen -y ~/.config/sops/age/keys.txt)
   AGE_RECIPIENT=$AGE_RECIPIENT just nx-encrypt-config
   ```
2. **Configure agents (repeat x3)**
   ```bash
   tailscale up --authkey tskey-...
   sops -d --input-type dotenv --output-type dotenv infra/nx-agents.env.sops > ~/nx.env
   source ~/nx.env
   HOMELAB=1 just nx-start-agent
   ```
3. **Start cache server**
   ```bash
   HOMELAB=1 just nx-cache-server-start
   just nx-cache-health
   ```
4. **Run distributed command**
   ```bash
   HOMELAB=1 DEPLOY_CONFIRM=yes just nx-distributed-build
   ```
5. **Inspect logs**
   - Orchestrator output should mention "Running distributed build across Nx agents" and list remote hosts.
   - Agents log acceptance of tasks in `~/.local/state/nx-agent.log` (script output).

## Success Criteria

- `just nx-cache-health` returns `✓ Cache server is healthy`.
- `pnpm exec nx run-many --target=build --all --parallel=3 --configuration=production` (triggered by the just recipe) prints remote execution logs instead of local-only runs.
- Each agent reports `Starting Nx agent with machine ID: 100.x.x.x` using its Tailscale IP.
- `HOMELAB=1 DEPLOY_CONFIRM=yes just nx-distributed-build` exits `0` without falling back to local execution.

After completion, enable the systemd timers from `scripts/nx-agent-health-monitor.sh` to keep agents online.
