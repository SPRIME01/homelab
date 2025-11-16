# Homelab Infrastructure

This repository codifies a security-first homelab with strict guard rails (`HOMELAB=1`, Tailscale SSH, encrypted secrets) and a fully-typed automation toolchain (Pulumi, Ansible, Nx, Molecule). Every command in the repo is designed to fail closed unless you are on a trusted machine that meets the guard conditions defined in `.github/copilot-instructions.md`.

## Five-Minute Setup

1. **Install the pinned toolchain**
   ```bash
   mise install          # installs node 22.17.0, python 3.13.9, pulumi 3.207.0, etc.
   pnpm install          # prepares the monorepo packages
   ```
2. **Load the development environment**
   ```bash
   direnv allow          # trusts .envrc so HOMELAB auto-detection works
   just detect-homelab   # confirms whether ~/.config/sops/age/keys.txt exists
   ```
3. **Verify guard rails before touching infrastructure**
   ```bash
   just ci-validate      # runs the 10 bash-based guard tests
   pnpm exec nx graph    # optional visualization of the Nx workspace
   ```
4. **Start with the first tutorial** – follow `docs/Tutorials/Your-First-Deployment.md` to generate age keys, join the tailnet, encrypt your first secret, and run a DRY-RUN deployment end-to-end.

## Documentation Map

- `docs/README.md` – decision-tree index for explanations, how-tos, references, and tutorials.
- `docs/Explanations/System-Architecture.md` – how devbox→mise→.envrc→just→Pulumi/Ansible/Nx link together, including the guard layers.
- `docs/Howto` – actionable guides such as `Setup-Pulumi.md`, `Deploy-Infrastructure.md`, and troubleshooting playbooks.
- `docs/Reference` – tables for environment variables, justfile recipes, tool versions, and branded type APIs.
- `docs/Tutorials` – progressive learning paths with success criteria and verification commands.

## Contributing Safely

- Never bypass the guard pattern `if [ "${HOMELAB:-0}" != "1" ]; then ...; fi` in scripts or just recipes.
- Mock external dependencies (Tailscale, Pulumi backends, Nx agents) in tests so CI can run with `HOMELAB=0`.
- Run `just ci-validate` before opening a pull request; treat exit code `2` as "skipped" per the testing convention.
- Document any new workflow inside the appropriate Diataxis section (Tutorial/How-to/Reference/Explanation) before requesting review.

If you are unsure where to start, open `docs/README.md` and follow the "If you want to..." prompts.
