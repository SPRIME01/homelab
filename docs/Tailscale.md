# Tailscale Integration (WSL2 + Windows)

This document describes how this homelab integrates Tailscale SSH with strict privilege boundaries.

## Quick Summary

- **Homelab machines:** have SSH server capability via Tailscale (enabled only when `HOMELAB=1`).
- **Dev machines:** automatically join the tailnet for connectivity only; do NOT run an SSH server.
- **Windows host:** runs the system `tailscaled` service (the only accepted `sudo` exception).
- **WSL2:** uses the Windows host Tailscale instance (access via Tailscale IP) by default.

## What is Tailscale?

Tailscale is a VPN service that creates a private network (called a "tailnet") between your devices. It uses WireGuard under the hood and handles NAT traversal automatically. Key concepts:

- **Tailnet:** Your private network of devices (e.g., `yourname.example.ts.net`).
- **Tailscale IP:** Each device gets a private IP in the `100.x.x.x` range that's reachable from other devices in your tailnet.
- **Auth key:** A secret token that allows new devices to join your tailnet without interactive login.
- **ACL (Access Control List):** Rules that control which devices can access which services (SSH, HTTP, etc.).
- **Tags:** Labels you assign to devices (e.g., `tag:homelab-wsl2`) to group them for ACL rules.

---

## Complete Setup Walkthrough

Follow these steps in order. Each section explains what you're doing and why.

### Step 1: Install Tailscale on your Windows 11 host

**What:** Install the Tailscale Windows client (system service) on your Windows machine.

**Why:** This is the primary Tailscale instance that will provide VPN connectivity. WSL2 will use this Windows service rather than running a separate Tailscale inside Linux.

**How:**
1. Open a web browser on Windows and go to: https://tailscale.com/download/windows
2. Download the Tailscale MSI installer for Windows.
3. Run the installer (this will prompt for Administrator permission — click Yes).
4. When the installation completes, Tailscale will open and ask you to log in.
5. Log in using your preferred identity provider (Google, Microsoft, GitHub, etc.). This creates your tailnet.
6. After login, Tailscale shows a small window with your device's Tailscale IP (looks like `100.x.x.x`). Write this down or leave the window open.

**Verify:**
- Open PowerShell on Windows and run:
  ```powershell
  tailscale status
  ```
  You should see your Windows machine listed with a `100.x.x.x` IP.

**Note:** This is the only step in the homelab project that requires `sudo` / Administrator privilege. All other steps are user-level.

---

### Step 2: Install the WSL2 helper script (optional but recommended)

**What:** Install a small helper that lets WSL2 discover the Windows Tailscale IP address.

**Why:** When you're in WSL2 and want to connect to another homelab node via Tailscale, you need to know your Windows machine's Tailscale IP. This helper automates that lookup.

**How:**
1. Open a WSL2 terminal (Ubuntu, Debian, etc.).
2. Navigate to the homelab repository:
   ```bash
   cd /home/prime/homelab
   ```
3. Run the installation script:
   ```bash
   bash scripts/install-tailscale-wsl2.sh
   ```
   This installs a small command called `wsl-tailscale-ip` into `~/.local/bin/`.

4. Add `~/.local/bin` to your PATH if it's not already there (check with `echo $PATH`):
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

**Verify:**
- Run:
  ```bash
  wsl-tailscale-ip
  ```
  You should see the `100.x.x.x` IP of your Windows machine printed.

---

### Step 3: Generate an age encryption keypair (if you don't have one)

**What:** Create a public/private keypair for encrypting secrets with the `age` tool.

**Why:** This homelab stores sensitive values (like Tailscale auth keys) encrypted with SOPS + age. The `age` private key decrypts secrets; the public key (called a "recipient") encrypts secrets. Only machines with the private key can decrypt.

**How:**

1. Check if you already have an age key:
   ```bash
   ls -l ~/.config/sops/age/keys.txt
   ```
   If the file exists, skip to "Extract the public recipient" below. If not, continue.

2. Install `age` and `age-keygen` (if not already installed):
   - On Ubuntu/Debian WSL2:
     ```bash
     sudo apt update && sudo apt install age -y
     ```
   - On macOS (if you plan to use this from macOS later):
     ```bash
     brew install age
     ```

3. Generate a new age keypair:
   ```bash
   mkdir -p ~/.config/sops/age
   age-keygen -o ~/.config/sops/age/keys.txt
   ```
   This creates a file with one private key line (starts with `AGE-SECRET-KEY-1...`) and prints the public recipient (starts with `age1...`).

4. Protect the private key file:
   ```bash
   chmod 600 ~/.config/sops/age/keys.txt
   ```

**Extract the public recipient:**
- Run:
  ```bash
  age-keygen -y ~/.config/sops/age/keys.txt
  ```
  This prints a line like:
  ```
  age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
  ```
  **Copy this `age1...` string.** You'll use it in the next steps. This is your **public recipient** and is safe to share (you can paste it in chat, commit it to a repo, etc.). The private key (`AGE-SECRET-KEY-1...`) must remain secret.

---

### Step 4: Create a Tailscale reusable auth key

**What:** Generate a secret token (auth key) that allows new devices to join your tailnet without interactive login.

**Why:** Automating the join process requires an auth key. You'll encrypt this key and store it in the repository.

**How:**

1. Open a web browser and log into the Tailscale admin console: https://login.tailscale.com/admin/settings/keys
   - (Alternatively, navigate to Admin → Settings → Keys in the Tailscale console.)

2. Click **Generate auth key** (or similar button).

3. Configure the key:
   - **Reusable:** Check this box (allows multiple devices to use the same key).
   - **Ephemeral:** Leave unchecked (unless you want devices to disappear when they disconnect).
   - **Preauthorized:** Check this (skips manual approval for each device).
   - **Tags:** Add a tag like `tag:homelab-wsl2`. This tag will be used in ACLs to restrict SSH access.
   - **Expiration:** Choose a long expiration (e.g., 90 days or 1 year) or "does not expire" if your security policy allows.
   - **Description:** Enter something like "homelab-wsl2 reusable key" so you remember what it's for.

4. Click **Generate key**. Copy the key (starts with `tskey-auth-...`). **Treat this like a password.**

**Important:** Do not paste this key in public chat, commit it to a repo unencrypted, or share it publicly. You will encrypt it in the next step.

---

### Step 5: Encrypt the Tailscale auth key with SOPS

**What:** Create a plaintext file with your auth key, encrypt it with SOPS + age, then delete the plaintext.

**Why:** Storing secrets in plaintext is insecure. SOPS encrypts the file so only machines with your `age` private key can decrypt it.

**How (using the `just` helper — recommended):**

1. Open a terminal in the homelab repository:
   ```bash
   cd /home/prime/homelab
   ```

2. Set environment variables with your age public recipient and Tailscale auth key (replace placeholders):
   ```bash
   export AGE_RECIPIENT="age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
   export TAILSCALE_AUTHKEY="tskey-auth-k..."
   export TAILNET="yourname.example.ts.net"   # optional; your tailnet name
   export TAILSCALE_WINDOWS_IP=""              # optional; leave empty or set to 100.x.x.x
   ```

3. Run the encryption helper:
   ```bash
   just tailscale-encrypt
   ```
   This creates `infra/tailscale.env.sops` (encrypted) and removes the plaintext file.

**Verify:**
- Check that `infra/tailscale.env.sops` exists:
  ```bash
  ls -l infra/tailscale.env.sops
  ```
- The file should look like encrypted gibberish if you open it (that's good).

**How (manual method, if you prefer):**

1. Create a plaintext file (DO NOT COMMIT THIS):
   ```bash
   cat > infra/tailscale.env <<'EOF'
   TAILSCALE_AUTHKEY=tskey-auth-k...
   TAILSCALE_WINDOWS_IP=
   TAILNET=yourname.example.ts.net
   EOF
   ```

2. Encrypt with SOPS (replace `<age-recipient>` with your `age1...` string):
   ```bash
   sops --encrypt --input-type dotenv --output-type dotenv --age "<age-recipient>" infra/tailscale.env > infra/tailscale.env.sops
   ```

3. Delete the plaintext file:
   ```bash
   shred -u infra/tailscale.env
   ```

**Important security notes:**
- Never commit `infra/tailscale.env` (plaintext) to source control.
- Only distribute the `age` private key (`~/.config/sops/age/keys.txt`) to machines you fully trust.
- The `age` public recipient (age1...) and the encrypted `infra/tailscale.env.sops` file are safe to commit and share.

---

### Step 6: Configure your tailnet ACL to restrict SSH access

**What:** Update your Tailscale ACL to allow SSH only to devices with a specific tag.

**Why:** By default, all devices in your tailnet can reach each other. ACLs enforce least-privilege: only homelab nodes (tagged `tag:homelab-wsl2`) will accept SSH connections.

**How:**

1. Open the Tailscale admin console: https://login.tailscale.com/admin/acls
2. Click **Edit** or **Edit file** (depending on your console version).
3. Replace the existing ACL JSON with the following template (or merge it):

```json
{
  "ACLs": [
    {
      "Action": "accept",
      "Users": ["*"],
      "Ports": ["tag:homelab-wsl2:22"]
    }
  ],
  "TagOwners": {
    "tag:homelab-wsl2": ["your-email@example.com"]
  },
  "Tests": []
}
```

4. Replace `your-email@example.com` with the email address you used to log into Tailscale.
5. Click **Save**. Tailscale will validate the ACL and apply it.

**What this does:**
- **Users `["*"]`** means "all users in the tailnet."
- **Ports `["tag:homelab-wsl2:22"]`** means "allow SSH (port 22) only to devices tagged `tag:homelab-wsl2`."
- **TagOwners** specifies who can assign the `tag:homelab-wsl2` tag to devices (only you, the admin).

**Advanced (optional):**
- Add more rules for HTTP, database ports, etc.
- Add posture checks (require specific OS versions or Tailscale client versions).
- See: https://tailscale.com/kb/1018/acls

---

### Step 7: Join your homelab machine to the tailnet

**What:** Use the encrypted auth key to join a homelab machine (e.g., a server or trusted dev machine) to your tailnet.

**Why:** This connects the machine to your private VPN so it can reach other devices and (optionally) accept SSH connections.

**How:**

1. On the machine you want to join (must be a trusted homelab machine), ensure:
   - You have the `age` private key at `~/.config/sops/age/keys.txt` (copy it securely if needed).
   - You have the repository cloned and `infra/tailscale.env.sops` exists.
   - `sops` is installed:
     ```bash
     # Ubuntu/Debian
     sudo apt install sops -y
     # macOS
     brew install sops
     ```
   - `tailscale` CLI is installed (if running tailscaled locally; otherwise skip if using Windows Tailscale via WSL2 helper).

2. Set the `HOMELAB` environment variable (this gates privileged actions):
   ```bash
   export HOMELAB=1
   ```

3. Run the join helper:
   ```bash
   just tailscale-join
   ```
   This decrypts `infra/tailscale.env.sops`, reads the `TAILSCALE_AUTHKEY`, and runs `tailscale up --authkey <key>`.

**Verify:**
- Run:
  ```bash
  tailscale status
  ```
  You should see your machine listed with a `100.x.x.x` IP and status "active" or "online."

**Notes:**
- If you're using WSL2 (and Windows Tailscale is already running), you don't need to join from WSL2 — the Windows machine is already in the tailnet. Use `wsl-tailscale-ip` to discover the Windows Tailscale IP.
- If you're joining a separate Linux server (not WSL2), install `tailscaled` as a system service first, then run `just tailscale-join`.

---

### Step 8: Enable SSH on homelab nodes (trusted machines only)

**What:** Allow your homelab machine to accept SSH connections over Tailscale.

**Why:** This lets you SSH into the machine from other devices in your tailnet without exposing SSH to the public internet.

**How:**

1. On the trusted homelab machine, ensure `HOMELAB=1` is set:
   ```bash
   export HOMELAB=1
   ```

2. Enable Tailscale SSH:
   ```bash
   just tailscale-ssh-enable
   ```
   This runs `tailscale up --ssh` (gated by the `HOMELAB=1` check in the `justfile`).

**Verify:**
- Run:
  ```bash
  tailscale status
  ```
  The output should show "Offers: ssh" or similar, indicating SSH is enabled.

- From another device in your tailnet, SSH to the machine using its Tailscale IP:
  ```bash
  ssh user@100.x.x.x
  ```
  (Replace `100.x.x.x` with the actual Tailscale IP and `user` with your username.)

**Important:**
- Only enable SSH on machines you trust and control. Do NOT enable SSH on shared or dev-only machines.
- The ACL (configured in Step 6) enforces that only devices tagged `tag:homelab-wsl2` accept SSH; other devices will be blocked even if you try to enable SSH.

---

### Step 9: Optional — Discover the Windows Tailscale IP from WSL2

**What:** Find the Windows host's Tailscale IP from within WSL2.

**Why:** You may want to SSH into the Windows host (if SSH is enabled there) or reference the IP in scripts.

**How:**
1. Run:
   ```bash
   wsl-tailscale-ip
   ```
   This prints the `100.x.x.x` IP of your Windows machine.

**Verify:**
- From WSL2, try pinging the IP:
  ```bash
  ping $(wsl-tailscale-ip)
  ```

---

### Step 10: Optional — Require Tailscale connectivity for deploys

**What:** Configure the `just deploy` recipe to fail if Tailscale is not connected.

**Why:** Prevents deploying infrastructure from a machine that's not on the tailnet (e.g., accidentally deploying from a public Wi-Fi laptop).

**How:**
1. When running `just deploy`, set `REQUIRE_TAILSCALE=1`:
   ```bash
   REQUIRE_TAILSCALE=1 DEPLOY_CONFIRM=yes HOMELAB=1 just deploy
   ```

2. If Tailscale is not running or not connected, the deploy will abort with an error.

**Note:** This is opt-in. If you don't set `REQUIRE_TAILSCALE=1`, the deploy will proceed without checking Tailscale status.

---

## Justfile Recipes Reference

The homelab `justfile` provides several recipes for Tailscale operations. Run them with `just <recipe-name>`.

- **`just tailscale-status`**
  Prints Tailscale status (safe; handles missing `tailscale` binary gracefully).

- **`just tailscale-join`**
  Joins the tailnet using `TAILSCALE_AUTHKEY` from `infra/tailscale.env.sops`. Requires `HOMELAB=1` implicitly (via SOPS key availability).

- **`just tailscale-ssh-enable`**
  (Guarded by `HOMELAB=1`) Runs `tailscale up --ssh` to accept SSH connections.

- **`just tailscale-ssh-disable`**
  (Guarded by `HOMELAB=1`) Runs `tailscale down` to stop accepting SSH.

- **`just tailscale-rotate-key`**
  (Guarded by `HOMELAB=1`) Prints instructions for rotating your auth key (manual step).

- **`just tailscale-encrypt`**
  Encrypts a plaintext `infra/tailscale.env` into `infra/tailscale.env.sops` using SOPS + age. Requires `AGE_RECIPIENT` and `TAILSCALE_AUTHKEY` env vars.

---

## Advanced Topics

### Auto-join vs Manual join (trade-offs)

- **Manual (recommended for scripts and CI):** Run `just tailscale-join` when you need connectivity. No network dependency during shell startup.
- **Auto-join (optional for convenience):** Add a call to `just tailscale-join` in your `.envrc` (commented example included in the repository). This improves UX but introduces a network dependency when the shell loads. Prefer manual for CI and scripts to avoid flaky startups.

### Subnet routes

If you want your tailnet to route traffic to a local subnet (e.g., `192.168.1.0/24`), configure subnet routes in the Tailscale admin console and use `autoApprovers` in the ACL to limit who can request routes.

### Posture checks

Tailscale can enforce posture checks (e.g., require specific OS versions, Tailscale client versions, or device compliance) before granting access. See: https://tailscale.com/kb/1017/install/

### Rotating auth keys

When an auth key expires or is compromised:
1. Generate a new auth key in the Tailscale admin console (Step 4 above).
2. Update `infra/tailscale.env` with the new key and re-encrypt:
   ```bash
   export AGE_RECIPIENT="age1..."
   export TAILSCALE_AUTHKEY="tskey-auth-NEW..."
   just tailscale-encrypt
   ```
3. On each homelab machine, run `just tailscale-join` again to re-authenticate (or `tailscale up --authkey <new-key>`).

---

## Troubleshooting

### `wsl-tailscale-ip` fails or returns empty

- **Verify Windows Tailscale is running:**
  - Open PowerShell on Windows and run: `tailscale status`
  - If Tailscale is not running, start it from the Windows Start menu or system tray.
- **Check that Tailscale has an IPv4 address:**
  - Run: `tailscale.exe ip -4` (PowerShell on Windows)
  - Should return an address like `100.x.x.x`.
- **Verify `powershell.exe` and `cmd.exe` are callable from WSL2:**
  - From WSL2, run: `powershell.exe -Command "Write-Output test"`
  - Should print `test`. If not, ensure WSL2 interop is enabled.

### `just tailscale-join` fails with "unable to decrypt"

- **Verify your `age` private key is present:**
  ```bash
  ls -l ~/.config/sops/age/keys.txt
  ```
- **Verify the key matches the encrypted file:**
  - Run: `sops --decrypt infra/tailscale.env.sops`
  - If decryption succeeds, you should see the plaintext env vars (including `TAILSCALE_AUTHKEY`).
  - If it fails, re-encrypt the file with the correct `age` recipient (Step 5 above).

### SSH connections are blocked by ACL

- **Verify the device has the correct tag:**
  - Run: `tailscale status` and check if the device shows `tag:homelab-wsl2` in the tags column.
  - If not, add the tag in the Tailscale admin console (Admin → Machines → [your machine] → Edit tags).
- **Verify the ACL allows SSH to that tag:**
  - Review your ACL at https://login.tailscale.com/admin/acls
  - Ensure there's a rule like:
    ```json
    {"Action": "accept", "Users": ["*"], "Ports": ["tag:homelab-wsl2:22"]}
    ```

### `tailscale up --ssh` fails with "permission denied"

- **Ensure `HOMELAB=1` is set:**
  ```bash
  export HOMELAB=1
  ```
- **Verify you're running on a trusted machine** (not a dev-only or shared machine).
- **Check that `tailscale` CLI is installed and accessible:**
  ```bash
  which tailscale
  ```

---

## Tested / Recommended Versions

- **Tailscale:** Targets the "stable" channel. Tailscale recommends staying on stable and enabling auto-updates. See https://tailscale.com/changelog for release notes.
- **SOPS:** Any recent version (1.7.0+).
- **age:** Any recent version (1.0.0+).

Because Tailscale auto-updates are recommended, we do not pin a specific client version in the repository. If you require a pinned version for compliance, install that version on your Windows host and document it in your homelab runbook.

---

## Key Files in This Repository

- **`infra/tailscale.env.sops`** — SOPS-encrypted dotenv holding `TAILSCALE_AUTHKEY`, optional `TAILSCALE_WINDOWS_IP`, and `TAILNET`.
- **`infra/tailscale-acl.json`** — Example ACL template (for reference; actual ACLs are managed in the Tailscale admin console).
- **`scripts/install-tailscale-wsl2.sh`** — Installs the `wsl-tailscale-ip` helper.
- **`scripts/tailscale-join.sh`** — Helper that decrypts the auth key and runs `tailscale up --authkey`.
- **`scripts/generate-tailscale-authkey.sh`** — Documentation helper with instructions for creating auth keys.
- **`tests/05_tailscale_ssh_guards.sh`** — Mocked tests for Tailscale recipes (CI-safe; no live network required).

---

## Notes on Validation

- Use `wsl-tailscale-ip` to discover the Windows Tailscale IP.
- Use `tailscale status` on Windows (or any tailscaled machine) to confirm connectivity.
- The project provides mocked tests (`tests/05_tailscale_ssh_guards.sh`) so CI can validate guard behavior without requiring a live Tailscale network.

---

## Security Notes

- **Never commit plaintext auth keys** to source control.
- **Protect your `age` private key** (`~/.config/sops/age/keys.txt`). Only copy it to trusted machines.
- **Use tags and ACLs** to enforce least-privilege access.
- **Enable SSH only on homelab nodes** you trust and control.
- **Review Tailscale audit logs** in the admin console periodically.

---

## Additional Resources

- Tailscale documentation: https://tailscale.com/kb
- Tailscale ACL reference: https://tailscale.com/kb/1018/acls
- SOPS documentation: https://github.com/mozilla/sops
- age encryption tool: https://age-encryption.org/

---

**Questions or issues?** Review the troubleshooting section above, check the Tailscale admin console for device status and ACL rules, and verify your `age` keypair and SOPS encryption setup.
