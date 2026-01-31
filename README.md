# Homelab Infrastructure

This repository codifies a security-first homelab with strict guard rails (`HOMELAB=1`, Tailscale SSH, encrypted secrets) and a fully-typed automation toolchain (Pulumi, Ansible, Nx, Molecule). Every command in the repo is designed to fail closed unless you are on a trusted machine that meets the guard conditions defined in `.github/copilot-instructions.md`.

## Generate Your Own Homelab (Copier Template)

This repository can be used as a **Copier template** to generate customized homelab projects with optional features:

```bash
# Install copier
pip install copier

# Generate a new project
copier copy gh:SPRIME01/homelab my-homelab \
  -d project_name=my-homelab \
  -d admin_email=you@example.com \
  -d enable_pulumi=true \
  -d enable_ansible=true \
  -d enable_nx_distributed=false

# Follow the post-generation security checklist
cd my-homelab
cat README.md
```

The template includes:
- ✅ Conditional infrastructure tooling (Pulumi, Ansible, Nx distributed builds)
- ✅ Pre-configured security guards with dual test system (bash + Python)
- ✅ Encrypted secrets management (SOPS + age with 2 recipients)
- ✅ Tailscale SSH transport for remote execution
- ✅ 23 inline validators for safe project generation
- ✅ VSCode tasks for running all test suites

See `docs/Reference/Template-Testing.md` for testing and customization details.

## Five-Minute Setup

1. **Install the pinned toolchain**
   ```bash
   mise install          # installs bun 1.2.36, python 3.13.9, pulumi 3.207.0, etc.
   bun install           # prepares the monorepo packages
   ```
2. **Load the development environment**
   ```bash
   direnv allow          # trusts .envrc so HOMELAB auto-detection works
   just detect-homelab   # confirms whether ~/.config/sops/age/keys.txt exists
   ```
3. **Verify guard rails before touching infrastructure**
   ```bash
   just ci-validate      # runs 10 bash infrastructure tests (guards, SOPS, Tailscale)
   bunx nx graph         # optional visualization of the Nx workspace
   ```
4. **Test Python template code** (uses Devbox for reproducible environment):
   ```bash
   devbox shell          # activates Python 3.13.9 + pytest + dev deps
   pytest tests/python -q   # runs 4 Python modules (hooks, validators, generation)
   exit
   ```
   See `docs/Reference/Template-Testing.md` for full testing guide.
5. **Start with the first tutorial** – follow `docs/Tutorials/Your-First-Deployment.md` to generate age keys, join the tailnet, encrypt your first secret, and run a DRY-RUN deployment end-to-end.

## Documentation Map

- `docs/README.md` – decision-tree index for explanations, how-tos, references, and tutorials.
- `docs/Explanations/System-Architecture.md` – how devbox→mise→.envrc→just→Pulumi/Ansible/Nx link together, including the guard layers.
- `docs/Howto` – actionable guides such as `Setup-Pulumi.md`, `Deploy-Infrastructure.md`, and troubleshooting playbooks.
- `docs/Reference` – tables for environment variables, justfile recipes, tool versions, and branded type APIs.
- `docs/Tutorials` – progressive learning paths with success criteria and verification commands.

## Contributing Safely

- Never bypass the guard pattern `if [ "${HOMELAB:-0}" != "1" ]; then ...; fi` in scripts or just recipes.
- Mock external dependencies (Tailscale, Pulumi backends, Nx agents) in tests so CI can run with `HOMELAB=0`.
- Run **both test systems** before opening a pull request:
  - `just ci-validate` — bash tests (exit code `2` = skip when optional deps missing)
  - `devbox shell && pytest tests/python -q` — Python template tests
- When modifying the Copier template, update validators in `copier.yml` AND `hooks/pre_copy.py`.
- Document any new workflow inside the appropriate Diataxis section (Tutorial/How-to/Reference/Explanation) before requesting review.

If you are unsure where to start, open `docs/README.md` and follow the "If you want to..." prompts.
