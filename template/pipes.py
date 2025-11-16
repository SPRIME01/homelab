"""Compatibility shim for the removed stdlib ``pipes`` module."""
from __future__ import annotations

import shlex
from typing import AnyStr


def quote(value: AnyStr) -> str:
    """Return a shell-escaped representation of *value*."""
    text = value.decode() if isinstance(value, (bytes, bytearray)) else str(value)
    return shlex.quote(text)
