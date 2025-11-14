#!/usr/bin/env bash
set -euo pipefail

# Portable installer for sops and age into $HOME/.local/bin (no sudo required)
# Usage: bash scripts/install-sops-age-wsl2.sh

PREFIX="${HOME}/.local"
BIN_DIR="$PREFIX/bin"
mkdir -p "$BIN_DIR"

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) PAT_TAG="linux_amd64" ;;
  aarch64|arm64) PAT_TAG="linux_arm64" ;;
  *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;;
esac

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
AUTH_HEADER=""
if [ -n "$GITHUB_TOKEN" ]; then
  AUTH_HEADER="-H Authorization: token $GITHUB_TOKEN"
fi

get_asset_url() {
  owner="$1"; repo="$2"; pattern="$3"
  api="https://api.github.com/repos/${owner}/${repo}/releases/latest"
  url=$(bash -lc "curl -sS $AUTH_HEADER '$api' | jq -r '.assets[]?.browser_download_url | select(test(\"${pattern}\"))' | head -n1")
  echo "$url"
}

echo "Detecting latest release assets for architecture: $PAT_TAG"
AGE_URL=$(get_asset_url FiloSottile age "${PAT_TAG}")
SOPS_URL=$(get_asset_url getsops sops "${PAT_TAG}")

if [ -z "$AGE_URL" ]; then
  echo "ERROR: could not find age release asset for ${PAT_TAG}" >&2
  exit 2
fi

tmpdir=$(mktemp -d)
cleanup(){ rm -rf "$tmpdir"; }
trap cleanup EXIT

echo "Downloading age from: $AGE_URL"
curl -sL "$AGE_URL" -o "$tmpdir/age.tar.gz"
tar -C "$tmpdir" -xzf "$tmpdir/age.tar.gz"

# Move any 'age' and 'age-keygen' binaries found to $BIN_DIR
shopt -s nullglob
for b in "$tmpdir"/*/age* "$tmpdir"/age* "$tmpdir"/bin/age*; do
  if [ -f "$b" ] && [ -x "$b" ]; then
    cp "$b" "$BIN_DIR/"
  fi
done
shopt -u nullglob

if [ -n "$SOPS_URL" ]; then
  echo "Downloading sops from: $SOPS_URL"
  curl -sL "$SOPS_URL" -o "$tmpdir/sops.tar.gz"
  tar -C "$tmpdir" -xzf "$tmpdir/sops.tar.gz"
  # Move sops binary
  shopt -s nullglob
  for s in "$tmpdir"/*/sops* "$tmpdir"/sops* "$tmpdir"/bin/sops*; do
    if [ -f "$s" ] && [ -x "$s" ]; then
      cp "$s" "$BIN_DIR/sops"
    fi
  done
  shopt -u nullglob
else
  echo "Warning: sops binary asset not found for ${PAT_TAG}. You can build sops from source (Go) or download manually from https://github.com/getsops/sops/releases" >&2
fi

chmod 0755 "$BIN_DIR/age" || true
chmod 0755 "$BIN_DIR/age-keygen" || true
chmod 0755 "$BIN_DIR/sops" || true

echo "Installed into: $BIN_DIR"
echo "Ensure $BIN_DIR is in your PATH (add 'export PATH=\"$BIN_DIR:\$PATH\"' to your shell rc)."
echo "Verify with: $BIN_DIR/age-keygen --version && $BIN_DIR/sops --version"
