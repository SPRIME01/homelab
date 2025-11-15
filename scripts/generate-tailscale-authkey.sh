#!/usr/bin/env bash
set -euo pipefail

cat <<'TXT'
This helper documents how to create a reusable, tagged Tailscale auth key for homelab nodes.

Recommended pattern (best practice):
- Create a single reusable auth key and assign it the tag `tag:homelab-wsl2`.
- Use that key for homelab machines that should run the SSH server. Dev machines should not receive this key.

Manual (UI):
1. Open https://login.tailscale.com/admin/settings/keys
2. Create a key, select "Reusable" and add a tag: `tag:homelab-wsl2`
3. Copy the generated key and store it securely (we recommend encrypting it with SOPS in `infra/tailscale.env.sops`).

Using the API (example):
# You need an API key from https://login.tailscale.com/admin/settings/authkeys
# Replace $TS_API_KEY with your admin API key
curl -sS -X POST -H "Authorization: Bearer $TS_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"capabilities": ["ssh"], "reusable": true, "tags": ["tag:homelab-wsl2"]}' \
  https://api.tailscale.com/api/v2/keys

Storing the key in SOPS (example):
1. Create `infra/tailscale.env` with the plaintext value:
   TAILSCALE_AUTHKEY=tskey-xxxx
2. Encrypt with SOPS to produce `infra/tailscale.env.sops`:
   sops --encrypt --input-type dotenv --output-type dotenv --age "<public-recipient>" infra/tailscale.env > infra/tailscale.env.sops

Rotation:
- To rotate, create a new reusable key in the admin console with the same tag, update `infra/tailscale.env.sops`, and run `just tailscale-rotate-key` (this recipe will re-encrypt and optionally remove the old key from circulation).

Security notes:
- Keep the private auth key out of source control. Only the encrypted `.sops` file should be committed.
- Do NOT distribute the `tag:homelab-wsl2` key to developer machines.

TXT
