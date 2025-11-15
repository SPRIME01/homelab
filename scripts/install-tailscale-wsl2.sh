#!/usr/bin/env bash
set -euo pipefail

# Helper for configuring WSL2 to use the Windows Tailscale instance.
# This script does NOT install tailscaled on Windows or WSL2.
# It installs a small user-local helper that can query the Windows host
# for Tailscale status/IP using PowerShell, and documents the sudo exception.

PREFIX="$HOME/.local"
BIN_DIR="$PREFIX/bin"
mkdir -p "$BIN_DIR"

echo "Note: Tailscale requires system networking setup on Windows."
echo "This repository treats Tailscale as a system-installed service on the Windows host."
echo "Installing or modifying system tailscaled is the only accepted exception to the no-sudo policy."

detect_windows_tailscale_ip() {
  # Prefer explicit env var (from SOPS-managed config)
  if [ -n "${TAILSCALE_WINDOWS_IP-}" ]; then
    echo "$TAILSCALE_WINDOWS_IP"
    return 0
  fi

  # Try to call PowerShell to get the IPv4 Tailscale address from the Windows host
  if command -v powershell.exe >/dev/null 2>&1; then
    # Use tailscale CLI on Windows if available to query the IP
    ip=$(powershell.exe -NoProfile -Command "try { (tailscale ip -4) -join '\n' } catch { \$null }" 2>/dev/null | tr -d '\r') || true
    ip=$(echo "$ip" | tr -d '\r' | sed -n 's/^\s*\(100\.[0-9]\+\.[0-9]\+\.[0-9]\+\)\s*$/\1/p' | head -n1 || true)
    if [ -n "$ip" ]; then
      echo "$ip"
      return 0
    fi
  fi

  # Fallback: attempt to parse ipconfig output for the 100.x.x.x address
  if command -v cmd.exe >/dev/null 2>&1; then
    ip=$(cmd.exe /c ipconfig 2>/dev/null | tr -d '\r' | sed -n 's/.*: \(100\.[0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p' | head -n1 || true)
    if [ -n "$ip" ]; then
      echo "$ip"
      return 0
    fi
  fi

  return 1
}

cat > "$BIN_DIR/wsl-tailscale-ip" <<'SH'
#!/usr/bin/env bash
# Prints the Windows host Tailscale IPv4 address if discoverable.
set -euo pipefail
if [ -n "${TAILSCALE_WINDOWS_IP-}" ]; then
  echo "$TAILSCALE_WINDOWS_IP"
  exit 0
fi
if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -Command "try { (tailscale ip -4) -join '\n' } catch { \$null }" 2>/dev/null | tr -d '\r' | sed -n 's/^\s*\(100\.[0-9]\+\.[0-9]\+\.[0-9]\+\)\s*$/\1/p' | head -n1
  exit $?
fi
if command -v cmd.exe >/dev/null 2>&1; then
  cmd.exe /c ipconfig 2>/dev/null | tr -d '\r' | sed -n 's/.*: \(100\.[0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p' | head -n1
  exit $?
fi
echo "" >&2
exit 1
SH

chmod 0755 "$BIN_DIR/wsl-tailscale-ip"

echo "Installed helper: $BIN_DIR/wsl-tailscale-ip"
echo "Add '$BIN_DIR' to your PATH if not already present: export PATH=\"$BIN_DIR:\$PATH\""
echo
echo "Recommended workflow (Windows host already has Tailscale):"
echo "  - On Windows: ensure Tailscale is running and SSH is enabled on homelab nodes via 'tailscale up --ssh'"
echo "  - In WSL2: use the helper 'wsl-tailscale-ip' to discover the Windows Tailscale IP and connect to Tailscale IPs directly"
echo
echo "If you intend to run a tailscaled daemon inside WSL2, that requires system-level networking changes and is the only permitted sudo exception. See docs/Tailscale.md for details."

exit 0
