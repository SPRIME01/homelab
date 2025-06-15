"""
Supabase infrastructure management with Pulumi for K3s cluster.
Follows homelab project patterns and best practices.
"""

from pathlib import Path
from typing import Any

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs
from pulumi_kubernetes.core.v1 import (
    ConfigMap,
    Namespace,
    PersistentVolumeClaim,
    PersistentVolumeClaimSpecArgs,
    Secret,
    Service,
    ServicePortArgs,
    ServiceSpecArgs,
    VolumeResourceRequirementsArgs,
)
from pulumi_kubernetes.meta.v1 import LabelSelectorArgs


class SupabaseInfrastructure:
    """Supabase infrastructure management with Pulumi."""

    def __init__(self, kubeconfig_path: Path) -> None:
        self.provider = k8s.Provider("k3s-provider", kubeconfig=str(kubeconfig_path))
        self.namespace_name = "supabase"

    def deploy_supabase_stack(self) -> dict[str, Any]:
        """Deploy complete Supabase stack to K3s cluster."""
        # Create namespace
        namespace = self._create_namespace()

        # Create secrets and configmaps
        secrets = self._create_secrets(namespace)
        config_map = self._create_config_map(namespace)

        # Create persistent storage
        postgres_pvc = self._create_postgres_storage(namespace)
        storage_pvc = self._create_storage_pvc(namespace)

        # Deploy core services
        postgres = self._deploy_postgres(namespace, secrets, postgres_pvc)
        postgrest = self._deploy_postgrest(namespace, secrets, config_map)
        gotrue = self._deploy_gotrue(namespace, secrets, config_map)
        realtime = self._deploy_realtime(namespace, secrets, config_map)
        storage = self._deploy_storage(namespace, secrets, storage_pvc)
        kong = self._deploy_kong_gateway(namespace, config_map)

        return {
            "namespace": namespace,
            "postgres": postgres,
            "postgrest": postgrest,
            "gotrue": gotrue,
            "realtime": realtime,
            "storage": storage,
            "kong": kong,
        }

    def _create_namespace(self) -> Namespace:
        """Create Supabase namespace."""
        return Namespace(
            "supabase-namespace",
            metadata={"name": self.namespace_name},
            opts=pulumi.ResourceOptions(provider=self.provider),
        )

    def _create_secrets(self, namespace: Namespace) -> Secret:
        """Create Supabase secrets."""
        return Secret(
            "supabase-secrets",
            metadata={"name": "supabase-secrets", "namespace": self.namespace_name},
            string_data={
                "postgres-password": "your-secure-postgres-password",
                "jwt-secret": "your-jwt-secret-key-here",
                "anon-key": "your-anon-key-here",
                "service-key": "your-service-key-here",
                "dashboard-username": "supabase",
                "dashboard-password": "supabase-dashboard-password",
            },
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _create_config_map(self, namespace: Namespace) -> ConfigMap:
        """Create Supabase configuration."""
        return ConfigMap(
            "supabase-config",
            metadata={"name": "supabase-config", "namespace": self.namespace_name},
            data={
                "postgres-host": "supabase-postgres-service",
                "postgres-port": "5432",
                "postgres-db": "postgres",
                "postgres-user": "supabase_admin",
                "api-url": "http://supabase-kong-service:8000",
                "studio-port": "3000",
            },
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _create_postgres_storage(self, namespace: Namespace) -> PersistentVolumeClaim:
        """Create PostgreSQL persistent volume claim."""
        return PersistentVolumeClaim(
            "supabase-postgres-pvc",
            metadata={
                "name": "supabase-postgres-pvc",
                "namespace": self.namespace_name,
            },
            spec=Persistentimplment
            VolumeClaimSpecArgs(
                access_modes=["ReadWriteOnce"],
                resources=VolumeResourceRequirementsArgs(
                    requests={"storage": "10Gi"}
                ),
            ),
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _create_storage_pvc(self, namespace: Namespace) -> PersistentVolumeClaim:
        """Create storage service persistent volume claim."""
        return PersistentVolumeClaim(
            "supabase-storage-pvc",
            metadata={
                "name": "supabase-storage-pvc",
                "namespace": self.namespace_name,
            },
            spec=PersistentVolumeClaimSpecArgs(
                access_modes=["ReadWriteOnce"],
                resources=VolumeResourceRequirementsArgs(
                    requests={"storage": "20Gi"}
                ),
            ),
            opts=pulumi.ResourceOptions(provider=self.provider, depends_on=[namespace]),
        )

    def _deploy_postgres(
        self, namespace: Namespace, secrets: Secret, pvc: PersistentVolumeClaim
    ) -> Deployment:
        """Deploy Supabase PostgreSQL with extensions."""
        deployment = Deployment(
            "supabase-postgres",
            metadata={"name": "supabase-postgres", "namespace": self.namespace_name},
            spec=DeploymentSpecArgs(
                selector=LabelSelectorArgs(match_labels={"app": "supabase-postgres"}),
                selector={"matchLabels": {"app": "supabase-postgres"}},
                template={
                    "metadata": {"labels": {"app": "supabase-postgres"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "postgres",
                                "image": "supabase/postgres:15.1.0.147",
                                "env": [
                                    {"name": "POSTGRES_DB", "value": "postgres"},
                                    {
                                        "name": "POSTGRES_USER",
                                        "value": "supabase_admin",
                                    },
                                    {
                                        "name": "POSTGRES_PASSWORD",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "supabase-secrets",
                                                "key": "postgres-password",
                                            }
                                        },
                                    },
                                    {
                                        "name": "JWT_SECRET",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "supabase-secrets",
                                                "key": "jwt-secret",
                                            }
                                        },
                                    },
                                ],
                                "ports": [{"containerPort": 5432}],
                                "volumeMounts": [
                                    {
                                        "name": "postgres-storage",
                                        "mountPath": "/var/lib/postgresql/data",
                                    }
                                ],
                                "resources": {
                                    "requests": {"memory": "256Mi", "cpu": "250m"},
                                    "limits": {"memory": "1Gi", "cpu": "500m"},
                                },
                            }
                        ],
                        "volumes": [
                            {
                                "name": "postgres-storage",
                                "persistentVolumeClaim": {
                                    "claimName": "supabase-postgres-pvc"
                                },
                            }
                        ],
                    },
                },
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, secrets, pvc]
            ),
        )

        # Create service for PostgreSQL
        Service(
            "supabase-postgres-service",
            metadata={
                "name": "supabase-postgres-service",
                "namespace": self.namespace_name,
            },
            spec=ServiceSpecArgs(
                selector={"app": "supabase-postgres"},
                ports=[ServicePortArgs(port=5432, target_port=5432, name="postgres")],
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_postgrest(
        self, namespace: Namespace, secrets: Secret, config_map: ConfigMap
    ) -> Deployment:
        """Deploy PostgREST API service."""
        deployment = Deployment(
            "supabase-postgrest",
            metadata={"name": "supabase-postgrest", "namespace": self.namespace_name},
            spec=DeploymentSpecArgs(
                selector=LabelSelectorArgs(match_labels={"app": "supabase-postgrest"}),
                template={
                    "metadata": {"labels": {"app": "supabase-postgrest"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "postgrest",
                                "image": "postgrest/postgrest:v11.2.0",
                                "env": [
                                    {
                                        "name": "PGRST_DB_URI",
                                        "value": "postgresql://supabase_admin@supabase-postgres-service:5432/postgres",
                                    },
                                    {"name": "PGRST_DB_SCHEMAS", "value": "public"},
                                    {"name": "PGRST_DB_ANON_ROLE", "value": "anon"},
                                    {
                                        "name": "PGRST_JWT_SECRET",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "supabase-secrets",
                                                "key": "jwt-secret",
                                            }
                                        },
                                    },
                                ],
                                "ports": [{"containerPort": 3000}],
                                "resources": {
                                    "requests": {"memory": "128Mi", "cpu": "100m"},
                                    "limits": {"memory": "256Mi", "cpu": "200m"},
                                },
                            }
                        ]
                    },
                },
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, secrets, config_map]
            ),
        )

        # Create service
        Service(
            "supabase-postgrest-service",
            metadata={
                "name": "supabase-postgrest-service",
                "namespace": self.namespace_name,
            },
            spec=ServiceSpecArgs(
                selector={"app": "supabase-postgrest"},
                ports=[ServicePortArgs(port=3000, target_port=3000, name="postgrest")],
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_gotrue(
        self, namespace: Namespace, secrets: Secret, config_map: ConfigMap
    ) -> Deployment:
        """Deploy GoTrue authentication service."""
        deployment = Deployment(
            "supabase-gotrue",
            metadata={"name": "supabase-gotrue", "namespace": self.namespace_name},
            spec=DeploymentSpecArgs(
                selector=LabelSelectorArgs(match_labels={"app": "supabase-gotrue"}),
                selector={"matchLabels": {"app": "supabase-gotrue"}},
                template={
                    "metadata": {"labels": {"app": "supabase-gotrue"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "gotrue",
                                "image": "supabase/gotrue:v2.132.3",
                                "env": [
                                    {"name": "GOTRUE_API_HOST", "value": "0.0.0.0"},
                                    {"name": "GOTRUE_API_PORT", "value": "9999"},
                                    {"name": "GOTRUE_DB_DRIVER", "value": "postgres"},
                                    {
                                        "name": "GOTRUE_DB_DATABASE_URL",
                                        "value": "postgresql://supabase_admin@supabase-postgres-service:5432/postgres",
                                    },
                                    {
                                        "name": "GOTRUE_JWT_SECRET",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "supabase-secrets",
                                                "key": "jwt-secret",
                                            }
                                        },
                                    },
                                ],
                                "ports": [{"containerPort": 9999}],
                                "resources": {
                                    "requests": {"memory": "128Mi", "cpu": "100m"},
                                    "limits": {"memory": "256Mi", "cpu": "200m"},
                                },
                            }
                        ]
                    },
                },
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, secrets, config_map]
            ),
        )

        # Create service
        Service(
            "supabase-gotrue-service",
            metadata={
                "name": "supabase-gotrue-service",
                "namespace": self.namespace_name,
            },
            spec=ServiceSpecArgs(
                selector={"app": "supabase-gotrue"},
                ports=[ServicePortArgs(port=9999, target_port=9999, name="gotrue")],
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_realtime(
        self, namespace: Namespace, secrets: Secret, config_map: ConfigMap
    ) -> Deployment:
        """Deploy Supabase Realtime service."""
        deployment = Deployment(
            "supabase-realtime",
            metadata={"name": "supabase-realtime", "namespace": self.namespace_name},
            spec=DeploymentSpecArgs(
                selector=LabelSelectorArgs(match_labels={"app": "supabase-realtime"}),
                selector={"matchLabels": {"app": "supabase-realtime"}},
                template={
                    "metadata": {"labels": {"app": "supabase-realtime"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "realtime",
                                "image": "supabase/realtime:v2.25.50",
                                "env": [
                                    {"name": "PORT", "value": "4000"},
                                    {
                                        "name": "DB_HOST",
                                        "value": "supabase-postgres-service",
                                    },
                                    {"name": "DB_PORT", "value": "5432"},
                                    {"name": "DB_NAME", "value": "postgres"},
                                    {"name": "DB_USER", "value": "supabase_admin"},
                                    {
                                        "name": "JWT_SECRET",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "supabase-secrets",
                                                "key": "jwt-secret",
                                            }
                                        },
                                    },
                                ],
                                "ports": [{"containerPort": 4000}],
                                "resources": {
                                    "requests": {"memory": "128Mi", "cpu": "100m"},
                                    "limits": {"memory": "256Mi", "cpu": "200m"},
                                },
                            }
                        ]
                    },
                },
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, secrets, config_map]
            ),
        )

        # Create service
        Service(
            "supabase-realtime-service",
            metadata={
                "name": "supabase-realtime-service",
                "namespace": self.namespace_name,
            },
            spec=ServiceSpecArgs(
                selector={"app": "supabase-realtime"},
                ports=[ServicePortArgs(port=4000, target_port=4000, name="realtime")],
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_storage(
        self, namespace: Namespace, secrets: Secret, pvc: PersistentVolumeClaim
    ) -> Deployment:
        """Deploy Supabase Storage service."""
        deployment = Deployment(
            "supabase-storage",
            metadata={"name": "supabase-storage", "namespace": self.namespace_name},
            spec=DeploymentSpecArgs(
                selector=LabelSelectorArgs(match_labels={"app": "supabase-storage"}),
                selector={"matchLabels": {"app": "supabase-storage"}},
                template={
                    "metadata": {"labels": {"app": "supabase-storage"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "storage",
                                "image": "supabase/storage-api:v0.43.11",
                                "env": [
                                    {
                                        "name": "ANON_KEY",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "supabase-secrets",
                                                "key": "anon-key",
                                            }
                                        },
                                    },
                                    {
                                        "name": "SERVICE_KEY",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "supabase-secrets",
                                                "key": "service-key",
                                            }
                                        },
                                    },
                                    {
                                        "name": "POSTGREST_URL",
                                        "value": "http://supabase-postgrest-service:3000",
                                    },
                                    {
                                        "name": "DATABASE_URL",
                                        "value": "postgresql://supabase_admin@supabase-postgres-service:5432/postgres",
                                    },
                                ],
                                "ports": [{"containerPort": 5000}],
                                "volumeMounts": [
                                    {
                                        "name": "storage-data",
                                        "mountPath": "/var/lib/storage",
                                    }
                                ],
                                "resources": {
                                    "requests": {"memory": "128Mi", "cpu": "100m"},
                                    "limits": {"memory": "512Mi", "cpu": "300m"},
                                },
                            }
                        ],
                        "volumes": [
                            {
                                "name": "storage-data",
                                "persistentVolumeClaim": {
                                    "claimName": "supabase-storage-pvc"
                                },
                            }
                        ],
                    },
                },
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, secrets, pvc]
            ),
        )

        # Create service
        Service(
            "supabase-storage-service",
            metadata={
                "name": "supabase-storage-service",
                "namespace": self.namespace_name,
            },
            spec=ServiceSpecArgs(
                selector={"app": "supabase-storage"},
                ports=[ServicePortArgs(port=5000, target_port=5000, name="storage")],
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment

    def _deploy_kong_gateway(
        self, namespace: Namespace, config_map: ConfigMap
    ) -> Deployment:
        """Deploy Kong Gateway for API routing."""
        deployment = Deployment(
            "supabase-kong",
            metadata={"name": "supabase-kong", "namespace": self.namespace_name},
            spec=DeploymentSpecArgs(
                selector=LabelSelectorArgs(match_labels={"app": "supabase-kong"}),
                selector={"matchLabels": {"app": "supabase-kong"}},
                template={
                    "metadata": {"labels": {"app": "supabase-kong"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "kong",
                                "image": "kong:3.4",
                                "env": [
                                    {"name": "KONG_DATABASE", "value": "off"},
                                    {
                                        "name": "KONG_DECLARATIVE_CONFIG",
                                        "value": "/usr/local/kong/kong.yml",
                                    },
                                    {"name": "KONG_DNS_ORDER", "value": "LAST,A,CNAME"},
                                    {
                                        "name": "KONG_PLUGINS",
                                        "value": "request-id,kong-prometheus-plugin,cors",
                                    },
                                    {
                                        "name": "KONG_NGINX_PROXY_PROXY_BUFFER_SIZE",
                                        "value": "160k",
                                    },
                                    {
                                        "name": "KONG_NGINX_PROXY_PROXY_BUFFERS",
                                        "value": "64 160k",
                                    },
                                ],
                                "ports": [
                                    {"containerPort": 8000},
                                    {"containerPort": 8001},
                                ],
                                "resources": {
                                    "requests": {"memory": "256Mi", "cpu": "200m"},
                                    "limits": {"memory": "512Mi", "cpu": "400m"},
                                },
                            }
                        ]
                    },
                },
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[namespace, config_map]
            ),
        )

        # Create service
        Service(
            "supabase-kong-service",
            metadata={
                "name": "supabase-kong-service",
                "namespace": self.namespace_name,
            },
            spec=ServiceSpecArgs(
                selector={"app": "supabase-kong"},
                ports=[
                    ServicePortArgs(port=8000, target_port=8000, name="kong-proxy"),
                    ServicePortArgs(port=8001, target_port=8001, name="kong-admin"),
                ],
            ),
            opts=pulumi.ResourceOptions(
                provider=self.provider, depends_on=[deployment]
            ),
        )

        return deployment
