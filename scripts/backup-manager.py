#!/usr/bin/env python3
"""
Comprehensive backup and disaster recovery for homelab.
Backs up K3s etcd, configurations, Home Assistant, Supabase, and development work.
"""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

from scripts._uv_utils import validate_uv_environment


class BackupManager:
    """Manage backups for entire homelab infrastructure."""

    def __init__(self) -> None:
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
            self._backup_docker_volumes(backup_dir),
        ]

        results = await asyncio.gather(*backup_tasks, return_exceptions=True)

        # Create backup manifest
        components = {}
        for i, task_name in enumerate(
            ["k3s", "home_assistant", "configs", "development", "docker"]
        ):
            components[task_name] = {
                "status": "success"
                if not isinstance(results[i], Exception)
                else "failed",
                "error": str(results[i]) if isinstance(results[i], Exception) else None,
            }

        manifest: dict[str, str | dict[str, dict[str, str | None]] | float] = {
            "timestamp": timestamp,
            "backup_location": str(backup_dir),
            "components": components,
            "size_mb": self._calculate_backup_size(backup_dir),
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

    async def create_supabase_backup(self) -> str:
        """Create Supabase-specific backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root / f"supabase_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)

        print("💾 Creating Supabase backup...")

        try:
            # Check if Supabase namespace exists
            result = subprocess.run(
                ["kubectl", "get", "namespace", "supabase"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print("❌ Supabase namespace not found!")
                return ""

            # Backup Supabase PostgreSQL database
            await self._backup_supabase_database(backup_dir)

            # Backup Supabase configurations
            await self._backup_supabase_config(backup_dir)

            # Backup Supabase storage volumes
            await self._backup_supabase_storage(backup_dir)

            # Create manifest
            manifest: dict[str, str | list[str] | float] = {
                "timestamp": timestamp,
                "backup_type": "supabase",
                "components": ["database", "config", "storage"],
                "size_mb": self._calculate_backup_size(backup_dir),
            }

            with open(backup_dir / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)

            # Create compressed archive
            archive_path = f"{backup_dir}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_dir, arcname=backup_dir.name)

            # Cleanup uncompressed backup
            shutil.rmtree(backup_dir)

            print(f"✅ Supabase backup completed: {archive_path}")
            return archive_path

        except Exception as e:
            print(f"❌ Supabase backup failed: {e}")
            return ""

    async def _backup_supabase_database(self, backup_dir: Path) -> None:
        """Backup Supabase PostgreSQL database."""
        db_backup_dir = backup_dir / "database"
        db_backup_dir.mkdir(exist_ok=True)

        backup_file = (
            db_backup_dir
            / f"supabase_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        )

        # Create database dump
        dump_cmd = [
            "kubectl",
            "exec",
            "-n",
            "supabase",
            "deployment/supabase-postgres",
            "--",
            "pg_dump",
            "-U",
            "supabase_admin",
            "-d",
            "postgres",
        ]

        with open(backup_file, "w") as f:
            process = await asyncio.create_subprocess_exec(
                *dump_cmd, stdout=f, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Database backup failed: {stderr.decode()}")

        print(f"✅ Database backup saved: {backup_file}")

    async def _backup_supabase_config(self, backup_dir: Path) -> None:
        """Backup Supabase configuration and secrets."""
        config_backup_dir = backup_dir / "config"
        config_backup_dir.mkdir(exist_ok=True)

        # Backup secrets
        await self._run_command(
            ["kubectl", "get", "secrets", "-n", "supabase", "-o", "yaml"],
            output_file=config_backup_dir / "secrets.yaml",
        )

        # Backup configmaps
        await self._run_command(
            ["kubectl", "get", "configmaps", "-n", "supabase", "-o", "yaml"],
            output_file=config_backup_dir / "configmaps.yaml",
        )

        # Backup deployments
        await self._run_command(
            ["kubectl", "get", "deployments", "-n", "supabase", "-o", "yaml"],
            output_file=config_backup_dir / "deployments.yaml",
        )

        # Backup services
        await self._run_command(
            ["kubectl", "get", "services", "-n", "supabase", "-o", "yaml"],
            output_file=config_backup_dir / "services.yaml",
        )

        print("✅ Configuration backup completed")

    async def _backup_supabase_storage(self, backup_dir: Path) -> None:
        """Backup Supabase storage volumes."""
        storage_backup_dir = backup_dir / "storage"
        storage_backup_dir.mkdir(exist_ok=True)

        # Backup persistent volume claims
        await self._run_command(
            ["kubectl", "get", "pvc", "-n", "supabase", "-o", "yaml"],
            output_file=storage_backup_dir / "pvc.yaml",
        )

        # Check if storage pod exists and backup storage data
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    "supabase",
                    "-l",
                    "app=supabase-storage",
                    "-o",
                    "jsonpath={.items[0].metadata.name}",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                storage_pod = result.stdout.strip()

                # Create tar archive of storage data
                await self._run_command(
                    [
                        "kubectl",
                        "exec",
                        "-n",
                        "supabase",
                        storage_pod,
                        "--",
                        "tar",
                        "-czf",
                        "/tmp/storage_backup.tar.gz",
                        "/var/lib/storage",
                    ]
                )

                # Copy backup from pod
                await self._run_command(
                    [
                        "kubectl",
                        "cp",
                        f"supabase/{storage_pod}:/tmp/storage_backup.tar.gz",
                        str(storage_backup_dir / "storage_data.tar.gz"),
                    ]
                )

                print("✅ Storage data backup completed")
            else:
                print("⚠️ Storage pod not found, skipping storage data backup")

        except Exception as e:
            print(f"⚠️ Storage backup warning: {e}")

    async def _backup_k3s_cluster(self, backup_dir: Path) -> None:
        """Backup K3s cluster state and configurations."""
        k3s_backup = backup_dir / "k3s"
        k3s_backup.mkdir(exist_ok=True)

        # Backup etcd snapshot
        await self._run_command(
            [
                "sudo",
                "k3s",
                "etcd-snapshot",
                "save",
                str(
                    k3s_backup
                    / f"etcd-snapshot-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                ),
            ]
        )

        # Backup kubeconfig
        shutil.copy2(Path.home() / ".kube" / "config", k3s_backup / "kubeconfig")

        # Export all resources
        namespaces = await self._get_namespaces()
        for ns in namespaces:
            ns_backup = k3s_backup / "resources" / ns
            ns_backup.mkdir(parents=True, exist_ok=True)

            # Export various resource types
            resources = [
                "deployments",
                "services",
                "configmaps",
                "secrets",
                "persistentvolumeclaims",
            ]
            for resource in resources:
                await self._run_command(
                    ["kubectl", "get", resource, "-n", ns, "-o", "yaml"],
                    output_file=ns_backup / f"{resource}.yaml",
                )

    async def _backup_home_assistant(self, backup_dir: Path) -> None:
        """Backup Home Assistant configuration."""
        ha_backup = backup_dir / "home_assistant"
        ha_backup.mkdir(exist_ok=True)

        # This would backup Home Assistant from the Yellow device
        # For now, just create a placeholder
        with open(ha_backup / "README.txt", "w") as f:
            f.write("Home Assistant backup requires manual intervention.\n")
            f.write("Access Home Assistant Yellow and create backup manually.\n")

    async def _backup_configurations(self, backup_dir: Path) -> None:
        """Backup important configuration files."""
        config_backup = backup_dir / "configurations"
        config_backup.mkdir(exist_ok=True)

        # Backup this project
        project_root = Path(__file__).parent.parent
        shutil.copytree(
            project_root,
            config_backup / "homelab-project",
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )

    async def _backup_development_work(self, backup_dir: Path) -> None:
        """Backup development work and projects."""
        dev_backup = backup_dir / "development"
        dev_backup.mkdir(exist_ok=True)

        # This is a placeholder - would backup development folders
        with open(dev_backup / "README.txt", "w") as f:
            f.write("Development backup placeholder.\n")

    async def _backup_docker_volumes(self, backup_dir: Path) -> None:
        """Backup Docker volumes and containers."""
        docker_backup = backup_dir / "docker"
        docker_backup.mkdir(exist_ok=True)

        # This is a placeholder - would backup Docker data
        with open(docker_backup / "README.txt", "w") as f:
            f.write("Docker backup placeholder.\n")

    async def _run_command(
        self, cmd: list[str], output_file: Path | None = None
    ) -> None:
        """Run command and optionally save output to file."""
        try:
            if output_file:
                with open(output_file, "w") as f:
                    process = await asyncio.create_subprocess_exec(
                        *cmd, stdout=f, stderr=asyncio.subprocess.PIPE
                    )
                    _, stderr = await process.communicate()
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(
                    f"Command failed: {' '.join(cmd)} - {stderr.decode()}"
                )

        except Exception as e:
            print(f"⚠️ Command failed: {' '.join(cmd)} - {e}")

    async def _get_namespaces(self) -> list[str]:
        """Get list of all namespaces."""
        process = await asyncio.create_subprocess_exec(
            "kubectl",
            "get",
            "namespaces",
            "-o",
            "jsonpath={.items[*].metadata.name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()

        if process.returncode == 0:
            return stdout.decode().split()
        return []

    def _calculate_backup_size(self, backup_dir: Path) -> float:
        """Calculate backup size in MB."""
        total_size = 0
        for root, _, files in os.walk(backup_dir):
            for filename in files:
                filepath = Path(root) / filename
                if filepath.is_file():
                    total_size += filepath.stat().st_size
        return round(total_size / (1024 * 1024), 2)

    def create_restore_script(self, backup_path: str) -> str:
        """Create restore script for disaster recovery."""

        restore_script = f"""#!/bin/bash
# Disaster Recovery Restore Script
# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
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

        restore_script_path = (
            Path(backup_path).parent / f"restore_{Path(backup_path).stem}.sh"
        )
        with open(restore_script_path, "w") as f:
            f.write(restore_script)

        # Make executable
        subprocess.run(["chmod", "+x", str(restore_script_path)])

        return str(restore_script_path)


async def main() -> None:
    """Main backup manager entry point."""
    validate_uv_environment()

    parser = argparse.ArgumentParser(description="Homelab Backup Manager")
    parser.add_argument(
        "--full-backup", action="store_true", help="Create full system backup"
    )
    parser.add_argument(
        "--supabase-backup", action="store_true", help="Create Supabase-only backup"
    )
    parser.add_argument(
        "--schedule", choices=["daily", "weekly", "monthly"], help="Schedule backup"
    )

    args = parser.parse_args()

    backup_manager = BackupManager()

    if args.supabase_backup:
        print("🗄️ Starting Supabase backup...")
        backup_path = await backup_manager.create_supabase_backup()
        if backup_path:
            print(f"✅ Supabase backup completed: {backup_path}")
        else:
            print("❌ Supabase backup failed")
            exit(1)

    elif args.full_backup:
        print("🔄 Starting full system backup...")
        backup_path = await backup_manager.create_full_backup()
        print(f"✅ Full backup completed: {backup_path}")

        # Create restore script
        restore_script = backup_manager.create_restore_script(backup_path)
        print(f"📜 Restore script created: {restore_script}")

    else:
        print("Please specify --full-backup or --supabase-backup")
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())

# Usage: python3 scripts/backup-manager.py --full-backup --schedule daily
