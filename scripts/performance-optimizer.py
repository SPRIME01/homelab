#!/usr/bin/env python3
"""
Performance optimization for WSL2 K3s homelab.
Monitors and optimizes resource usage, suggests improvements.
"""

import psutil
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class OptimizationRecommendation:
    category: str
    priority: str  # HIGH, MEDIUM, LOW
    description: str
    command: str
    expected_improvement: str

class PerformanceOptimizer:
    """Optimize homelab performance and resource usage."""

    def analyze_and_optimize(self) -> List[OptimizationRecommendation]:
        """Analyze system and provide optimization recommendations."""
        recommendations = []

        # Memory optimization
        recommendations.extend(self._analyze_memory_usage())

        # CPU optimization
        recommendations.extend(self._analyze_cpu_usage())

        # Disk I/O optimization
        recommendations.extend(self._analyze_disk_usage())

        # Network optimization
        recommendations.extend(self._analyze_network_performance())

        # K3s specific optimizations
        recommendations.extend(self._analyze_k3s_performance())

        return sorted(recommendations, key=lambda x: {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}[x.priority], reverse=True)

    def _analyze_memory_usage(self) -> List[OptimizationRecommendation]:
        """Analyze memory usage and suggest optimizations."""
        recommendations = []
        memory = psutil.virtual_memory()

        if memory.percent > 85:
            recommendations.append(OptimizationRecommendation(
                category="Memory",
                priority="HIGH",
                description="High memory usage detected. Consider increasing WSL2 memory limit.",
                command="echo '[wsl2]\nmemory=8GB' >> /mnt/c/Users/$USER/.wslconfig",
                expected_improvement="Reduce memory pressure, improve K3s stability"
            ))

        # Check for memory leaks in pods
        recommendations.append(OptimizationRecommendation(
            category="Memory",
            priority="MEDIUM",
            description="Implement pod memory limits to prevent memory leaks",
            command="kubectl patch deployment <deployment-name> -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"<container>\",\"resources\":{\"limits\":{\"memory\":\"512Mi\"}}}]}}}}'",
            expected_improvement="Prevent pod memory leaks, improve cluster stability"
        ))

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

        wslconfig_path = Path("/mnt/c/Users") / os.getenv("USER", "ubuntu") / ".wslconfig"
        with open(wslconfig_path, "w") as f:
            f.write(wslconfig_content)

        print("✅ WSL2 optimizations applied. Restart WSL2 with: wsl --shutdown")

# Usage: python3 scripts/performance-optimizer.py --analyze --apply-optimizations
