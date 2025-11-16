"""Hooks package for generated homelab projects.

This package exposes pre/post copy hooks used by the template. Package
is empty but necessary so tests in generated projects can import
`hooks.pre_copy`.
"""

__all__ = ["pre_copy"]
