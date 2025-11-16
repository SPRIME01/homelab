# Homelab Documentation Hub

This repository follows the Diataxis framework. Use the prompts below to jump directly to the right document for your current task or level of experience.

## Quick Decision Tree

| If you want to... | Start here |
| --- | --- |
| Understand how the pieces fit together | `docs/Explanations/System-Architecture.md` and `docs/Explanations/Security-Model.md` |
| Learn core ideas like secrets, Tailscale ACLs, or automation guards | `docs/Explanations/Automation.md`, `docs/Explanations/Secrets-Management.md`, `docs/Explanations/Tailscale-ACL.md`, `docs/Explanations/Tailscale.md` |
| Follow a step-by-step task | `docs/Howto/Setup-Development-Environment.md`, `docs/Howto/Setup-Pulumi.md`, `docs/Howto/Setup-Ansible.md`, `docs/Howto/Deploy-Infrastructure.md`, `docs/Howto/Run Nx Distributed Task Execution.md`, `docs/Howto/Troubleshoot-Common-Issues.md`, and the new targeted guides in the same folder |
| Look up exact settings, environment variables, or API details | `docs/Reference/Environment-Variables.md`, `docs/Reference/Justfile-Recipe-Index.md`, `docs/Reference/Test-Suite-Index.md`, `docs/Reference/Tool-Versions.md`, `docs/Reference/Branded-Types-API.md` |
| Practice or teach someone else | `docs/Tutorials/Your-First-Deployment.md`, `docs/Tutorials/Build-A-Typed-Infrastructure-Module.md`, `docs/Tutorials/Setup-Three-Node-Distributed-Build.md` |

## Audience Paths

- **Beginner**: Read `System-Architecture`, run the "Your First Deployment" tutorial, then complete `Setup-Development-Environment` and `Setup-Pulumi` how-tos.
- **Operator**: Follow `Setup-Ansible`, `Deploy-Infrastructure`, and keep `Troubleshoot-Common-Issues` handy. Use the reference tables for quick lookups.
- **Contributor**: After onboarding, study `Security-Model`, `Test-Exit-Code-Convention`, and `Nx-Distributed-Architecture`, then work through the intermediate/advanced tutorials.

## Maintaining the Map

Whenever you introduce a new workflow:
1. Decide whether you are explaining, guiding, referencing, or teaching.
2. Add or update the matching document in `Explanations/`, `Howto/`, `Reference/`, or `Tutorials/`.
3. Link it back here so newcomers can find it via the decision tree.

Keep every document focused—tutorials should be narrative, how-tos should be terse checklists with human task reminders, references should be tables, and explanations should answer "why".
