# Test Exit Code Convention

All bash-based test suites in `tests/` follow a strict exit-code policy so CI and humans agree on pass/fail semantics.

## Codes

| Exit Code | Meaning | When to Use |
| --- | --- | --- |
| `0` | Success | The test validated its assertions and homelab guards behaved as expected |
| `1` | Failure | A guard, schema, or workflow regressed; CI must fail |
| `2` | Skip | A dependency (SOPS key, Tailscale CLI, Docker, etc.) is missing; CI should show yellow but continue |

## Example Pattern

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Test: decrypt infra secrets requires HOMELAB"
if [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then
  echo "SKIP: no homelab key, cannot test decryption" >&2
  exit 2
fi

if HOMELAB=0 sops -d infra/example.env.sops >/dev/null 2>&1; then
  echo "FAIL: decryption succeeded with HOMELAB=0" >&2
  exit 1
fi

echo "PASS: guard enforced"
```

## Mocking External Tools

Use temporary directories and shim scripts so tests never require production credentials:

```bash
TMPDIR="$(mktemp -d)"
cat > "$TMPDIR/tailscale" <<'MOCK'
#!/usr/bin/env bash
echo "100.64.0.10"
MOCK
chmod +x "$TMPDIR/tailscale"
export PATH="$TMPDIR:$PATH"
```

Combine the shims with exit code `2` when the required binary cannot be installed automatically. This keeps CI green while still documenting missing prerequisites.

## Tips

- Document skip reasons in stderr so CI logs explain what to install.
- Avoid `set +e`; let bash exit immediately and rely on `trap` if cleanup is needed.
- Add new suites to `tests/run-tests.sh` so `just ci-validate` picks them up automatically.
