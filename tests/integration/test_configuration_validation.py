"""Integration tests for configuration validation and environment setup.

Tests cover configuration loading, validation, environment variables,
and configuration-driven deployments across different environments.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
import yaml

# Add project directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from test_helpers import AAATester


class TestConfigurationValidation(AAATester):
    """Test suite for configuration validation and loading."""

    @pytest.fixture
    def valid_homelab_config(self) -> dict[str, Any]:
        """Valid homelab configuration fixture."""
        return {
            "version": "1.0",
            "environment": "development",
            "cluster": {
                "name": "homelab-k3s",
                "control_plane": {
                    "ip": "192.168.0.51",
                    "external_ip": "192.168.0.50",
                    "user": "ubuntu",
                    "ssh_key": "~/.ssh/homelab_rsa",
                },
                "agent_nodes": [
                    {
                        "name": "jetson-orin",
                        "ip": "192.168.0.66",
                        "user": "ubuntu",
                        "roles": ["worker", "gpu"],
                    }
                ],
                "network": {
                    "cluster_cidr": "10.42.0.0/16",
                    "service_cidr": "10.43.0.0/16",
                    "dns_servers": ["192.168.0.1", "8.8.8.8"],
                },
            },
            "services": {
                "traefik": {
                    "enabled": True,
                    "version": "v2.10",
                    "dashboard": True,
                    "acme": {
                        "enabled": False,
                        "email": "admin@homelab.local",
                    },
                },
                "supabase": {
                    "enabled": True,
                    "project_name": "homelab-db",
                    "region": "us-east-1",
                    "database": {
                        "size": "small",
                        "backup_enabled": True,
                    },
                },
                "monitoring": {
                    "prometheus": {"enabled": True, "retention": "30d"},
                    "grafana": {
                        "enabled": True,
                        "admin_password": "${GRAFANA_PASSWORD}",
                    },
                    "alertmanager": {"enabled": False},
                },
            },
            "storage": {
                "nfs": {
                    "enabled": True,
                    "server": "192.168.0.50",
                    "path": "/mnt/storage",
                },
                "local": {
                    "enabled": True,
                    "path": "/var/lib/homelab",
                },
            },
            "security": {
                "rbac_enabled": True,
                "network_policies": True,
                "pod_security_standards": "restricted",
                "encryption": {
                    "secrets": True,
                    "etcd": True,
                },
            },
        }

    @pytest.fixture
    def invalid_config_missing_required(self) -> dict[str, Any]:
        """Invalid configuration missing required fields."""
        return {
            "version": "1.0",
            # Missing 'cluster' section
            "services": {"traefik": {"enabled": True}},
        }

    @pytest.fixture
    def config_with_env_vars(self) -> dict[str, Any]:
        """Configuration with environment variable substitution."""
        return {
            "version": "1.0",
            "environment": "${HOMELAB_ENV:-development}",
            "cluster": {
                "name": "${CLUSTER_NAME}",
                "control_plane": {
                    "ip": "${CONTROL_IP}",
                    "user": "${SSH_USER:-ubuntu}",
                },
            },
            "services": {
                "monitoring": {
                    "grafana": {
                        "admin_password": "${GRAFANA_PASSWORD}",
                        "database_url": "${DATABASE_URL}",
                    }
                }
            },
        }

    def test_valid_configuration_loading(
        self, valid_homelab_config: dict[str, Any]
    ) -> None:
        """Test loading and validation of valid configuration."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_homelab_config, f)
            config_file = f.name

        # Act
        result = self._load_and_validate_configuration(config_file)

        # Assert
        assert result["valid"] is True
        assert result["config"]["version"] == "1.0"
        assert result["config"]["cluster"]["name"] == "homelab-k3s"
        assert len(result["config"]["cluster"]["agent_nodes"]) == 1
        assert result["validation_errors"] == []

        # Cleanup
        os.unlink(config_file)

    def test_invalid_configuration_validation(
        self, invalid_config_missing_required: dict[str, Any]
    ) -> None:
        """Test validation of invalid configuration."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_config_missing_required, f)
            config_file = f.name

        # Act
        result = self._load_and_validate_configuration(config_file)

        # Assert
        assert result["valid"] is False
        assert len(result["validation_errors"]) > 0
        assert any("cluster" in error.lower() for error in result["validation_errors"])

        # Cleanup
        os.unlink(config_file)

    def test_environment_variable_substitution(
        self, config_with_env_vars: dict[str, Any]
    ) -> None:
        """Test environment variable substitution in configuration."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_with_env_vars, f)
            config_file = f.name

        env_vars = {
            "HOMELAB_ENV": "production",
            "CLUSTER_NAME": "prod-cluster",
            "CONTROL_IP": "10.0.0.100",
            "SSH_USER": "admin",
            "GRAFANA_PASSWORD": "secure123",
            "DATABASE_URL": "postgresql://user:pass@db:5432/grafana",
        }

        # Act
        with patch.dict(os.environ, env_vars):
            result = self._load_and_validate_configuration(config_file)

        # Assert
        assert result["valid"] is True
        assert result["config"]["environment"] == "production"
        assert result["config"]["cluster"]["name"] == "prod-cluster"
        assert result["config"]["cluster"]["control_plane"]["ip"] == "10.0.0.100"
        assert result["config"]["cluster"]["control_plane"]["user"] == "admin"
        assert (
            result["config"]["services"]["monitoring"]["grafana"]["admin_password"]
            == "secure123"
        )

        # Cleanup
        os.unlink(config_file)

    def test_configuration_schema_validation(
        self, valid_homelab_config: dict[str, Any]
    ) -> None:
        """Test configuration against predefined schema."""
        # Arrange & Act
        result = self._validate_configuration_schema(valid_homelab_config)

        # Assert
        assert result["schema_valid"] is True
        assert result["required_fields_present"] is True
        assert result["type_validation_passed"] is True
        assert len(result["schema_errors"]) == 0

    def test_multi_environment_configuration(self) -> None:
        """Test configuration loading for different environments."""
        # Arrange
        environments = ["development", "staging", "production"]
        base_config = {
            "version": "1.0",
            "cluster": {"name": "homelab"},
            "services": {"traefik": {"enabled": True}},
        }

        # Act
        results = {}
        for env in environments:
            env_config = base_config.copy()
            env_config["environment"] = env

            # Environment-specific overrides
            if env == "production":
                env_config["cluster"]["name"] = "prod-homelab"
                env_config["services"]["traefik"]["replicas"] = 3
            elif env == "staging":
                env_config["cluster"]["name"] = "staging-homelab"
                env_config["services"]["traefik"]["replicas"] = 2

            results[env] = self._validate_environment_configuration(env_config, env)

        # Assert
        for env, result in results.items():
            assert result["valid"] is True
            assert result["environment"] == env

        assert results["production"]["config"]["services"]["traefik"]["replicas"] == 3
        assert results["staging"]["config"]["services"]["traefik"]["replicas"] == 2

    def test_configuration_dependency_validation(
        self, valid_homelab_config: dict[str, Any]
    ) -> None:
        """Test validation of service dependencies in configuration."""
        # Arrange
        config_with_deps = valid_homelab_config.copy()
        config_with_deps["services"]["app"] = {
            "enabled": True,
            "dependencies": ["supabase", "traefik"],
        }
        config_with_deps["services"]["worker"] = {
            "enabled": True,
            "dependencies": ["app", "nonexistent-service"],
        }

        # Act
        result = self._validate_service_dependencies(config_with_deps)

        # Assert
        assert result["dependencies_valid"] is False
        assert len(result["missing_dependencies"]) == 1
        assert "nonexistent-service" in result["missing_dependencies"]
        assert len(result["dependency_graph"]) > 0

    def _load_and_validate_configuration(self, config_file: str) -> dict[str, Any]:
        """Load and validate configuration from file."""
        try:
            # Load YAML file
            with open(config_file) as f:
                content = f.read()

            # Substitute environment variables
            content = self._substitute_environment_variables(content)

            # Parse YAML
            config = yaml.safe_load(content)

            # Validate configuration
            validation_errors = self._validate_config_structure(config)

            return {
                "valid": len(validation_errors) == 0,
                "config": config,
                "validation_errors": validation_errors,
            }

        except Exception as e:
            return {
                "valid": False,
                "config": None,
                "validation_errors": [f"Failed to load configuration: {str(e)}"],
            }

    def _substitute_environment_variables(self, content: str) -> str:
        """Substitute environment variables in configuration content."""
        import re

        def replace_env_var(match):
            var_expr = match.group(1)
            if ":-" in var_expr:
                var_name, default = var_expr.split(":-", 1)
                return os.getenv(var_name, default)
            else:
                var_name = var_expr
                value = os.getenv(var_name)
                if value is None:
                    raise ValueError(
                        f"Required environment variable {var_name} not set"
                    )
                return value

        return re.sub(r"\$\{([^}]+)\}", replace_env_var, content)

    def _validate_config_structure(self, config: dict[str, Any]) -> list[str]:
        """Validate configuration structure and required fields."""
        errors = []

        # Check required top-level fields
        required_fields = ["version", "cluster"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate cluster configuration
        if "cluster" in config:
            cluster = config["cluster"]
            if "name" not in cluster:
                errors.append("Missing required field: cluster.name")
            if "control_plane" not in cluster:
                errors.append("Missing required field: cluster.control_plane")
            elif "ip" not in cluster["control_plane"]:
                errors.append("Missing required field: cluster.control_plane.ip")

        # Validate version format
        if "version" in config:
            version = config["version"]
            if not isinstance(version, str) or not re.match(r"^\d+\.\d+$", version):
                errors.append("Invalid version format, expected 'X.Y'")

        return errors

    def _validate_configuration_schema(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate configuration against predefined schema."""
        schema_errors = []

        # Define expected schema
        schema = {
            "version": str,
            "cluster": {
                "name": str,
                "control_plane": {
                    "ip": str,
                    "user": str,
                },
            },
            "services": dict,
        }

        # Validate schema recursively
        def validate_recursive(data, schema_part, path=""):
            if isinstance(schema_part, type):
                if not isinstance(data, schema_part):
                    schema_errors.append(
                        f"Type mismatch at {path}: expected {schema_part.__name__}, got {type(data).__name__}"
                    )
            elif isinstance(schema_part, dict):
                if not isinstance(data, dict):
                    schema_errors.append(
                        f"Type mismatch at {path}: expected dict, got {type(data).__name__}"
                    )
                    return

                for key, expected_type in schema_part.items():
                    if key in data:
                        validate_recursive(
                            data[key], expected_type, f"{path}.{key}" if path else key
                        )

        # Check required fields
        required_fields = ["version", "cluster"]
        required_fields_present = all(field in config for field in required_fields)

        # Validate types
        validate_recursive(config, schema)

        return {
            "schema_valid": len(schema_errors) == 0 and required_fields_present,
            "required_fields_present": required_fields_present,
            "type_validation_passed": len(schema_errors) == 0,
            "schema_errors": schema_errors,
        }

    def _validate_environment_configuration(
        self, config: dict[str, Any], environment: str
    ) -> dict[str, Any]:
        """Validate configuration for specific environment."""
        validation_errors = []

        # Environment-specific validations
        if environment == "production":
            # Production should have stricter requirements
            if config.get("security", {}).get("rbac_enabled") is not True:
                validation_errors.append("RBAC must be enabled in production")

            if (
                config.get("services", {}).get("monitoring", {}).get("enabled")
                is not True
            ):
                validation_errors.append("Monitoring must be enabled in production")

        return {
            "valid": len(validation_errors) == 0,
            "environment": environment,
            "config": config,
            "validation_errors": validation_errors,
        }

    def _validate_service_dependencies(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate service dependencies in configuration."""
        services = config.get("services", {})
        missing_dependencies = []
        dependency_graph = {}

        # Build dependency graph
        for service_name, service_config in services.items():
            dependencies = service_config.get("dependencies", [])
            dependency_graph[service_name] = dependencies

            # Check if dependencies exist
            for dep in dependencies:
                if dep not in services:
                    missing_dependencies.append(dep)

        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(dependency_graph)

        return {
            "dependencies_valid": len(missing_dependencies) == 0
            and len(circular_deps) == 0,
            "missing_dependencies": missing_dependencies,
            "circular_dependencies": circular_deps,
            "dependency_graph": dependency_graph,
        }

    def _detect_circular_dependencies(self, graph: dict[str, list[str]]) -> list[str]:
        """Detect circular dependencies in service graph."""
        visited = set()
        rec_stack = set()
        circular_deps = []

        def dfs(node, path):
            if node in rec_stack:
                # Found circular dependency
                cycle_start = path.index(node)
                circular_deps.append(" -> ".join(path[cycle_start:] + [node]))
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return circular_deps


class TestEnvironmentSetup(AAATester):
    """Test suite for environment setup and configuration deployment."""

    def test_development_environment_setup(self) -> None:
        """Test development environment setup."""
        # Arrange
        dev_config = {
            "environment": "development",
            "debug": True,
            "resource_limits": {"cpu": "500m", "memory": "512Mi"},
            "replicas": 1,
        }

        # Act
        result = self._setup_environment(dev_config)

        # Assert
        assert result["environment_ready"] is True
        assert result["debug_enabled"] is True
        assert result["resource_constraints"] == "minimal"

    def test_production_environment_setup(self) -> None:
        """Test production environment setup."""
        # Arrange
        prod_config = {
            "environment": "production",
            "debug": False,
            "resource_limits": {"cpu": "2000m", "memory": "4Gi"},
            "replicas": 3,
            "security": {"rbac": True, "network_policies": True},
        }

        # Act
        result = self._setup_environment(prod_config)

        # Assert
        assert result["environment_ready"] is True
        assert result["debug_enabled"] is False
        assert result["high_availability"] is True
        assert result["security_hardened"] is True

    def test_configuration_driven_deployment(self) -> None:
        """Test deployment driven by configuration."""
        # Arrange
        deployment_config = {
            "services": {
                "traefik": {"enabled": True, "priority": 1},
                "supabase": {
                    "enabled": True,
                    "priority": 2,
                    "dependencies": ["traefik"],
                },
                "app": {"enabled": False, "priority": 3},
            }
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._deploy_from_configuration(deployment_config)

        # Assert
        assert result["deployment_successful"] is True
        assert len(result["deployed_services"]) == 2  # traefik and supabase
        assert "app" not in result["deployed_services"]  # disabled
        assert result["deployment_order"] == ["traefik", "supabase"]

    def _setup_environment(self, config: dict[str, Any]) -> dict[str, Any]:
        """Setup environment based on configuration."""
        environment = config["environment"]

        # Environment-specific setup
        if environment == "development":
            return {
                "environment_ready": True,
                "debug_enabled": config.get("debug", False),
                "resource_constraints": "minimal",
                "monitoring": "basic",
            }
        elif environment == "production":
            return {
                "environment_ready": True,
                "debug_enabled": config.get("debug", False),
                "high_availability": config.get("replicas", 1) > 1,
                "security_hardened": bool(config.get("security")),
                "monitoring": "comprehensive",
            }
        else:
            return {
                "environment_ready": False,
                "error": f"Unknown environment: {environment}",
            }

    def _deploy_from_configuration(self, config: dict[str, Any]) -> dict[str, Any]:
        """Deploy services based on configuration."""
        import subprocess

        services = config.get("services", {})
        deployed_services = []
        deployment_order = []

        # Sort services by priority and dependencies
        service_list = [
            (name, svc_config)
            for name, svc_config in services.items()
            if svc_config.get("enabled", True)
        ]
        service_list.sort(key=lambda x: x[1].get("priority", 999))

        # Deploy services in order
        for service_name, service_config in service_list:
            # Check dependencies
            dependencies = service_config.get("dependencies", [])
            deps_satisfied = all(dep in deployed_services for dep in dependencies)

            if deps_satisfied:
                # Deploy service
                cmd = ["kubectl", "apply", "-f", f"{service_name}-manifest.yaml"]
                subprocess.run(cmd, check=True)

                deployed_services.append(service_name)
                deployment_order.append(service_name)

        return {
            "deployment_successful": True,
            "deployed_services": deployed_services,
            "deployment_order": deployment_order,
            "total_enabled_services": len(service_list),
        }
