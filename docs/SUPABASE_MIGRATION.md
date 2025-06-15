# Supabase Migration Guide

This guide explains how to migrate from PostgreSQL to Supabase in your K3s homelab environment.

## Overview

The Supabase migration implementation provides:

- **Complete Supabase stack deployment** - PostgreSQL, PostgREST, GoTrue (Auth), Realtime, Storage, Kong Gateway
- **Automated migration from existing PostgreSQL** - Data and schema migration with rollback capabilities
- **Health monitoring and diagnostics** - Comprehensive health checks for all Supabase components
- **Performance optimization** - Tuned configurations for K3s environment

## Prerequisites

1. **K3s cluster running** with kubeconfig properly configured
2. **UV package manager** installed and environment set up
3. **Sufficient resources** - At least 4GB RAM and 30GB storage available
4. **Network connectivity** between cluster nodes

## Quick Start

### 1. Deploy Supabase Stack

```bash
# Deploy complete Supabase infrastructure
make supabase-deploy
```

### 2. Migrate from Existing PostgreSQL (Optional)

```bash
# Run migration from existing PostgreSQL to Supabase
make supabase-migrate
```

### 3. Check Health Status

```bash
# Check all Supabase components
make supabase-health

# Continuous monitoring
make supabase-monitor
```

## Detailed Migration Process

### Step 1: Pre-Migration Backup

The migration process automatically creates backups:

```bash
# Manual backup (optional)
make supabase-backup
```

### Step 2: Infrastructure Deployment

The Supabase stack includes:

- **PostgreSQL Database** - Primary data storage with Supabase extensions
- **PostgREST API** - RESTful API layer for database access
- **GoTrue Auth Service** - Authentication and user management
- **Realtime Service** - Real-time subscriptions and updates
- **Storage Service** - File storage and management
- **Kong Gateway** - API gateway and routing

### Step 3: Data Migration

Configuration options (set via environment variables):

```bash
# Source PostgreSQL configuration
export OLD_POSTGRES_HOST="postgres-service.default.svc.cluster.local"
export OLD_POSTGRES_PORT="5432"
export OLD_POSTGRES_DB="homelab"
export OLD_POSTGRES_USER="postgres"
export OLD_POSTGRES_PASSWORD="your-password"

# Target Supabase configuration
export SUPABASE_HOST="supabase-postgres-service.supabase.svc.cluster.local"
export SUPABASE_PORT="5432"
export SUPABASE_DB="postgres"
export SUPABASE_USER="supabase_admin"
export SUPABASE_PASSWORD="your-secure-password"

# Backup location
export BACKUP_PATH="/tmp/postgres_backups"
```

### Step 4: Application Configuration Updates

The migration automatically updates application configurations to use Supabase endpoints.

## Access Information

Once deployed, access Supabase services:

### API Gateway (Kong)

```bash
kubectl port-forward -n supabase svc/supabase-kong-service 8000:8000
```

- API Gateway: <http://localhost:8000>

### Direct Service Access

```bash
# PostgreSQL Database
kubectl port-forward -n supabase svc/supabase-postgres-service 5432:5432

# PostgREST API
kubectl port-forward -n supabase svc/supabase-postgrest-service 3000:3000

# Auth Service (GoTrue)
kubectl port-forward -n supabase svc/supabase-gotrue-service 9999:9999

# Realtime Service
kubectl port-forward -n supabase svc/supabase-realtime-service 4000:4000

# Storage Service
kubectl port-forward -n supabase svc/supabase-storage-service 5000:5000
```

## Configuration Management

### Secrets Management

Supabase secrets are stored in Kubernetes secrets:

```bash
# View secrets (encoded)
kubectl get secret supabase-secrets -n supabase -o yaml

# Update secrets
kubectl patch secret supabase-secrets -n supabase -p='{"stringData":{"postgres-password":"new-password"}}'
```

### Configuration Updates

Application configuration is managed via ConfigMaps:

```bash
# View configuration
kubectl get configmap supabase-config -n supabase -o yaml

# Update configuration
kubectl patch configmap supabase-config -n supabase -p='{"data":{"postgres-host":"new-host"}}'
```

## Performance Optimization

The performance optimizer includes Supabase-specific recommendations:

```bash
# Run performance analysis
make optimize
```

Optimizations include:

- **Connection pooling** for PostgREST
- **PostgreSQL tuning** for memory and cache settings
- **Resource limits** for all services
- **Storage optimization** for file operations

## Monitoring and Health Checks

### Health Check Components

- **Pod Status** - Kubernetes pod health and readiness
- **Service Connectivity** - Network connectivity between services
- **Database Connectivity** - PostgreSQL connection and query tests
- **API Endpoint Health** - HTTP health endpoints where available

### Continuous Monitoring

```bash
# Start continuous monitoring (every 5 minutes)
make supabase-monitor
```

### Manual Diagnostics

```bash
# Check pod status
kubectl get pods -n supabase

# Check logs
kubectl logs -n supabase deployment/supabase-postgres
kubectl logs -n supabase deployment/supabase-postgrest
kubectl logs -n supabase deployment/supabase-gotrue

# Check events
kubectl get events -n supabase --sort-by='.lastTimestamp'

# Resource usage
kubectl top pods -n supabase
```

## Troubleshooting

### Common Issues

#### 1. Pod Start Failures

```bash
# Check resource availability
kubectl top nodes
kubectl describe pod -n supabase <pod-name>

# Check storage
kubectl get pv,pvc -n supabase
```

#### 2. Service Connectivity Issues

```bash
# Test service discovery
kubectl exec -n supabase deployment/supabase-postgrest -- nslookup supabase-postgres-service

# Check service endpoints
kubectl get endpoints -n supabase
```

#### 3. Database Connection Problems

```bash
# Test database connectivity
kubectl exec -n supabase deployment/supabase-postgres -- pg_isready -U supabase_admin

# Check database logs
kubectl logs -n supabase deployment/supabase-postgres
```

### Recovery Procedures

#### Rollback Migration

```bash
# Stop Supabase services
kubectl scale deployment --replicas=0 -n supabase --all

# Restore original PostgreSQL (manual process)
# Redeploy original PostgreSQL configuration
```

#### Restart Services

```bash
# Restart all Supabase deployments
kubectl rollout restart deployment -n supabase

# Restart specific service
kubectl rollout restart deployment/supabase-postgres -n supabase
```

## Integration with Homelab Applications

### Connection Strings

Applications should use these connection patterns:

```bash
# PostgreSQL Direct
postgresql://supabase_admin:password@supabase-postgres-service.supabase.svc.cluster.local:5432/postgres

# PostgREST API
http://supabase-postgrest-service.supabase.svc.cluster.local:3000

# Auth API
http://supabase-gotrue-service.supabase.svc.cluster.local:9999

# Storage API
http://supabase-storage-service.supabase.svc.cluster.local:5000

# Realtime
ws://supabase-realtime-service.supabase.svc.cluster.local:4000/socket
```

### Environment Variables

Set these in your application deployments:

```yaml
env:
  - name: DATABASE_URL
    value: "postgresql://supabase_admin:password@supabase-postgres-service.supabase.svc.cluster.local:5432/postgres"
  - name: SUPABASE_URL
    value: "http://supabase-kong-service.supabase.svc.cluster.local:8000"
  - name: SUPABASE_ANON_KEY
    valueFrom:
      secretKeyRef:
        name: supabase-secrets
        key: anon-key
```

## Best Practices

1. **Security**
   - Change default passwords before production use
   - Use Kubernetes secrets for sensitive data
   - Enable network policies for service isolation
   - Regular security updates

2. **Performance**
   - Monitor resource usage regularly
   - Tune PostgreSQL settings for your workload
   - Use connection pooling for high-traffic applications
   - Implement proper indexing strategies

3. **Backup and Recovery**
   - Schedule regular backups
   - Test restore procedures
   - Monitor backup integrity
   - Maintain multiple backup retention periods

4. **Monitoring**
   - Set up alerts for service failures
   - Monitor resource utilization
   - Track API response times
   - Log analysis for troubleshooting

## Advanced Configuration

### Custom PostgreSQL Configuration

```bash
# Create custom PostgreSQL config
kubectl create configmap postgres-config -n supabase \
  --from-literal=postgresql.conf="max_connections = 200
shared_buffers = 512MB
effective_cache_size = 2GB"

# Update deployment to use custom config
kubectl patch deployment supabase-postgres -n supabase -p='...'
```

### SSL/TLS Configuration

```bash
# Create TLS certificates
kubectl create secret tls supabase-tls -n supabase \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key

# Update Kong gateway for HTTPS
kubectl patch deployment supabase-kong -n supabase -p='...'
```

This comprehensive Supabase integration provides a robust, scalable database solution for your K3s homelab while maintaining the project's high standards for automation, monitoring, and best practices.
