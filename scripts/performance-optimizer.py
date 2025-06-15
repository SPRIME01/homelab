#!/usr/bin/env python3
"""
Performance optimization for WSL2 K3s homelab.
Monitors and optimizes resource usage, suggests improvements.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import psutil


@dataclass
class OptimizationRecommendation:
    category: str
    priority: str  # HIGH, MEDIUM, LOW
    description: str
    command: str
    expected_improvement: str


class PerformanceOptimizer:
    """Optimize homelab performance and resource usage."""

    def analyze_and_optimize(self) -> list[OptimizationRecommendation]:
        """Analyze system and provide optimization recommendations."""
        recommendations = []

        # Memory optimization
        recommendations.extend(self._analyze_memory_usage())

        # CPU optimization
        recommendations.extend(self._analyze_cpu_usage())

        # Disk I/O optimization
        recommendations.extend(self._analyze_disk_usage())

        # Network optimization
        recommendations.extend(
            self._analyze_network_performance()
        )  # K3s specific optimizations
        recommendations.extend(self._analyze_k3s_performance())

        # Supabase specific optimizations
        recommendations.extend(self._analyze_supabase_performance())

        return sorted(
            recommendations,
            key=lambda x: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[x.priority],
            reverse=True,
        )

    def _analyze_memory_usage(self) -> list[OptimizationRecommendation]:
        """Analyze memory usage and suggest optimizations."""
        recommendations = []
        memory = psutil.virtual_memory()

        if memory.percent > 85:
            recommendations.append(
                OptimizationRecommendation(
                    category="Memory",
                    priority="HIGH",
                    description="High memory usage detected. Consider increasing WSL2 memory limit.",
                    command="echo '[wsl2]\nmemory=8GB' >> /mnt/c/Users/$USER/.wslconfig",
                    expected_improvement="Reduce memory pressure, improve K3s stability",
                )
            )

        # Check for memory leaks in pods
        recommendations.append(
            OptimizationRecommendation(
                category="Memory",
                priority="MEDIUM",
                description="Implement pod memory limits to prevent memory leaks",
                command='kubectl patch deployment <deployment-name> -p \'{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"memory":"512Mi"}}}]}}}}\'',
                expected_improvement="Prevent pod memory leaks, improve cluster stability",
            )
        )

        return recommendations

    def apply_wsl2_optimizations(self) -> None:
        """Apply WSL2-specific performance optimizations."""

        # Create optimized .wslconfig
        wslconfig_content = """[wsl2]
# Limit memory usage
memory=8GB

# Enable nested virtualization
nestedVirtualization=true

# Optimize processor count
processors=4

# Enable page reporting
pageReporting=true

# Optimize swap
swap=2GB
swapFile=C:\\temp\\wsl-swap.vhdx

# Network optimizations
networkingMode=mirrored
firewall=true
"""

        wslconfig_path = (
            Path("/mnt/c/Users") / os.getenv("USER", "ubuntu") / ".wslconfig"
        )
        with open(wslconfig_path, "w") as f:
            f.write(wslconfig_content)

        print("✅ WSL2 optimizations applied. Restart WSL2 with: wsl --shutdown")

    def _analyze_cpu_usage(self) -> list[OptimizationRecommendation]:
        """Analyze CPU usage and suggest optimizations."""
        recommendations = []
        cpu_percent = psutil.cpu_percent(interval=1)

        if cpu_percent > 80:
            recommendations.append(
                OptimizationRecommendation(
                    category="CPU",
                    priority="HIGH",
                    description="High CPU usage detected. Consider CPU limits and node affinity.",
                    command='kubectl patch deployment <deployment-name> -p \'{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"cpu":"500m"}}}]}}}}\'',
                    expected_improvement="Prevent CPU throttling, improve overall performance",
                )
            )

        return recommendations

    def _analyze_disk_usage(self) -> list[OptimizationRecommendation]:
        """Analyze disk I/O and suggest optimizations."""
        recommendations = []
        disk_usage = psutil.disk_usage("/")

        if disk_usage.percent > 85:
            recommendations.append(
                OptimizationRecommendation(
                    category="Disk",
                    priority="HIGH",
                    description="High disk usage detected. Consider cleanup and storage optimization.",
                    command="docker system prune -f && kubectl delete pods --field-selector=status.phase!=Running -A",
                    expected_improvement="Free up disk space, improve I/O performance",
                )
            )

        return recommendations

    def _analyze_network_performance(self) -> list[OptimizationRecommendation]:
        """Analyze network performance and suggest optimizations."""
        recommendations = []

        # Add network optimization suggestions
        recommendations.append(
            OptimizationRecommendation(
                category="Network",
                priority="MEDIUM",
                description="Optimize K3s network performance with CNI tuning",
                command='kubectl patch configmap flannel-cfg -n kube-system --patch \'{"data":{"net-conf.json":"{\\"Network\\":\\"10.42.0.0/16\\",\\"Backend\\":{\\"Type\\":\\"vxlan\\",\\"Directrouting\\":true}}"}}\'',
                expected_improvement="Reduce network latency, improve pod-to-pod communication",
            )
        )

        return recommendations

    def _analyze_k3s_performance(self) -> list[OptimizationRecommendation]:
        """Analyze K3s cluster performance and suggest optimizations."""
        recommendations = []

        # K3s etcd optimization
        recommendations.append(
            OptimizationRecommendation(
                category="K3s",
                priority="MEDIUM",
                description="Optimize K3s etcd performance for better cluster operations",
                command="sudo systemctl edit k3s --full && echo 'ETCD_HEARTBEAT_INTERVAL=200' >> /etc/systemd/system/k3s.service",
                expected_improvement="Reduce etcd latency, improve cluster responsiveness",
            )
        )

        return recommendations

    def _analyze_supabase_performance(self) -> list[OptimizationRecommendation]:
        """Analyze Supabase performance and suggest optimizations."""
        recommendations = []

        # Check Supabase connection pooling
        recommendations.append(
            OptimizationRecommendation(
                category="Database",
                priority="HIGH",
                description="Configure Supabase connection pooling for better performance",
                command='kubectl patch configmap supabase-config -n supabase -p \'{"data":{"PGRST_DB_POOL":"20","PGRST_DB_POOL_TIMEOUT":"10"}}\'',
                expected_improvement="Reduce database connection overhead, improve response times",
            )
        )

        # Supabase PostgreSQL tuning
        recommendations.append(
            OptimizationRecommendation(
                category="Database",
                priority="MEDIUM",
                description="Optimize Supabase PostgreSQL configuration for K3s",
                command="kubectl exec -n supabase deployment/supabase-postgres -- psql -U supabase_admin -c \"ALTER SYSTEM SET shared_buffers = '256MB'; ALTER SYSTEM SET effective_cache_size = '1GB'; SELECT pg_reload_conf();\"",
                expected_improvement="Better memory utilization and query performance",
            )
        )

        # Supabase storage optimization
        recommendations.append(
            OptimizationRecommendation(
                category="Storage",
                priority="MEDIUM",
                description="Optimize Supabase storage service configuration",
                command='kubectl patch deployment supabase-storage -n supabase -p \'{"spec":{"template":{"spec":{"containers":[{"name":"storage","resources":{"requests":{"memory":"256Mi","cpu":"200m"},"limits":{"memory":"512Mi","cpu":"500m"}}}]}}}}\'',
                expected_improvement="Improve file upload/download performance",
            )
        )

        return recommendations


# Usage: python3 scripts/performance-optimizer.py --analyze --apply-optimizations
