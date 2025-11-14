# Secrets Management

This document describes the homelab secrets workflow using Mozilla SOPS and age recipients.

## Key generation

- Generate homelab and CI age keypairs using `scripts/generate-keys.sh`.
- The script will write the homelab private identity to `~/.config/sops/age/keys.txt` (permissions `600`).
- The CI private identity will be written to `./ci-keys.txt`. Copy the CI private identity into your CI secret store (example: GitHub Actions secret `SOPS_AGE_KEY`) and then securely remove `./ci-keys.txt`.

## Key storage & backup

- Keep `~/.config/sops/age/keys.txt` machine-local and never commit it to the repository.
- Create at least two encrypted offline backups of your `keys.txt` (symmetric GPG-encrypted archive stored on separate offline media). Example:

```sh
tar -czf homelab-keys.tar.gz ~/.config/sops/age/keys.txt
gpg --symmetric --cipher-algo AES256 --output homelab-keys.tar.gz.gpg homelab-keys.tar.gz
```

- Test restoring the backup from your offline media to ensure recoverability.
- Plan to migrate to a hardware-backed key (YubiKey/OpenPGP) later; see YubiKey notes below.

## YubiKey / Hardware token (high-level)

- YubiKeys typically support OpenPGP/PIV; SOPS supports PGP recipients. If you want hardware-backed protection, generate or import an OpenPGP key onto the YubiKey and use that PGP public key as an additional SOPS recipient.
- Do NOT attempt to import an age identity directly onto a YubiKey unless you have a trusted, documented tool that supports it.

## Using SOPS

- Add recipients (public keys) to `.sops.yaml` under `creation_rules` so that files under `infra/` matching `*.sops` are encrypted to the proper recipients.
- Encrypt a file non-interactively:

```sh
sops --encrypt --input-type dotenv --output-type dotenv --age "<age-recipient>" infra/example.env > infra/example.env.sops
```

- Decrypt:

```sh
sops --decrypt --input-type dotenv --output-type dotenv infra/example.env.sops > infra/example.env
```

## Installing SOPS and age (portable, recommended)

- Best-practice, portable route: download official release binaries and install to a local user bin directory (no sudo). This works well for WSL2 and avoids system package inconsistencies.
- A helper script is included at `scripts/install-sops-age-wsl2.sh` which:
	- detects your CPU architecture (`amd64`/`arm64`),
	- downloads the latest `age` and `sops` release assets from GitHub,
	- installs the `age`, `age-keygen`, and `sops` binaries into `$HOME/.local/bin`.
- To run the installer locally:

```sh
chmod +x scripts/install-sops-age-wsl2.sh
scripts/install-sops-age-wsl2.sh
```

- After running, ensure `$HOME/.local/bin` is in your `PATH` (add to `~/.profile` / `~/.bashrc` / `~/.zshrc`):

```sh
export PATH="$HOME/.local/bin:$PATH"
```

- If the script cannot find a matching `sops` binary for your architecture it will warn; you can then either build `sops` from source using Go (see upstream docs) or download the correct binary manually from the SOPS releases page.

This portable install route is chosen because it is repeatable, doesn't require sudo, and works well across WSL2 distributions.


## Adding new services / CI

- If CI needs to decrypt secrets, create a CI-only age recipient and store its private identity in the CI provider secret store (e.g., `SOPS_AGE_KEY`). In CI startup, write that secret into `$HOME/.config/sops/age/keys.txt` with `chmod 600` before running `sops`.
- Add the CI public recipient to `.sops.yaml` so CI can decrypt/encrypt as needed.

### Setting up GitHub Actions

1. Extract the CI private identity from `ci-keys.txt`:
```sh
cat ci-keys.txt | grep -v "^#"
```

2. In your GitHub repository, go to **Settings → Secrets and variables → Actions → New repository secret**:
   - Name: `SOPS_AGE_KEY`
   - Value: paste the `AGE-SECRET-KEY-...` line from step 1

3. The GitHub Actions workflow (`.github/workflows/sops-ci.yml`) will automatically:
   - Restore the CI identity to `~/.config/sops/age/keys.txt`
   - Decrypt secrets during CI runs
   - Clean up when the ephemeral runner terminates

4. After storing the secret in GitHub, securely delete `ci-keys.txt` locally:
```sh
shred -u ci-keys.txt  # Linux
# or
rm -P ci-keys.txt     # macOS
```

## Rotation and retirement

- To rotate keys: generate a new age identity, add its public recipient to `.sops.yaml`, re-encrypt files to include the new recipient, and then safely retire/remove the old private identity.

## Troubleshooting

- If decrypting fails, ensure your `~/.config/sops/age/keys.txt` contains the correct private identity (and has `chmod 600`).
- For `.env` files, always specify `--input-type dotenv --output-type dotenv` flags. Without these, SOPS defaults to JSON parsing which will fail with "invalid character" errors.
- Check `.sops.yaml` `creation_rules` regex matches the target file path and that recipients are listed correctly. Use single backslashes in YAML single-quoted strings (e.g., `'.*infra/.*\.(yaml|json|env)\.sops$'` not double backslashes).
- The `path_regex` matches against the filename passed to SOPS (or `--filename-override` value), not absolute filesystem paths.
