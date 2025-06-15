#!/usr/bin/env python3
"""
Comprehensive backup and disaster recovery for homelab.
Backs up K3s etcd, configurations, Home Assistant, and development work.
"""

import asyncio
import tarfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import subprocess

class BackupManager:
    """Manage backups for entire homelab infrastructure."""

    def __init__(self):
        self.backup_root = Path("/mnt/c/HomeLabBackups")  # Windows host backup location
        self.backup_root.mkdir(exist_ok=True)

    async def create_full_backup(self) -> str:
        """Create complete system backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root / f"homelab_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)

        backup_tasks = [
            self._backup_k3s_cluster(backup_dir),
            self._backup_home_assistant(backup_dir),
            self._backup_configurations(backup_dir),
            self._backup_development_work(backup_dir),
            self._backup_docker_volumes(backup_dir)
        ]

        results = await asyncio.gather(*backup_tasks, return_exceptions=True)

        # Create backup manifest
        manifest = {
            "timestamp": timestamp,
            "backup_location": str(backup_dir),
            "components": {},
            "size_mb": self._calculate_backup_size(backup_dir)
        }

        for i, task_name in enumerate(["k3s", "home_assistant", "configs", "development", "docker"]):
            manifest["components"][task_name] = {
                "status": "success" if not isinstance(results[i], Exception) else "failed",
                "error": str(results[i]) if isinstance(results[i], Exception) else None
            }

        with open(backup_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Create compressed archive
        archive_path = f"{backup_dir}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(backup_dir, arcname=backup_dir.name)

        # Cleanup uncompressed backup
        shutil.rmtree(backup_dir)

        return archive_path

    async def _backup_k3s_cluster(self, backup_dir: Path) -> None:
        """Backup K3s cluster state and configurations."""
        k3s_backup = backup_dir / "k3s"
        k3s_backup.mkdir(exist_ok=True)

        # Backup etcd snapshot
        await self._run_command([
            "sudo", "k3s", "etcd-snapshot", "save",
            str(k3s_backup / f"etcd-snapshot-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        ])

        # Backup kubeconfig
        shutil.copy2(Path.home() / ".kube" / "config", k3s_backup / "kubeconfig")

        # Export all resources
        namespaces = await self._get_namespaces()
        for ns in namespaces:
            ns_backup = k3s_backup / "resources" / ns
            ns_backup.mkdir(parents=True, exist_ok=True)

            # Export various resource types
            resources = ["deployments", "services", "configmaps", "secrets", "persistentvolumeclaims"]
            for resource in resources:
                await self._run_command([
                    "kubectl", "get", resource, "-n", ns, "-o", "yaml"
                ], output_file=ns_backup / f"{resource}.yaml")

    def create_restore_script(self, backup_path: str) -> str:
        """Create restore script for disaster recovery."""

        restore_script = f"""#!/bin/bash
# Disaster Recovery Restore Script
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Backup: {backup_path}

set -e

echo "🔄 Starting disaster recovery restore..."
echo "Backup source: {backup_path}"

# Extract backup
echo "📦 Extracting backup archive..."
tar -xzf "{backup_path}" -C /tmp/

BACKUP_DIR="/tmp/$(basename {backup_path} .tar.gz)"

# Restore K3s cluster
echo "☸️  Restoring K3s cluster..."
if [ -f "$BACKUP_DIR/k3s/etcd-snapshot-*" ]; then
    sudo k3s server --cluster-reset --cluster-reset-restore-path="$BACKUP_DIR/k3s/etcd-snapshot-*"
    sudo systemctl restart k3s

    # Wait for cluster to be ready
    echo "⏳ Waiting for cluster to be ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout=300s
fi

# Restore kubeconfig
echo "🔑 Restoring kubeconfig..."
cp "$BACKUP_DIR/k3s/kubeconfig" ~/.kube/config

# Restore resources
echo "📄 Restoring Kubernetes resources..."
for namespace_dir in "$BACKUP_DIR/k3s/resources"/*; do
    if [ -d "$namespace_dir" ]; then
        namespace=$(basename "$namespace_dir")
        echo "Restoring namespace: $namespace"

        # Create namespace if it doesn't exist
        kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -

        # Apply resources
        for resource_file in "$namespace_dir"/*.yaml; do
            if [ -f "$resource_file" ]; then
                kubectl apply -f "$resource_file" -n "$namespace" || echo "Warning: Failed to restore $(basename $resource_file)"
            fi
        done
    fi
done

# Restore Home Assistant (if accessible)
echo "🏠 Restoring Home Assistant..."
if [ -d "$BACKUP_DIR/home_assistant" ] && ping -c 1 192.168.0.41 &> /dev/null; then
    echo "Home Assistant restore requires manual intervention"
    echo "Backup location: $BACKUP_DIR/home_assistant"
    echo "Please manually restore to Home Assistant Yellow device"
fi

echo "✅ Disaster recovery restore completed!"
echo "🔍 Please verify all services are running correctly"
echo "Run: kubectl get pods --all-namespaces"

# Cleanup
rm -rf "$BACKUP_DIR"
"""

        restore_script_path = Path(backup_path).parent / f"restore_{Path(backup_path).stem}.sh"
        with open(restore_script_path, "w") as f:
            f.write(restore_script)

        # Make executable
        subprocess.run(["chmod", "+x", str(restore_script_path)])

        return str(restore_script_path)

# Usage: python3 scripts/backup-manager.py --full-backup --schedule daily
