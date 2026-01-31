# Add New Nx Project

Create a typed infrastructure-related package inside the Nx workspace and wire it into distributed execution.

## Steps

1. **Generate the project**
   ```bash
   bunx nx g @nrwl/node:library libs/my-new-lib --directory=packages --unitTestRunner=vitest
   ```
2. **Adopt branded types**
   - Import `TailscaleIP`, `NxProjectName`, etc. from `packages/homelab-types/src/index.ts`.
   - Enforce guard rails in entry points (`assertHomelabAccess()` for privileged logic).
3. **Add targets**
   - Update `project.json` with `build`, `test`, `lint`, and any custom targets.
   - Use Nx cacheable operations so distributed agents can execute them; run `bunx nx show project my-new-lib` to confirm.
4. **Update documentation/tests**
   - Reference the project inside `docs/Reference/Justfile-Recipe-Index.md` if you add new recipes.
   - Extend `tests/10_nx_distributed_validation.sh` if new guard checks are required.
5. **Validate**
   ```bash
   bunx nx test my-new-lib
   bunx nx run-many --target=build --projects=my-new-lib
   HOMELAB=1 DEPLOY_CONFIRM=yes just nx-distributed-build
   ```

## Remaining Human Tasks

- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)
- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)
- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)
- [ ] Copy and customize example.envrc for your environment
- [ ] Create Pulumi stack secrets (pulumi config set --secret)
- [ ] Setup systemd user timers for nx-agent-health-monitor.sh
