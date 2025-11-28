#!/usr/bin/env bash
set -euo pipefail

# Test: Ansible project structure and Molecule configuration validation

if ! command -v python3 >/dev/null 2>&1; then
  echo "SKIP: python3 not installed" >&2
  exit 2
fi

echo "Test: Ansible project files exist"
if [ ! -f "infra/ansible-bootstrap/ansible.cfg" ]; then
  echo "FAIL: infra/ansible-bootstrap/ansible.cfg not found" >&2
  exit 1
fi

if [ ! -f "infra/ansible-bootstrap/requirements.txt" ]; then
  echo "FAIL: infra/ansible-bootstrap/requirements.txt not found" >&2
  exit 1
fi

if [ ! -f "infra/ansible-bootstrap/molecule/default/molecule.yml" ]; then
  echo "FAIL: infra/ansible-bootstrap/molecule/default/molecule.yml not found" >&2
  exit 1
fi

if [ ! -f "infra/ansible-bootstrap/library/inventory_utils.py" ]; then
  echo "FAIL: infra/ansible-bootstrap/library/inventory_utils.py not found" >&2
  exit 1
fi

echo "Test: ansible.cfg forces Tailscale SSH transport"
if ! grep -q "ssh_executable = tailscale ssh" infra/ansible-bootstrap/ansible.cfg; then
  echo "FAIL: ansible.cfg must use 'tailscale ssh' as ssh_executable" >&2
  exit 1
fi

echo "Test: inventory_utils.py uses modern Python typing"
if ! grep -q "from typing import Protocol" infra/ansible-bootstrap/library/inventory_utils.py; then
  echo "FAIL: inventory_utils.py missing Protocol import" >&2
  exit 1
fi

if ! grep -q "TypedDict" infra/ansible-bootstrap/library/inventory_utils.py; then
  echo "FAIL: inventory_utils.py missing TypedDict usage" >&2
  exit 1
fi

if ! grep -q "NewType" infra/ansible-bootstrap/library/inventory_utils.py; then
  echo "FAIL: inventory_utils.py missing NewType (branded types)" >&2
  exit 1
fi

if ! grep -q "TypeGuard" infra/ansible-bootstrap/library/inventory_utils.py; then
  echo "FAIL: inventory_utils.py missing TypeGuard" >&2
  exit 1
fi

echo "Test: inventory_utils.py has HOMELAB guard"
if ! grep -q "HOMELAB" infra/ansible-bootstrap/library/inventory_utils.py; then
  echo "FAIL: inventory_utils.py missing HOMELAB guard" >&2
  exit 1
fi

echo "Test: Molecule configuration exists and is valid YAML"
if ! uv run python -c "import yaml; yaml.safe_load(open('infra/ansible-bootstrap/molecule/default/molecule.yml'))" 2>/dev/null; then
  echo "FAIL: molecule.yml is not valid YAML" >&2
  exit 1
fi

echo "Test: Molecule uses Docker driver"
if ! grep -q "driver:" infra/ansible-bootstrap/molecule/default/molecule.yml || \
   ! grep -q "name: docker" infra/ansible-bootstrap/molecule/default/molecule.yml; then
  echo "FAIL: molecule.yml must use Docker driver" >&2
  exit 1
fi

echo "Test: Molecule has verifier configured"
if ! grep -q "verifier:" infra/ansible-bootstrap/molecule/default/molecule.yml; then
  echo "FAIL: molecule.yml missing verifier section" >&2
  exit 1
fi

echo "Test: Molecule test files exist"
if [ ! -f "infra/ansible-bootstrap/molecule/default/converge.yml" ]; then
  echo "FAIL: molecule/default/converge.yml not found" >&2
  exit 1
fi

if [ ! -f "infra/ansible-bootstrap/molecule/default/verify.yml" ]; then
  echo "FAIL: molecule/default/verify.yml not found" >&2
  exit 1
fi

echo "Ansible and Molecule validation tests passed"
exit 0
