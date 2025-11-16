"""Compatibility shim for the deprecated stdlib ``pipes`` module.

Python 3.13 removed :mod:`pipes`, but third-party packages such as
``pytest-molecule`` still import :func:`pipes.quote`.  Providing the
function locally keeps those dependencies working without modifying the
packages themselves.
"""
from __future__ import annotations

import shlex
from typing import AnyStr


def quote(value: AnyStr) -> str:
    """Return a shell-escaped version of *value*.

    This mirrors :func:`shlex.quote` and preserves backwards compatible
    semantics for callers that previously relied on ``pipes.quote``.
    """

    # Ensure we always operate on a plain string for shlex.quote.
    text = value.decode() if isinstance(value, (bytes, bytearray)) else str(value)
    return shlex.quote(text)
