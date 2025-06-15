#!/usr/bin/env python3
"""
Supabase deployment configuration example.
Copy this file and modify settings for your environment.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SupabaseConfig:
    """Supabase deployment configuration."""

    # Kubernetes Configuration
    namespace: str = "supabase"
    kubeconfig_path: Path = Path.home() / ".kube" / "config"

    # PostgreSQL Configuration
    postgres_version: str = "15.1.0.147"
    postgres_database: str = "postgres"
    postgres_user: str = "supabase_admin"
    postgres_password: str = "your-secure-postgres-password"
    postgres_storage_size: str = "10Gi"
    postgres_memory_request: str = "256Mi"
    postgres_memory_limit: str = "1Gi"
    postgres_cpu_request: str = "250m"
    postgres_cpu_limit: str = "500m"

    # PostgREST Configuration
    postgrest_version: str = "v11.2.0"
    postgrest_db_schemas: str = "public"
    postgrest_db_anon_role: str = "anon"
    postgrest_memory_request: str = "128Mi"
    postgrest_memory_limit: str = "256Mi"
    postgrest_cpu_request: str = "100m"
    postgrest_cpu_limit: str = "200m"

    # GoTrue (Auth) Configuration
    gotrue_version: str = "v2.132.3"
    gotrue_api_host: str = "0.0.0.0"
    gotrue_api_port: str = "9999"
    gotrue_memory_request: str = "128Mi"
    gotrue_memory_limit: str = "256Mi"
    gotrue_cpu_request: str = "100m"
    gotrue_cpu_limit: str = "200m"

    # Realtime Configuration
    realtime_version: str = "v2.25.50"
    realtime_port: str = "4000"
    realtime_memory_request: str = "128Mi"
    realtime_memory_limit: str = "256Mi"
    realtime_cpu_request: str = "100m"
    realtime_cpu_limit: str = "200m"

    # Storage Configuration
    storage_version: str = "v0.43.11"
    storage_port: str = "5000"
    storage_size: str = "20Gi"
    storage_memory_request: str = "128Mi"
    storage_memory_limit: str = "512Mi"
    storage_cpu_request: str = "100m"
    storage_cpu_limit: str = "300m"

    # Kong Gateway Configuration
    kong_version: str = "3.4"
    kong_proxy_port: str = "8000"
    kong_admin_port: str = "8001"
    kong_memory_request: str = "256Mi"
    kong_memory_limit: str = "512Mi"
    kong_cpu_request: str = "200m"
    kong_cpu_limit: str = "400m"

    # Security Configuration
    jwt_secret: str = "your-jwt-secret-key-here-minimum-32-characters"
    anon_key: str = "your-anon-key-here"
    service_key: str = "your-service-key-here"
    dashboard_username: str = "supabase"
    dashboard_password: str = "supabase-dashboard-password"

    # Migration Configuration
    migration_backup_path: Path = Path("/tmp/postgres_backups")
    migration_timeout: int = 300  # seconds

    # Old PostgreSQL Configuration (for migration)
    old_postgres_host: str = "postgres-service.default.svc.cluster.local"
    old_postgres_port: int = 5432
    old_postgres_db: str = "homelab"
    old_postgres_user: str = "postgres"
    old_postgres_password: str = "password"


# Environment-specific configurations
CONFIGS: dict[str, SupabaseConfig] = {
    "development": SupabaseConfig(
        # Development with minimal resources
        postgres_storage_size="5Gi",
        postgres_memory_limit="512Mi",
        storage_size="10Gi",
        jwt_secret="dev-jwt-secret-key-for-development-only",
        anon_key="dev-anon-key",
        service_key="dev-service-key",
    ),
    "production": SupabaseConfig(
        # Production with enhanced resources and security
        postgres_storage_size="50Gi",
        postgres_memory_request="512Mi",
        postgres_memory_limit="2Gi",
        postgres_cpu_request="500m",
        postgres_cpu_limit="1000m",
        storage_size="100Gi",
        # Use secure secrets in production
        jwt_secret="prod-jwt-secret-replace-with-secure-value",
        anon_key="prod-anon-key-replace-with-secure-value",
        service_key="prod-service-key-replace-with-secure-value",
        dashboard_password="secure-dashboard-password",
    ),
    "homelab": SupabaseConfig(
        # Balanced configuration for homelab use
        postgres_storage_size="20Gi",
        postgres_memory_request="512Mi",
        postgres_memory_limit="1Gi",
        storage_size="50Gi",
        # Homelab-specific settings
        jwt_secret="homelab-jwt-secret-change-me",
        anon_key="homelab-anon-key-change-me",
        service_key="homelab-service-key-change-me",
    ),
}


def get_config(environment: str = "homelab") -> SupabaseConfig:
    """Get configuration for specified environment."""
    if environment not in CONFIGS:
        raise ValueError(
            f"Unknown environment: {environment}. Available: {list(CONFIGS.keys())}"
        )

    return CONFIGS[environment]


def validate_config(config: SupabaseConfig) -> None:
    """Validate configuration settings."""
    errors = []

    # Check required paths
    if not config.kubeconfig_path.exists():
        errors.append(f"Kubeconfig not found: {config.kubeconfig_path}")

    # Check security settings
    if config.jwt_secret == "your-jwt-secret-key-here-minimum-32-characters":
        errors.append("JWT secret must be changed from default value")

    if len(config.jwt_secret) < 32:
        errors.append("JWT secret must be at least 32 characters long")

    if config.postgres_password == "your-secure-postgres-password":
        errors.append("PostgreSQL password must be changed from default value")

    if config.anon_key == "your-anon-key-here":
        errors.append("Anon key must be changed from default value")

    if config.service_key == "your-service-key-here":
        errors.append("Service key must be changed from default value")

    # Check backup path
    try:
        config.migration_backup_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        errors.append(f"Cannot create backup directory: {e}")

    if errors:
        raise ValueError(
            "Configuration validation failed:\n"
            + "\n".join(f"- {error}" for error in errors)
        )


# Example usage
if __name__ == "__main__":
    # Get configuration for homelab environment
    config = get_config("homelab")

    # Validate configuration
    try:
        validate_config(config)
        print("✅ Configuration validation passed")
    except ValueError as e:
        print(f"❌ Configuration validation failed:\n{e}")

    # Print configuration summary
    print("\n📋 Supabase Configuration Summary:")
    print("  Environment: homelab")
    print(f"  Namespace: {config.namespace}")
    print(f"  PostgreSQL Storage: {config.postgres_storage_size}")
    print(f"  File Storage: {config.storage_size}")
    print(f"  Backup Path: {config.migration_backup_path}")

    print("\n🔐 Security Settings:")
    print(
        f"  JWT Secret: {'✅ Set' if config.jwt_secret != 'your-jwt-secret-key-here-minimum-32-characters' else '❌ Default'}"
    )
    print(
        f"  PostgreSQL Password: {'✅ Set' if config.postgres_password != 'your-secure-postgres-password' else '❌ Default'}"
    )
    print(
        f"  Anon Key: {'✅ Set' if config.anon_key != 'your-anon-key-here' else '❌ Default'}"
    )
    print(
        f"  Service Key: {'✅ Set' if config.service_key != 'your-service-key-here' else '❌ Default'}"
    )
