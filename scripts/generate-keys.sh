#!/usr/bin/env bash
set -euo pipefail

echo "Generating homelab age keypair (will write private identity to ~/.config/sops/age/keys.txt)"
mkdir -p "$HOME/.config/sops/age"
if [ -f "$HOME/.config/sops/age/keys.txt" ]; then
  echo "ERROR: $HOME/.config/sops/age/keys.txt already exists. Aborting to avoid overwrite." >&2
  echo "If you want to rotate keys, back up the existing file and remove it first." >&2
  exit 1
fi

age-keygen -o ./homelab-keys.txt
mv ./homelab-keys.txt "$HOME/.config/sops/age/keys.txt"
chmod 600 "$HOME/.config/sops/age/keys.txt"
echo "Homelab private identity written to $HOME/.config/sops/age/keys.txt (permissions 600)."
echo
echo "Homelab public recipient:"
grep '^# public key:' "$HOME/.config/sops/age/keys.txt" | sed 's/^# public key: //'

echo
echo "Generating CI age keypair (local file: ./ci-keys.txt). DO NOT commit ci-keys.txt."
age-keygen -o ./ci-keys.txt
chmod 600 ./ci-keys.txt
echo "CI public recipient:"
grep '^# public key:' ./ci-keys.txt | sed 's/^# public key: //'
echo
echo "CI private identity (copy this value into your CI secret store, e.g. GitHub Actions secret SOPS_AGE_KEY):"
grep -v '^#' ./ci-keys.txt

echo
echo "Next steps:
- Add the two public recipients into .sops.yaml (replace placeholders).
- Encrypt infra/example.env with: sops --encrypt --age <homelab-or-ci-public> infra/example.env > infra/example.env.sops
- Back up $HOME/.config/sops/age/keys.txt securely (see Secrets Management.md).
"
