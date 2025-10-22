#!/usr/bin/env bash
set -euo pipefail

# Validate all YAML files under docs/ using Python's PyYAML (safe_load)
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
DOCS_DIR="$ROOT_DIR/docs"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run this script"
  exit 2
fi

python3 - <<'PY'
import sys, pathlib
try:
    import yaml
except Exception as e:
    print('PyYAML is required. Install with: pip install pyyaml')
    sys.exit(2)

root = pathlib.Path('docs')
errors = 0
for p in sorted(root.rglob('*.yml')) + sorted(root.rglob('*.yaml')):
    try:
        with p.open('r', encoding='utf-8') as fh:
            yaml.safe_load(fh)
    except Exception as e:
        print(f'YAML parse error in {p}: {e}', file=sys.stderr)
        errors += 1

if errors:
    print(f"Found {errors} YAML parse error(s)")
    sys.exit(1)
else:
    print('All YAML files under docs/ parsed successfully')
    sys.exit(0)
PY
