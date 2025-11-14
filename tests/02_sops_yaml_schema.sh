#!/usr/bin/env bash
set -euo pipefail

# Test: validate .sops.yaml contains creation_rules with an infra rule and age recipients
python3 - <<'PY'
import sys, yaml, re
try:
    cfg = yaml.safe_load(open('.sops.yaml'))
except Exception as e:
    print('FAIL: cannot parse .sops.yaml:', e)
    sys.exit(2)
if not cfg or 'creation_rules' not in cfg:
    print('FAIL: creation_rules missing')
    sys.exit(3)
found = False
for r in cfg['creation_rules']:
    pr = r.get('path_regex','')
    age = r.get('age', None)
    # Robust check: ensure the regex references infra and .sops and that age recipients exist
    if 'infra' in pr and '.sops' in pr and age:
        found = True
        break
if not found:
    print('FAIL: matching creation_rule with age recipients not found')
    sys.exit(4)
print('PASS: .sops.yaml schema and rule validated')
sys.exit(0)
PY
