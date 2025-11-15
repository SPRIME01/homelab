"""
Typed Ansible inventory utilities using modern Python features.

This module provides type-safe inventory management with Protocols, TypedDict,
and branded types for security-sensitive values.
"""

from typing import Protocol, TypedDict, NewType, Literal, TypeGuard, Required, NotRequired
from dataclasses import dataclass
import os
import sys

# Branded types for security-sensitive values
TailscaleIP = NewType('TailscaleIP', str)
HomelabFlag = Literal['0', '1']


class AnsibleHost(TypedDict, total=True):
    """Type-safe representation of an Ansible inventory host."""
    ansible_host: Required[TailscaleIP]
    ansible_user: Required[str]
    tags: Required[list[str]]
    ansible_connection: NotRequired[Literal['ssh', 'local']]


class InventoryProvider(Protocol):
    """Protocol for inventory data sources."""

    def get_hosts(self) -> dict[str, AnsibleHost]:
        """Return dictionary of hostname -> host configuration."""
        ...

    def verify_connectivity(self) -> bool:
        """Verify that required connectivity (e.g., Tailscale) is active."""
        ...


def is_tailscale_ip(value: str) -> TypeGuard[TailscaleIP]:
    """Type guard for validating Tailscale IP addresses (100.x.x.x range)."""
    parts = value.split('.')
    if len(parts) != 4:
        return False

    try:
        return (
            int(parts[0]) == 100 and
            all(0 <= int(p) <= 255 for p in parts[1:])
        )
    except ValueError:
        return False


def validate_tailscale_ip(raw: str) -> TailscaleIP:
    """Validate and brand a Tailscale IP address."""
    if not is_tailscale_ip(raw):
        raise ValueError(f"Invalid Tailscale IP: {raw} (must be in 100.x.x.x range)")
    return TailscaleIP(raw)


@dataclass(frozen=True)
class HomelabInventory:
    """Immutable inventory configuration for homelab nodes."""
    hosts: dict[str, AnsibleHost]

    @classmethod
    def from_env(cls) -> 'HomelabInventory':
        """
        Load inventory from environment variables.

        Raises:
            RuntimeError: if HOMELAB != 1
            ValueError: if required configuration is missing
        """
        homelab_flag = os.environ.get('HOMELAB', '0')
        if homelab_flag != '1':
            raise RuntimeError(
                f"Refusing to load inventory: HOMELAB != 1 (got {homelab_flag})\n"
                "Set HOMELAB=1 to enable infrastructure operations on trusted machines."
            )

        # In production, load from encrypted SOPS file or dynamic inventory
        # For now, return empty inventory (to be populated by user)
        return cls(hosts={})

    def verify_tailscale_active(self) -> bool:
        """Verify Tailscale is running and connected."""
        import subprocess
        try:
            result = subprocess.run(
                ['tailscale', 'status'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


if __name__ == '__main__':
    # Example usage
    try:
        inventory = HomelabInventory.from_env()
        if not inventory.verify_tailscale_active():
            print("WARNING: Tailscale is not active", file=sys.stderr)
            sys.exit(2)

        print(f"Loaded {len(inventory.hosts)} hosts")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
