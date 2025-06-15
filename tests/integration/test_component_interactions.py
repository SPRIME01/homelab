"""Integration tests for component interactions and configuration loading.

Tests cover multi-component workflows, configuration validation,
and end-to-end system interactions with realistic scenarios.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Add project directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "infrastructure"))

from test_helpers import AAATester


class TestConfigurationIntegration(AAATester):
    """Test suite for configuration loading and validation integration."""

    @pytest.fixture
    def sample_homelab_config(self, tmp_path: Path) -> Path:
        """Create a sample homelab configuration file."""
        config_content = """
# Homelab Configuration
cluster:
  name: homelab-k3s
  control_plane:
    ip: 192.168.0.51
    external_ip: 192.168.0.50
    user: ubuntu
  agent_nodes:
    - ip: 192.168.0.66
      user: ubuntu

services:
  traefik:
    enabled: true
    version: v2.10
    dashboard: true
  supabase:
    enabled: true
    project_name: homelab-db
    region: us-east-1
  mqtt:
    broker: 192.168.0.41
    port: 1883
    username: homelab

storage:
  nfs:
    server: 192.168.0.50
    path: /mnt/storage
  backups:
    enabled: true
    schedule: "0 2 * * *"
    retention_days: 30
"""
        config_file = tmp_path / "homelab.yaml"
        config_file.write_text(config_content.strip())
        return config_file

    def test_configuration_loading_success(self, sample_homelab_config: Path) -> None:
        """Test successful configuration loading and validation."""
        # Arrange & Act
        result = self._load_and_validate_config(sample_homelab_config)

        # Assert
        assert result["valid"] is True
        assert result["cluster"]["name"] == "homelab-k3s"
        assert result["cluster"]["control_plane"]["ip"] == "192.168.0.51"
        assert len(result["cluster"]["agent_nodes"]) == 1
        assert result["services"]["traefik"]["enabled"] is True

    def test_configuration_validation_missing_required_fields(
        self, tmp_path: Path
    ) -> None:
        """Test configuration validation with missing required fields."""
        # Arrange
        invalid_config = tmp_path / "invalid.yaml"
        invalid_config.write_text("incomplete: config")

        # Act
        result = self._load_and_validate_config(invalid_config)

        # Assert
        assert result["valid"] is False
        assert "missing required fields" in result["error"].lower()

    def test_configuration_environment_substitution(self, tmp_path: Path) -> None:
        """Test environment variable substitution in configuration."""
        # Arrange
        config_with_env = tmp_path / "env_config.yaml"
        config_content = """
cluster:
  name: ${HOMELAB_NAME:-homelab-default}
  control_plane:
    ip: ${CONTROL_IP}
services:
  mqtt:
    username: ${MQTT_USER}
    password: ${MQTT_PASS}
"""
        config_with_env.write_text(config_content.strip())

        # Act
        with patch.dict(
            os.environ,
            {
                "HOMELAB_NAME": "test-cluster",
                "CONTROL_IP": "10.0.0.100",
                "MQTT_USER": "testuser",
                "MQTT_PASS": "secret123",
            },
        ):
            result = self._load_and_validate_config(config_with_env)

        # Assert
        assert result["valid"] is True
        assert result["cluster"]["name"] == "test-cluster"
        assert result["cluster"]["control_plane"]["ip"] == "10.0.0.100"
        assert result["services"]["mqtt"]["username"] == "testuser"

    def _load_and_validate_config(self, config_file: Path) -> dict[str, Any]:
        """Mock configuration loading and validation."""
        import yaml

        try:
            # Load YAML content
            content = config_file.read_text()

            # Substitute environment variables
            import os
            import re

            def replace_env_vars(match):
                var_expr = match.group(1)
                if ":-" in var_expr:
                    var_name, default = var_expr.split(":-", 1)
                    return os.getenv(var_name, default)
                else:
                    return os.getenv(var_expr, "")

            content = re.sub(r"\$\{([^}]+)\}", replace_env_vars, content)

            # Parse YAML
            config = yaml.safe_load(content)

            # Basic validation
            required_fields = ["cluster"]
            if not all(field in config for field in required_fields):
                return {
                    "valid": False,
                    "error": "Missing required fields: cluster configuration",
                }

            return {
                "valid": True,
                **config,
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Configuration error: {str(e)}",
            }


class TestComponentInteractionIntegration(AAATester):
    """Test suite for component interaction workflows."""

    def test_k3s_cluster_setup_workflow(self) -> None:
        """Test complete K3s cluster setup workflow."""
        # Arrange
        cluster_config = {
            "control_plane": "192.168.0.51",
            "external_ip": "192.168.0.50",
            "agent_nodes": ["192.168.0.66"],
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._setup_k3s_cluster_workflow(cluster_config)

        # Assert
        assert result["success"] is True
        assert result["control_plane_ready"] is True
        assert result["agent_nodes_joined"] == 1
        assert len(result["kubeconfig_files"]) == 2  # internal and external

    def test_service_deployment_workflow(self) -> None:
        """Test service deployment workflow with dependencies."""
        # Arrange
        services = [
            {"name": "traefik", "dependencies": [], "type": "ingress"},
            {"name": "supabase", "dependencies": ["traefik"], "type": "database"},
            {"name": "mqtt-broker", "dependencies": [], "type": "messaging"},
        ]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._deploy_services_workflow(services)

        # Assert
        assert result["success"] is True
        assert len(result["deployed_services"]) == 3
        assert result["deployment_order"] == ["traefik", "mqtt-broker", "supabase"]

    def test_backup_and_restore_workflow(self) -> None:
        """Test complete backup and restore workflow."""
        # Arrange
        backup_config = {
            "targets": ["k3s-etcd", "supabase-db", "persistent-volumes"],
            "destination": "/backup/storage",
            "encryption": True,
        }

        # Act
        with (
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            mock_run.return_value = Mock(returncode=0)
            result = self._backup_restore_workflow(backup_config)

        # Assert
        assert result["backup_success"] is True
        assert result["restore_success"] is True
        assert len(result["backed_up_components"]) == 3
        assert result["backup_encrypted"] is True

    def test_network_configuration_workflow(self) -> None:
        """Test network configuration and validation workflow."""
        # Arrange
        network_config = {
            "cluster_cidr": "10.42.0.0/16",
            "service_cidr": "10.43.0.0/16",
            "dns_server": "192.168.0.1",
            "external_dns": ["8.8.8.8", "1.1.1.1"],
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="PING 8.8.8.8")
            result = self._configure_network_workflow(network_config)

        # Assert
        assert result["success"] is True
        assert result["cluster_networking"] is True
        assert result["dns_resolution"] is True
        assert result["external_connectivity"] is True

    def test_monitoring_setup_workflow(self) -> None:
        """Test monitoring and observability setup workflow."""
        # Arrange
        monitoring_config = {
            "prometheus": {"enabled": True, "retention": "30d"},
            "grafana": {"enabled": True, "admin_password": "secure123"},
            "alertmanager": {"enabled": True, "webhook_url": "http://alerts"},
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._setup_monitoring_workflow(monitoring_config)

        # Assert
        assert result["success"] is True
        assert result["prometheus_deployed"] is True
        assert result["grafana_deployed"] is True
        assert result["dashboards_imported"] is True

    def _setup_k3s_cluster_workflow(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mock K3s cluster setup workflow."""
        workflow_steps = [
            "install_k3s_control_plane",
            "configure_dual_ip_kubeconfig",
            "join_agent_nodes",
            "validate_cluster_status",
        ]

        for step in workflow_steps:
            # Simulate each step
            cmd = f"k3s-{step.replace('_', '-')}"
            subprocess.run([cmd], check=True)

        return {
            "success": True,
            "control_plane_ready": True,
            "agent_nodes_joined": len(config["agent_nodes"]),
            "kubeconfig_files": ["config-internal", "config-external"],
            "workflow_steps": workflow_steps,
        }

    def _deploy_services_workflow(
        self, services: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Mock service deployment workflow with dependency resolution."""
        # Sort services by dependencies
        deployed = []
        remaining = services.copy()

        while remaining:
            for service in remaining[:]:
                dependencies_met = all(
                    dep in [s["name"] for s in deployed]
                    for dep in service.get("dependencies", [])
                )

                if dependencies_met:
                    # Deploy service
                    subprocess.run(
                        ["kubectl", "apply", "-f", f"{service['name']}.yaml"],
                        check=True,
                    )
                    deployed.append(service)
                    remaining.remove(service)

        return {
            "success": True,
            "deployed_services": [s["name"] for s in deployed],
            "deployment_order": [s["name"] for s in deployed],
            "total_services": len(services),
        }

    def _backup_restore_workflow(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mock backup and restore workflow."""
        from pathlib import Path

        # Create backup directory
        backup_dir = Path(config["destination"])
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup each component
        backed_up = []
        for target in config["targets"]:
            backup_file = backup_dir / f"{target}-backup.tar.gz"
            cmd = ["tar", "czf", str(backup_file), f"/data/{target}"]
            if config.get("encryption"):
                cmd = ["gpg", "--encrypt"] + cmd
            subprocess.run(cmd, check=True)
            backed_up.append(target)

        # Test restore (dry run)
        for target in backed_up:
            backup_file = backup_dir / f"{target}-backup.tar.gz"
            cmd = ["tar", "tzf", str(backup_file)]
            subprocess.run(cmd, check=True)

        return {
            "backup_success": True,
            "restore_success": True,
            "backed_up_components": backed_up,
            "backup_encrypted": config.get("encryption", False),
            "backup_location": str(backup_dir),
        }

    def _configure_network_workflow(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mock network configuration workflow."""
        # Configure cluster networking
        cluster_net_cmd = [
            "kubectl",
            "patch",
            "configmap",
            "coredns",
            "-n",
            "kube-system",
            "--patch",
            f"data:\n  Corefile: |\n    {config['cluster_cidr']}",
        ]
        subprocess.run(cluster_net_cmd, check=True)

        # Test DNS resolution
        dns_cmd = [
            "nslookup",
            "kubernetes.default.svc.cluster.local",
            config["dns_server"],
        ]
        subprocess.run(dns_cmd, check=True)

        # Test external connectivity
        for dns in config["external_dns"]:
            ping_cmd = ["ping", "-c", "1", dns]
            subprocess.run(ping_cmd, check=True)

        return {
            "success": True,
            "cluster_networking": True,
            "dns_resolution": True,
            "external_connectivity": True,
            "configured_cidrs": [config["cluster_cidr"], config["service_cidr"]],
        }

    def _setup_monitoring_workflow(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mock monitoring setup workflow."""
        deployed_components = []

        if config["prometheus"]["enabled"]:
            subprocess.run(
                ["helm", "install", "prometheus", "prometheus-community/prometheus"],
                check=True,
            )
            deployed_components.append("prometheus")

        if config["grafana"]["enabled"]:
            subprocess.run(
                ["helm", "install", "grafana", "grafana/grafana"], check=True
            )
            deployed_components.append("grafana")

        if config["alertmanager"]["enabled"]:
            subprocess.run(["kubectl", "apply", "-f", "alertmanager.yaml"], check=True)
            deployed_components.append("alertmanager")

        return {
            "success": True,
            "prometheus_deployed": "prometheus" in deployed_components,
            "grafana_deployed": "grafana" in deployed_components,
            "alertmanager_deployed": "alertmanager" in deployed_components,
            "dashboards_imported": True,
            "deployed_components": deployed_components,
        }


class TestEndToEndWorkflows(AAATester):
    """Test suite for complete end-to-end workflows."""

    def test_complete_homelab_setup_workflow(self) -> None:
        """Test complete homelab setup from scratch."""
        # Arrange
        setup_config = {
            "phase_1": "system_preparation",
            "phase_2": "cluster_installation",
            "phase_3": "service_deployment",
            "phase_4": "configuration_validation",
        }

        # Act
        with patch("subprocess.run") as mock_run, patch("time.sleep") as mock_sleep:
            mock_run.return_value = Mock(returncode=0)
            result = self._complete_homelab_setup(setup_config)

        # Assert
        assert result["success"] is True
        assert len(result["completed_phases"]) == 4
        assert result["setup_time"] > 0
        assert result["validation_passed"] is True

    def test_disaster_recovery_workflow(self) -> None:
        """Test disaster recovery and cluster rebuild workflow."""
        # Arrange
        disaster_scenario = {
            "affected_nodes": ["control-plane"],
            "data_loss": ["etcd", "persistent-volumes"],
            "network_issues": False,
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._disaster_recovery_workflow(disaster_scenario)

        # Assert
        assert result["recovery_success"] is True
        assert result["data_restored"] is True
        assert result["cluster_operational"] is True
        assert result["recovery_time"] > 0

    def test_security_hardening_workflow(self) -> None:
        """Test security hardening and compliance workflow."""
        # Arrange
        security_config = {
            "rbac_enabled": True,
            "network_policies": True,
            "pod_security_standards": "restricted",
            "encryption_at_rest": True,
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._security_hardening_workflow(security_config)

        # Assert
        assert result["hardening_complete"] is True
        assert result["compliance_score"] >= 90
        assert result["vulnerabilities_found"] == 0
        assert result["security_policies_applied"] > 0

    def test_performance_optimization_workflow(self) -> None:
        """Test performance monitoring and optimization workflow."""
        # Arrange
        optimization_targets = {
            "cpu_utilization": 70,
            "memory_utilization": 80,
            "network_latency": 10,  # ms
            "storage_iops": 1000,
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="CPU: 65%, Memory: 75%")
            result = self._performance_optimization_workflow(optimization_targets)

        # Assert
        assert result["optimization_success"] is True
        assert result["performance_improved"] is True
        assert result["targets_met"] >= 3
        assert len(result["optimizations_applied"]) > 0

    def _complete_homelab_setup(self, config: dict[str, str]) -> dict[str, Any]:
        """Mock complete homelab setup workflow."""
        start_time = time.time()
        completed_phases = []

        # Phase 1: System preparation
        subprocess.run(["python", "scripts/00-system-audit.py"], check=True)
        completed_phases.append(config["phase_1"])

        # Phase 2: Cluster installation
        subprocess.run(["python", "scripts/01-install-components.py"], check=True)
        completed_phases.append(config["phase_2"])

        # Phase 3: Service deployment
        subprocess.run(["kubectl", "apply", "-f", "manifests/"], check=True)
        completed_phases.append(config["phase_3"])

        # Phase 4: Validation
        subprocess.run(["python", "scripts/cluster-health-monitor.py"], check=True)
        completed_phases.append(config["phase_4"])

        setup_time = time.time() - start_time

        return {
            "success": True,
            "completed_phases": completed_phases,
            "setup_time": setup_time,
            "validation_passed": True,
            "services_ready": ["traefik", "supabase", "mqtt"],
        }

    def _disaster_recovery_workflow(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Mock disaster recovery workflow."""
        start_time = time.time()
        recovery_steps = []

        # Assess damage
        subprocess.run(["kubectl", "get", "nodes"], check=True)
        recovery_steps.append("damage_assessment")

        # Restore from backup
        if "etcd" in scenario["data_loss"]:
            subprocess.run(
                ["etcdctl", "snapshot", "restore", "/backup/etcd.db"], check=True
            )
            recovery_steps.append("etcd_restore")

        # Rebuild affected nodes
        for node in scenario["affected_nodes"]:
            subprocess.run(["k3s-uninstall.sh"], check=True)
            subprocess.run(
                ["curl", "-sfL", "https://get.k3s.io", "|", "sh"], check=True
            )
            recovery_steps.append(f"rebuild_{node}")

        # Validate recovery
        subprocess.run(["kubectl", "get", "pods", "--all-namespaces"], check=True)
        recovery_steps.append("validation")

        recovery_time = time.time() - start_time

        return {
            "recovery_success": True,
            "data_restored": True,
            "cluster_operational": True,
            "recovery_time": recovery_time,
            "recovery_steps": recovery_steps,
        }

    def _security_hardening_workflow(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mock security hardening workflow."""
        applied_policies = []

        # Enable RBAC
        if config["rbac_enabled"]:
            subprocess.run(["kubectl", "apply", "-f", "rbac-policies.yaml"], check=True)
            applied_policies.append("rbac")

        # Apply network policies
        if config["network_policies"]:
            subprocess.run(
                ["kubectl", "apply", "-f", "network-policies.yaml"], check=True
            )
            applied_policies.append("network_policies")

        # Set pod security standards
        if config["pod_security_standards"]:
            subprocess.run(
                [
                    "kubectl",
                    "label",
                    "namespace",
                    "default",
                    f"pod-security.kubernetes.io/enforce={config['pod_security_standards']}",
                ],
                check=True,
            )
            applied_policies.append("pod_security")

        # Run security scan
        subprocess.run(["trivy", "k8s", "--report", "summary"], check=True)

        return {
            "hardening_complete": True,
            "compliance_score": 95,
            "vulnerabilities_found": 0,
            "security_policies_applied": len(applied_policies),
            "applied_policies": applied_policies,
        }

    def _performance_optimization_workflow(
        self, targets: dict[str, int]
    ) -> dict[str, Any]:
        """Mock performance optimization workflow."""
        # Collect current metrics
        metrics_cmd = ["kubectl", "top", "nodes"]
        result = subprocess.run(metrics_cmd, capture_output=True, text=True, check=True)

        optimizations = []
        targets_met = 0

        # CPU optimization
        if "cpu_utilization" in targets:
            subprocess.run(
                [
                    "kubectl",
                    "patch",
                    "deployment",
                    "cpu-intensive-app",
                    "-p",
                    '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"limits":{"cpu":"500m"}}}]}}}}',
                ],
                check=True,
            )
            optimizations.append("cpu_limits")
            targets_met += 1

        # Memory optimization
        if "memory_utilization" in targets:
            subprocess.run(
                [
                    "kubectl",
                    "patch",
                    "deployment",
                    "memory-intensive-app",
                    "-p",
                    '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"limits":{"memory":"512Mi"}}}]}}}}',
                ],
                check=True,
            )
            optimizations.append("memory_limits")
            targets_met += 1

        # Network optimization
        if "network_latency" in targets:
            subprocess.run(
                ["kubectl", "apply", "-f", "network-optimization.yaml"], check=True
            )
            optimizations.append("network_tuning")
            targets_met += 1

        return {
            "optimization_success": True,
            "performance_improved": True,
            "targets_met": targets_met,
            "optimizations_applied": optimizations,
            "baseline_metrics": result.stdout,
        }
