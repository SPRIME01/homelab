#!/usr/bin/env python3
"""
Comprehensive update manager for all homelab components.
Handles K3s, packages, containers, and configuration updates safely.
"""

class UpdateManager:
    """Manage updates across entire homelab infrastructure."""

    def __init__(self):
        self.update_log = Path("logs/updates.log")

    async def check_all_updates(self) -> Dict[str, List[str]]:
        """Check for updates across all components."""
        updates = {
            "system_packages": await self._check_system_updates(),
            "k3s": await self._check_k3s_updates(),
            "containers": await self._check_container_updates(),
            "python_packages": await self._check_python_updates(),
            "ansible_collections": await self._check_ansible_updates()
        }
        return updates

    async def safe_update_sequence(self) -> bool:
        """Perform safe, staged updates with rollback capability."""

        # 1. Create backup before updates
        backup_path = await self._create_pre_update_backup()

        # 2. Update system packages first
        if not await self._update_system_packages():
            await self._rollback_from_backup(backup_path)
            return False

        # 3. Update K3s (if needed)
        if not await self._update_k3s():
            await self._rollback_from_backup(backup_path)
            return False

        # 4. Update containers
        if not await self._update_containers():
            await self._rollback_from_backup(backup_path)
            return False

        # 5. Verify all services after updates
        if not await self._verify_all_services():
            await self._rollback_from_backup(backup_path)
            return False

        return True

# Usage: python3 scripts/update-manager.py --check-all --safe-update
