"""
Supabase infrastructure management with Pulumi for K3s cluster.
Follows homelab project patterns and best practices.
"""

import os
from pathlib import Path
from typing import Any

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs
from pulumi_kubernetes.core.v1 import (
    ConfigMap,
    ContainerArgs,
    ContainerPortArgs,
    EnvVarArgs,
    EnvVarSourceArgs,
    Namespace,
    PersistentVolumeClaim,
    PersistentVolumeClaimSpecArgs,
    PodSpecArgs,
    PodTemplateSpecArgs,
    ProbeArgs,
    ResourceRequirementsArgs,
    Secret,
    SecretKeySelectorArgs,
    Service,
    ServicePortArgs,
    ServiceSpecArgs,
    TCPSocketActionArgs,
    VolumeArgs,
    VolumeMountArgs,
)
from pulumi_kubernetes.meta.v1 import LabelSelectorArgs, ObjectMetaArgs


class SupabaseInfrastructure:
    """Supabase infrastructure management with Pulumi following best practices."""

    def __init__(
        self, kubeconfig_path: Path, config: dict[str, Any] | None = None
    ) -> None:
        """Initialize Supabase infrastructure.

        Args:
            kubeconfig_path: Path to Kubernetes config file
            config: Optional configuration dictionary
        """
        self.provider = k8s.Provider("k3s-provider", kubeconfig=str(kubeconfig_path))
        self.namespace_name = "supabase"
        self.config = config or self._get_default_config()
        self.labels = {"app.kubernetes.io/part-of": "supabase"}

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration with environment variable overrides."""
        return {
            "postgres": {
                "image": "supabase/postgres:15.1.0.147",
                "storage": "10Gi",
                "resources": {
                    "requests": {"memory": "256Mi", "cpu": "250m"},
                    "limits": {"memory": "1Gi", "cpu": "500m"},
                },
            },
            "postgrest": {
                "image": "postgrest/postgrest:v11.2.0",
                "resources": {
                    "requests": {"memory": "128Mi", "cpu": "100m"},
                    "limits": {"memory": "256Mi", "cpu": "200m"},
                },
            },
            "gotrue": {
                "image": "supabase/gotrue:v2.132.3",
                "resources": {
                    "requests": {"memory": "128Mi", "cpu": "100m"},
                    "limits": {"memory": "256Mi", "cpu": "200m"},
                },
            },
            "realtime": {
                "image": "supabase/realtime:v2.25.50",
                "resources": {
                    "requests": {"memory": "128Mi", "cpu": "100m"},
                    "limits": {"memory": "256Mi", "cpu": "200m"},
                },
            },
            "storage": {
                "image": "supabase/storage-api:v0.43.11",
                "storage": "20Gi",
                "resources": {
                    "requests": {"memory": "128Mi", "cpu": "100m"},
                    "limits": {"memory": "512Mi", "cpu": "300m"},
                },
            },
            "kong": {
                "image": "kong:3.4",
                "resources": {
                    "requests": {"memory": "256Mi", "cpu": "200m"},
                    "limits": {"memory": "512Mi", "cpu": "400m"},
                },
            },
        }

    def deploy_supabase_stack(self) -> dict[str, Any]:
        """Deploy complete Supabase stack to K3s cluster."""
        try:
            # Create namespace
            namespace = self._create_namespace()

            # Create secrets and configmaps
            secrets = self._create_secrets(namespace)
            config_map = self._create_config_map(namespace)

            # Create persistent storage
            postgres_pvc = self._create_postgres_storage(namespace)
            storage_pvc = self._create_storage_pvc(namespace)

            # Deploy core services in dependency order
            postgres = self._deploy_postgres(namespace, secrets, postgres_pvc)
            postgrest = self._deploy_postgrest(namespace, secrets, config_map, postgres)
            gotrue = self._deploy_gotrue(namespace, secrets, config_map, postgres)
            realtime = self._deploy_realtime(namespace, secrets, config_map, postgres)
            storage = self._deploy_storage(namespace, secrets, storage_pvc, postgrest)
            kong = self._deploy_kong_gateway(
                namespace, config_map, [postgrest, gotrue, realtime, storage]
            )

            return {
                "namespace": namespace,
                "postgres": postgres,
                "postgrest": postgrest,
                "gotrue": gotrue,
                "realtime": realtime,
                "storage": storage,
                "kong": kong,
            }
        except Exception as e:
            pulumi.log.error(f"Failed to deploy Supabase stack: {e}")
            raise

    def _create_namespace(self) -> Namespace:
        """Create Supabase namespace with proper labels."""
        return Namespace(
            "supabase-namespace",
            metadata=ObjectMetaArgs(
                name=self.namespace_name,
                labels={**self.labels, "name": self.namespace_name},
            ),
            opts=pulumi.ResourceOptions(provider=self.provider),
        )

    def _create_secrets(self, namespace: Namespace) -> Secret:
        """Create Supabase secrets with proper validation."""
        # Use environment variables or generate secure defaults
        secret_data = {
            "postgres-password": os.getenv(
                "SUPABASE_POSTGRES_PASSWORD", "change-me-in-production"
            ),
            "jwt-secret": os.getenv(
                "SUPABASE_JWT_SECRET", "your-jwt-secret-key-here-must-be-32-chars"
            ),
            "anon-key": os.getenv("SUPABASE_ANON_KEY", "your-anon-key-here"),
            "service-key": os.getenv("SUPABASE_SERVICE_KEY", "your-service-key-here"),
            "dashboard-username": os.getenv("SUPABASE_DASHBOARD_USERNAME", "supabase"),
            "dashboard-password": os.getenv(
                "SUPABASE_DASHBOARD_PASSWORD", "change-me-in-production"
            ),
        }

        # Validate critical secrets
        for key, value in secret_data.items():
            if "change-me" in value or "your-" in value:
                pulumi.log.warn(
                    f"Using default value for {key}. Please set environment variable in production."
                )

        return Secret(
            "supabase-secrets",
            metadata=ObjectMetaArgs(
                name="supabase-secrets",
                namespace=self.namespace_name,
                labels={**self.labels, "app.kubernetes.io/component": "secrets"},
            ),
            string_data=secret_data,
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _create_config_map(self, namespace: Namespace) -> ConfigMap:
        """Create Supabase configuration with proper structure."""
        return ConfigMap(
            "supabase-config",
            metadata=ObjectMetaArgs(
                name="supabase-config",
                namespace=self.namespace_name,
                labels={**self.labels, "app.kubernetes.io/component": "config"},
            ),
            data={
                "postgres-host": "supabase-postgres-service",
                "postgres-port": "5432",
                "postgres-db": "postgres",
                "postgres-user": "supabase_admin",
                "api-url": "http://supabase-kong-service:8000",
                "studio-port": "3000",
                "postgrest-url": "http://supabase-postgrest-service:3000",
                "gotrue-url": "http://supabase-gotrue-service:9999",
                "realtime-url": "http://supabase-realtime-service:4000",
                "storage-url": "http://supabase-storage-service:5000",
            },
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _create_postgres_storage(self, namespace: Namespace) -> PersistentVolumeClaim:
        """Create PostgreSQL persistent volume claim with proper configuration."""
        return PersistentVolumeClaim(
            "supabase-postgres-pvc",
            metadata=ObjectMetaArgs(
                name="supabase-postgres-pvc",
                namespace=self.namespace_name,
                labels={
                    **self.labels,
                    "app.kubernetes.io/component": "postgres-storage",
                },
            ),
            spec=PersistentVolumeClaimSpecArgs(
                access_modes=["ReadWriteOnce"],
                resources={"requests": {"storage": self.config["postgres"]["storage"]}},
                storage_class_name="local-path",  # K3s default storage class
            ),
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _create_storage_pvc(self, namespace: Namespace) -> PersistentVolumeClaim:
        """Create storage service persistent volume claim."""
        return PersistentVolumeClaim(
            "supabase-storage-pvc",
            metadata=ObjectMetaArgs(
                name="supabase-storage-pvc",
                namespace=self.namespace_name,
                labels={**self.labels, "app.kubernetes.io/component": "storage-pvc"},
            ),
            spec=PersistentVolumeClaimSpecArgs(
                access_modes=["ReadWriteOnce"],
                resources={"requests": {"storage": self.config["storage"]["storage"]}},
                storage_class_name="local-path",
            ),
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _deploy_postgres(
        self, namespace: Namespace, secrets: Secret, pvc: PersistentVolumeClaim
    ) -> Deployment:
        """Deploy PostgreSQL with Supabase extensions and best practices."""
        component_labels = {
            **self.labels,
            "app.kubernetes.io/component": "postgres",
            "app": "supabase-postgres",
        }

        deployment = Deployment(
            "supabase-postgres",
            metadata=ObjectMetaArgs(
                name="supabase-postgres",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=DeploymentSpecArgs(
                replicas=1,
                selector=LabelSelectorArgs(match_labels={"app": "supabase-postgres"}),
                template=PodTemplateSpecArgs(
                    metadata=ObjectMetaArgs(labels=component_labels),
                    spec=PodSpecArgs(
                        containers=[
                            ContainerArgs(
                                name="postgres",
                                image=self.config["postgres"]["image"],
                                env=[
                                    EnvVarArgs(name="POSTGRES_DB", value="postgres"),
                                    EnvVarArgs(
                                        name="POSTGRES_USER", value="supabase_admin"
                                    ),
                                    EnvVarArgs(
                                        name="POSTGRES_PASSWORD",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="postgres-password",
                                            )
                                        ),
                                    ),
                                    EnvVarArgs(
                                        name="JWT_SECRET",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="jwt-secret",
                                            )
                                        ),
                                    ),
                                    EnvVarArgs(
                                        name="PGDATA",
                                        value="/var/lib/postgresql/data/pgdata",
                                    ),
                                ],
                                ports=[
                                    ContainerPortArgs(
                                        container_port=5432, name="postgres"
                                    )
                                ],
                                volume_mounts=[
                                    VolumeMountArgs(
                                        name="postgres-storage",
                                        mount_path="/var/lib/postgresql/data",
                                    )
                                ],
                                resources=ResourceRequirementsArgs(
                                    **self.config["postgres"]["resources"]
                                ),
                                liveness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=5432),
                                    initial_delay_seconds=30,
                                    period_seconds=10,
                                ),
                                readiness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=5432),
                                    initial_delay_seconds=5,
                                    period_seconds=5,
                                ),
                            )
                        ],
                        volumes=[
                            VolumeArgs(
                                name="postgres-storage",
                                persistent_volume_claim={
                                    "claim_name": "supabase-postgres-pvc"
                                },
                            )
                        ],
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, secrets, pvc]
            ),
        )

        # Create service for PostgreSQL
        Service(
            "supabase-postgres-service",
            metadata=ObjectMetaArgs(
                name="supabase-postgres-service",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=ServiceSpecArgs(
                selector={"app": "supabase-postgres"},
                ports=[ServicePortArgs(port=5432, target_port=5432, name="postgres")],
                type="ClusterIP",
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_postgrest(
        self,
        namespace: Namespace,
        secrets: Secret,
        config_map: ConfigMap,
        postgres: Deployment,
    ) -> Deployment:
        """Deploy PostgREST API service with proper configuration."""
        component_labels = {
            **self.labels,
            "app.kubernetes.io/component": "postgrest",
            "app": "supabase-postgrest",
        }

        deployment = Deployment(
            "supabase-postgrest",
            metadata=ObjectMetaArgs(
                name="supabase-postgrest",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=DeploymentSpecArgs(
                replicas=1,
                selector=LabelSelectorArgs(match_labels={"app": "supabase-postgrest"}),
                template=PodTemplateSpecArgs(
                    metadata=ObjectMetaArgs(labels=component_labels),
                    spec=PodSpecArgs(
                        containers=[
                            ContainerArgs(
                                name="postgrest",
                                image=self.config["postgrest"]["image"],
                                env=[
                                    EnvVarArgs(
                                        name="PGRST_DB_URI",
                                        value="postgresql://supabase_admin@supabase-postgres-service:5432/postgres",
                                    ),
                                    EnvVarArgs(name="PGRST_DB_SCHEMAS", value="public"),
                                    EnvVarArgs(name="PGRST_DB_ANON_ROLE", value="anon"),
                                    EnvVarArgs(
                                        name="PGRST_DB_USE_LEGACY_GUCS", value="false"
                                    ),
                                    EnvVarArgs(
                                        name="PGRST_JWT_SECRET",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="jwt-secret",
                                            )
                                        ),
                                    ),
                                ],
                                ports=[
                                    ContainerPortArgs(container_port=3000, name="http")
                                ],
                                resources=ResourceRequirementsArgs(
                                    **self.config["postgrest"]["resources"]
                                ),
                                liveness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=3000),
                                    initial_delay_seconds=30,
                                    period_seconds=10,
                                ),
                                readiness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=3000),
                                    initial_delay_seconds=5,
                                    period_seconds=5,
                                ),
                            )
                        ]
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider,
                depends_on=[namespace, secrets, config_map, postgres],
            ),
        )

        # Create service
        Service(
            "supabase-postgrest-service",
            metadata=ObjectMetaArgs(
                name="supabase-postgrest-service",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=ServiceSpecArgs(
                selector={"app": "supabase-postgrest"},
                ports=[ServicePortArgs(port=3000, target_port=3000, name="http")],
                type="ClusterIP",
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_gotrue(
        self,
        namespace: Namespace,
        secrets: Secret,
        config_map: ConfigMap,
        postgres: Deployment,
    ) -> Deployment:
        """Deploy GoTrue authentication service with proper configuration."""
        component_labels = {
            **self.labels,
            "app.kubernetes.io/component": "gotrue",
            "app": "supabase-gotrue",
        }

        deployment = Deployment(
            "supabase-gotrue",
            metadata=ObjectMetaArgs(
                name="supabase-gotrue",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=DeploymentSpecArgs(
                replicas=1,
                selector=LabelSelectorArgs(match_labels={"app": "supabase-gotrue"}),
                template=PodTemplateSpecArgs(
                    metadata=ObjectMetaArgs(labels=component_labels),
                    spec=PodSpecArgs(
                        containers=[
                            ContainerArgs(
                                name="gotrue",
                                image=self.config["gotrue"]["image"],
                                env=[
                                    EnvVarArgs(name="GOTRUE_API_HOST", value="0.0.0.0"),
                                    EnvVarArgs(name="GOTRUE_API_PORT", value="9999"),
                                    EnvVarArgs(
                                        name="GOTRUE_DB_DRIVER", value="postgres"
                                    ),
                                    EnvVarArgs(
                                        name="GOTRUE_DB_DATABASE_URL",
                                        value="postgresql://supabase_admin@supabase-postgres-service:5432/postgres",
                                    ),
                                    EnvVarArgs(
                                        name="GOTRUE_SITE_URL",
                                        value="http://localhost:3000",
                                    ),
                                    EnvVarArgs(name="GOTRUE_URI_ALLOW_LIST", value="*"),
                                    EnvVarArgs(
                                        name="GOTRUE_JWT_SECRET",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="jwt-secret",
                                            )
                                        ),
                                    ),
                                ],
                                ports=[
                                    ContainerPortArgs(container_port=9999, name="http")
                                ],
                                resources=ResourceRequirementsArgs(
                                    **self.config["gotrue"]["resources"]
                                ),
                                liveness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=9999),
                                    initial_delay_seconds=30,
                                    period_seconds=10,
                                ),
                                readiness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=9999),
                                    initial_delay_seconds=5,
                                    period_seconds=5,
                                ),
                            )
                        ]
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider,
                depends_on=[namespace, secrets, config_map, postgres],
            ),
        )

        # Create service
        Service(
            "supabase-gotrue-service",
            metadata=ObjectMetaArgs(
                name="supabase-gotrue-service",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=ServiceSpecArgs(
                selector={"app": "supabase-gotrue"},
                ports=[ServicePortArgs(port=9999, target_port=9999, name="http")],
                type="ClusterIP",
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_realtime(
        self,
        namespace: Namespace,
        secrets: Secret,
        config_map: ConfigMap,
        postgres: Deployment,
    ) -> Deployment:
        """Deploy Supabase Realtime service with proper configuration."""
        component_labels = {
            **self.labels,
            "app.kubernetes.io/component": "realtime",
            "app": "supabase-realtime",
        }

        deployment = Deployment(
            "supabase-realtime",
            metadata=ObjectMetaArgs(
                name="supabase-realtime",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=DeploymentSpecArgs(
                replicas=1,
                selector=LabelSelectorArgs(match_labels={"app": "supabase-realtime"}),
                template=PodTemplateSpecArgs(
                    metadata=ObjectMetaArgs(labels=component_labels),
                    spec=PodSpecArgs(
                        containers=[
                            ContainerArgs(
                                name="realtime",
                                image=self.config["realtime"]["image"],
                                env=[
                                    EnvVarArgs(name="PORT", value="4000"),
                                    EnvVarArgs(
                                        name="DB_HOST",
                                        value="supabase-postgres-service",
                                    ),
                                    EnvVarArgs(name="DB_PORT", value="5432"),
                                    EnvVarArgs(name="DB_NAME", value="postgres"),
                                    EnvVarArgs(name="DB_USER", value="supabase_admin"),
                                    EnvVarArgs(name="DB_SSL", value="false"),
                                    EnvVarArgs(
                                        name="DB_PASSWORD",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="postgres-password",
                                            )
                                        ),
                                    ),
                                    EnvVarArgs(
                                        name="JWT_SECRET",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="jwt-secret",
                                            )
                                        ),
                                    ),
                                ],
                                ports=[
                                    ContainerPortArgs(container_port=4000, name="http")
                                ],
                                resources=ResourceRequirementsArgs(
                                    **self.config["realtime"]["resources"]
                                ),
                                liveness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=4000),
                                    initial_delay_seconds=30,
                                    period_seconds=10,
                                ),
                                readiness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=4000),
                                    initial_delay_seconds=5,
                                    period_seconds=5,
                                ),
                            )
                        ]
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider,
                depends_on=[namespace, secrets, config_map, postgres],
            ),
        )

        # Create service
        Service(
            "supabase-realtime-service",
            metadata=ObjectMetaArgs(
                name="supabase-realtime-service",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=ServiceSpecArgs(
                selector={"app": "supabase-realtime"},
                ports=[ServicePortArgs(port=4000, target_port=4000, name="http")],
                type="ClusterIP",
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_storage(
        self,
        namespace: Namespace,
        secrets: Secret,
        pvc: PersistentVolumeClaim,
        postgrest: Deployment,
    ) -> Deployment:
        """Deploy Supabase Storage service with proper configuration."""
        component_labels = {
            **self.labels,
            "app.kubernetes.io/component": "storage",
            "app": "supabase-storage",
        }

        deployment = Deployment(
            "supabase-storage",
            metadata=ObjectMetaArgs(
                name="supabase-storage",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=DeploymentSpecArgs(
                replicas=1,
                selector=LabelSelectorArgs(match_labels={"app": "supabase-storage"}),
                template=PodTemplateSpecArgs(
                    metadata=ObjectMetaArgs(labels=component_labels),
                    spec=PodSpecArgs(
                        containers=[
                            ContainerArgs(
                                name="storage",
                                image=self.config["storage"]["image"],
                                env=[
                                    EnvVarArgs(
                                        name="ANON_KEY",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="anon-key",
                                            )
                                        ),
                                    ),
                                    EnvVarArgs(
                                        name="SERVICE_KEY",
                                        value_from=EnvVarSourceArgs(
                                            secret_key_ref=SecretKeySelectorArgs(
                                                name="supabase-secrets",
                                                key="service-key",
                                            )
                                        ),
                                    ),
                                    EnvVarArgs(
                                        name="POSTGREST_URL",
                                        value="http://supabase-postgrest-service:3000",
                                    ),
                                    EnvVarArgs(
                                        name="DATABASE_URL",
                                        value="postgresql://supabase_admin@supabase-postgres-service:5432/postgres",
                                    ),
                                    EnvVarArgs(
                                        name="FILE_STORAGE_BACKEND", value="file"
                                    ),
                                    EnvVarArgs(name="STORAGE_BACKEND", value="file"),
                                    EnvVarArgs(
                                        name="FILE_STORAGE_DIRECTORY",
                                        value="/var/lib/storage",
                                    ),
                                ],
                                ports=[
                                    ContainerPortArgs(container_port=5000, name="http")
                                ],
                                volume_mounts=[
                                    VolumeMountArgs(
                                        name="storage-data",
                                        mount_path="/var/lib/storage",
                                    )
                                ],
                                resources=ResourceRequirementsArgs(
                                    **self.config["storage"]["resources"]
                                ),
                                liveness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=5000),
                                    initial_delay_seconds=30,
                                    period_seconds=10,
                                ),
                                readiness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=5000),
                                    initial_delay_seconds=5,
                                    period_seconds=5,
                                ),
                            )
                        ],
                        volumes=[
                            VolumeArgs(
                                name="storage-data",
                                persistent_volume_claim={
                                    "claim_name": "supabase-storage-pvc"
                                },
                            )
                        ],
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, secrets, pvc, postgrest]
            ),
        )

        # Create service
        Service(
            "supabase-storage-service",
            metadata=ObjectMetaArgs(
                name="supabase-storage-service",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=ServiceSpecArgs(
                selector={"app": "supabase-storage"},
                ports=[ServicePortArgs(port=5000, target_port=5000, name="http")],
                type="ClusterIP",
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_kong_gateway(
        self, namespace: Namespace, config_map: ConfigMap, dependencies: list
    ) -> Deployment:
        """Deploy Kong Gateway as API gateway with proper configuration."""
        component_labels = {
            **self.labels,
            "app.kubernetes.io/component": "kong",
            "app": "supabase-kong",
        }

        deployment = Deployment(
            "supabase-kong",
            metadata=ObjectMetaArgs(
                name="supabase-kong",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=DeploymentSpecArgs(
                replicas=1,
                selector=LabelSelectorArgs(match_labels={"app": "supabase-kong"}),
                template=PodTemplateSpecArgs(
                    metadata=ObjectMetaArgs(labels=component_labels),
                    spec=PodSpecArgs(
                        containers=[
                            ContainerArgs(
                                name="kong",
                                image=self.config["kong"]["image"],
                                env=[
                                    EnvVarArgs(name="KONG_DATABASE", value="off"),
                                    EnvVarArgs(
                                        name="KONG_DECLARATIVE_CONFIG",
                                        value="/usr/local/kong/kong.yml",
                                    ),
                                    EnvVarArgs(
                                        name="KONG_DNS_ORDER", value="LAST,A,CNAME"
                                    ),
                                    EnvVarArgs(
                                        name="KONG_PLUGINS",
                                        value="request-id,kong-prometheus-plugin,cors",
                                    ),
                                    EnvVarArgs(
                                        name="KONG_NGINX_PROXY_PROXY_BUFFER_SIZE",
                                        value="160k",
                                    ),
                                    EnvVarArgs(
                                        name="KONG_NGINX_PROXY_PROXY_BUFFERS",
                                        value="64 160k",
                                    ),
                                    EnvVarArgs(name="KONG_LOG_LEVEL", value="info"),
                                ],
                                ports=[
                                    ContainerPortArgs(
                                        container_port=8000, name="proxy"
                                    ),
                                    ContainerPortArgs(
                                        container_port=8001, name="admin"
                                    ),
                                ],
                                resources=ResourceRequirementsArgs(
                                    **self.config["kong"]["resources"]
                                ),
                                liveness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=8000),
                                    initial_delay_seconds=30,
                                    period_seconds=10,
                                ),
                                readiness_probe=ProbeArgs(
                                    tcp_socket=TCPSocketActionArgs(port=8000),
                                    initial_delay_seconds=5,
                                    period_seconds=5,
                                ),
                            )
                        ]
                    ),
                ),
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider,
                depends_on=[namespace, config_map] + dependencies,
            ),
        )

        # Create service
        Service(
            "supabase-kong-service",
            metadata=ObjectMetaArgs(
                name="supabase-kong-service",
                namespace=self.namespace_name,
                labels=component_labels,
            ),
            spec=ServiceSpecArgs(
                selector={"app": "supabase-kong"},
                ports=[
                    ServicePortArgs(port=8000, target_port=8000, name="proxy"),
                    ServicePortArgs(port=8001, target_port=8001, name="admin"),
                ],
                type="ClusterIP",
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment


def main():
    """Main function to deploy Supabase infrastructure."""
    # Get kubeconfig path from environment or use default
    kubeconfig_path = Path(os.getenv("KUBECONFIG", "~/.kube/config")).expanduser()

    if not kubeconfig_path.exists():
        raise FileNotFoundError(f"Kubeconfig not found at {kubeconfig_path}")

    # Initialize and deploy Supabase infrastructure
    supabase = SupabaseInfrastructure(kubeconfig_path)
    stack = supabase.deploy_supabase_stack()

    # Export useful outputs
    pulumi.export("namespace", stack["namespace"].metadata.name)
    pulumi.export("postgres_service", "supabase-postgres-service")
    pulumi.export("api_gateway", "supabase-kong-service")
    pulumi.export("api_url", "http://supabase-kong-service:8000")


if __name__ == "__main__":
    main()
