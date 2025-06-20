#!/usr/bin/env python3
"""
Test suite for Supabase deployment and migration functionality.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "infrastructure"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import TestHelpers from the test_helpers module
from tests.test_helpers import TestHelpers
from supabase_config import get_config, validate_config
from supabase_health_check import SupabaseHealthChecker
from supabase_migration import MigrationConfig, SupabaseMigrator


class TestSupabaseConfig:
    """Test Supabase configuration management."""

    def test_get_config_homelab(self):
        """Test getting homelab configuration."""
        config = get_config("homelab")
        assert config.namespace == "supabase"
        assert config.postgres_database == "postgres"
        assert config.postgres_user == "supabase_admin"

    def test_get_config_development(self):
        """Test getting development configuration."""
        config = get_config("development")
        assert config.postgres_storage_size == "5Gi"
        assert config.storage_size == "10Gi"

    def test_get_config_production(self):
        """Test getting production configuration."""
        config = get_config("production")
        assert config.postgres_storage_size == "50Gi"
        assert config.postgres_memory_limit == "2Gi"

    def test_get_config_invalid_environment(self):
        """Test getting configuration for invalid environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            get_config("invalid")

    def test_validate_config_default_values(self):
        """Test configuration validation with default values."""
        config = get_config("homelab")
        # Should fail validation due to default security values
        with pytest.raises(ValueError, match="Configuration validation failed"):
            validate_config(config)


class TestSupabaseMigrator:
    """Test Supabase migration functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = MigrationConfig(
            old_postgres_host="old-host",
            old_postgres_port=5432,
            old_postgres_db="old_db",
            old_postgres_user="old_user",
            old_postgres_password="old_pass",
            supabase_host="supabase-host",
            supabase_port=5432,
            supabase_db="postgres",
            supabase_user="supabase_admin",
            supabase_password="supabase_pass",
            backup_path=Path("/tmp/test_backups"),
        )
        self.migrator = SupabaseMigrator(self.config)

    def test_migrator_initialization(self):
        """Test migrator initialization."""
        assert self.migrator.config == self.config
        assert self.migrator.log_file == Path("/tmp/supabase_migration.log")

    def test_log_message(self, tmp_path):
        """Test log message functionality."""
        log_file = tmp_path / "test.log"
        self.migrator.log_file = log_file

        self.migrator.log_message("Test message", "INFO")

        assert log_file.exists()
        log_content = log_file.read_text()
        assert "Test message" in log_content
        assert "[INFO]" in log_content

    @patch("subprocess.run")
    async def test_backup_existing_postgres_no_deployment(self, mock_run):
        """Test backup when no PostgreSQL deployment exists."""
        # Mock kubectl get deployment to return non-zero (not found)
        mock_run.return_value = Mock(returncode=1)

        await self.migrator._backup_existing_postgres()

        mock_run.assert_called_once()

    @patch("asyncio.create_subprocess_exec")
    async def test_deploy_supabase_success(self, mock_subprocess):
        """Test successful Supabase deployment."""
        # Mock successful deployment
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"success", b""))
        mock_subprocess.return_value = mock_process

        await self.migrator._deploy_supabase()

        mock_subprocess.assert_called_once()

    @patch("asyncio.create_subprocess_exec")
    async def test_deploy_supabase_failure(self, mock_subprocess):
        """Test failed Supabase deployment."""
        # Mock failed deployment
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"error"))
        mock_subprocess.return_value = mock_process

        with pytest.raises(RuntimeError, match="Supabase deployment failed"):
            await self.migrator._deploy_supabase()

    @patch("subprocess.run")
    @patch("asyncio.sleep")
    async def test_wait_for_supabase_ready_success(self, mock_sleep, mock_run):
        """Test waiting for Supabase to be ready - success case."""
        # Mock successful readiness check
        mock_run.return_value = Mock(returncode=0, stdout="Running")

        await self.migrator._wait_for_supabase_ready()

        assert mock_run.called

    @patch("subprocess.run")
    @patch("asyncio.sleep")
    async def test_wait_for_supabase_ready_timeout(self, mock_sleep, mock_run):
        """Test waiting for Supabase to be ready - timeout case."""
        # Mock continuous non-ready state
        mock_run.return_value = Mock(returncode=1)

        with pytest.raises(RuntimeError, match="failed to become ready within timeout"):
            await self.migrator._wait_for_supabase_ready()


class TestSupabaseHealthChecker:
    """Test Supabase health check functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = SupabaseHealthChecker()

    def test_health_checker_initialization(self):
        """Test health checker initialization."""
        assert "PostgreSQL" in self.checker.services
        assert "PostgREST" in self.checker.services
        assert "GoTrue" in self.checker.services
        assert "Realtime" in self.checker.services
        assert "Storage" in self.checker.services
        assert "Kong" in self.checker.services

    @patch("subprocess.run")
    async def test_check_namespace_exists(self, mock_run):
        """Test namespace existence check - positive case."""
        mock_run.return_value = Mock(returncode=0)

        result = await self.checker._check_namespace()

        assert result is True
        mock_run.assert_called_with(
            ["kubectl", "get", "namespace", "supabase"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    async def test_check_namespace_not_exists(self, mock_run):
        """Test namespace existence check - negative case."""
        mock_run.return_value = Mock(returncode=1)

        result = await self.checker._check_namespace()

        assert result is False

    @patch("subprocess.run")
    async def test_check_pod_status_running(self, mock_run):
        """Test pod status check - running pod."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"items":[{"status":{"phase":"Running","containerStatuses":[{"ready":true,"restartCount":0}]}}]}',
        )

        result = await self.checker._check_pod_status("postgres")

        assert result["healthy"] is True
        assert result["phase"] == "Running"
        assert result["containers_ready"] is True

    @patch("subprocess.run")
    async def test_check_pod_status_not_found(self, mock_run):
        """Test pod status check - pod not found."""
        mock_run.return_value = Mock(returncode=1)

        result = await self.checker._check_pod_status("postgres")

        assert result["healthy"] is False
        assert "Pod not found" in result["error"]

    @patch("subprocess.run")
    async def test_test_database_connectivity_success(self, mock_run):
        """Test database connectivity - success case."""
        mock_run.return_value = Mock(returncode=0)

        result = await self.checker._test_database_connectivity()

        assert result["healthy"] is True
        assert result["ready"] is True

    @patch("subprocess.run")
    async def test_test_database_connectivity_failure(self, mock_run):
        """Test database connectivity - failure case."""
        mock_run.return_value = Mock(returncode=1)

        result = await self.checker._test_database_connectivity()

        assert result["healthy"] is False


@pytest.mark.integration
class TestSupabaseIntegration:
    """Integration tests for Supabase deployment."""

    @pytest.mark.asyncio
    async def test_full_migration_workflow(self):
        """Test complete migration workflow (requires running K3s cluster)."""
        # This test requires a real K3s cluster and is marked as integration
        # It can be run with: pytest -m integration
        pytest.skip("Integration test - requires running K3s cluster")

    def test_kubectl_available(self):
        """Test that kubectl is available for integration tests."""
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("kubectl not available")


# Removed local create_test_kubeconfig and mock_kubectl_response
# Use TestHelpers.create_test_kubeconfig or conftest.mock_kubeconfig fixture
# Use TestHelpers.mock_kubectl_response


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
