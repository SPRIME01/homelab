# Plan: Reorganize and Expand Homelab Documentation (Diataxis Style)

The project has **partial Diataxis structure** with duplicate root-level docs, a 526-line monolithic howto, and missing entry points. This plan consolidates existing content, eliminates duplicates, creates critical gaps (root README, tutorials, system architecture), and reorganizes everything into proper Explanations/Howto/Reference/Tutorials categories with novice-friendly granularity.

## Steps

1. **Delete duplicates and create entry points** — Remove 3 root-level duplicate docs (`docs/Automation.md`, `docs/Secrets Management.md`, `docs/Tailscale.md`), create `README.md` (quick start with project purpose, 5-min setup, links to first tutorial), create `docs/README.md` (navigation index with "If you want to X, read Y" decision tree pointing to all 4 Diataxis categories)

2. **Reorganize Explanations/** — Keep 4 existing docs (rename `Secrets Management.md` → `Secrets-Management.md` for consistency), create 4 new concept docs: `System-Architecture.md` (Mermaid diagram: devbox→mise→envrc→justfile→infra tools chain, XDG patterns, tool pinning strategy), `Security-Model.md` (5 defense layers table, threat model matrix), `Test-Exit-Code-Convention.md` (exit 2=skip rationale, mock patterns), `Nx-Distributed-Architecture.md` (Mermaid sequence diagram for agent discovery, cache hierarchy flowchart)

3. **Refactor Howto/ task guides** — Split `Complete Infrastructure Configuration.md` (526 lines) into 4 focused guides: `Setup-Pulumi.md` (backend config, stack init, typed credentials), `Setup-Ansible.md` (inventory structure, Tailscale SSH transport, molecule testing), `Deploy-Infrastructure.md` (pulumi up/destroy workflows, ansible deploy patterns, rollback procedures), `Troubleshoot-Common-Issues.md` (extract 5 common pitfalls from `.github/copilot-instructions.md` lines 157-161, add diagnostic commands for each); rename `Bootstrap this Project.md` → `Setup-Development-Environment.md`; create 4 new task guides (`Generate-And-Rotate-Keys.md`, `Add-New-Homelab-Node.md`, `Add-New-Nx-Project.md`, `Encrypt-New-Secrets.md`)

4. **Build Reference/ technical specs** — Keep 6 existing `example.*` files, extract implicit docs into 5 new references: `Environment-Variables.md` (markdown table: Variable | Type | Default | Purpose | Required For), `Justfile-Recipe-Index.md` (all 33 recipes grouped by category with one-line descriptions, guard requirements, usage examples), `Test-Suite-Index.md` (10 test files with one-line purposes and exit code behaviors), `Tool-Versions.md` (pinned versions from `.mise.toml` with Context7/GitHub sources and update dates), `Branded-Types-API.md` (TypeScript/Python type guards from `packages/homelab-types/src/index.ts` with code examples)

5. **Create Tutorials/ learning paths** — Write 3 hands-on tutorials with **Success Criteria sections containing verification commands**: `Your-First-Deployment.md` (beginner, 30-min: prerequisites check → generate age keys → join tailnet → encrypt first secret → `HOMELAB=1 DRY_RUN=1 just deploy` → verify with `just ci-validate`), `Build-A-Typed-Infrastructure-Module.md` (intermediate: create Nx project → define branded types → implement guarded Pulumi stack → write mocked tests → verify with `pnpm exec nx build <project>` and `just pulumi-preview`), `Setup-Three-Node-Distributed-Build.md` (advanced: bootstrap orchestrator → generate Nx agent secret → configure 3 agents → start cache server → verify with `pnpm exec nx run-many --target=build --all` showing distributed execution logs)

6. **Add dependency graphs and checklists** — Embed Mermaid flowchart in `System-Architecture.md` (User Shell → .envrc → mise/devbox → HOMELAB detection → justfile guards → Pulumi/Ansible/Nx with guard layers), add "Remaining Human Tasks" checklists to each relevant howto following this pattern: `- [ ] Generate production SOPS age keypair (cannot be automated, store in password manager)`, `- [ ] Encrypt cloud provider API tokens (AWS_ACCESS_KEY_ID, etc.)`, `- [ ] Configure Tailscale ACL tags in admin console (tag:homelab-wsl2, tag:homelab-server)`, `- [ ] Copy and customize example.envrc for your environment`, `- [ ] Create Pulumi stack secrets (pulumi config set --secret)`, `- [ ] Setup systemd user timers for nx-agent-health-monitor.sh`

## Further Considerations

1. **Mermaid diagram complexity** — System-Architecture.md will have a large flowchart showing devbox→mise→envrc→justfile→tools. Should we create one comprehensive diagram or split into 3 focused diagrams (Environment Setup, Guard Flow, Tool Integration)?

2. **Navigation index structure** — Should `docs/README.md` group links by audience role (beginner/intermediate/advanced) or by task type (setup/deploy/troubleshoot/extend)? Role-based helps learning progression, task-based helps quick lookup.

3. **Troubleshooting format** — Should `Troubleshoot-Common-Issues.md` use symptom-cause-solution tables or step-by-step decision trees? Tables are scannable, decision trees guide diagnosis systematically.

4. **Tutorial pre-flight checks** — Should tutorials include automated prerequisite validation scripts (e.g., `scripts/check-tutorial-prerequisites.sh`) or rely on manual checklist verification? Automated checks reduce errors but add maintenance burden.
