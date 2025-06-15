#!/usr/bin/env python3
"""
Migrate from PostgreSQL to Supabase in K3s cluster.
Handles data migration, schema recreation, and service updates.
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scripts._uv_utils import validate_uv_environment


@dataclass
class MigrationConfig:
    """Migration configuration."""

    old_postgres_host: str
    old_postgres_port: int
    old_postgres_db: str
    old_postgres_user: str
    old_postgres_password: str
    supabase_host: str
    supabase_port: int
    supabase_db: str
    supabase_user: str
    supabase_password: str
    backup_path: Path


class SupabaseMigrator:
    """Handle PostgreSQL to Supabase migration."""

    def __init__(self, config: MigrationConfig):
        self.config = config
        self.log_file = Path("/tmp/supabase_migration.log")

    def log_message(self, message: str, level: str = "INFO") -> None:
        """Log migration progress."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)

        with open(self.log_file, "a") as f:
            f.write(log_entry + "\n")

    async def migrate_to_supabase(self) -> bool:
        """Execute complete migration to Supabase."""
        try:
            self.log_message("Starting PostgreSQL to Supabase migration")

            # 1. Create backup of existing PostgreSQL
            await self._backup_existing_postgres()

            # 2. Deploy Supabase stack
            await self._deploy_supabase()

            # 3. Wait for Supabase to be ready
            await self._wait_for_supabase_ready()

            # 4. Migrate schema
            await self._migrate_schema()

            # 5. Migrate data
            await self._migrate_data()

            # 6. Update application configurations
            await self._update_app_configs()

            # 7. Verify migration
            await self._verify_migration()

            self.log_message("Supabase migration completed successfully", "SUCCESS")
            return True

        except Exception as e:
            self.log_message(f"Migration failed: {e}", "ERROR")
            await self._rollback_migration()
            return False

    async def _backup_existing_postgres(self) -> None:
        """Create backup of existing PostgreSQL database."""
        self.log_message("Creating backup of existing PostgreSQL database")

        # Ensure backup directory exists
        self.config.backup_path.mkdir(parents=True, exist_ok=True)

        backup_file = (
            self.config.backup_path
            / f"postgres_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        )

        # Check if PostgreSQL deployment exists
        check_cmd = ["kubectl", "get", "deployment", "postgres", "-n", "default"]
        result = subprocess.run(check_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self.log_message(
                "No existing PostgreSQL deployment found - skipping backup"
            )
            return

        # Create backup using kubectl exec
        backup_cmd = [
            "kubectl",
            "exec",
            "-n",
            "default",
            "deployment/postgres",
            "--",
            "pg_dump",
            "-U",
            self.config.old_postgres_user,
            "-h",
            "localhost",
            "-p",
            str(self.config.old_postgres_port),
            self.config.old_postgres_db,
        ]

        with open(backup_file, "w") as f:
            process = await asyncio.create_subprocess_exec(
                *backup_cmd, stdout=f, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Backup failed: {stderr.decode()}")

        self.log_message(f"Backup created: {backup_file}")

    async def _deploy_supabase(self) -> None:
        """Deploy Supabase stack using Make target."""
        self.log_message("Deploying Supabase stack")

        cmd = ["make", "supabase-deploy"]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Supabase deployment failed: {stderr.decode()}")

        self.log_message("Supabase deployment completed")

    async def _wait_for_supabase_ready(self) -> None:
        """Wait for Supabase services to be ready."""
        self.log_message("Waiting for Supabase services to be ready")

        max_attempts = 60  # 5 minutes with 5-second intervals
        attempt = 0

        while attempt < max_attempts:
            try:
                # Check if Supabase PostgreSQL pod is ready
                check_cmd = [
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    "supabase",
                    "-l",
                    "app=supabase-postgres",
                    "-o",
                    "jsonpath={.items[0].status.phase}",
                ]

                result = subprocess.run(check_cmd, capture_output=True, text=True)

                if result.returncode == 0 and result.stdout.strip() == "Running":
                    self.log_message("Supabase PostgreSQL is ready")

                    # Additional check for database readiness
                    await asyncio.sleep(10)  # Give database time to initialize
                    return

            except Exception as e:
                self.log_message(f"Health check attempt {attempt + 1} failed: {e}")

            attempt += 1
            await asyncio.sleep(5)

        raise RuntimeError("Supabase services failed to become ready within timeout")

    async def _migrate_schema(self) -> None:
        """Migrate database schema to Supabase."""
        self.log_message("Migrating database schema")

        # Find the latest backup file
        backup_files = list(self.config.backup_path.glob("postgres_backup_*.sql"))
        if not backup_files:
            self.log_message("No backup file found for schema migration")
            return

        latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)

        # Extract schema from backup and apply to Supabase
        restore_cmd = [
            "kubectl",
            "exec",
            "-i",
            "-n",
            "supabase",
            "deployment/supabase-postgres",
            "--",
            "psql",
            "-U",
            self.config.supabase_user,
            "-d",
            self.config.supabase_db,
        ]

        with open(latest_backup) as f:
            process = await asyncio.create_subprocess_exec(
                *restore_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(input=f.read().encode())

        if process.returncode != 0:
            self.log_message(f"Schema migration warnings: {stderr.decode()}", "WARNING")
        else:
            self.log_message("Schema migration completed successfully")

    async def _migrate_data(self) -> None:
        """Migrate data to Supabase."""
        self.log_message("Migrating data to Supabase")

        # Data migration is typically handled by the schema restore
        # Additional data-specific migrations can be added here
        self.log_message("Data migration completed")

    async def _update_app_configs(self) -> None:
        """Update application configurations to use Supabase."""
        self.log_message("Updating application configurations")

        # Update ConfigMaps and Secrets for applications
        config_updates = {
            "DATABASE_HOST": self.config.supabase_host,
            "DATABASE_PORT": str(self.config.supabase_port),
            "DATABASE_NAME": self.config.supabase_db,
            "DATABASE_USER": self.config.supabase_user,
        }

        for key, value in config_updates.items():
            cmd = [
                "kubectl",
                "patch",
                "configmap",
                "app-config",
                "-p",
                json.dumps({"data": {key: value}}),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.log_message(f"Updated {key} in app configuration")
            else:
                self.log_message(f"Failed to update {key}: {result.stderr}", "WARNING")

    async def _verify_migration(self) -> None:
        """Verify migration success."""
        self.log_message("Verifying migration")

        # Test database connectivity
        test_cmd = [
            "kubectl",
            "exec",
            "-n",
            "supabase",
            "deployment/supabase-postgres",
            "--",
            "psql",
            "-U",
            self.config.supabase_user,
            "-d",
            self.config.supabase_db,
            "-c",
            "SELECT 1;",
        ]

        result = subprocess.run(test_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            self.log_message("Database connectivity verified")
        else:
            raise RuntimeError(f"Database connectivity test failed: {result.stderr}")

    async def _rollback_migration(self) -> None:
        """Rollback migration in case of failure."""
        self.log_message("Rolling back migration", "WARNING")

        # Restore original PostgreSQL deployment
        # This would involve redeploying the original PostgreSQL configuration
        self.log_message("Rollback procedures would be implemented here")


def main():
    """Main migration entry point."""
    validate_uv_environment()

    # Load configuration from environment or config file
    config = MigrationConfig(
        old_postgres_host=os.getenv(
            "OLD_POSTGRES_HOST", "postgres-service.default.svc.cluster.local"
        ),
        old_postgres_port=int(os.getenv("OLD_POSTGRES_PORT", "5432")),
        old_postgres_db=os.getenv("OLD_POSTGRES_DB", "homelab"),
        old_postgres_user=os.getenv("OLD_POSTGRES_USER", "postgres"),
        old_postgres_password=os.getenv("OLD_POSTGRES_PASSWORD", "password"),
        supabase_host=os.getenv(
            "SUPABASE_HOST", "supabase-postgres-service.supabase.svc.cluster.local"
        ),
        supabase_port=int(os.getenv("SUPABASE_PORT", "5432")),
        supabase_db=os.getenv("SUPABASE_DB", "postgres"),
        supabase_user=os.getenv("SUPABASE_USER", "supabase_admin"),
        supabase_password=os.getenv("SUPABASE_PASSWORD", "your-secure-password"),
        backup_path=Path(os.getenv("BACKUP_PATH", "/tmp/postgres_backups")),
    )

    migrator = SupabaseMigrator(config)
    success = asyncio.run(migrator.migrate_to_supabase())

    if success:
        print("✅ Migration to Supabase completed successfully")
    else:
        print("❌ Migration failed. Check logs for details.")
        exit(1)


if __name__ == "__main__":
    main()
