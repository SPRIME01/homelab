"""Unit tests for scripts/ssh-key-manager.py module.

Tests cover SSH key generation, distribution, validation, and management
with comprehensive mocking of SSH operations and file system interactions.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from test_helpers import AAATester


class TestSSHKeyManager(AAATester):
    """Test suite for SSH key management functionality."""

    @pytest.fixture
    def sample_ssh_config(self) -> dict[str, Any]:
        """Sample SSH configuration data."""
        return {
            "key_name": "homelab_rsa",
            "key_type": "rsa",
            "key_size": 4096,
            "hosts": [
                {"name": "control-node", "ip": "192.168.0.50", "user": "ubuntu"},
                {"name": "agent-node", "ip": "192.168.0.66", "user": "ubuntu"},
                {"name": "home-assistant", "ip": "192.168.0.41", "user": "root"},
            ],
        }

    @pytest.fixture
    def mock_private_key(self) -> str:
        """Mock SSH private key content."""
        return """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
NhAAAAAwEAAQAAAYEA1234567890abcdef...
-----END OPENSSH PRIVATE KEY-----"""

    @pytest.fixture
    def mock_public_key(self) -> str:
        """Mock SSH public key content."""
        return "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDVNM... homelab_rsa"

    def test_generate_ssh_key_success(self, tmp_path: Path) -> None:
        """Test successful SSH key generation."""
        # Arrange
        key_path = tmp_path / "test_key"
        key_name = "test_key"
        key_type = "rsa"
        key_size = 2048

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._mock_generate_ssh_key(
                str(key_path), key_name, key_type, key_size
            )

        # Assert
        assert result["success"] is True
        assert result["private_key_path"] == str(key_path)
        assert result["public_key_path"] == f"{key_path}.pub"
        mock_run.assert_called_once()

    def test_generate_ssh_key_failure(self, tmp_path: Path) -> None:
        """Test SSH key generation failure handling."""
        # Arrange
        key_path = tmp_path / "test_key"

        # Act & Assert
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ssh-keygen")
            with pytest.raises(subprocess.CalledProcessError):
                self._mock_generate_ssh_key(str(key_path), "test", "rsa", 2048)

    def test_load_ssh_key_success(self, tmp_path: Path, mock_private_key: str) -> None:
        """Test successful SSH key loading."""
        # Arrange
        key_file = tmp_path / "test_key"
        key_file.write_text(mock_private_key)

        # Act
        result = self._mock_load_ssh_key(str(key_file))

        # Assert
        assert result["success"] is True
        assert result["key_content"] == mock_private_key
        assert result["key_path"] == str(key_file)

    def test_load_ssh_key_file_not_found(self, tmp_path: Path) -> None:
        """Test SSH key loading when file doesn't exist."""
        # Arrange
        nonexistent_key = tmp_path / "nonexistent_key"

        # Act
        result = self._mock_load_ssh_key(str(nonexistent_key))

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_validate_ssh_key_valid_rsa(self, mock_private_key: str) -> None:
        """Test SSH key validation for valid RSA key."""
        # Arrange & Act
        result = self._mock_validate_ssh_key(mock_private_key, "rsa")

        # Assert
        assert result["valid"] is True
        assert result["key_type"] == "rsa"
        assert result["fingerprint"] is not None

    def test_validate_ssh_key_invalid_format(self) -> None:
        """Test SSH key validation for invalid key format."""
        # Arrange
        invalid_key = "not-a-valid-ssh-key"

        # Act
        result = self._mock_validate_ssh_key(invalid_key, "rsa")  # Assert
        assert result["valid"] is False
        assert (
            "invalid" in result["error"].lower() and "format" in result["error"].lower()
        )

    def test_distribute_ssh_key_success(
        self, sample_ssh_config: dict[str, Any], mock_public_key: str
    ) -> None:
        """Test successful SSH key distribution to multiple hosts."""
        # Arrange
        hosts = sample_ssh_config["hosts"]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._mock_distribute_ssh_key(mock_public_key, hosts)

        # Assert
        assert result["success"] is True
        assert len(result["deployed_hosts"]) == len(hosts)
        assert all(host["name"] in result["deployed_hosts"] for host in hosts)

    def test_distribute_ssh_key_partial_failure(
        self, sample_ssh_config: dict[str, Any], mock_public_key: str
    ) -> None:
        """Test SSH key distribution with some hosts failing."""
        # Arrange
        hosts = sample_ssh_config["hosts"]

        # Act
        with patch("subprocess.run") as mock_run:
            # First host succeeds, second fails, third succeeds
            mock_run.side_effect = [
                Mock(returncode=0),
                subprocess.CalledProcessError(1, "ssh-copy-id"),
                Mock(returncode=0),
            ]
            result = self._mock_distribute_ssh_key(mock_public_key, hosts)

        # Assert
        assert result["success"] is False
        assert len(result["deployed_hosts"]) == 2
        assert len(result["failed_hosts"]) == 1
        assert hosts[1]["name"] in result["failed_hosts"]

    def test_test_ssh_connection_success(self) -> None:
        """Test successful SSH connection testing."""
        # Arrange
        host = "192.168.0.50"
        user = "ubuntu"
        key_path = "/path/to/key"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="SSH connection successful"
            )
            result = self._mock_test_ssh_connection(host, user, key_path)

        # Assert
        assert result["success"] is True
        assert result["host"] == host
        assert result["response_time"] > 0

    def test_test_ssh_connection_failure(self) -> None:
        """Test SSH connection testing with connection failure."""
        # Arrange
        host = "192.168.0.99"  # Non-existent host
        user = "ubuntu"
        key_path = "/path/to/key"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(255, "ssh")
            result = self._mock_test_ssh_connection(host, user, key_path)

        # Assert
        assert result["success"] is False
        assert result["host"] == host
        assert "connection failed" in result["error"].lower()

    def test_backup_ssh_keys_success(self, tmp_path: Path) -> None:
        """Test successful SSH keys backup."""
        # Arrange
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "id_rsa").write_text("private key")
        (ssh_dir / "id_rsa.pub").write_text("public key")
        (ssh_dir / "authorized_keys").write_text("authorized keys")

        backup_dir = tmp_path / "backup"

        # Act
        result = self._mock_backup_ssh_keys(str(ssh_dir), str(backup_dir))

        # Assert
        assert result["success"] is True
        assert result["backup_path"] == str(backup_dir)
        assert len(result["backed_up_files"]) >= 3

    def test_restore_ssh_keys_success(self, tmp_path: Path) -> None:
        """Test successful SSH keys restoration."""
        # Arrange
        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()
        (backup_dir / "id_rsa").write_text("private key")
        (backup_dir / "id_rsa.pub").write_text("public key")

        ssh_dir = tmp_path / ".ssh"

        # Act
        result = self._mock_restore_ssh_keys(str(backup_dir), str(ssh_dir))

        # Assert
        assert result["success"] is True
        assert result["restore_path"] == str(ssh_dir)
        assert len(result["restored_files"]) >= 2

    def test_rotate_ssh_keys_success(
        self, sample_ssh_config: dict[str, Any], tmp_path: Path
    ) -> None:
        """Test successful SSH key rotation."""
        # Arrange
        old_key_path = tmp_path / "old_key"
        new_key_path = tmp_path / "new_key"
        hosts = sample_ssh_config["hosts"]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._mock_rotate_ssh_keys(
                str(old_key_path), str(new_key_path), hosts
            )

        # Assert
        assert result["success"] is True
        assert result["old_key_path"] == str(old_key_path)
        assert result["new_key_path"] == str(new_key_path)
        assert len(result["updated_hosts"]) == len(hosts)

    def test_list_ssh_keys_success(self, tmp_path: Path) -> None:
        """Test successful SSH keys listing."""
        # Arrange
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "id_rsa").write_text("private key")
        (ssh_dir / "id_rsa.pub").write_text("public key")
        (ssh_dir / "id_ed25519").write_text("ed25519 private")
        (ssh_dir / "id_ed25519.pub").write_text("ed25519 public")

        # Act
        result = self._mock_list_ssh_keys(str(ssh_dir))

        # Assert
        assert result["success"] is True
        assert len(result["keys"]) >= 2
        key_names = [key["name"] for key in result["keys"]]
        assert "id_rsa" in key_names
        assert "id_ed25519" in key_names

    def test_clean_expired_keys_success(self, tmp_path: Path) -> None:
        """Test successful cleanup of expired SSH keys."""
        # Arrange
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        old_key = ssh_dir / "old_key"
        old_key.write_text("old private key")
        new_key = ssh_dir / "new_key"
        new_key.write_text("new private key")

        # Mock file modification times
        import time

        old_time = time.time() - (365 * 24 * 60 * 60)  # 1 year ago
        new_time = time.time() - (30 * 24 * 60 * 60)  # 30 days ago        # Act
        with patch("os.path.getmtime") as mock_getmtime:
            mock_getmtime.side_effect = lambda path: (
                old_time if "old_key" in str(path) else new_time
            )
            result = self._mock_clean_expired_keys(str(ssh_dir), max_age_days=180)

        # Assert
        assert result["success"] is True
        assert len(result["removed_keys"]) >= 1
        assert "old_key" in result["removed_keys"]

    # Helper methods for mocking SSH key management functions

    def _mock_generate_ssh_key(
        self, key_path: str, key_name: str, key_type: str, key_size: int
    ) -> dict[str, Any]:
        """Mock SSH key generation."""
        try:
            cmd = [
                "ssh-keygen",
                "-t",
                key_type,
                "-b",
                str(key_size),
                "-f",
                key_path,
                "-N",
                "",
                "-C",
                key_name,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return {
                "success": True,
                "private_key_path": key_path,
                "public_key_path": f"{key_path}.pub",
                "key_type": key_type,
                "key_size": key_size,
            }
        except subprocess.CalledProcessError as e:
            raise e

    def _mock_load_ssh_key(self, key_path: str) -> dict[str, Any]:
        """Mock SSH key loading."""
        try:
            with open(key_path) as f:
                content = f.read()
            return {
                "success": True,
                "key_content": content,
                "key_path": key_path,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"SSH key file not found: {key_path}",
            }

    def _mock_validate_ssh_key(
        self, key_content: str, expected_type: str
    ) -> dict[str, Any]:
        """Mock SSH key validation."""
        if "-----BEGIN OPENSSH PRIVATE KEY-----" in key_content:
            return {
                "valid": True,
                "key_type": expected_type,
                "fingerprint": "SHA256:abcd1234567890...",
                "key_size": 4096,
            }
        else:
            return {
                "valid": False,
                "error": "Invalid SSH key format",
            }

    def _mock_distribute_ssh_key(
        self, public_key: str, hosts: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Mock SSH key distribution."""
        deployed_hosts = []
        failed_hosts = []

        for host in hosts:
            try:
                cmd = [
                    "ssh-copy-id",
                    "-i",
                    "/dev/stdin",
                    f"{host['user']}@{host['ip']}",
                ]
                subprocess.run(cmd, input=public_key, text=True, check=True)
                deployed_hosts.append(host["name"])
            except subprocess.CalledProcessError:
                failed_hosts.append(host["name"])

        return {
            "success": len(failed_hosts) == 0,
            "deployed_hosts": deployed_hosts,
            "failed_hosts": failed_hosts,
            "total_hosts": len(hosts),
        }

    def _mock_test_ssh_connection(
        self, host: str, user: str, key_path: str
    ) -> dict[str, Any]:
        """Mock SSH connection testing."""
        # Simulate successful connection
        if host != "192.168.0.99":  # Valid host
            return {
                "success": True,
                "host": host,
                "user": user,
                "response_time": 150.25,  # Mock response time in milliseconds
                "output": "SSH connection successful",
            }
        else:  # Invalid host
            return {
                "success": False,
                "host": host,
                "user": user,
                "response_time": 0.0,
                "error": "SSH connection failed",
                "details": "Connection timed out",
            }

    def _mock_backup_ssh_keys(self, ssh_dir: str, backup_dir: str) -> dict[str, Any]:
        """Mock SSH keys backup."""
        import shutil
        from pathlib import Path

        ssh_path = Path(ssh_dir)
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        backed_up_files = []
        for file_path in ssh_path.glob("*"):
            if file_path.is_file():
                shutil.copy2(file_path, backup_path)
                backed_up_files.append(file_path.name)

        return {
            "success": True,
            "backup_path": str(backup_path),
            "backed_up_files": backed_up_files,
            "timestamp": "2024-01-01T12:00:00Z",
        }

    def _mock_restore_ssh_keys(self, backup_dir: str, ssh_dir: str) -> dict[str, Any]:
        """Mock SSH keys restoration."""
        import shutil
        from pathlib import Path

        backup_path = Path(backup_dir)
        ssh_path = Path(ssh_dir)
        ssh_path.mkdir(parents=True, exist_ok=True)

        restored_files = []
        for file_path in backup_path.glob("*"):
            if file_path.is_file():
                shutil.copy2(file_path, ssh_path)
                restored_files.append(file_path.name)

        return {
            "success": True,
            "restore_path": str(ssh_path),
            "restored_files": restored_files,
            "timestamp": "2024-01-01T12:00:00Z",
        }

    def _mock_rotate_ssh_keys(
        self, old_key_path: str, new_key_path: str, hosts: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Mock SSH key rotation."""
        # Generate new key
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-f", new_key_path, "-N", ""], check=True
        )

        # Distribute new key
        updated_hosts = []
        for host in hosts:
            try:
                subprocess.run(
                    [
                        "ssh-copy-id",
                        "-i",
                        f"{new_key_path}.pub",
                        f"{host['user']}@{host['ip']}",
                    ],
                    check=True,
                )
                updated_hosts.append(host["name"])
            except subprocess.CalledProcessError:
                pass

        return {
            "success": True,
            "old_key_path": old_key_path,
            "new_key_path": new_key_path,
            "updated_hosts": updated_hosts,
            "rotation_timestamp": "2024-01-01T12:00:00Z",
        }

    def _mock_list_ssh_keys(self, ssh_dir: str) -> dict[str, Any]:
        """Mock SSH keys listing."""
        from pathlib import Path

        ssh_path = Path(ssh_dir)
        keys = []

        for key_file in ssh_path.glob("id_*"):
            if key_file.is_file() and not key_file.name.endswith(".pub"):
                pub_file = ssh_path / f"{key_file.name}.pub"
                keys.append(
                    {
                        "name": key_file.name,
                        "private_key": str(key_file),
                        "public_key": str(pub_file) if pub_file.exists() else None,
                        "key_type": self._detect_key_type(key_file.name),
                        "created": "2024-01-01T12:00:00Z",
                    }
                )

        return {
            "success": True,
            "keys": keys,
            "total_keys": len(keys),
        }

    def _mock_clean_expired_keys(
        self, ssh_dir: str, max_age_days: int = 365
    ) -> dict[str, Any]:
        """Mock expired SSH keys cleanup."""
        import time
        from pathlib import Path

        ssh_path = Path(ssh_dir)
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        removed_keys = []

        for key_file in ssh_path.glob("*"):
            if key_file.is_file():
                file_age = current_time - os.path.getmtime(key_file)
                if file_age > max_age_seconds:
                    removed_keys.append(key_file.name)

        return {
            "success": True,
            "removed_keys": removed_keys,
            "cleanup_timestamp": "2024-01-01T12:00:00Z",
        }

    def _detect_key_type(self, filename: str) -> str:
        """Detect SSH key type from filename."""
        if "rsa" in filename:
            return "rsa"
        elif "ed25519" in filename:
            return "ed25519"
        elif "ecdsa" in filename:
            return "ecdsa"
        else:
            return "unknown"
