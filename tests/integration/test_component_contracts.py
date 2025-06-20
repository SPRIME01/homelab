"""Integration tests for component contracts and cross-service communication.

Tests cover API contracts, service discovery, health checks,
and inter-component communication patterns.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
import psycopg2 # Ensure psycopg2 is imported
from testcontainers.core.container import DockerContainer # For type hint

# Add project directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from test_helpers import AAATester


class TestServiceContracts(AAATester):
    """Test suite for service API contracts and interfaces."""

    @pytest.fixture
    def mock_k8s_api_client(self) -> Mock:
        """Mock Kubernetes API client for testing."""
        mock_client = Mock()
        mock_client.list_namespaced_pod.return_value = Mock(
            items=[
                Mock(
                    metadata=Mock(name="traefik-pod", namespace="traefik-system"),
                    status=Mock(phase="Running"),
                ),
                Mock(
                    metadata=Mock(name="supabase-pod", namespace="supabase"),
                    status=Mock(phase="Running"),
                ),
            ]
        )
        return mock_client

    @pytest.fixture
    def sample_service_manifest(self) -> dict[str, Any]:
        """Sample Kubernetes service manifest."""
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "test-service",
                "namespace": "default",
                "labels": {"app": "test"},
            },
            "spec": {
                "selector": {"app": "test"},
                "ports": [{"name": "http", "port": 80, "targetPort": 8080}],
                "type": "ClusterIP",
            },
        }

    def test_kubernetes_api_contract_validation(
        self, mock_k8s_api_client: Mock
    ) -> None:
        """Test Kubernetes API contract compliance."""
        # Arrange & Act
        result = self._validate_k8s_api_contract(mock_k8s_api_client)

        # Assert
        assert result["contract_valid"] is True
        assert result["api_version_supported"] is True
        assert len(result["available_resources"]) > 0
        assert "pods" in result["available_resources"]

    def test_service_discovery_contract(
        self, sample_service_manifest: dict[str, Any]
    ) -> None:
        """Test service discovery and DNS resolution contract."""
        # Arrange
        service_name = "test-service"
        namespace = "default"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=f"{service_name}.{namespace}.svc.cluster.local has address 10.43.0.100",
            )
            result = self._test_service_discovery_contract(service_name, namespace)

        # Assert
        assert result["service_discoverable"] is True
        assert result["dns_resolution"] is True
        assert result["cluster_ip"] == "10.43.0.100"

    def test_health_check_contract(self) -> None:
        """Test service health check endpoint contracts."""
        # Arrange
        services = [
            {"name": "traefik", "health_endpoint": "/health", "port": 8080},
            {"name": "supabase", "health_endpoint": "/health", "port": 3000},
            {"name": "mqtt-broker", "health_endpoint": "/status", "port": 1883},
        ]

        # Act
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200, json=lambda: {"status": "healthy", "version": "1.0.0"}
            )
            result = self._validate_health_check_contracts(services)

        # Assert
        assert result["all_healthy"] is True
        assert len(result["healthy_services"]) == 3
        assert len(result["unhealthy_services"]) == 0

    def test_api_versioning_contract(self) -> None:
        """Test API versioning and backward compatibility."""
        # Arrange
        api_versions = ["v1", "v2"]
        endpoints = ["/api/users", "/api/projects", "/api/health"]

        # Act
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                headers={"API-Version": "v2", "Supported-Versions": "v1,v2"},
            )
            result = self._test_api_versioning_contract(api_versions, endpoints)

        # Assert
        assert result["versioning_compliant"] is True
        assert result["backward_compatible"] is True
        assert len(result["supported_versions"]) == 2

    def _validate_k8s_api_contract(self, client: Mock) -> dict[str, Any]:
        """Validate Kubernetes API client contract."""
        try:
            # Test basic API operations
            pods = client.list_namespaced_pod(namespace="default")

            # Validate response structure
            available_resources = ["pods", "services", "deployments", "configmaps"]

            return {
                "contract_valid": True,
                "api_version_supported": True,
                "available_resources": available_resources,
                "pod_count": len(pods.items),
            }
        except Exception as e:
            return {
                "contract_valid": False,
                "error": str(e),
            }

    def _test_service_discovery_contract(
        self, service_name: str, namespace: str
    ) -> dict[str, Any]:
        """Test service discovery contract implementation."""
        import subprocess

        # Test DNS resolution
        fqdn = f"{service_name}.{namespace}.svc.cluster.local"
        cmd = ["nslookup", fqdn]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and "has address" in result.stdout:
            # Extract IP address
            lines = result.stdout.split("\n")
            ip_line = next((line for line in lines if "has address" in line), "")
            ip_address = ip_line.split()[-1] if ip_line else None

            return {
                "service_discoverable": True,
                "dns_resolution": True,
                "cluster_ip": ip_address,
                "fqdn": fqdn,
            }
        else:
            return {
                "service_discoverable": False,
                "dns_resolution": False,
                "error": result.stderr,
            }

    def _validate_health_check_contracts(
        self, services: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Validate health check endpoint contracts."""
        import requests

        healthy_services = []
        unhealthy_services = []

        for service in services:
            try:
                url = f"http://{service['name']}:{service['port']}{service['health_endpoint']}"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get("status") == "healthy":
                        healthy_services.append(service["name"])
                    else:
                        unhealthy_services.append(service["name"])
                else:
                    unhealthy_services.append(service["name"])

            except Exception:
                unhealthy_services.append(service["name"])

        return {
            "all_healthy": len(unhealthy_services) == 0,
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "total_services": len(services),
        }

    def _test_api_versioning_contract(
        self, versions: list[str], endpoints: list[str]
    ) -> dict[str, Any]:
        """Test API versioning contract compliance."""
        import requests

        supported_versions = []

        for version in versions:
            version_supported = True
            for endpoint in endpoints:
                try:
                    url = f"http://api-gateway/{version}{endpoint}"
                    response = requests.get(
                        url,
                        headers={
                            "Accept": f"application/vnd.api+json;version={version}"
                        },
                    )

                    if response.status_code not in [
                        200,
                        404,
                    ]:  # 404 is acceptable for optional endpoints
                        version_supported = False
                        break

                except Exception:
                    version_supported = False
                    break

            if version_supported:
                supported_versions.append(version)

        return {
            "versioning_compliant": len(supported_versions) > 0,
            "backward_compatible": "v1" in supported_versions,
            "supported_versions": supported_versions,
            "latest_version": max(supported_versions) if supported_versions else None,
        }


# import paho.mqtt.client as mqtt # This import is in _test_mqtt_communication

class TestCrossComponentCommunication(AAATester):
    """Test suite for cross-component communication patterns."""

    def test_mqtt_message_flow(self, mqtt_test_config: dict) -> None:
        """Test MQTT message flow between components."""
        # Arrange
        # mqtt_test_config now provides broker and port
        full_mqtt_config = {
            **mqtt_test_config,
            "topics": ["homelab/sensors", "homelab/alerts", "homelab/logs"],
        }

        # Act
        result = self._test_mqtt_communication(full_mqtt_config)

        # Assert
        assert result["connection_successful"] is True
        assert result["messages_published"] > 0
        assert result["messages_received"] > 0 # This will now depend on actual broker interaction
        assert len(result["active_topics"]) == 3

    def test_http_api_communication(self, httpbin_test_base_url: str) -> None:
        """Test HTTP API communication between services."""
        # Arrange
        # httpbin_test_base_url provides http://host:port
        api_endpoints = [
            {"service": httpbin_test_base_url, "endpoint": "/get", "method": "GET"},
            {"service": httpbin_test_base_url, "endpoint": "/headers", "method": "GET"},
            {"service": httpbin_test_base_url, "endpoint": "/ip", "method": "GET"},
        ]

        # Act
        result = self._test_http_api_communication(api_endpoints)

        # Assert
        assert result["all_apis_responsive"] is True
        assert len(result["successful_calls"]) == 3 # successful_calls now stores the base URL
        assert len(result["failed_calls"]) == 0

    def test_database_connectivity(self, postgres_test_config: dict) -> None:
        """Test database connectivity and query execution."""
        # Arrange
        # postgres_test_config directly provides the db_config dictionary
        # Act
        result = self._test_database_connectivity(postgres_test_config)

        # Assert
        assert result["connection_successful"] is True
        assert result["query_execution"] is True
        assert "PostgreSQL" in result["database_version"]

    def test_event_driven_communication(self, rabbitmq_test_config: dict) -> None:
        """Test event-driven communication patterns."""
        # Arrange
        # rabbitmq_test_config provides host and port
        full_event_config = {
            **rabbitmq_test_config,
            "exchanges": ["homelab.events", "homelab.alerts"],
            "queues": ["sensor.data", "system.logs", "alerts.critical"],
        }

        # Act
        result = self._test_event_driven_communication(full_event_config)

        # Assert
        assert result["event_bus_connected"] is True
        assert result["exchanges_declared"] == 2
        assert result["queues_declared"] == 3
        assert result["events_published"] > 0

    @pytest.mark.asyncio
    async def test_async_service_communication(self, echo_websocket_test_endpoint: str) -> None:
        """Test asynchronous service communication patterns."""
        # Arrange
        # echo_websocket_test_endpoint provides ws://host:port
        async_services = [
            {"name": "echo-service1", "endpoint": echo_websocket_test_endpoint},
            {"name": "echo-service2", "endpoint": echo_websocket_test_endpoint},
        ]

        # Act
        result = await self._test_async_service_communication(async_services)

        # Assert
        assert result["async_connections"] == 2 # Assuming both connect successfully
        assert result["messages_received"] == 2 # Each connection sends and receives one message
        assert result["connection_stability"] is True

    def _test_mqtt_communication(self, config: dict[str, Any]) -> dict[str, Any]:
        """Test MQTT communication implementation."""
        from paho.mqtt.client import Client

        # Create MQTT client
        client = Client()

        # Connect to broker
        client.connect(config["broker"], config["port"], 60)

        # Publish test messages
        messages_published = 0
        for topic in config["topics"]:
            payload = json.dumps({"timestamp": time.time(), "data": "test"})
            client.publish(topic, payload)
            messages_published += 1

        # Subscribe and receive messages
        messages_received = 0

        def on_message(client, userdata, msg):
            nonlocal messages_received
            messages_received += 1

        client.on_message = on_message
        for topic in config["topics"]:
            client.subscribe(topic)

        client.loop_start()
        time.sleep(1)  # Allow time for message processing
        client.loop_stop()

        # For mocked tests, simulate received messages equal to published messages
        # This part needs to be re-evaluated for real broker.
        # If the client is not a mock, actual messages must be received.
        # The original logic has a time.sleep(1) which might be enough for local container.
        # if hasattr(client, "_mock_name"): # This condition will now be false
        #     messages_received = messages_published

        return {
            "connection_successful": True, # This is set true before connect attempt in original code
            "messages_published": messages_published,
            "messages_received": messages_received, # This will depend on real broker interaction
            "active_topics": config["topics"],
        }

    def _test_http_api_communication(
        self, endpoints: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Test HTTP API communication implementation."""
        import requests

        successful_calls = []
        failed_calls = []

        for endpoint in endpoints:
            try:
                url = f"http://{endpoint['service']}{endpoint['endpoint']}"
                response = requests.request(
                    method=endpoint["method"], url=url, timeout=5
                )

                if response.status_code < 400:
                    successful_calls.append(endpoint["service"])
                else:
                    failed_calls.append(endpoint["service"])

            except Exception:
                failed_calls.append(endpoint["service"])

        return {
            "all_apis_responsive": len(failed_calls) == 0,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "total_endpoints": len(endpoints),
        }

    def _test_database_connectivity(self, config: dict[str, Any]) -> dict[str, Any]:
        """Test database connectivity implementation."""
        import psycopg2

        try:
            # Connect to database
            # Ensure password from config is used.
            conn = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                database=config["database"],
                user=config["user"],
                password=config["password"], # Ensure password from config is used.
            )

            # Execute test query
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return {
                "connection_successful": True,
                "query_execution": True,
                "database_version": version,
            }

        except Exception as e:
            return {
                "connection_successful": False,
                "query_execution": False,
                "error": str(e),
            }

    def _test_event_driven_communication(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Test event-driven communication implementation."""
        import pika

        # Connect to message broker
        # Modified to use host and port from config
        connection_params = pika.ConnectionParameters(
            host=config["host"],
            port=config["port"]
        )
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()

        # Declare exchanges
        exchanges_declared = 0
        for exchange in config["exchanges"]:
            channel.exchange_declare(exchange=exchange, exchange_type="topic")
            exchanges_declared += 1

        # Declare queues
        queues_declared = 0
        for queue in config["queues"]:
            channel.queue_declare(queue=queue, durable=True)
            queues_declared += 1

        # Publish test events
        events_published = 0
        for exchange in config["exchanges"]:
            message = json.dumps({"event": "test", "timestamp": time.time()})
            channel.basic_publish(
                exchange=exchange, routing_key="test.event", body=message
            )
            events_published += 1

        connection.close()

        return {
            "event_bus_connected": True,
            "exchanges_declared": exchanges_declared,
            "queues_declared": queues_declared,
            "events_published": events_published,
        }

    async def _test_async_service_communication(
        self, services: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Test asynchronous service communication implementation."""
        from websockets import connect

        connections = 0
        messages_received = 0

        async def test_websocket_connection(service: dict[str, Any]) -> bool:
            nonlocal connections, messages_received
            try:
                async with connect(service["endpoint"]) as websocket:
                    connections += 1

                    sent_message = {"type": "test", "data": "ping", "service_name": service["name"]}
                    await websocket.send(json.dumps(sent_message))

                    received_message_str = await websocket.recv()
                    received_message = json.loads(received_message_str)

                    # Echo server should return what was sent
                    if received_message == sent_message:
                        messages_received += 1
                        return True
                    else:
                        # Optionally log mismatch
                        print(f"WS message mismatch: sent {sent_message}, got {received_message}")
                        return False
            except Exception as e:
                print(f"WS connection error for {service['name']}: {e}")
                return False

        # Test all service connections concurrently
        tasks = [test_websocket_connection(service) for service in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stable_connections = sum(1 for r in results if r is True)

        return {
            "async_connections": connections,
            "messages_received": messages_received,
            "connection_stability": stable_connections == len(services),
            "total_services": len(services),
        }


class TestSystemIntegration(AAATester):
    """Test suite for complete system integration scenarios."""

    def test_full_stack_deployment_integration(self) -> None:
        """Test complete full-stack application deployment."""
        # Arrange
        stack_components = [
            {"name": "database", "type": "postgresql", "dependencies": []},
            {"name": "backend", "type": "api", "dependencies": ["database"]},
            {"name": "frontend", "type": "spa", "dependencies": ["backend"]},
            {"name": "ingress", "type": "traefik", "dependencies": ["frontend"]},
        ]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._test_full_stack_deployment(stack_components)

        # Assert
        assert result["deployment_successful"] is True
        assert len(result["deployed_components"]) == 4
        assert result["dependencies_resolved"] is True
        assert result["health_checks_passed"] is True

    def test_data_flow_integration(self) -> None:
        """Test end-to-end data flow through the system."""
        # Arrange
        data_pipeline = [
            {"stage": "ingestion", "component": "mqtt-broker"},
            {"stage": "processing", "component": "data-processor"},
            {"stage": "storage", "component": "supabase"},
            {"stage": "visualization", "component": "grafana"},
        ]

        # Act
        with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
            mock_post.return_value = Mock(status_code=201)
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {"data": [{"timestamp": "2024-01-01", "value": 42}]},
            )
            result = self._test_data_flow_integration(data_pipeline)

        # Assert
        assert result["data_flow_complete"] is True
        assert result["data_integrity"] is True
        assert len(result["pipeline_stages"]) == 4
        assert result["processing_time"] > 0

    def test_security_integration(self) -> None:
        """Test security integration across all components."""
        # Arrange
        security_checks = [
            {"component": "api-gateway", "check": "tls_termination"},
            {"component": "database", "check": "encryption_at_rest"},
            {"component": "message-queue", "check": "authentication"},
            {"component": "monitoring", "check": "rbac_policies"},
        ]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Security check passed")
            result = self._test_security_integration(security_checks)

        # Assert
        assert result["security_compliant"] is True
        assert result["vulnerabilities_found"] == 0
        assert len(result["passed_checks"]) == 4
        assert result["compliance_score"] >= 95

    def _test_full_stack_deployment(
        self, components: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Test full-stack deployment integration."""
        import subprocess

        deployed_components = []
        deployment_order = []

        # Sort components by dependencies
        remaining = components.copy()
        while remaining:
            for component in remaining[:]:
                deps_satisfied = all(
                    dep in [c["name"] for c in deployed_components]
                    for dep in component.get("dependencies", [])
                )

                if deps_satisfied:
                    # Deploy component
                    cmd = [
                        "kubectl",
                        "apply",
                        "-f",
                        f"{component['name']}-manifest.yaml",
                    ]
                    subprocess.run(cmd, check=True)

                    deployed_components.append(component)
                    deployment_order.append(component["name"])
                    remaining.remove(component)

        # Verify health checks
        health_checks_passed = True
        for component in deployed_components:
            cmd = ["kubectl", "rollout", "status", f"deployment/{component['name']}"]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                health_checks_passed = False
                break

        return {
            "deployment_successful": len(deployed_components) == len(components),
            "deployed_components": deployment_order,
            "dependencies_resolved": True,
            "health_checks_passed": health_checks_passed,
        }

    def _test_data_flow_integration(
        self, pipeline: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Test data flow integration through pipeline."""
        import time

        import requests

        start_time = time.time()

        # Simulate data ingestion
        test_data = {"sensor_id": "temp_01", "value": 23.5, "timestamp": time.time()}
        response = requests.post("http://mqtt-broker/publish", json=test_data)

        # Allow processing time
        time.sleep(0.1)

        # Verify data in storage
        storage_response = requests.get("http://supabase/rest/v1/sensor_data")
        stored_data = storage_response.json()

        # Verify visualization
        viz_response = requests.get("http://grafana/api/datasources/test")

        processing_time = time.time() - start_time

        # Check data integrity
        data_integrity = (
            response.status_code == 201
            and len(stored_data.get("data", [])) > 0
            and viz_response.status_code == 200
        )

        return {
            "data_flow_complete": True,
            "data_integrity": data_integrity,
            "pipeline_stages": [stage["stage"] for stage in pipeline],
            "processing_time": processing_time,
        }

    def _test_security_integration(
        self, checks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Test security integration across components."""
        import subprocess

        passed_checks = []
        failed_checks = []
        vulnerabilities = 0

        for check in checks:
            component = check["component"]
            check_type = check["check"]

            # Run security check
            cmd = ["security-scanner", "--component", component, "--check", check_type]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and "passed" in result.stdout.lower():
                passed_checks.append(f"{component}:{check_type}")
            else:
                failed_checks.append(f"{component}:{check_type}")
                vulnerabilities += 1

        # Calculate compliance score
        total_checks = len(checks)
        compliance_score = (
            (len(passed_checks) / total_checks) * 100 if total_checks > 0 else 0
        )

        return {
            "security_compliant": len(failed_checks) == 0,
            "vulnerabilities_found": vulnerabilities,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "compliance_score": compliance_score,
        }
