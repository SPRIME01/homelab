# Test Suite Index

| File | Purpose | Skip Condition |
| --- | --- | --- |
| `tests/01_non_homelab_decrypt.sh` | Verifies secrets cannot be decrypted when `HOMELAB=0` | Missing age key (`~/.config/sops/age/keys.txt`) |
| `tests/02_sops_yaml_schema.sh` | Validates `.sops.yaml` structure and path regex | SOPS binary unavailable |
| `tests/03_round_trip_homelab.sh` | Confirms encrypt/decrypt round trip and guard enforcement | Missing age key |
| `tests/04_just_safety_guards.sh` | Ensures just recipes enforce HOMELAB/confirmation/DRY_RUN patterns | `just` not installed (rare) |
| `tests/05_tailscale_ssh_guards.sh` | Mocks Tailscale CLI to verify SSH guard logic | Tailscale binary missing (mock provided, but skip if mktemp fails) |
| `tests/06_pulumi_project_validation.sh` | Checks Pulumi strict mode, branded types, and DRY_RUN support | Pulumi CLI not installed |
| `tests/07_ansible_molecule_validation.sh` | Validates Ansible inventory + Molecule harness | `ansible`/`molecule` CLI missing |
| `tests/08_infra_guards.sh` | Ensures infra scripts refuse to run without HOMELAB or confirmations | Bash not available (practically never) |
| `tests/09_tailscale_ssh_verification.sh` | Checks Tailscale SSH configuration and ACL enforcement | Tailscale CLI missing |
| `tests/10_nx_distributed_validation.sh` | Validates Nx workspace guard rails and distributed settings | pnpm/Nx CLI missing |

All suites follow the exit-code convention documented in `docs/Explanations/Test-Exit-Code-Convention.md`: `0` success, `1` failure, `2` skip (safe to ignore in CI).
