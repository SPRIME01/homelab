# Tailscale ACL (annotated)

This file mirrors the annotated HuJSON stored at `infra/tailscale-acl.json`. The Tailscale Admin Console accepts strict JSON without comments, so keep `infra/tailscale-acl.clean.json` (auto-generated, no comments) for pasting or API workflows.

**Privacy tip:** the repo ships with placeholder identities such as `admin@example.com`. Make a private copy (for example `infra/tailscale-acl.local.json`, ignored by git) or encrypt one with SOPS when you substitute your real email addresses.

```bash
cp infra/tailscale-acl.clean.json infra/tailscale-acl.local.json
$EDITOR infra/tailscale-acl.local.json  # replace admin@example.com with your account
```

Annotated ACL (comments for humans only)

```jsonc
{
  // Tag owners define who can assign tags to devices. Replace the placeholder
  // email with your admin identity before applying.
  "tagOwners": {
    "tag:k8s-operator": [],
    "tag:k8s": ["tag:k8s-operator"],
    "tag:homelab-wsl2": ["admin@example.com"]
  },

  // Grants control general connectivity (non-SSH). This example leaves general
  // connectivity wide-open; narrow it if you want more restrictions.
  "grants": [
    { "src": ["*"], "dst": ["*"], "ip": ["*"] }
  ],

  // The `ssh` block is special for Tailscale SSH. We use three entries:
  // 1) Accept: allow the admin user to SSH into devices tagged `tag:homelab-wsl2`.
  // 2) Check: allow users to SSH into their own devices (non-root/root) in check mode.
  // 3) Deny: deny all other SSH access to homelab-tagged hosts (defense-in-depth).
  "ssh": [
    {
      "action": "accept",
      "src": ["admin@example.com"],
      "dst": ["tag:homelab-wsl2"],
      "users": ["admin@example.com"]
    },

    {
      "action": "check",
      "src": ["autogroup:member"],
      "dst": ["autogroup:self"],
      "users": ["autogroup:nonroot", "root"]
    },

    {
      "action": "deny",
      "src": ["*"],
      "dst": ["tag:homelab-wsl2"],
      "users": ["*"]
    }
  ],

  // Tests help verify policy before applying. Update emails/tags for your environment.
  "tests": [
    { "src": "admin@example.com", "accept": ["tag:homelab-wsl2"], "deny": [] },
    { "src": "someone-else@example.com", "accept": [], "deny": ["tag:homelab-wsl2"] }
  ]
}
```

How to keep comments in the repository but still apply a valid ACL

- Option A (recommended): Keep this annotated `docs/Tailscale-ACL.md` as the human reference and use the machine-readable `infra/tailscale-acl.json` when pasting into the Admin Console.
- Option B (GitOps / HuJSON): If you want comments preserved in the repo and have a GitOps workflow, use HuJSON (JSON with comments) or JSONC and apply the policy with a tool that supports HuJSON (for example `tailscale gitops-pusher` or the Terraform provider). These tools can preserve comments and convert to valid JSON when applying.
  - Example: store `policy.hujson` with comments and run a gitops pusher that accepts HuJSON.

Quick commands (strip comments and validate)

If you have a commented JSON file (JSONC/HuJSON) and need a clean JSON file to paste, you can strip comments locally:

```bash
# using npm package strip-json-comments (install: npm i -g strip-json-comments)
strip-json-comments infra/tailscale-acl.hujson > infra/tailscale-acl.json

# or with a small Node one-liner (no install):
node -e "console.log(require('strip-json-comments')(require('fs').readFileSync('infra/tailscale-acl.hujson','utf8')));" > infra/tailscale-acl.json
```

Applying via API (advanced)

You can also PUT the JSON to the Tailscale API if you have a service API key (tskey) and want automation. See the Tailscale API docs for `tailnet/<name>/acl` and use `curl` with the API key.

Final notes

- The Tailscale Admin Console expects valid JSON when pasting raw policy; comments will generally cause a parse error there.
- For human-friendly repo storage, keep an annotated version in `docs/` and a machine-ready copy in `infra/`.
