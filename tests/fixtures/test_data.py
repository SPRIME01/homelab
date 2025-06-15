# Test Environment Configuration
# Used for setting up consistent test environments

HOMELAB_TEST_CONFIG = {
    "cluster": {
        "name": "homelab-test",
        "control_node_ip": "192.168.0.50",
        "wsl2_ip": "192.168.0.51",
        "agent_node_ip": "192.168.0.66",
        "kubeconfig_path": "/tmp/test-kubeconfig",
    },
    "supabase": {
        "namespace": "supabase",
        "postgres_password": "test-password-123",
        "jwt_secret": "test-jwt-secret-32-characters-minimum",
        "postgres_storage": "5Gi",
        "storage_size": "10Gi",
    },
    "networking": {
        "home_assistant_url": "http://192.168.0.41:8123",
        "mqtt_broker": "192.168.0.41:1883",
        "network_range": "192.168.0.0/24",
    },
    "paths": {
        "ssh_key_path": "/tmp/test-ssh-key",
        "backup_root": "/tmp/test-backups",
        "log_directory": "/tmp/test-logs",
    },
}

# Sample kubectl outputs for testing
KUBECTL_SAMPLE_OUTPUTS = {
    "pods_running": """
NAME                           READY   STATUS    RESTARTS   AGE
supabase-postgres-0            1/1     Running   0          5m30s
supabase-gotrue-abc123         1/1     Running   0          5m20s
supabase-storage-def456        1/1     Running   0          5m10s
supabase-kong-ghi789           1/1     Running   0          5m00s
""",
    "pods_json": {
        "items": [
            {
                "metadata": {"name": "supabase-postgres-0"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [{"ready": True, "restartCount": 0}],
                },
            },
            {
                "metadata": {"name": "supabase-gotrue-abc123"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [{"ready": True, "restartCount": 0}],
                },
            },
        ]
    },
    "nodes": """
NAME           STATUS   ROLES                  AGE   VERSION
control-node   Ready    control-plane,master   5d    v1.28.4+k3s1
agent-node     Ready    <none>                 5d    v1.28.4+k3s1
""",
    "services": """
NAME                TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                    AGE
supabase-postgres   ClusterIP   10.43.200.100   <none>        5432/TCP                   5m
supabase-kong       NodePort    10.43.200.101   <none>        8000:30000/TCP,8001:30001/TCP   5m
supabase-storage    ClusterIP   10.43.200.102   <none>        5000/TCP                   5m
""",
}

# Sample device discovery data
SAMPLE_DEVICES = [
    {
        "ip": "192.168.0.41",
        "hostname": "homeassistant",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "device_type": "home_assistant",
        "services": ["http", "mqtt", "mdns"],
        "manufacturer": "Home Assistant",
        "open_ports": [8123, 1883, 5353],
    },
    {
        "ip": "192.168.0.66",
        "hostname": "jetson-orin",
        "mac_address": "11:22:33:44:55:66",
        "device_type": "kubernetes_node",
        "services": ["ssh", "k3s", "docker"],
        "manufacturer": "NVIDIA",
        "open_ports": [22, 6443, 2376],
    },
    {
        "ip": "192.168.0.100",
        "hostname": "smart-switch-tp",
        "mac_address": "99:88:77:66:55:44",
        "device_type": "network_switch",
        "services": ["snmp", "http", "telnet"],
        "manufacturer": "TP-Link",
        "open_ports": [80, 161, 23],
    },
    {
        "ip": "192.168.0.110",
        "hostname": "smart-bulb-hue",
        "mac_address": "33:44:55:66:77:88",
        "device_type": "smart_light",
        "services": ["http", "upnp"],
        "manufacturer": "Philips",
        "open_ports": [80, 1900],
    },
]

# Performance monitoring test data
PERFORMANCE_TEST_DATA = {
    "cpu_usage": 25.5,
    "memory_usage": 65.2,
    "disk_usage": 78.1,
    "network_stats": {
        "bytes_sent": 1024000,
        "bytes_recv": 2048000,
        "packets_sent": 8000,
        "packets_recv": 12000,
    },
    "k8s_metrics": {
        "pod_count": 15,
        "node_count": 2,
        "service_count": 8,
        "namespace_count": 5,
    },
    "supabase_metrics": {
        "postgres_connections": 12,
        "storage_used_gb": 2.5,
        "requests_per_minute": 150,
    },
}

# Sample backup manifest data
BACKUP_MANIFEST_SAMPLE = {
    "timestamp": "2024-12-15T12:00:00Z",
    "version": "1.0",
    "components": {
        "k3s": {
            "status": "success",
            "files": ["etcd-snapshot.db", "kubeconfig"],
            "size_mb": 45.2,
        },
        "supabase": {
            "status": "success",
            "files": ["postgres_dump.sql", "config_backup.yaml"],
            "size_mb": 123.7,
        },
        "home_assistant": {
            "status": "success",
            "files": ["configuration.yaml", "automations.yaml"],
            "size_mb": 2.1,
        },
        "configurations": {
            "status": "success",
            "files": ["app_configs.tar.gz"],
            "size_mb": 15.8,
        },
    },
    "total_size_mb": 186.8,
    "backup_path": "/tmp/test-backups/homelab_backup_20241215_120000",
    "checksum": "sha256:abc123def456789...",
}

# SSH configuration test data
SSH_TEST_CONFIG = {
    "default_user": "ubuntu",
    "default_port": 22,
    "key_types": ["rsa", "ed25519"],
    "test_connections": [
        {
            "host": "192.168.0.66",
            "user": "ubuntu",
            "key_path": "/tmp/test-ssh-key",
            "expected_success": True,
        },
        {
            "host": "192.168.0.999",  # Invalid IP
            "user": "ubuntu",
            "key_path": "/tmp/test-ssh-key",
            "expected_success": False,
        },
    ],
}

# Error scenarios for testing
ERROR_SCENARIOS = {
    "network_timeout": {
        "exception": "TimeoutError",
        "message": "Connection timed out after 30 seconds",
    },
    "kubernetes_api_error": {
        "exception": "KubernetesAPIError",
        "message": "Unable to connect to the server",
    },
    "file_not_found": {
        "exception": "FileNotFoundError",
        "message": "No such file or directory: '/path/to/missing/file'",
    },
    "permission_denied": {
        "exception": "PermissionError",
        "message": "Permission denied: '/restricted/path'",
    },
    "invalid_yaml": {
        "exception": "yaml.YAMLError",
        "message": "Invalid YAML syntax at line 15",
    },
}
