#!/usr/bin/env python3
"""
Discover and integrate smart home devices and services.
Auto-configures Home Assistant entities, MQTT topics, and K8s services.
"""

import asyncio
import json
import requests
from typing import Dict, List
import nmap
from dataclasses import dataclass
import yaml

@dataclass
class DiscoveredDevice:
    ip: str
    hostname: str
    mac_address: str
    device_type: str
    services: List[str]
    manufacturer: str = "Unknown"

class SmartHomeDiscovery:
    """Discover and integrate smart home devices."""

    def __init__(self):
        self.network_range = "192.168.0.0/24"
        self.known_devices = {}
        self.home_assistant_url = "http://192.168.0.41:8123"

    async def discover_network_devices(self) -> List[DiscoveredDevice]:
        """Scan network for smart home devices."""
        nm = nmap.PortScanner()
        devices = []

        # Scan network
        nm.scan(hosts=self.network_range, arguments='-sn')

        for host in nm.all_hosts():
            if nm[host].state() == 'up':
                device = await self._identify_device(host, nm[host])
                if device:
                    devices.append(device)

        return devices

    async def _identify_device(self, ip: str, host_info) -> Optional[DiscoveredDevice]:
        """Identify device type and capabilities."""
        hostname = host_info.hostname() if host_info.hostname() else ip

        # Check common smart home ports
        device_type = "unknown"
        services = []

        # Port scanning for device identification
        port_checks = {
            80: "http",
            443: "https",
            1883: "mqtt",
            8123: "home_assistant",
            9443: "unifi",
            22: "ssh",
            23: "telnet"
        }

        nm = nmap.PortScanner()
        nm.scan(ip, arguments='-p' + ','.join(map(str, port_checks.keys())))

        if ip in nm.all_hosts():
            for port, service in port_checks.items():
                if nm[ip]['tcp'][port]['state'] == 'open':
                    services.append(service)

        # Device type inference
        if "8123" in [str(p) for p in services]:
            device_type = "home_assistant"
        elif "1883" in services:
            device_type = "mqtt_broker"
        elif "alexa" in hostname.lower():
            device_type = "amazon_echo"
        elif any(brand in hostname.lower() for brand in ['philips', 'hue']):
            device_type = "philips_hue"
        elif "unifi" in services:
            device_type = "unifi_device"

        return DiscoveredDevice(
            ip=ip,
            hostname=hostname,
            mac_address=self._get_mac_address(ip),
            device_type=device_type,
            services=services
        )

    def generate_home_assistant_config(self, devices: List[DiscoveredDevice]) -> str:
        """Generate Home Assistant configuration for discovered devices."""
        config = {
            'mqtt': {
                'broker': '192.168.0.41',
                'port': 1883,
                'discovery': True
            },
            'device_tracker': [],
            'switch': [],
            'sensor': []
        }

        for device in devices:
            if device.device_type == "amazon_echo":
                config['media_player'] = config.get('media_player', [])
                config['media_player'].append({
                    'platform': 'alexa_media',
                    'accounts': [{
                        'email': 'your_email@example.com',  # User to configure
                        'password': 'your_password',
                        'url': 'amazon.com'
                    }]
                })

            # Add device tracker for all discovered devices
            config['device_tracker'].append({
                'platform': 'nmap_tracker',
                'hosts': f"{device.ip}/32",
                'home_interval': 10,
                'consider_home': 180
            })

        return yaml.dump(config, default_flow_style=False)

    def generate_k8s_services(self, devices: List[DiscoveredDevice]) -> str:
        """Generate Kubernetes service configurations."""
        services = []

        for device in devices:
            if device.device_type in ["home_assistant", "mqtt_broker"]:
                service_config = {
                    'apiVersion': 'v1',
                    'kind': 'Service',
                    'metadata': {
                        'name': f"{device.device_type.replace('_', '-')}-external",
                        'namespace': 'smart-home'
                    },
                    'spec': {
                        'type': 'ExternalName',
                        'externalName': device.ip,
                        'ports': self._get_service_ports(device.services)
                    }
                }
                services.append(service_config)

        return yaml.dump_all(services, default_flow_style=False)

# Usage: python3 scripts/homelab-discovery.py --scan --generate-configs
