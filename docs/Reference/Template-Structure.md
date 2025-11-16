# Template Structure Reference

This document describes the structure of the Copier template and how files are organized to generate customized homelab projects.

## Overview

The template uses Copier 9.0+ with Jinja2 templating (`.j2` suffix) to generate projects with optional features controlled by boolean flags (`enable_pulumi`, `enable_ansible`, `enable_nx_distributed`).

## Directory Structure

```
homelab/
├── copier.yml                    # Template configuration and variables
├── .copier-answers.yml           # Generated in output (tracks template version)
├── template/                     # All files to be copied to generated projects
│   ├── justfile.j2              # Templated with conditional recipes
│   ├── pytest.ini               # Configures Python import paths
│   ├── package.json.j2          # Templated with project metadata
│   ├── devbox.json.j2           # Templated Devbox configuration
│   ├── README.md.j2             # Customized with project details
│   ├── extensions/              # Jinja2 filters and validators
│   │   ├── __init__.py          # Makes it a Python package
│   │   └── validators.py        # Validation filters (semver, email, npm_scope)
│   ├── hooks/                   # Pre/post generation hooks
│   │   ├── __init__.py          # Makes it a Python package
│   │   ├── pre_copy.py          # Validates user inputs before generation
│   │   └── post_copy.sh         # Prints security checklist after generation
│   ├── docs/                    # Documentation templates
│   │   └── Reference/
│   │       └── example.envrc.j2 # Templated example files
│   ├── packages/                # TypeScript packages
│   │   ├── homelab-types/       # Branded types library
│   │   └── pulumi-bootstrap/    # Pulumi infrastructure code
│   └── tests/                   # Test suite for generated projects
│       ├── 04_just_safety_guards.sh     # Validates justfile guards
│       ├── 08_infra_guards.sh           # Validates infra recipe guards
│       ├── run-tests.sh.jinja           # Test runner (conditionally includes tests)
│       └── python/                      # Python unit tests
│           ├── test_validators.py.jinja # Tests for validation filters
│           └── test_pre_copy.py.jinja   # Tests for pre-copy validation
├── extensions/                  # Root-level Jinja extensions (used by Copier)
│   └── validators.py            # Same as template/extensions/validators.py
├── hooks/                       # Root-level hooks (executed by Copier)
│   ├── pre_copy.py              # Validates answers before copying
│   └── post_copy.sh             # Prints checklist after copying
├── tests/                       # Tests for the template itself
│   └── python/
│       ├── test_validators.py           # Tests extensions.validators
│       ├── test_pre_copy.py             # Tests hooks.pre_copy
│       └── test_template_generation.py  # Integration tests
├── docs/                        # Template documentation
│   ├── Plans/
│   │   └── copier_dev.plan.md           # Implementation plan
│   └── Reference/
│       ├── Template-Testing.md          # Testing guide
│       ├── Template-Updates.md          # Update guide
│       └── Template-Structure.md        # This file
└── scripts/                     # Helper scripts
    └── migrations/
        └── migrate_v1_to_v2.sh          # Migration scripts
```

## Key Files

### copier.yml

Defines template variables and configuration:

```yaml
_subdirectory: template              # Files to copy from template/
_templates_suffix: .j2               # Use .j2 for Jinja2 templates
_jinja_extensions:
  - extensions/validators.py:ValidationFilters  # Custom Jinja filters

# Variables with validation
project_name:
  type: str
  help: Project name (lowercase, alphanumeric, hyphens, underscores)
  validator: "{% if not (project_name is match('^[a-z0-9\\-_]+$')) %}Must be lowercase{% endif %}"

enable_pulumi:
  type: bool
  default: true
  help: Include Pulumi infrastructure as code

enable_ansible:
  type: bool
  default: true
  help: Include Ansible configuration management

_exclude:
  - "{% if not enable_pulumi %}packages/pulumi-bootstrap{% endif %}"
  - "{% if not enable_ansible %}infra/ansible-bootstrap{% endif %}"

_tasks:
  - ["python", "hooks/pre_copy.py", ...]  # Pre-generation validation
  - ["bash", "hooks/post_copy.sh"]         # Post-generation checklist
```

### template/justfile.j2

Conditionally includes recipes based on feature flags:

```jinja
{% raw %}
# Core recipes (always included)
deploy:
	bash -lc 'if [ "${HOMELAB:-0}" != "1" ]; then exit 1; fi; ...'
{% endraw %}

{% if enable_pulumi %}
{% raw %}
# Pulumi recipes (only if enable_pulumi=true)
pulumi-preview:
	bash -lc '...'

pulumi-up:
	bash -lc 'if [ "${HOMELAB:-0}" != "1" ]; then exit 1; fi; ...'
{% endraw %}
{% endif %}

{% if enable_ansible %}
{% raw %}
# Ansible recipes (only if enable_ansible=true)
ansible-ping:
	bash -lc 'if [ "${HOMELAB:-0}" != "1" ]; then exit 1; fi; ...'
{% endraw %}
{% endif %}
```

### template/pytest.ini

Configures pytest for generated projects:

```ini
[pytest]
# Add project root to Python path so tests can import from extensions/ and hooks/
pythonpath = .

# Standard pytest discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests/python

# Show extra test summary info
addopts = -ra --strict-markers
```

This enables tests to import:
- `from extensions.validators import ValidationFilters`
- `from hooks import pre_copy`

### template/extensions/validators.py

Jinja2 extension providing custom filters:

```python
import re
from jinja2.ext import Extension

def is_semver(value: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+$", value))

class ValidationFilters(Extension):
    def __init__(self, environment=None):
        # Allow instantiation without environment for unit tests
        if environment is None:
            self.is_semver = is_semver
            return

        super().__init__(environment)
        environment.filters["is_semver"] = is_semver
```

## Feature Flags

### enable_pulumi (default: true)

When enabled, includes:
- `packages/pulumi-bootstrap/` — TypeScript Pulumi project
- `infra/pulumi-bootstrap/` — Symlink to packages/pulumi-bootstrap
- Pulumi recipes in justfile: `pulumi-preview`, `pulumi-up`, `pulumi-destroy`, `pulumi-stack-init`
- Test: `tests/06_pulumi_project_validation.sh`

When disabled, excludes all of the above via `_exclude` and conditional blocks.

### enable_ansible (default: true)

When enabled, includes:
- `infra/ansible-bootstrap/` — Ansible playbooks and roles
- Ansible recipes in justfile: `ansible-ping`, `ansible-deploy`, `ansible-check`, `ansible-molecule-*`
- Test: `tests/07_ansible_molecule_validation.sh`

When disabled, excludes all of the above.

### enable_nx_distributed (default: true)

When enabled, includes:
- `scripts/nx-*.sh` — Agent setup scripts
- `docs/Explanations/Nx-Distributed-Architecture.md`
- Nx recipes in justfile: `nx-init`, `nx-encrypt-config`, `nx-start-agent`, `nx-distributed-build`
- Test: `tests/10_nx_distributed_validation.sh`

When disabled, excludes all of the above.

## Validation and Hooks

### Pre-generation validation (hooks/pre_copy.py)

Validates user inputs before copying:
- `project_name` matches `^[a-z0-9\-_]+$`
- `admin_email` contains `@` and valid TLD
- `npm_scope` (if provided) starts with `@` and matches `^@[a-z0-9\-_]+$`
- Tool versions match semver pattern `^\d+\.\d+\.\d+$`

Exits with code 1 and helpful message if validation fails.

### Post-generation checklist (hooks/post_copy.sh)

Prints 8-step security checklist:
1. Generate age keypair
2. Extract public recipient
3. Update .sops.yaml with real recipient
4. Create and encrypt secrets
5. Obtain Tailscale auth key
6. Configure Tailscale ACL tags
7. Run validation suite (`just ci-validate`)
8. Follow first deployment tutorial

## Testing Generated Projects

Generated projects include a full test suite:

### Shell tests
- `tests/04_just_safety_guards.sh` — Validates HOMELAB guards, DEPLOY_CONFIRM, DRY_RUN
- `tests/08_infra_guards.sh` — Validates Pulumi/Ansible recipe guards

### Python tests
- `tests/python/test_validators.py` — Unit tests for validation filters
- `tests/python/test_pre_copy.py` — Unit tests for pre-copy validation logic

Run with:
```bash
cd generated-project/
bash tests/04_just_safety_guards.sh
bash tests/08_infra_guards.sh
pytest tests/python -q
```

Or use the justfile target:
```bash
just ci-validate  # Runs all tests
```

## Updating Generated Projects

Use `copier update` to apply template changes:

```bash
# In generated project directory
copier update --vcs-ref=v1.1.0  # Update to specific version

# Or update to latest
copier update
```

See `docs/Reference/Template-Updates.md` for safe update workflows and versioning strategy.

## Development Workflow

### Testing the template locally

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run unit tests for validators and hooks
pytest tests/python -q

# Generate a test project
copier copy --vcs-ref=HEAD . /tmp/test-project \
  -d project_name=test -d admin_email=test@example.com \
  -d enable_pulumi=true -d enable_ansible=true \
  --defaults --UNSAFE

# Test the generated project
cd /tmp/test-project
bash tests/04_just_safety_guards.sh
bash tests/08_infra_guards.sh
pytest tests/python -q
```

### Using just targets

```bash
just copier-test       # Run unit tests
just copier-validate   # Generate and test a project
```

## Common Patterns

### Conditional file inclusion

Use `_exclude` in `copier.yml`:
```yaml
_exclude:
  - "{% if not enable_feature %}path/to/exclude{% endif %}"
```

### Conditional content blocks

Use Jinja2 conditionals in `.j2` files:
```jinja
{% if enable_feature %}
# Feature-specific content
{% endif %}
```

### Accessing variables in templates

```jinja
Project: {{ project_name }}
Email: {{ admin_email }}
{% if npm_scope %}Scope: {{ npm_scope }}{% endif %}
```

### Custom validation filters

In validators.py:
```python
def my_filter(value: str) -> bool:
    return bool(re.match(pattern, value))

class ValidationFilters(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        environment.filters["my_filter"] = my_filter
```

Use in copier.yml:
```yaml
my_var:
  type: str
  validator: "{% if not (my_var | my_filter) %}Invalid!{% endif %}"
```

## Security Considerations

1. **Never prompt for secrets** in copier.yml — guide users to generate them post-copy
2. **Always use `--vcs-ref=HEAD`** in CI to avoid remote template injection
3. **Validate all user inputs** in pre_copy.py before file generation
4. **Test with `HOMELAB=0`** to ensure guards work correctly
5. **Encrypt sensitive files** with SOPS before committing to template

## References

- Copier documentation: https://copier.readthedocs.io/
- Jinja2 documentation: https://jinja.palletsprojects.com/
- Template plan: `docs/Plans/copier_dev.plan.md`
- Testing guide: `docs/Reference/Template-Testing.md`
- Update guide: `docs/Reference/Template-Updates.md`
