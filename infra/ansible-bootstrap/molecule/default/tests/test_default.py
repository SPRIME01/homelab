"""
Pytest-based tests for Ansible playbook verification.

These tests use pytest-ansible to validate infrastructure state after
Molecule converges the playbooks.
"""

import pytest


def test_curl_installed(host):
    """Verify curl is installed and accessible."""
    cmd = host.run("which curl")
    assert cmd.rc == 0
    assert "/curl" in cmd.stdout


def test_testuser_exists(host):
    """Verify the test user was created correctly."""
    user = host.user("testuser")
    assert user.exists
    assert user.home == "/home/testuser"


def test_home_directory_permissions(host):
    """Verify home directory has correct permissions."""
    home = host.file("/home/testuser")
    assert home.exists
    assert home.is_directory
    assert home.user == "testuser"


def test_ca_certificates_installed(host):
    """Verify CA certificates package is installed."""
    if host.system_info.distribution in ["ubuntu", "debian"]:
        pkg = host.package("ca-certificates")
        assert pkg.is_installed
    elif host.system_info.distribution in ["centos", "rhel", "fedora"]:
        pkg = host.package("ca-certificates")
        assert pkg.is_installed


@pytest.mark.skipif(
    "True",  # Skip by default - requires live Tailscale
    reason="Requires active Tailscale connection"
)
def test_tailscale_connectivity(host):
    """Verify Tailscale is active (integration test - requires live connectivity)."""
    cmd = host.run("tailscale status")
    assert cmd.rc == 0
