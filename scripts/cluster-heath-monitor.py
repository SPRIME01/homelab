#!/usr/bin/env python3
"""
Comprehensive K3s cluster health monitoring with auto-healing capabilities.
Monitors nodes, pods, services, and network connectivity continuously.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class HealthCheck:
    name: str
    status: str
    message: str
    timestamp: datetime
    severity: str  # INFO, WARNING, CRITICAL
    auto_fix_attempted: bool = False

class ClusterHealthMonitor:
    """Continuous cluster health monitoring with notifications."""

    def __init__(self):
        self.health_history = []
        self.alert_thresholds = {
            'node_down_minutes': 5,
            'pod_restart_count': 10,
            'memory_usage_percent': 85,
            'disk_usage_percent': 90
        }
        self.notification_config = {}
    async def run_health_checks(self) -> List[HealthCheck]:
    async def run_health_checks(self) -> list[HealthCheck]:
        checks = []

        # Node health
        checks.extend(await self._check_nodes())

        # Pod health
        checks.extend(await self._check_pods())

        # Service connectivity
        checks.extend(await self._check_services())

        # Resource usage
        checks.extend(await self._check_resources())

        # Network connectivity (dual-IP)
        checks.extend(await self._check_network_connectivity())

        # Home Assistant MQTT connectivity
        checks.extend(await self._check_mqtt_connectivity())

        return checks

    async def _check_nodes(self) -> List[HealthCheck]:
        checks = []
        try:
            result = await self._run_kubectl(['get', 'nodes', '-o', 'json'])
            if result['returncode'] == 0:
                nodes = json.loads(result['stdout'])

                for node in nodes['items']:
                    node_name = node['metadata']['name']
                    conditions = node['status']['conditions']

                    ready_condition = next((c for c in conditions if c['type'] == 'Ready'), None)
                    if ready_condition and ready_condition['status'] != 'True':
                        checks.append(HealthCheck(
                            name=f"node_{node_name}",
                            status="UNHEALTHY",
                            message=f"Node {node_name} is not ready: {ready_condition['message']}",
                            timestamp=datetime.now(),
                            severity="CRITICAL"
                        ))

                        # Auto-fix attempt: restart node services
                        if await self._attempt_node_recovery(node_name):
                            checks[-1].auto_fix_attempted = True
                    else:
                        checks.append(HealthCheck(
                            name=f"node_{node_name}",
                            status="HEALTHY",
                            message=f"Node {node_name} is ready",
                            timestamp=datetime.now(),
                            severity="INFO"
                        ))
        except Exception as e:
            checks.append(HealthCheck(
                name="node_check",
                status="ERROR",
                message=f"Failed to check nodes: {e}",
                timestamp=datetime.now(),
                severity="CRITICAL"
            ))

        return checks

    async def _check_mqtt_connectivity(self) -> List[HealthCheck]:
    async def _check_mqtt_connectivity(self) -> List[HealthCheck]:
        try:
            import paho.mqtt.client as mqtt

            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    checks.append(HealthCheck(
                        name="mqtt_connectivity",
                        status="HEALTHY",
                        message="MQTT connection to Home Assistant successful",
                        timestamp=datetime.now(),
                        severity="INFO"
                    ))
                else:
                    checks.append(HealthCheck(
                        name="mqtt_connectivity",
                        status="UNHEALTHY",
                        message=f"MQTT connection failed with code {rc}",
                        timestamp=datetime.now(),
                        severity="WARNING"
                    ))

            client = mqtt.Client()
            client.on_connect = on_connect
            client.connect("192.168.0.41", 1883, 60)  # Home Assistant Yellow
            client.loop_start()

            # Wait for connection
            await asyncio.sleep(5)
            client.disconnect()

        except ImportError:
            checks.append(HealthCheck(
                name="mqtt_connectivity",
                status="SKIPPED",
                message="paho-mqtt not installed, skipping MQTT check",
                timestamp=datetime.now(),
                severity="INFO"
            ))
        except Exception as e:
            checks.append(HealthCheck(
                name="mqtt_connectivity",
                status="ERROR",
                message=f"MQTT check failed: {e}",
                timestamp=datetime.now(),
                severity="WARNING"
            ))

        return checks

    async def _attempt_node_recovery(self, node_name: str) -> bool:
        """Attempt to recover an unhealthy node."""
        try:
            # Restart K3s service
            if node_name == "control-node":  # Control node
                result = await self._run_command(['sudo', 'systemctl', 'restart', 'k3s'])
                return result['returncode'] == 0
            else:  # Agent node - would need SSH
                # This would require SSH to agent node
                return False
        except:
            return False

    def generate_health_report(self, checks: List[HealthCheck]) -> str:
    def generate_health_report(self, checks: list[HealthCheck]) -> str:
    def generate_health_report(self, checks: List[HealthCheck]) -> str:
        healthy_services = [c for c in checks if c.status == "HEALTHY"]

        report = [
            "=" * 60,
            f"K3S CLUSTER HEALTH REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            f"Overall Status: {'🔴 CRITICAL' if critical_issues else '🟡 WARNING' if warnings else '🟢 HEALTHY'}",
            f"Total Checks: {len(checks)}",
            f"Healthy: {len(healthy_services)}",
            f"Warnings: {len(warnings)}",
            f"Critical: {len(critical_issues)}",
            ""
        ]

        if critical_issues:
            report.extend([
                "🔴 CRITICAL ISSUES:",
                "-" * 20
            ])
            for issue in critical_issues:
                fix_status = " (Auto-fix attempted)" if issue.auto_fix_attempted else ""
                report.append(f"• {issue.name}: {issue.message}{fix_status}")
            report.append("")

        if warnings:
            report.extend([
                "🟡 WARNINGS:",
                "-" * 10
            ])
            for warning in warnings:
                report.append(f"• {warning.name}: {warning.message}")
            report.append("")

        report.extend([
            "🟢 HEALTHY SERVICES:",
            "-" * 20
        ])
        for healthy in healthy_services[:10]:  # Limit to first 10
            report.append(f"• {healthy.name}: {healthy.message}")

        return "\n".join(report)

# Usage: python3 scripts/cluster-health-monitor.py --continuous --interval 300
