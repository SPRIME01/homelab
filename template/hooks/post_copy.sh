#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'

✅ Security checklist — follow these steps to get started safely

1) Generate age keypair
   mkdir -p ~/.config/sops/age
   age-keygen -o ~/.config/sops/age/keys.txt
   chmod 600 ~/.config/sops/age/keys.txt

2) Extract public recipient
   age-keygen -y ~/.config/sops/age/keys.txt
   # Copy the displayed value for the next step

3) Update .sops.yaml with real recipient
   # Edit .sops.yaml and replace the placeholder with the public key you generated.

4) Create and encrypt secrets
   # For each example file in docs/Reference/
   cp docs/Reference/example.tailscale.env infra/tailscale.env
   vim infra/tailscale.env  # Fill with real values
   export AGE_RECIPIENT="age1..."  # Your public key
   just tailscale-encrypt

5) Obtain Tailscale auth key
   # Visit Tailscale admin console -> Create auth keys -> Store before encrypting the env file

6) Configure Tailscale tags
   # Create tags like: tag:homelab-wsl2 tag:homelab-server
   # Assign admin_email as tagOwner where relevant

7) Run validation suite
   just ci-validate
   # All test scripts should either PASS or emit SKIP (exit code 2). Review failures.

8) Follow first deployment tutorial
   cat docs/Tutorials/Your-First-Deployment.md

⚠️ NEVER commit plaintext secrets to git!
⚠️ Store the age private key securely (e.g. password manager, encrypted backup).
⚠️ Confirm all guard tests pass before first deployment.

EOF
