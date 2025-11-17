# Create a New Development Machine from the Copier Template

This guide walks you through creating a new project from this repository's Copier template, step-by-step. It's designed for beginners and assumes minimal prior knowledge.

## What You're Building

You'll generate a complete homelab infrastructure project with:
- Security guards that prevent accidental changes to production
- Encrypted secrets management
- Optional infrastructure tools (Pulumi, Ansible, Nx)
- A full test suite to verify everything works

## Important Concepts Before You Start

### What is HOMELAB=1?

`HOMELAB=1` is an environment variable (a setting for your terminal session) that acts as a safety switch:

- **HOMELAB=0** (default): You're on a regular development laptop. Dangerous commands are blocked.
- **HOMELAB=1**: You're on a trusted homelab machine. Infrastructure commands are allowed.

**For dev machines**: Keep `HOMELAB=0`. You can still write code and run tests.
**For homelab nodes**: Set `HOMELAB=1` after installing encryption keys.

### Do I Need HOMELAB=1 to Join Tailscale?

**No!** You can join your Tailscale network (tailnet) from a dev machine without `HOMELAB=1`. See "Joining Tailscale on a Dev Machine" below.

## Prerequisites

Before starting, install these tools on your machine:

1. **Python 3.11+** - Check with: `python3 --version`
2. **pip** - Python's package installer, usually comes with Python
3. **copier** - Install with: `pip install copier` or `pip3 install copier`

That's all you need to generate the project. Additional tools will be installed in later steps.

## Step 1: Generate Your Project

Open a terminal and run the copier command. Replace the values as follows:

- **`my-dev-machine`**: Your project folder name (lowercase letters, numbers, hyphens, underscores only)
- **`you@example.com`**: Your email address for admin contact

```bash
copier copy gh:SPRIME01/homelab my-dev-machine \
  -d project_name=my-dev-machine \
  -d admin_email=you@example.com \
  -d enable_pulumi=true \
  -d enable_ansible=true \
  -d enable_nx_distributed=true
```

**What the flags mean:**
- `-d project_name=...`: Sets your project name (used in configs and package names)
- `-d admin_email=...`: Sets admin contact email (used in Tailscale ACL configs)
- `-d enable_pulumi=true`: Includes Pulumi infrastructure-as-code tools
- `-d enable_ansible=true`: Includes Ansible configuration management
- `-d enable_nx_distributed=true`: Includes Nx distributed build system

**What happens:**
1. Copier downloads the template from GitHub
2. It validates your inputs (project name must be lowercase, email must be valid)
3. It generates all files in the `my-dev-machine` folder
4. It runs post-generation scripts to set up permissions

**If you see an error**: Check that your project name is lowercase with no spaces, and your email has an `@` symbol.

## Step 2: Enter Your New Project

Change into the newly created project directory:

```bash
cd my-dev-machine
```

**What to read first:**

View the project README (press `q` to exit the viewer):
```bash
less README.md
```

Or if `less` doesn't work, use `cat`:
```bash
cat README.md
```

View the first deployment tutorial:
```bash
less docs/Tutorials/Your-First-Deployment.md
```

These files explain what's in your project and guide you through the first deployment.

## Step 3: Install Development Tools

This project uses specific versions of tools to ensure everything works correctly. You need to install:

### Option A: Using mise (Recommended)

`mise` is a tool version manager that installs the exact versions specified in `.mise.toml`.

**Install mise first** (if you don't have it):
- Visit: https://mise.jdx.dev/getting-started.html
- Or use the quick install: `curl https://mise.run | sh`
- Then restart your terminal or run: `source ~/.bashrc` (or `~/.zshrc` for zsh)

**Install all pinned tools**:
```bash
mise install
```

This installs:
- Node.js 22.17.0
- Python 3.13.9
- Pulumi 3.207.0
- And other pinned tools

### Option B: Manual Installation

If you prefer not to use `mise`, install these tools manually:
- Node.js 22.17.0+: https://nodejs.org/
- Python 3.13.9+: https://www.python.org/
- pnpm 10.22.0+: `npm install -g pnpm`
- Just: https://just.systems/
- Pulumi (if enable_pulumi=true): https://www.pulumi.com/docs/get-started/install/

### Install Node.js Dependencies

After installing Node.js and pnpm, install the project's JavaScript packages:

```bash
pnpm install
```

**What this does**: Downloads and installs all Node.js libraries needed for the TypeScript packages, Nx build system, and testing tools.

**If pnpm command not found**: Install it with `npm install -g pnpm` first.

## Step 4: Set Up Environment Auto-Loading (Optional but Recommended)

`direnv` automatically loads project-specific environment variables when you enter the directory.

### Install direnv

**macOS**: `brew install direnv`
**Linux**: `sudo apt install direnv` (Ubuntu/Debian) or check https://direnv.net/docs/installation.html
**Windows (WSL2)**: `sudo apt install direnv`

### Configure Your Shell

Add direnv to your shell configuration:

**For bash** (add to `~/.bashrc`):
```bash
eval "$(direnv hook bash)"
```

**For zsh** (add to `~/.zshrc`):
```bash
eval "$(direnv hook zsh)"
```

Then restart your terminal or run: `source ~/.bashrc` (or `~/.zshrc`)

### Trust the Project's Environment File

```bash
direnv allow
```

**What this does**: Tells direnv it's safe to load `.envrc` in this directory. The `.envrc` file:
- Activates `mise` tool versions automatically
- Detects if you have homelab encryption keys installed
- Sets `HOMELAB=0` or `HOMELAB=1` based on key presence

### Check Your Environment Status

```bash
just detect-homelab
```

**Expected output for a dev machine**:
```
No homelab SOPS/age key detected; HOMELAB defaults to 0
To force-enable guarded actions (use with caution): export HOMELAB=1
```

This is correct! Your dev machine should have `HOMELAB=0` by default.

**If you see "HOMELAB detected"**: You already have encryption keys installed at `~/.config/sops/age/keys.txt`. This is fine if you set up keys previously.

## Step 5: Encryption Keys (Skip for Dev Machines)

**For regular development work, skip this step.** You don't need encryption keys to write code and run tests.

**When you DO need keys:**
- You're setting up a homelab node (not a dev laptop)
- You need to decrypt production secrets
- You want to run infrastructure deployment commands

### If You Need Keys

Follow the detailed guide in `docs/Tutorials/Your-First-Deployment.md`.

Or use the quick helper script (generates new keys for testing):
```bash
bash scripts/generate-keys.sh
```

**What this creates:**
- A private key at `~/.config/sops/age/keys.txt` (keep this secret!)
- A public key displayed in the terminal (safe to share)

After creating keys, `.envrc` will automatically set `HOMELAB=1` when you're in this directory.

## Step 6: Run Tests to Verify Setup

This project has two types of tests. Run both to ensure everything is working.

### Install devbox (for Python tests)

`devbox` creates an isolated environment with Python 3.13.9 and testing tools.

**Install devbox**:
- Visit: https://www.jetify.com/devbox/docs/installing_devbox/
- Or quick install: `curl -fsSL https://get.jetify.com/devbox | bash`

### Run Python Template Tests

These tests verify the Copier template validation works correctly.

```bash
devbox shell          # Enter isolated environment (takes a moment first time)
pytest tests/python -q  # Run template tests
exit                  # Leave the devbox environment
```

**Expected output**: All tests pass (green dots or "passed" messages).

**What's being tested:**
- Template validators (email format, project name rules, etc.)
- Jinja template rendering
- Hook scripts that run during generation

### Run Bash Infrastructure Tests

These tests verify the security guards and configuration files work correctly.

```bash
just ci-validate
```

**Expected output**: Tests pass or skip (yellow "SKIP" is OK for tests that need optional tools).

**What's being tested:**
- SOPS encryption/decryption guards
- Justfile safety checks (HOMELAB flag, confirmation prompts)
- Tailscale SSH configuration
- Pulumi and Ansible structure validation

**Common test results:**
- ✅ **PASS**: Test succeeded
- ⚠️ **SKIP**: Test skipped (missing optional tools like Tailscale or homelab keys)
- ❌ **FAIL**: Something is wrong, read the error message

## Step 7: Additional Development Commands

### Build TypeScript Packages

```bash
pnpm exec nx build homelab-types
```

**What this does**: Compiles the TypeScript branded types library used by infrastructure code.

### Run JavaScript Tests

```bash
pnpm vitest
```

**What this does**: Runs unit tests for TypeScript packages using Vitest.

### Full Template Validation

```bash
just copier-validate
```

**What this does**: Generates a test project in `/tmp` and validates it end-to-end. This is a comprehensive test used in CI.

### View Available Just Recipes

```bash
just --list
```

**What this does**: Shows all available commands defined in the `justfile`.

## Joining Tailscale on a Dev Machine (Without HOMELAB=1)

You can join your Tailscale network from a dev machine without setting `HOMELAB=1`. This gives you network connectivity to homelab nodes without enabling dangerous infrastructure commands.

### Step 1: Install Tailscale

**macOS**: `brew install tailscale` then `sudo tailscaled install`
**Linux**: Follow https://tailscale.com/download/linux
**Windows**: Download from https://tailscale.com/download/windows

### Step 2: Join Your Tailnet Manually

**Option A: Interactive Login (Recommended for Dev Machines)**

```bash
tailscale up
```

This opens your browser to authenticate with your Tailscale account. No auth keys needed.

**Option B: Using an Auth Key (For Automation)**

1. Generate an auth key in your Tailscale admin console: https://login.tailscale.com/admin/settings/keys
2. Use it to join (do NOT commit this key to git):

```bash
export TAILSCALE_AUTHKEY="tskey-auth-xxxxxxxxxxxxx"
tailscale up --authkey "$TAILSCALE_AUTHKEY"
```

### Step 3: Verify Connection

```bash
tailscale status
tailscale ip -4
```

You should see your machine's Tailscale IP address (usually starts with `100.`).

### What You Can Do Now

- ✅ SSH to homelab nodes via their Tailscale IPs
- ✅ Access services running on homelab nodes
- ✅ Develop and test code locally
- ❌ Run infrastructure deployment commands (still blocked without `HOMELAB=1`)

## Homelab Node Setup (Advanced - Skip for Dev Machines)

**Only follow this section if you're setting up a dedicated homelab machine**, not a regular development laptop.

### Prerequisites for Homelab Nodes

- Encryption keys installed at `~/.config/sops/age/keys.txt`
- `HOMELAB=1` set (auto-detected by `.envrc` when keys present)
- Tailscale installed and connected

### Homelab-Only Commands

**Join tailnet using encrypted config**:
```bash
just tailscale-join
```

**What this does**: Decrypts `infra/tailscale.env.sops` and joins the tailnet using the auth key inside. Requires `HOMELAB=1`.

**Enable Tailscale SSH**:
```bash
just tailscale-ssh-enable
```

**What this does**: Enables SSH server over Tailscale. Other machines on your tailnet can SSH to this node. Requires `HOMELAB=1`.

**Start Nx distributed build agent**:
```bash
just nx-start-agent
```

**What this does**: Starts an Nx agent that can receive build tasks from the orchestrator. Used for distributed TypeScript builds. Requires `HOMELAB=1`.

## Quick Reference

### Dev Machine vs Homelab Node

| Aspect | Dev Machine | Homelab Node |
|--------|-------------|--------------|
| **HOMELAB flag** | `0` (default) | `1` (with keys) |
| **Encryption keys** | Not needed | Required at `~/.config/sops/age/keys.txt` |
| **Join Tailscale** | ✅ `tailscale up` (interactive) | ✅ `just tailscale-join` (uses encrypted auth key) |
| **Run tests** | ✅ Yes | ✅ Yes |
| **Deploy infrastructure** | ❌ Blocked | ✅ Allowed |
| **Decrypt secrets** | ❌ Blocked | ✅ Allowed |
| **Start Nx agents** | ❌ Blocked | ✅ Allowed |

### Essential Commands

```bash
# Check your environment
just detect-homelab           # Shows HOMELAB status

# Run tests
just ci-validate              # Bash infrastructure tests
devbox shell && pytest tests/python -q   # Python template tests

# Build code
pnpm exec nx build homelab-types    # Build TypeScript packages

# Join Tailscale (dev machine)
tailscale up                  # Interactive login

# View all available commands
just --list
```

## Troubleshooting

### "Command not found: mise"
Install mise from https://mise.jdx.dev/getting-started.html and restart your terminal.

### "Command not found: pnpm"
Install with: `npm install -g pnpm`

### "Command not found: just"
Install from https://just.systems/ or use `mise`: add `just = "latest"` to `.mise.toml` and run `mise install`.

### "Command not found: devbox"
Install from https://www.jetify.com/devbox/docs/installing_devbox/

### Tests fail with "HOMELAB != 1"
This is expected on dev machines. The test is checking that guards work correctly. Tests that require `HOMELAB=1` will be skipped automatically.

### "Permission denied" when running scripts
Make sure scripts are executable: `chmod +x scripts/*.sh`

### Tailscale commands fail on WSL2
WSL2 uses the Windows host's Tailscale instance. Install Tailscale on Windows, not inside WSL2.

## Next Steps

1. **Read the tutorials**: Start with `docs/Tutorials/Your-First-Deployment.md`
2. **Explore the documentation**: Check `docs/README.md` for the full documentation map
3. **Join the community**: (Add your community links here)

## Security Reminders

- ⚠️ **Never commit plaintext secrets** - Always use `sops --encrypt` before committing
- ⚠️ **Keep encryption keys safe** - Back up `~/.config/sops/age/keys.txt` securely
- ⚠️ **Don't disable guards** - The `HOMELAB` check prevents accidents
- ⚠️ **Use dev machines for development** - Reserve `HOMELAB=1` for trusted homelab nodes

## Further Reading

- `copier.yml` — Template questions and validators
- `hooks/pre_copy.py` — Python validation logic
- `justfile` — All available commands with guards
- `docs/Tutorials/Your-First-Deployment.md` — Complete deployment walkthrough
- `docs/Explanations/Security-Model.md` — Why the guards exist
- `.envrc` — Environment auto-detection logic
