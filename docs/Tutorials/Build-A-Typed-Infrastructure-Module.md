# Tutorial: Build a Typed Infrastructure Module

**Audience**: Intermediate contributors

## Goal

Create a new Nx project that ships branded types, integrates with Pulumi, and includes mocked tests to prove guard compliance.

## Steps

1. **Generate project skeleton**
   ```bash
   bunx nx g @nrwl/node:library packages/infra-hello --unitTestRunner=vitest
   ```
2. **Adopt branded types**
   - Import `TailscaleIP`, `assertHomelabAccess`, and other helpers from `@homelab/homelab-types`.
   - Add runtime guard calls at the top of your module entry point.
3. **Implement Pulumi resources**
   - Create `packages/infra-hello/src/stack.ts` exporting a factory that accepts typed inputs.
   - Reference the module inside `infra/pulumi-bootstrap/index.ts` to provision a mock resource (e.g., Pulumi component or config map).
4. **Mock external services**
   - Write Vitest suites that stub Tailscale IP validation and ensure `assertHomelabAccess()` throws when `HOMELAB=0`.
   - Add bash coverage if the module introduces new scripts.
5. **Wire Nx targets**
   - Update `project.json` to mark `build`, `test`, and optional `lint` as cacheable.
6. **Document usage**
   - Add a short section to `docs/Reference/Branded-Types-API.md` or a how-to if you created new workflows.

## Success Criteria

Run the following commands and confirm they succeed:

```bash
bunx nx build infra-hello
bunx nx test infra-hello
just pulumi-preview
HOMELAB=1 DRY_RUN=1 DEPLOY_CONFIRM=yes just pulumi-up  # should exit after DRY RUN message
```

You have completed the tutorial when both Nx commands and the Pulumi preview succeed without bypassing guard rails.
