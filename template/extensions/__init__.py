"""Extensions package for copier template.

This package exposes Jinja filter extensions used during template
generation. The package is intentionally minimal and only exists to
make imports like `from extensions.validators import ValidationFilters`
work in tests that run inside the generated project.
"""

__all__ = ["validators"]
