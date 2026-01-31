# Homelab AI Infrastructure System Design

**Document Type**: System Design Specification / Implementation Roadmap
**Primary Audience**: AI Agent Implementers
**Status**: Ready for Implementation
**Last Updated**: 2025-01-31

---

## 1. Executive Summary

### Problem Statement

A unified platform is needed for container orchestration, document ingestion, vector search, and AI inference across a distributed homelab environment. Current solutions either require cloud dependencies, lack hardware awareness, or tightly couple components making future changes expensive.

### Solution

A distributed **AI-native homelab platform** spanning three compute zones connected via Tailscale tailnet:

| Zone | Hardware | Role |
|------|----------|------|
| **Desktop** | 32GB RAM, k3s (Rancher Desktop) | Control plane + orchestration hub |
| **HA Yellow** | Home Assistant Yellow | Time-series telemetry storage |
| **Jetson AGX Orin** | NVIDIA GPU | AI/ML inference compute |

### Architecture Philosophy

**Event-driven architecture** with NATS/JetStream as the messaging fabric and Garage for durable object storage. All services run as Kubernetes workloads on k3s, communicating exclusively through well-defined interfaces.

**Loose coupling via Ports & Adapters**: Every component implements dependency injection and port-based interfaces. Swap Garage for MinIO? Replace Cognee with a custom KG worker? Change LiteLLM to a different proxy? All possible without touching core business logic.

**Hardware-aware design**: Ansible-based hardware auditing detects CPU, RAM, GPU, storage IOPS, and network characteristics to auto-tune resource allocations for optimal performance on each machine.

### Trust Boundary

**Tailscale tailnet is the security perimeter**. All services are ClusterIP-only within the tailnet. No public exposure. SOPS+Age encrypts secrets. HOMELAB guard pattern prevents accidental execution on non-control-plane machines.

### Technology Choices

Preference for **Rust-based components** where available (Oxigraph, LiteLLM proxy) for performance and memory safety. Integrated with existing Nx + Pulumi + Ansible workflow from this repository.

**Core stack**: NATS+JetStream, Garage (S3-compatible), Supabase Postgres+pgvector, Oxigraph, LiteLLM proxy, Docling, Cognee/KG pipeline, llama.cpp/GLM-4.7-Flash, Promptfoo, MCP Context Forge, OpenClaw.

### Implementation Model

**Single-session implementation for AI agents**. Complete Pulumi infrastructure-as-code, Ansible provisioning playbooks, integration tests. No stubs, no TODOs, no technical debt.

### Success Criteria

Implementation is complete when:
- End-to-end integration tests pass
- A document can be ingested, chunked, embedded, and stored in vector DB
- Semantic search retrieves relevant results
- Knowledge graph queries return structured triples
- All `just` recipes work idempotently

### Risks & Constraints

| Risk | Mitigation |
|------|------------|
| **32GB desktop memory limit** | Hardware-aware tuning, burst workload scaling, Postgres memory limits, JetStream retention capping |
| **Jetson unconfigured** | Phase 3 defers Jetson setup; can validate core infrastructure first |
| **Component complexity** | Four-phase rollout with validation gates between phases |
| **Single-session execution scope** | Document is complete specification; AI agent can implement linearly |

### Operational Model

Everything managed via `just` recipes. Pulumi stacks for k3s resources. Ansible playbooks for system provisioning. Idempotent, auditable, reversible.

## 2. Architecture Overview

### 2.1 System Diagram

```mermaid
graph TB
    subgraph "Foundation Tooling"
        DEVBOX[devbox]
        MISE[mise]
        CHEZMOI[chezmoi]
        DIRENV[direnv]
        JUST[just]
        UV[uv]
        NX[Nx + nx-pulumi]
    end

    subgraph "Home Assistant Yellow"
        HA[Home Assistant]
        TSDB[(TimescaleDB<br/>Time-Series)]
        HA --> TSDB
        TSDB -->|telemetry.events| NATS
    end

    subgraph "Tailscale Tailnet"
        TAILNET[Trust Boundary]
    end

    subgraph "Desktop k3s Cluster"
        NATS[NATS + JetStream<br/>Messaging Fabric]

        subgraph "Storage Layer"
            GARAGE[Garage<br/>S3 Object Store]
            SUPA[(Supabase Postgres<br/>+ pgvector)]
            OXIGRAPH[(Oxigraph<br/>RDF Graph)]
        end

        subgraph "Ingestion Pipeline"
            DOCLING[Docling Workers<br/>Document Extraction]
            COGNEE[Cognee/KG Workers<br/>Chunk + Embed]
        end

        subgraph "Inference Layer"
            LITELLM[LiteLLM Proxy<br/>OpenAI-Compatible]
        end

        subgraph "Observability"
            OO[OpenObserve<br/>Logs + Metrics]
            OTEL[OpenTelemetry<br/>Traces]
            LOGFIRE[Logfire SDK<br/>Tracing]
        end

        DOCLING --> GARAGE
        DOCLING --> NATS
        COGNEE --> SUPA
        COGNEE --> OXIGRAPH
        LITELLM --> SUPA
        LITELLM --> OXIGRAPH
    end

    subgraph "NVIDIA Jetson AGX Orin"
        GLM[GLM-4.7-Flash<br/>llama.cpp]
    end

    subgraph "Client Layer"
        OPENCLAW[OpenClaw<br/>Agent Client]
        MCP[MCP Context Forge<br/>Tool Server]
        PROMPTFOO[Promptfoo<br/>Eval Framework]
    end

    TAILNET --- NATS
    TAILNET --- LITELLM
    TAILNET --- OLLAMA
    TAILNET --- OPENCLAW
    TAILNET --- MCP

    LITELLM -.->|embeddings| OLLAMA
    LITELLM -.->|completions| OLLAMA

    OO -.->|collects| DOCLING
    OO -.->|collects| COGNEE
    OO -.->|collects| LITELLM
    OTEL -.->|traces| LOGFIRE

    DEVBOX --> NX
    MISE --> NX
    JUST --> NX

    NX -->|provisions| k3s
    ANSIBLE[Ansible] -->|provisions| TSDB
    ANSIBLE -->|provisions| OLLAMA

    style TAILNET fill:#ff9900,stroke:#cc7a00,color:#fff
    style NATS fill:#00c853,stroke:#009624,color:#fff
    style OO fill:#1565c0,stroke:#0d47a1,color:#fff
```

**Key Architectural Decisions**:
| Decision | Rationale |
|----------|-----------|
| **Tailscale as trust boundary** | All inter-machine communication encrypted and authenticated; no public exposure |
| **NATS/JetStream as fabric** | Lightweight, performant message bus with built-in durability and streaming |
| **Mermaid for diagrams** | Human-readable, version-controllable, renders in GitHub/markdown viewers |
| **OpenObserve + oTel + Logfire** | Vendor-neutral observability; Logfire SDK for structured tracing without proprietary lock-in |
| **Nx + nx-pulumi** | Monorepo-scale infrastructure as code; type-safe resource definitions |
| **Devbox + mise + chezmoi + direnv** | Reproducible dev environments; declarative dotfiles; automatic env loading |

### 2.2 Component Taxonomy (by Layer)

#### Foundation Layer
| Component | Purpose | Language |
|-----------|---------|----------|
| **devbox** | Reproducible shell environments (Python 3.13.9) | Shell |
| **mise** | Tool version pinning (bun, python, pulumi, nx) | Rust |
| **chezmoi** | Declarative dotfile management | Go |
| **direnv** | Per-directory environment loading (HOMELAB auto-detect) | Shell |
| **just** | Command runner with recipes (61 recipes) | Rust |
| **uv** | Fast Python package management | Rust |
| **Nx** | Monorepo orchestration, caching, distributed execution | TypeScript |
| **nx-pulumi** | Pulumi integration with Nx workspace | TypeScript |

#### Provisioning Layer
| Component | Purpose | Language |
|-----------|---------|----------|
| **Ansible** | System-level provisioning, hardware audit, Jetson setup | Python |

#### Observability Layer
| Component | Purpose | Language |
|-----------|---------|----------|
| **OpenObserve** | Logs, metrics, dashboards (self-hosted alternative to Datadog) | Rust |
| **OpenTelemetry** | Standardized telemetry collection | Go/Python |
| **Logfire SDK** | Structured tracing (non-proprietary SDK only) | Python |

#### Underlay Layer
| Component | Purpose | Language |
|-----------|---------|----------|
| **k3s / Rancher Desktop** | Kubernetes cluster on desktop | Go |
| **Tailscale** | Tailnet (zero-config VPN, mesh networking) | Go |

#### Storage Layer
| Component | Purpose | Language | Zone |
|-----------|---------|----------|------|
| **Garage** | S3-compatible object store (raw docs, artifacts) | Rust | Desktop k3s |
| **Supabase Postgres + pgvector** | Relational + vector embeddings | C/PLpgSQL | Desktop k3s |
| **Oxigraph** | RDF knowledge graph (SPARQL) | Rust | Desktop k3s |
| **TimescaleDB** | Time-series telemetry | C | HA Yellow |

#### Messaging Layer
| Component | Purpose | Language | Zone |
|-----------|---------|----------|------|
| **NATS + JetStream** | Event bus, work queues, durable streams | Go | Desktop k3s |

#### Ingestion Layer
| Component | Purpose | Language | Zone |
|-----------|---------|----------|------|
| **Docling** | PDF/document extraction, parsing | Rust | Desktop k3s |
| **Cognee / KG Workers** | Chunking, embeddings, knowledge graph | Python | Desktop k3s |

#### Inference Layer
| Component | Purpose | Language | Zone |
|-----------|---------|----------|------|
| **LiteLLM Proxy** | OpenAI-compatible API gateway | Python | Desktop k3s |
| **llama.cpp** | GLM-4.7-Flash inference (agentic coding + OpenClaw) | C++ | Jetson |

#### Query Layer
| Component | Purpose | Interface |
|-----------|---------|-----------|
| **Semantic Search** | Vector similarity search | Supabase/pgvector |
| **Graph Queries** | Knowledge graph traversal | Oxigraph SPARQL |

#### Client Layer
| Component | Purpose | Language |
|-----------|---------|----------|
| **OpenClaw** | Agent client for tool execution | Rust |
| **MCP Context Forge** | Model Context Protocol tool server | Python |
| **Promptfoo** | LLM eval framework (CLI + k8s Job) | TypeScript |

### 2.3 Data Flow

#### Flow 1: Home Assistant Telemetry → Analytics

```
┌─────────────┐      ┌──────────────┐      ┌─────────┐      ┌─────────────┐
│ Home        │─────▶│ TimescaleDB  │─────▶│ NATS    │─────▶│ Consumers   │
│ Assistant   │store │ (HA Yellow)  │pub   │ JetStream│sub   │ (analytics) │
│ Automation  │      │              │      │         │      │             │
└─────────────┘      └──────────────┘      └─────────┘      └─────────────┘
                           │                        │
                           │                        │
                           └──telemetry.* subjects──┘
```

**Sequence**:
1. Home Assistant automation fires → writes to TimescaleDB on HA Yellow
2. TimescaleDB (or bridge service) publishes to `telemetry.ha.{entity_id}` via NATS
3. Downstream consumers subscribe for analytics, monitoring, alerting
4. OpenObserve ingests for dashboards

**Error handling**:
- TimescaleDB unavailable: HA buffers in memory (default queue) with backpressure
- NATS unavailable: Events remain in TimescaleDB; replay on reconnect
- Consumer lag: JetStream retains for 24h (configurable); slow consumers catch up on restart

#### Flow 2: Document Ingestion Pipeline

```
┌──────────┐   ┌─────────┐   ┌──────────┐   ┌────────┐   ┌─────────┐
│ Upload   │──▶│ Garage  │──▶│ NATS     │──▶│ Docling│──▶│ Garage  │
│ Document │   │ raw/    │   │ ingest.  │   │Worker  │   │processed│
└──────────┘   └─────────┘   │ requested│   └────────┘   └─────────┘
                                 │                            │
                                 │          ┌─────────┐       │
                                 └─────────▶| Chunker │◀──────┘
                                            │(Cognee) │
                                            └─────────┘
                                                 │
                                                 ▼
┌──────────┐   ┌─────────┐   ┌────────┐   ┌─────────┐   ┌─────────┐
│ Query    │◀─│ LiteLLM │◀─│ Supa   │◀─│ Embedder│◀─│ NATS     │
│ Results  │   │ Proxy   │   │ bse    │   │(via     │   │chunked  │
└──────────┘   └─────────┘   │ pgvector│   │llama.cpp)│   └─────────┘
                             └─────────┘   └─────────┘         │
                                   │                           │
                                   ▼                           ▼
                             ┌─────────┐   ┌──────────┐   ┌─────────┐
                             │ KG      │◀─│ embed    │◀─│ NATS     │
                             │ Worker  │   │completed │   │completed │
                             └─────────┘   └──────────┘   └─────────┘
                                   │
                                   ▼
                             ┌─────────┐
                             │ Oxigraph│
                             │ triples │
                             └─────────┘
```

**NATS Subject Schema**:

| Subject | Payload | Purpose |
|---------|---------|---------|
| `doc.ingest.requested` | `{source_uri, metadata}` | Trigger document ingestion |
| `doc.ingest.extracted` | `{garage_key, structure}` | Docling completed extraction |
| `doc.chunked` | `{chunks[], doc_id}` | Document ready for embedding |
| `embed.requested` | `{chunk_id, text}` | Request embedding generation |
| `embed.completed` | `{chunk_id, vector}` | Embedding stored in pgvector |
| `kg.upsert.requested` | `{entities[], relations[]}` | Request KG update |
| `kg.upsert.completed` | `{triples_count}` | Oxigraph update complete |
| `telemetry.ha.*` | `{entity_id, value, ts}` | HA telemetry events |

**Error Handling & Retry Logic**:

| Component | Error Type | Retry Strategy | Backoff |
|-----------|-----------|----------------|---------|
| Docling | OOM on large PDF | Scale up HPA, retry with same doc | 30s exponential, max 3 retries |
| Docling | Parse failure | Dead-letter queue, alert | No retry (malformed input) |
| Embedder | llama.cpp unavailable | Retry via NATS | 1s → 5s → 30s (exponential) |
| Embedder | Rate limit (429) | Backoff, queue in JetStream | Circuit breaker after 5 failures |
| KG Worker | Oxigraph connection fail | Retry with transaction rollback | 5s fixed, max 5 retries |
| NATS | Auth failure | Security backoff (suspicious activity) | 1s → 5s → 30s → alert |
| NATS | Malformed payload | Reject to DLQ, log to OpenObserve | No retry |

**Security Backoffs**:
- Repeated auth failures from same service → trigger 1s → 5s → 30s backoff before allowing reconnect
- Rate limit detected (llama.cpp overloaded) → circuit breaker opens, stops traffic for 60s
- Malformed payloads → rejected immediately, sent to DLQ for inspection, logged to OpenObserve with alert

#### Flow 3: Semantic Query

```
┌─────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐
│ User/   │──▶│ LiteLLM  │──▶│ Supabase│──▶│ pgvector│◀─│ llama.cpp│
│ Agent   │   │ Proxy    │   │ query   │   │ search  │   │(optional)│
└─────────┘   └──────────┘   └─────────┘   └─────────┘   └──────────┘
                    │                                    │
                    ▼                                    │
              ┌──────────┐                              │
              │ Oxigraph │◀────KG context────────────────┘
              │ SPARQL   │
              └──────────┘
```

**Sequence**:
1. Agent queries LiteLLM proxy with search request
2. LiteLLM queries Supabase pgvector for semantic similarity (AND/OR Oxigraph for graph context)
3. LiteLLM optionally calls llama.cpp for LLM completion with retrieved context
4. Results returned to agent

**Error handling**:
- Supabase unavailable: Return cached results if available, else 503
- Oxigraph timeout: Return vector-only results (degraded mode)
- llama.cpp unavailable: Return raw search results without LLM synthesis

## 3. Infrastructure Layers

### 3.1 Underlay (Tailnet, k3s)

The underlay provides the network and compute fabric that all other layers depend on.

#### Tailscale Tailnet

**Role**: Zero-config VPN, trust boundary, service discovery, authenticated mesh network.

**Configuration**:
| Setting | Value | Notes |
|---------|-------|-------|
| **Accept Routes** | Enabled | Control plane advertises routes to workers |
| **Accept DNS** | Enabled | Use MagicDNS for service discovery (`service.namespace.tailnet-name.ts.net`) |
| **NAT Traversal** | Enabled (DERP) | Fallback relay when direct P2P unavailable |
| **Key Expiry** | 180 days | Re-auth required quarterly |
| **ACL Tags** | `tag:control-plane`, `tag:worker` | Segment access; only control-plane can provision |
| **4via6** | Enabled | Use Tailscale IPv6 for NAT traversal |

**Current State**: Already deployed on desktop k3s and HA Yellow.

**Pulumi Integration**: Use `tailscale` provider to configure ACL tags, approve nodes, and manage route advertisements.

**See Also**: Section 5.4 (LiteLLM Proxy), Section 9.3 (Trust Boundaries)

#### k3s / Rancher Desktop

**Role**: Lightweight Kubernetes cluster on desktop; runs all AI platform services.

**Configuration**:
| Setting | Value | Notes |
|---------|-------|-------|
| **Container Runtime** | containerd | Default for Rancher Desktop 1.14+ |
| **Ingress** | Traefik (k3s default) | ClusterIP-only; expose via Tailscale |
| **DNS** | CoreDNS | Forward internal queries to Tailscale |
| **Network** | Flannel VXLAN | Default; 10.42.0.0/16 pod CIDR |
| **Node Local DNS** | Enabled | Cache DNS for performance |
| **Resource Limits** | 80% of system RAM reserved | Leave 20% for host OS; detect via hardware audit |

**Current State**: Rancher Desktop installed with k3s.

**Hardware-Aware Tuning** (via Ansible):
```yaml
# Pulumi reads these values from facts.d/
k3s_reserved_memory_percent: 20
k3s_reserved_cpu_percent: 10
# On 32GB desktop: 6.4GB reserved, ~25GB for pods
# On 16GB machine: 3.2GB reserved, ~12GB for pods
```

**Pulumi Integration**:
- Use `kubernetes` provider to deploy all workloads
- Use `helm` provider for NATS, Supabase, LiteLLM charts
- Resource requests/limits calculated as percentages from hardware audit

**See Also**: Section 4.2 (Hardware Audit), Section 7.3 (Dynamic Resources)

### 3.2 Storage & Event Spine

The spine provides durable storage (Garage) and reliable messaging (NATS). All services read/write through these layers.

#### Garage Object Store

**Role**: S3-compatible blob storage for raw documents, extracted artifacts, and derived data.

**Architectural Role**:
- **Single source of truth** for document content
- **Immutable storage**: never mutate, always append new versions
- **Presigned URLs**: Generate time-limited access tokens for Docling, query services
- **Replication**: 3-way replication across zones (future: multi-zone HA)

**Configuration**:
| Setting | Value | Notes |
|---------|-------|-------|
| **Replication Factor** | 3 (configurable) | `replication_factor = 3` in Garage config |
| **Consistency Mode** | Quorum | Trade latency for consistency |
| **Bucket Layout** | `raw/`, `processed/`, `models/` | Separate ingestion artifacts |
| **Versioning** | Enabled | Track document history |
| **Lifecycle Rules** | 90-day retention for raw | Move to cold storage after 90d (future) |
| **S3 API Port** | 3900 (ClusterIP) | Internal-only; no external exposure |

**Pulumi Integration**:
```typescript
// Use Helm chart for Garage deployment
const garage = new Chart('garage', {
  chart: 'garage',
  repo: 'https://garagehq.github.io/garage',
  values: {
    replicationFactor: 3,
    persistence: { size: '100Gi' } // 100% of available SSD space
  }
});
```

**Hardware-Aware Sizing**:
| Storage Type | Allocation |
|--------------|------------|
| **SSD (Desktop)** | 70% for Garage data, 30% for JetStream/Postgres |
| **HDD (fallback)** | 50% for Garage, 50% for backups |

**See Also**: Section 5.2 (Garage Specification), Section 4.3 (Tuning Profiles)

#### NATS + JetStream

**Role**: Event bus, work queues, and durable message streaming for all inter-service communication.

**Architectural Role**:
- **Decoupling**: Services publish events without knowing consumers
- **Reliability**: JetStream persists messages; consumers replay after failures
- **Backpressure**: Flow control prevents overwhelming slow services
- **Observability**: Built-in metrics for consumer lag, message rates

**Configuration**:
| Setting | Value | Notes |
|---------|-------|-------|
| **Memory Storage** | 25% of available RAM | Configured via hardware audit |
| **File Storage** | 20Gi on SSD | Persistent JetStream data |
| **Max Payload Size** | 1MB | Reject larger payloads (use Garage pointers) |
| **Retention** | 24h for streams, 1h for KV | Configurable per stream |
| **Replication** | Enabled (raft) | 3-node cluster (future) |

**Stream Definitions**:
| Stream | Subjects | Retention | Max Size |
|--------|----------|-----------|----------|
| `INGEST` | `doc.ingest.*` | 24h | 10Gi |
| `EMBED` | `embed.*` | 24h | 10Gi |
| `KG` | `kg.*` | 24h | 5Gi |
| `TELEMETRY` | `telemetry.*` | 6h | 5Gi |

**Pulumi Integration**:
```typescript
// NATS JetStream resources via CRDs (nats.io)
const ingestStream = new NATSJetStream('ingest-stream', {
  name: 'INGEST',
  subjects: ['doc.ingest.>'],
  retention: 'limits',
  maxAge: '24h',
  maxBytes: 10 * 1024 * 1024 * 1024 // 10Gi
});
```

**Hardware-Aware Memory**:
```yaml
# From hardware audit
jetstream_memory_max_percent: 25  # of total RAM
# On 64GB: ~16GB for JetStream
# On 32GB: ~8GB for JetStream
# On 16GB: ~4GB for JetStream
```

**See Also**: Section 5.1 (NATS Specification), Appendix B (NATs Subject Schema)

### 3.3 Data Plane (Component Placement)

The data plane defines where components run, considering the 32GB desktop constraint and hardware-specific optimizations.

#### Desktop k3s Cluster (Primary Zone)

**Hardware Profile**: 32GB RAM, SSD storage, 8+ CPU cores

**Baseline Services** (Always-on, ~14-18GB):
| Service | RAM Allocation | CPU | Purpose |
|---------|---------------|-----|---------|
| k3s + system | 2-4GB | 10% | Orchestration overhead |
| NATS + JetStream | 1-2GB (25% of remaining) | 5% | Messaging fabric |
| Supabase Postgres + pgvector | 6-10GB (40-50% of RAM) | 30% | Vector + relational DB |
| Oxigraph | 1-2.5GB | 5% | Knowledge graph |
| LiteLLM Proxy | 0.5-1GB | 2% | API gateway |
| OpenObserve | 1-2GB | 3% | Logs + metrics |
| **Subtotal** | **~14-18GB** | **~55%** | |

**Burst Services** (Scale-to-zero, up to ~10-14GB):
| Service | RAM (per replica) | Max Replicas | HPA Trigger |
|---------|------------------|--------------|-------------|
| Docling Workers | 3-6GB | 3 | CPU > 70% |
| Cognee/KG Workers | 2-6GB | 2 | Memory > 80% |
| Promptfoo (Job) | 0.5-2GB | 1 (on-demand) | Manual trigger |
| MindsDB (optional) | 2-6GB | 1 | Manual (not 24/7) |

**Total Peak**: ~28-30GB (within 32GB limit with ~2GB headroom)

**Hardware-Aware Sizing** (Pulumi calculates from Ansible facts):
```typescript
// Example: Supabase Postgres memory
const totalRamGB = hardwareAudit.totalRam / 1024 / 1024 / 1024;
const postgresRamGB = totalRamGB * 0.40; // 40% for Postgres
const postgresSharedBuffers = postgresRamGB * 0.25; // 25% of Postgres RAM for shared_buffers

const postgres = new Deployment('supabase-postgres', {
  spec: {
    containers: [{
      resources: {
        requests: { memory: `${postgresRamGB * 0.8}Gi` },  // 80% of target
        limits: { memory: `${postgresRamGB}Gi` }
      },
      env: [{ name: 'SHARED_BUFFERS', value: `${postgresSharedBuffers}GB` }]
    }]
  }
});
```

#### Home Assistant Yellow (Telemetry Zone)

**Hardware Profile**: Limited RAM, eMMC storage, ARM64

**Services**:
| Service | Purpose | Connection |
|---------|---------|------------|
| Home Assistant | Automation platform | Local only |
| TimescaleDB | Time-series storage | NATS publisher |
| NATS Client | Telemetry bridge | Publishes to desktop cluster |

**Resource Allocation**:
- TimescaleDB: 50% of available RAM (hardware-detected)
- Retention: 30-day rolling window
- Replication: Future - stream to desktop long-term storage

**See Also**: Section 5.9 (TimescaleDB Specification)

#### NVIDIA Jetson AGX Orin (Inference Zone)

**Hardware Profile**: 64GB unified memory, GPU (CUDA sm_87), ARM64, NVMe SSD

**Status**: Not yet configured (Phase 3)

**Primary Purpose**: Agentic coding with tool calling + subagent concurrency

**Planned Services**:
| Service | Purpose | Connection |
|---------|---------|------------|
| Tailscale | VPN connectivity | Joins tailnet |
| llama.cpp | Inference runtime (llama-server) | Local HTTP endpoint |
| GLM-4.7-Flash GGUF | 30B-A3B MoE model (~3.6B active/token) | Stored on NVMe |
| (Optional) vLLM + AWQ | High-concurrency serving | Alternative runtime |

**Resource Allocation** (hardware-detected):
- Model weights: ~18-24GB for Q4-Q8 GGUF (30B total MoE weights)
- KV cache: 8-16GB for 8k context with 2-4 parallel sequences
- System: 30% for OS + CUDA + overhead
- Models: 70% for unified memory (weights + KV cache)

**Performance Expectations**:
- Single-agent: ~5-12 tokens/sec (4k-8k context)
- Concurrency: 2-4 parallel sequences
- Thermal: MaxN mode + pinned clocks required

**Architecture**:
- **Jetson**: Stateless inference appliance (llama-server OpenAI-compatible endpoint)
- **Control plane (laptop/desktop)**: Stateful agent orchestration (Goose/OpenCode)

**See Also**: Section 5.8 (GLM-4.7-Flash llama.cpp), Section 6.3 (Phase 3: AI Inference)

#### Summary Table

| Zone | Hardware | Services | RAM Baseline | RAM Peak |
|------|----------|----------|--------------|----------|
| **Desktop k3s** | 32GB RAM, SSD | NATS, Garage, Supabase, Oxigraph, LiteLLM, Docling, Cognee, OpenObserve | 14-18GB | 28-30GB |
| **HA Yellow** | Limited RAM, eMMC | HA, TimescaleDB, NATS client | 50% of available | Same |
| **Jetson** | 64GB unified, GPU | Tailscale, llama.cpp, GLM-4.7-Flash | 30% for system | 70% for models + KV cache |

**Key Constraint**: Desktop 32GB is the bottleneck. All resource calculations use percentages to remain portable across hardware.

**See Also**: Section 10 (Resource Management), Section 4 (Hardware Auditing)

## 4. Hardware Auditing & Auto-Tuning

Hardware-aware provisioning ensures every component is configured for optimal performance based on actual machine capabilities. This implements the **Ports & Adapters** pattern: hardware audit adapters detect capabilities, tuning profiles adapt configurations, and Pulumi consumes the facts without tight coupling to specific hardware.

### 4.1 Detection Strategy

The detection strategy uses a layered approach: Ansible collects facts during provisioning, stores them in `facts.d/`, and Pulumi reads these facts to generate hardware-tuned infrastructure.

#### Detection Layers

| Layer | Tool | Detects | Output Location |
|-------|------|---------|-----------------|
| **Base Facts** | Ansible `setup` module | CPU cores, RAM, disk, OS version | `/etc/ansible/facts.d/homelab.fact` |
| **CPU Flags** | Ansible `cpu_flags` custom module | AVX, AVX2, AVX512, NEON, CUDA | `facts.d/cpu_capabilities.json` |
| **Storage IOPS** | Ansible `fio` benchmark | Sequential/rand read/write IOPS | `facts.d/storage_performance.json` |
| **GPU Detection** | Ansible `gpu_detect` module | CUDA cores, VRAM, driver version | `facts.d/gpu_info.json` |
| **Network Latency** | Ansible `ping` + `iperf3` | Bandwidth, latency to other zones | `facts.d/network_profile.json` |

#### Detection Philosophy

**Detect once, use everywhere**: Facts are collected during Phase 0 (Ansible provisioning) and written to persistent storage. All subsequent Pulumi deployments read from these facts, ensuring consistency across runs.

**Graceful degradation**: If detection fails for a capability, use conservative defaults. For example, if GPU detection fails, assume no GPU and route embeddings to CPU/embedding API.

**Port & Adapter Pattern**:
```typescript
// Pulumi: HardwarePort interface (port)
interface HardwareFacts {
  totalRam: number;
  cpuCores: number;
  cpuFlags: string[];
  hasGPU: boolean;
  gpuVRAM?: number;
  storageIOPS?: number;
}

// AnsibleJSONFileAdapter (adapter)
class AnsibleFactsAdapter implements HardwarePort {
  async getFacts(inventoryHost: string): Promise<HardwareFacts> {
    const factsPath = `/etc/ansible/facts.d/${inventoryHost}.json`;
    return JSON.parse(await fs.readFile(factsPath));
  }
}

// Swap adapter without changing business logic
const hardware = new AnsibleFactsAdapter(); // or MockAdapter for testing
```

### 4.2 Ansible Fact Collection

#### Playbook Structure

```yaml
# infra/ansible-bootstrap/playbooks/audit-hardware.yml
---
- name: Audit hardware capabilities
  hosts: all
  gather_facts: true
  become: true

  tasks:
    - name: Detect base hardware facts
      ansible.builtin.setup:
      register: base_facts

    - name: Write base facts to facts.d
      ansible.builtin.copy:
        dest: /etc/ansible/facts.d/homelab.fact
        content: |
          {
            "total_ram_mb": {{ base_facts.ansible_memtotal_mb }},
            "cpu_cores": {{ base_facts.ansible_processor_vcpus }},
            "architecture": {{ base_facts.ansible_architecture }},
            "os_family": {{ base_facts.ansible_os_family }}
          }
        mode: '0644'

    - name: Detect CPU flags (AVX, AVX2, AVX512, NEON)
      ansible.builtin.shell:
        cmd: |
          if [ -f /proc/cpuinfo ]; then
            grep -oP 'flags\s*:\s*\K.*' /proc/cpuinfo | head -1
          elif [ "{{ ansible_architecture }}" = "aarch64" ]; then
            echo "neon asimd"
          fi
      register: cpu_flags
      changed_when: false

    - name: Write CPU capabilities
      ansible.builtin.copy:
        dest: /etc/ansible/facts.d/cpu_capabilities.json
        content: |
          {
            "flags": {{ cpu_flags.stdout.split() | to_json }},
            "has_avx": {{ "'avx' in cpu_flags.stdout" }},
            "has_avx2": {{ "'avx2' in cpu_flags.stdout" }},
            "has_avx512": {{ "'avx512f' in cpu_flags.stdout" }},
            "has_neon": {{ "'neon' in cpu_flags.stdout or ansible_architecture == 'aarch64' }}
          }
        mode: '0644'

    - name: Detect GPU (NVIDIA CUDA)
      block:
        - name: Check for nvidia-smi
          ansible.builtin.command: nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
          register: gpu_info
          changed_when: false
          failed_when: false

        - name: Write GPU facts
          ansible.builtin.copy:
            dest: /etc/ansible/facts.d/gpu_info.json
            content: |
              {
                "has_gpu": true,
                "gpu_name": "{{ gpu_info.stdout.split(',')[0] | trim }}",
                "gpu_vram_mb": {{ gpu_info.stdout.split(',')[1].strip().replace(' MiB', '') | int }}
              }
            mode: '0644'
          when: gpu_info.rc == 0

        - name: Write no-GPU facts
          ansible.builtin.copy:
            dest: /etc/ansible/facts.d/gpu_info.json
            content: '{"has_gpu": false}'
            mode: '0644'
          when: gpu_info.rc != 0

    - name: Benchmark storage IOPS (fio)
      ansible.builtin.command:
        cmd: >
          fio --name=benchmark --filename=/tmp/homelab-benchmark.tmp
          --size=1G --rw=read --bs=4k --direct=1 --numjobs=1
          --output-format=json
      register: fio_result
      changed_when: false
      failed_when: false
      when: "'storage_benchmark' in ansible_run_tags"

    - name: Write storage performance
      ansible.builtin.copy:
        dest: /etc/ansible/facts.d/storage_performance.json
        content: |
          {
            "read_iops": {{ fio_result.stdout | from_json | json_query('jobs[0].read.iops') | default(0) }},
            "read_bw_mb": {{ fio_result.stdout | from_json | json_query('jobs[0].read.bw') | default(0) / 1024 }}
          }
        mode: '0644'
      when: "'storage_benchmark' in ansible_run_tags"
```

#### Usage

```bash
# Run hardware audit on all machines
ansible-playbook -i inventory/ homelab.yml --tags hardware_audit

# Run with storage benchmark (slow, ~30 seconds)
ansible-playbook -i inventory/ homelab.yml --tags hardware_audit,storage_benchmark

# Audit specific host
ansible-playbook -i inventory/ homelab.yml --limit jetson --tags hardware_audit
```

#### Custom Module: CPU Flags

Create `infra/ansible-bootstrap/library/cpu_flags.py`:

```python
#!/usr/bin/env python3
"""Ansible module to detect CPU instruction sets."""

from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(argument_spec={})
    result = {
        'changed': False,
        'flags': [],
        'has_avx': False,
        'has_avx2': False,
        'has_avx512': False,
        'has_neon': False
    }

    # Detection logic...
    module.exit_json(**result)

if __name__ == '__main__':
    main()
```

### 4.3 Tuning Profiles

Tuning profiles map hardware capabilities to configuration parameters. Each profile is a set of percentage-based allocations that scale with available resources.

#### Profile Schema

```yaml
# infra/ansible-bootstrap/roles/hardware_audit/templates/profiles/
---
memory_allocation:
  postgres_percent: 40          # 40% of RAM for Postgres
  postgres_shared_buffers: 25   # 25% of Postgres RAM for shared_buffers
  jetstream_percent: 25         # 25% of RAM for NATS JetStream
  oxigraph_percent: 8           # 8% of RAM for Oxigraph
  litellm_percent: 3            # 3% of RAM for LiteLLM
  openobserve_percent: 5        # 5% of RAM for OpenObserve
  headroom_percent: 2           # 2% headroom

cpu_allocation:
  postgres_percent: 30          # 30% of CPU cores for Postgres
  docling_min_cores: 2          # Minimum 2 cores for Docling
  hpa_threshold_percent: 70     # Scale when CPU > 70%

storage_allocation:
  garage_percent: 70            # 70% of SSD for Garage
  jetstream_percent: 20         # 20% of SSD for JetStream
  postgres_percent: 10          # 10% of SSD for Postgres

profile_specific:
  high_memory:
    condition: "total_ram_gb >= 32"
    postgres_percent: 45        # More aggressive on 32GB+ machines
    jetstream_percent: 30

  low_memory:
    condition: "total_ram_gb < 16"
    postgres_percent: 30        # Conservative on 16GB- machines
    jetstream_percent: 15
    oxigraph_percent: 5         # Reduce Oxigraph footprint

  gpu_optimized:
    condition: "has_gpu == true"
    ollama_model: "mixtral"      # Use larger models on GPU
    ollama_vram_percent: 70     # 70% of VRAM for models

  cpu_optimized:
    condition: "has_gpu == false and has_avx2 == true"
    ollama_model: "llama3.2"    # CPU-optimized model
    embedding_batch_size: 32    # Higher batch for AVX2
```

#### Profile Selection Logic

```python
# Pulumi: Auto-select profile based on facts
function selectProfile(facts: HardwareFacts): TuningProfile {
  if (facts.totalRamGB >= 32 && facts.hasGPU) {
    return profiles.get('high_memory_gpu');
  } else if (facts.totalRamGB >= 32) {
    return profiles.get('high_memory');
  } else if (facts.totalRamGB < 16) {
    return profiles.get('low_memory');
  } else if (facts.hasGPU) {
    return profiles.get('gpu_optimized');
  } else {
    return profiles.get('default');
  }
}
```

#### Example: 32GB Desktop Profile

```yaml
# Applied to desktop k3s (32GB RAM, no GPU)
computed_resources:
  postgres_ram_gb: 12.8        # 32GB * 0.40
  postgres_shared_buffers_gb: 3.2  # 12.8GB * 0.25
  jetstream_ram_gb: 6.4        # 32GB * 0.20 (reduced for non-GPU)
  oxigraph_ram_gb: 2.0         # 32GB * 0.0625
  litellm_ram_gb: 0.8          # 32GB * 0.025
  openobserve_ram_gb: 1.5      # 32GB * 0.047
  headroom_gb: 0.6             # 32GB * 0.02

  garage_storage_gb: 140       # 200GB SSD * 0.70
  jetstream_storage_gb: 40     # 200GB SSD * 0.20
  postgres_storage_gb: 20      # 200GB SSD * 0.10
```

#### Example: Jetson AGX Orin Profile

```yaml
# Applied to Jetson (32GB unified memory, GPU)
computed_resources:
  ollama_model_ram_gb: 22.4     # 32GB * 0.70 (for models)
  system_ram_gb: 9.6           # 32GB * 0.30 (for system)

  model_selection:
    embedding_model: "nomic-embed-text"
    completion_model: "mixtral:8x7b"  # Fits in ~22GB VRAM
```

### 4.4 Pulumi Integration

Pulumi reads hardware facts and applies tuning profiles to generate hardware-aware infrastructure.

#### Fact Reading Pattern

```typescript
// packages/pulumi-ai-infrastructure/src/hardware.ts

import * as fs from 'fs';
import * as path from 'path';

export interface HardwareFacts {
  totalRam: number;        // bytes
  cpuCores: number;
  architecture: string;
  hasAVX2: boolean;
  hasGPU: boolean;
  gpuVRAM?: number;        // bytes
}

export class HardwareAudit {
  private readonly factsPath: string;

  constructor(inventoryHost: string) {
    this.factsPath = `/etc/ansible/facts.d/${inventoryHost}.json`;
  }

  loadFacts(): HardwareFacts {
    try {
      const raw = fs.readFileSync(this.factsPath, 'utf-8');
      const facts = JSON.parse(raw);

      return {
        totalRam: facts.total_ram_mb * 1024 * 1024,
        cpuCores: facts.cpu_cores,
        architecture: facts.architecture,
        hasAVX2: facts.cpu_flags?.includes('avx2') ?? false,
        hasGPU: facts.has_gpu ?? false,
        gpuVRAM: facts.gpu_vram_mb ? facts.gpu_vram_mb * 1024 * 1024 : undefined,
      };
    } catch (error) {
      throw new Error(`Failed to load hardware facts from ${this.factsPath}: ${error}`);
    }
  }
}

// Usage in Pulumi stack
const hardware = new HardwareAudit('desktop-k3s').loadFacts();
```

#### Dynamic Resource Allocation

```typescript
// packages/pulumi-ai-infrastructure/index.ts

import * as k8s from '@pulumi/kubernetes';

const hardware = new HardwareAudit('desktop-k3s').loadFacts();

// Calculate memory allocations (percentages)
const postgresRamBytes = hardware.totalRam * 0.40;
const postgresSharedBuffers = postgresRamBytes * 0.25;
const jetstreamRamBytes = hardware.totalRam * 0.20;

const postgres = new k8s.core.v1.Deployment('supabase-postgres', {
  spec: {
    containers: [{
      name: 'postgres',
      resources: {
        requests: {
          memory: `${postgresRamBytes * 0.8}`,    // 80% of target as request
          cpu: `${hardware.cpuCores * 0.30}`,     // 30% of cores
        },
        limits: {
          memory: `${postgresRamBytes}`,          // 100% of target as limit
          cpu: `${hardware.cpuCores * 0.50}`,     // 50% of cores
        },
      },
      env: [
        { name: 'SHARED_BUFFERS', value: `${postgresSharedBuffers}` },
        { name: 'EFFECTIVE_CACHE_SIZE', value: `${postgresRamBytes * 0.50}` },
      ],
    }],
  },
});

// CPU-optimized: Use AVX2 if available
const docling = new k8s.core.v1.Deployment('docling', {
  spec: {
    containers: [{
      name: 'docling',
      env: [
        {
          name: 'RAYON_NUM_THREADS',
          value: hardware.hasAVX2 ? `${Math.max(2, hardware.cpuCores * 0.25)}` : '1',
        },
      ],
    }],
  },
});
```

#### HPA Configuration with Hardware Thresholds

```typescript
import * as k8s from '@pulumi/kubernetes';

const hpaCpuTarget = hardware.cpuCores >= 8 ? 70 : 80;  // Stricter on high-core
const hpaMemoryTarget = hardware.totalRam > (16 * 1024 * 1024 * 1024) ? 80 : 70;

const doclingHPA = new k8s.autoscaling.v2.HorizontalPodAutoscaler('docling-hpa', {
  spec: {
    scaleTargetRef: {
      apiVersion: 'apps/v1',
      kind: 'Deployment',
      name: 'docling',
    },
    minReplicas: 1,
    maxReplicas: hardware.cpuCores >= 8 ? 3 : 2,  // More replicas on high-core
    metrics: [
      {
        type: 'Resource',
        resource: {
          name: 'cpu',
          target: {
            type: 'Utilization',
            averageUtilization: hpaCpuTarget,
          },
        },
      },
      {
        type: 'Resource',
        resource: {
          name: 'memory',
          target: {
            type: 'Utilization',
            averageUtilization: hpaMemoryTarget,
          },
        },
      },
    ],
  },
});
```

#### Storage Allocation (percentages)

```typescript
// Detect storage from hardware facts
const storageSSD = hardware.storageSSDBytes ?? 200 * 1024 * 1024 * 1024;  // Default 200GB

const garageStorage = storageSSD * 0.70;
const jetstreamStorage = storageSSD * 0.20;
const postgresStorage = storageSSD * 0.10;

const garagePVC = new k8s.core.v1.PersistentVolumeClaim('garage-data', {
  spec: {
    accessModes: ['ReadWriteOnce'],
    resources: {
      requests: {
        storage: `${garageStorage}`,
      },
    },
  },
});
```

#### Hardware-Specific ConfigMaps

```typescript
const hardwareConfig = new k8s.core.v1.ConfigMap('hardware-facts', {
  data: {
    'profile.json': JSON.stringify({
      totalRamGB: Math.round(hardware.totalRam / 1024 / 1024 / 1024),
      cpuCores: hardware.cpuCores,
      hasGPU: hardware.hasGPU,
      hasAVX2: hardware.hasAVX2,
      profile: hardware.totalRam > (32 * 1024 * 1024 * 1024) ? 'high_memory' : 'standard',
    }, null, 2),
  },
});
```

**See Also**: Section 7.3 (Dynamic Resource Patterns), Appendix D (Hardware Audit Schema)

## 5. Component Specifications

Each component implements a port-based interface for loose coupling. Swap implementations without touching business logic.

### 5.1 NATS + JetStream

**Purpose**: Event-driven messaging fabric with durable streaming for all inter-service communication.

**Version**: nats:2.10-alpine

**Pulumi Deployment**:
```typescript
import * as k8s from '@pulumi/kubernetes';
import { Chart } from '@pulumi/kubernetes/helm/v3';

// Hardware-aware memory from Section 4
const hardware = new HardwareAudit('desktop-k3s').loadFacts();
const jetstreamRam = hardware.totalRam * 0.20;  // 20% of RAM

// Deploy NATS via Helm chart
const nats = new Chart('nats', {
  chart: 'nats',
  repo: 'https://nats-io.github.io/k8s-nats-helm-chart/',
  version: '1.x',
  values: {
    nats: {
      jetstream: {
        enabled: true,
        memoryStorage: {
          enabled: true,
          size: `${Math.round(jetstreamRam / 1024 / 1024 / 1024)}Gi`,
        },
        fileStorage: {
          enabled: true,
          size: '20Gi',
          storageDirectory: '/data/jetstream',
        },
      },
    },
    config: {
      max_payload: 1024 * 1024,  // 1MB max payload
      max_pending: 512 * 1024,    // Backpressure threshold
    },
  },
});

// JetStream streams via CRDs
const streams: k8s.apiextensions.CustomResource[] = [
  {
    apiVersion: 'jetstream.nats.io/v1beta2',
    kind: 'Stream',
    metadata: { name: 'ingest' },
    spec: {
      name: 'INGEST',
      subjects: ['doc.ingest.>'],
      retention: 'limits',
      maxAge: '24h',
      maxBytes: 10 * 1024 * 1024 * 1024,  // 10Gi
      storage: 'file',
      replicas: 1,
    },
  },
  // ... EMBED, KG, TELEMETRY streams
];
```

**Health Checks**:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8222
  initialDelaySeconds: 10
readinessProbe:
  httpGet:
    path: /healthz?js-server-only=true
    port: 8222
```

**See Also**: Section 3.2 (Storage Spine), Appendix B (NATS Schema)

---

### 5.2 Garage Object Store

**Purpose**: S3-compatible object storage for raw documents and processed artifacts.

**Version**: dxflrs/garage:latest

**Pulumi Deployment**:
```typescript
const garage = new Chart('garage', {
  chart: 'garage',
  repo: 'https://garagehq.github.io/garage',
  values: {
    garage: {
      replicationFactor: 3,
      rpcSecret: { secretKeyRef: { name: 'garage-secret', key: 'rpc-secret' } },
    },
    persistence: {
      size: '100Gi',  // 70% of SSD from hardware audit
      storageClass: 'local-path',
    },
    service: {
      type: 'ClusterIP',
      port: 3900,
    },
  },
});

// S3 credentials from SOPS
const garageSecret = new k8s.core.v1.Secret('garage-credentials', {
  type: 'Opaque',
  stringData: {
    's3-access-key': sopsDecrypt('infra/ai-infrastructure/garage.env.sops', 'S3_ACCESS_KEY'),
    's3-secret-key': sopsDecrypt('infra/ai-infrastructure/garage.env.sops', 'S3_SECRET_KEY'),
    'rpc-secret': sopsDecrypt('infra/ai-infrastructure/garage.env.sops', 'RPC_SECRET'),
  },
});
```

**Buckets**:
| Bucket | Purpose | Lifecycle |
|--------|---------|-----------|
| `raw-documents` | Incoming PDFs, docs | 90-day expiration |
| `processed` | Docling output, chunks | Never expire |
| `models` | Cached ML models | Never expire |

**Health Checks**:
```yaml
livenessProbe:
  tcpSocket:
    port: 3900
  initialDelaySeconds: 5
readinessProbe:
  exec:
    command: ["/garage", "health", "-k"]
```

**See Also**: Section 3.2 (Storage Spine)

---

### 5.3 Supabase Postgres + pgvector

**Purpose**: Relational database with vector similarity search for embeddings.

**Version**: supabase/postgres:15.1.0.147 (includes pgvector)

**Pulumi Deployment**:
```typescript
const hardware = new HardwareAudit('desktop-k3s').loadFacts();
const postgresRam = hardware.totalRam * 0.40;  // 40% of RAM
const postgresSharedBuffers = postgresRam * 0.25;

const postgres = new k8s.core.v1.Deployment('supabase-postgres', {
  metadata: { name: 'supabase-postgres' },
  spec: {
    replicas: 1,
    template: {
      spec: {
        containers: [{
          name: 'postgres',
          image: 'supabase/postgres:15.1.0.147',
          resources: {
            requests: {
              memory: `${postgresRam * 0.8}`,
              cpu: `${hardware.cpuCores * 0.30}`,
            },
            limits: {
              memory: `${postgresRam}`,
              cpu: `${hardware.cpuCores * 0.50}`,
            },
          },
          env: [
            { name: 'POSTGRES_PASSWORD', valueFrom: { secretKeyRef: { name: 'supabase-secret', key: 'password' } } },
            { name: 'SHARED_BUFFERS', value: `${postgresSharedBuffers}` },
            { name: 'EFFECTIVE_CACHE_SIZE', value: `${postgresRam * 0.50}` },
            { name: 'MAINTENANCE_WORK_MEM', value: '2GB' },
            { name: 'WORK_MEM', value: '32MB' },
            { name: 'MAX_WORKER_PROCESSES', value: `${hardware.cpuCores}` },
            { name: 'MAX_PARALLEL_WORKERS_PER_GATHER', value: '4' },
            { name: 'MAX_PARALLEL_WORKERS', value: `${Math.floor(hardware.cpuCores * 0.75)}` },
          ],
          ports: [{ containerPort: 5432 }],
          livenessProbe: { exec: { command: ['pg_isready', '-U', 'postgres'] } },
          readinessProbe: { exec: { command: ['pg_isready', '-U', 'postgres'] } },
        }],
      },
    },
  },
});

// Storage
const postgresPVC = new k8s.core.v1.PersistentVolumeClaim('supabase-postgres-data', {
  spec: {
    accessModes: ['ReadWriteOnce'],
    resources: { requests: { storage: '50Gi' } },  // 25% of SSD
  },
});
```

**pgvector Configuration**:
```sql
-- Run via init script
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INT,
  chunk_text TEXT,
  embedding vector(768),  -- nomic-embed-text dimension
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Health Checks**: Via `pg_isready`

**See Also**: Section 3.2 (Storage Spine)

---

### 5.4 LiteLLM Proxy

**Purpose**: OpenAI-compatible API gateway that routes requests to llama.cpp (Jetson) or external providers.

**Version**: ghcr.io/riptide-dp/predictable-llm-litellm-proxy:latest

**Pulumi Deployment**:
```typescript
const litellm = new Chart('litellm', {
  chart: 'litellm',
  repo: 'https://litellm-helm.github.io/litellm-helm',
  values: {
    image: { repo: 'ghcr.io/riptide-dp/predictable-llm-litellm-proxy' },
    replicas: 1,
    resources: {
      requests: { memory: '512Mi', cpu: '250m' },
      limits: { memory: '1Gi', cpu: '500m' },
    },
    env: [
      { name: 'LITELLM_PORT', value: '4000' },
      { name: 'LITELLM_SALT_KEY', valueFrom: { secretKeyRef: { name: 'litellm-secret', key: 'salt-key' } } },
    ],
    config: {
      model_list: [
        {
          model_name: 'ollama/nomic-embed-text',
          litellm_params: {
            api_base: 'http://ollama.jetson.svc.cluster.local:11434',
            rpm: 300,  // Rate limit: 5 requests/second
          },
        },
        {
          model_name: 'ollama/llama3.2',
          litellm_params: {
            api_base: 'http://ollama.jetson.svc.cluster.local:11434',
            rpm: 30,
          },
        },
      ],
    },
    service: {
      type: 'ClusterIP',
      port: 4000,
    },
  },
});
```

**Port Interface**:
```typescript
interface EmbeddingPort {
  embed(text: string): Promise<number[]>;
}

interface LLMPort {
  complete(prompt: string, options?: CompletionOptions): Promise<string>;
}

// LiteLLM adapter
class LiteLLMAdapter implements EmbeddingPort, LLMPort {
  private baseUrl = 'http://litellm.ai-infrastructure.svc.cluster.local:4000';

  async embed(text: string): Promise<number[]> {
    const response = await fetch(`${this.baseUrl}/v1/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: text,
        model: 'ollama/nomic-embed-text',
      }),
    });
    return (await response.json()).data[0].embedding;
  }

  async complete(prompt: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/v1/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'ollama/llama3.2',
        prompt,
        max_tokens: 2048,
      }),
    });
    return (await response.json()).choices[0].text;
  }
}
```

**Health Checks**: `/health` endpoint

**See Also**: Section 2.3 (Data Flow), Section 5.8 (GLM-4.7-Flash llama.cpp)

---

### 5.5 Oxigraph Knowledge Graph

**Purpose**: RDF triple store for knowledge graph with SPARQL query support.

**Version: ghcr.io/oxigraph/oxigraph:latest

**Pulumi Deployment**:
```typescript
const hardware = new HardwareAudit('desktop-k3s').loadFacts();
const oxigraphRam = hardware.totalRam * 0.08;  // 8% of RAM

const oxigraph = new k8s.core.v1.Deployment('oxigraph', {
  metadata: { name: 'oxigraph' },
  spec: {
    replicas: 1,
    template: {
      spec: {
        containers: [{
          name: 'oxigraph',
          image: 'ghcr.io/oxigraph/oxigraph:latest',
          resources: {
            requests: { memory: `${oxigraphRam * 0.8}`, cpu: '200m' },
            limits: { memory: `${oxigraphRam}`, cpu: '500m' },
          },
          ports: [{ containerPort: 7878 }],
          env: [
            { name: 'OXIPORT', value: '7878' },
            { name: 'OXISERVER_DATA', value: '/data' },
          ],
          volumeMounts: [{ name: 'data', mountPath: '/data' }],
        }],
        volumes: [{
          name: 'data',
          persistentVolumeClaim: { claimName: 'oxigraph-data' },
        }],
      },
    },
  },
});

const oxigraphPVC = new k8s.core.v1.PersistentVolumeClaim('oxigraph-data', {
  spec: {
    accessModes: ['ReadWriteOnce'],
    resources: { requests: { storage: '20Gi' } },
  },
});
```

**SPARQL Queries** (examples):
```sparql
# Find all entities related to a document
SELECT ?entity ?relation WHERE {
  ?doc a :Document .
  ?doc :hasEntity ?entity .
  ?entity ?relation ?doc .
}

# Knowledge graph traversal
SELECT ?start ?end ?path WHERE {
  ?start :path* ?end .
}
```

**Health Checks**: HTTP `GET /` returns 200

---

### 5.6 Docling Workers

**Purpose**: Document extraction (PDF → structured text, tables, images) using Rust-based Docling.

**Version**: ghcr.io/docling/docling:latest

**Pulumi Deployment**:
```typescript
const hardware = new HardwareAudit('desktop-k3s').loadFacts();

const docling = new k8s.core.v1.Deployment('docling', {
  metadata: { name: 'docling' },
  spec: {
    replicas: 1,  // Scales via HPA
    template: {
      spec: {
        containers: [{
          name: 'docling',
          image: 'ghcr.io/docling/docling:latest',
          resources: {
            requests: { memory: '3Gi', cpu: '500m' },
            limits: { memory: '6Gi', cpu: '2000m' },
          },
          env: [
            { name: 'NATS_URL', value: 'nats://nats:4222' },
            { name: 'GARAGE_ENDPOINT', value: 'http://garage:3900' },
            { name: 'GARAGE_ACCESS_KEY', valueFrom: { secretKeyRef: { name: 'garage-credentials', key: 's3-access-key' } } },
            { name: 'GARAGE_SECRET_KEY', valueFrom: { secretKeyRef: { name: 'garage-credentials', key: 's3-secret-key' } } },
            { name: 'RAYON_NUM_THREADS', value: `${Math.max(2, hardware.cpuCores * 0.25)}` },
          ],
        }],
      },
    },
  },
});

// HPA
const doclingHPA = new k8s.autoscaling.v2.HorizontalPodAutoscaler('docling-hpa', {
  spec: {
    scaleTargetRef: { apiVersion: 'apps/v1', kind: 'Deployment', name: 'docling' },
    minReplicas: 1,
    maxReplicas: 3,
    metrics: [
      { type: 'Resource', resource: { name: 'cpu', target: { type: 'Utilization', averageUtilization: 70 } } },
      { type: 'Resource', resource: { name: 'memory', target: { type: 'Utilization', averageUtilization: 80 } } },
    ],
  },
});
```

**Port Interface**:
```typescript
interface DocumentExtractorPort {
  extract(sourceUri: string): Promise<ExtractedDocument>;
}

class DoclingAdapter implements DocumentExtractorPort {
  async extract(sourceUri: string): Promise<ExtractedDocument> {
    // Subscribe to doc.ingest.requested
    // Download from Garage
    // Run docling parse
    // Upload artifacts to Garage
    // Publish doc.ingest.extracted
  }
}
```

**Health Checks**: `/healthz` endpoint

---

### 5.7 Cognee/KG Pipeline

**Purpose**: Chunking, embedding generation, and knowledge graph construction.

**Version**: cognee:latest (or custom kg-worker)

**Pulumi Deployment**:
```typescript
const cognee = new k8s.core.v1.Deployment('cognee', {
  metadata: { name: 'cognee' },
  spec: {
    replicas: 1,
    template: {
      spec: {
        containers: [{
          name: 'cognee',
          image: 'cognee:latest',
          resources: {
            requests: { memory: '2Gi', cpu: '500m' },
            limits: { memory: '6Gi', cpu: '1500m' },
          },
          env: [
            { name: 'NATS_URL', value: 'nats://nats:4222' },
            { name: 'LITELM_ENDPOINT', value: 'http://litellm:4000' },
            { name: 'SUPABASE_URL', valueFrom: { secretKeyRef: { name: 'supabase-secret', key: 'url' } } },
            { name: 'OXIGRAPH_ENDPOINT', value: 'http://oxigraph:7878' },
            { name: 'EMBEDDING_MODEL', value: 'ollama/nomic-embed-text' },
            { name: 'CHUNK_SIZE', value: '512' },
            { name: 'CHUNK_OVERLAP', value: '128' },
          ],
        }],
      },
    },
  },
});
```

**Pipeline Flow**:
1. Subscribe to `doc.ingest.extracted`
2. Chunk text (512 tokens, 128 overlap)
3. Publish `doc.chunked`
4. Subscribe to `doc.chunked`
5. Call LiteLLM for embeddings
6. Store in Supabase pgvector
7. Publish `embed.completed`
8. Extract entities/relations
9. Publish `kg.upsert.requested`
10. Store triples in Oxigraph
11. Publish `kg.upsert.completed`

**Health Checks**: `/health` endpoint

---

### 5.8 GLM-4.7-Flash llama.cpp (Jetson)

**Purpose**: LLM inference for both **agentic coding** (tool calling, subagents) and **OpenClaw** (query → retrieve → synthesize).

**Model**: GLM-4.7-Flash (30B-A3B MoE: ~30B total weights, ~3.6B active/token)

**Status**: Phase 3 (not yet configured)

**Performance Expectations**:
- Single-agent: ~5-12 tokens/sec (4k-8k context)
- Concurrency: 2-4 parallel sequences (subagents)

**Ansible Provisioning** (to be run on Jetson after Tailscale SSH):
```yaml
# infra/ansible-bootstrap/roles/llama-cpp/tasks/main.yml
---
- name: Install build dependencies
  ansible.builtin.apt:
    name:
      - build-essential
      - git
      - cmake
      - cuda-toolkit
      - libcuda-common
    state: present

- name: Clone llama.cpp
  ansible.builtin.git:
    repo: https://github.com/ggerganov/llama.cpp
    dest: /opt/llama.cpp
    update: false

- name: Build llama.cpp with CUDA for Orin (sm_87)
  ansible.builtin.shell: |
    cmake -B build \
      -DCMAKE_CUDA_ARCHITECTURES=87 \
      -DLLAMA_CUBLAS=ON \
      -DLLAMA_FLASH_ATTN=ON \
      -DCMAKE_BUILD_TYPE=Release
    cmake --build build --config Release -j$(nproc)
  args:
    chdir: /opt/llama.cpp

- name: Create model directory on NVMe
  ansible.builtin.file:
    path: /nvme/models
    state: directory
    mode: '0755'

- name: Download GLM-4.7-Flash GGUF (Q8_0 recommended)
  ansible.builtin.get_url:
    url: https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF/resolve/main/GLM-4.7-Flash-Q8_0.gguf
    dest: /nvme/models/GLM-4.7-Flash-Q8_0.gguf
    mode: '0644'
  when: glm_gguf_url is defined

- name: Create llama-server systemd service
  ansible.builtin.copy:
    dest: /etc/systemd/system/llama-server.service
    content: |
      [Unit]
      Description=llama.cpp OpenAI-compatible server
      After=network.target

      [Service]
      Type=simple
      User=jetson
      WorkingDirectory=/opt/llama.cpp
      ExecStart=/opt/llama.cpp/build/llama-server \
        --model /nvme/models/GLM-4.7-Flash-Q8_0.gguf \
        --host 0.0.0.0 --port 8080 \
        --ctx-size 8192 \
        --parallel 2 \
        --n-gpu-layers 999 \
        --threads 8 \
        --flash-attn
      Restart=on-failure
      RestartSec=10

      [Install]
      WantedBy=multi-user.target
  notify: reload systemd

- name: Enable MaxN power mode
  ansible.builtin.shell: |
    sudo nvpmodel -m 0
    sudo jetson_clocks
  args:
    creates: /tmp/maxn_enabled
```

**llama-server Configuration**:
```bash
# Primary: single-agent low-latency
./llama-server \
  -m /nvme/models/GLM-4.7-Flash-Q8_0.gguf \
  --host 0.0.0.0 --port 8080 \
  --ctx-size 8192 \
  --parallel 2 \
  --n-gpu-layers 999 \
  --threads 8 \
  --flash-attn

# High concurrency mode (adjust --parallel based on testing)
./llama-server \
  -m /nvme/models/GLM-4.7-Flash-Q8_0.gguf \
  --host 0.0.0.0 --port 8080 \
  --ctx-size 8192 \
  --parallel 4 \
  --n-gpu-layers 999 \
  --threads 8 \
  --flash-attn \
  --ub 8 --ub-l 4
```

**Two Performance Profiles**:

| Profile | Purpose | Settings |
|---------|---------|----------|
| **A: Tool-call correctness** | Reliable tool JSON | `--ctx-size 4096`, low temp, JSON schema mode |
| **B: Candidate batching** | High throughput | `--ctx-size 8192`, moderate temp, `--parallel 4` |

**Speculative Decoding** (optional, measure net win):
```bash
./llama-server \
  --model /nvme/models/GLM-4.7-Flash-Q8_0.gguf \
  --model-draft /nvme/models/tiny-draft.Q4_K.gguf \
  --ctx-size 8192 \
  --parallel 2
```

**Quantization Benchmark** (run to find fastest on your Jetson):
```bash
# Test Q4_K_M, Q6_K, Q8_0 with same settings
for quant in Q4_K_M Q6_K Q8_0; do
  ./llama-cli \
    -m /nvme/models/GLM-4.7-Flash-$quant.gguf \
    -p "Say hello in one sentence." \
    -t 2 -n 32 --ctx-size 2048
done
```

**Health Checks**: `curl http://jetson-ip:8080/v1/models`

**Port Interface**:
```typescript
interface LLMInferencePort {
  complete(request: CompletionRequest): Promise<CompletionResponse>;
  embed(text: string): Promise<number[]>;
}

// llama-server adapter (OpenAI-compatible)
class LLamaServerAdapter implements LLMInferencePort {
  private baseUrl = 'http://jetson.tailnet-name.ts.net:8080';

  async complete(request: CompletionRequest): Promise<CompletionResponse> {
    const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'local',
        messages: request.messages,
        temperature: request.temperature ?? 0.2,
        max_tokens: request.maxTokens ?? 2048,
      }),
    });
    return await response.json();
  }

  async embed(text: string): Promise<number[]> {
    // Call Jetson for embeddings (or route to desktop k3s)
    return await this.embedViaDesktop(text);
  }
}
```

**See Also**: Section 6.3 (Phase 3: AI Inference), Section 5.4 (LiteLLM Proxy)

---

### 5.9 TimescaleDB (HA Yellow)

**Purpose**: Time-series telemetry storage from Home Assistant automations.

**Status**: Already running on HA Yellow

**Ansible Configuration** (verify/configure):
```yaml
# infra/ansible-bootstrap/roles/timescale/tasks/main.yml
---
- name: Check TimescaleDB installation
  ansible.builtin.command: psql --version
  register: timescale_version
  failed_when: false

- name: Create telemetry database
  community.postgresql.postgresql_db:
    name: telemetry
    state: present
  become_user: postgres

- name: Create timescaledb extension
  community.postgresql.postgresql_ext:
    name: timescaledb
    db: telemetry
  become_user: postgres

- name: Create hypertable
  community.postgresql.postgresql_query:
    db: telemetry
    query: |
      CREATE TABLE IF NOT EXISTS events (
        time TIMESTAMPTZ NOT NULL,
        entity_id TEXT NOT NULL,
        value FLOAT,
        attributes JSONB
      );
      SELECT create_hypertable('events', 'time', if_not_exists => TRUE);
  become_user: postgres
```

**NATS Bridge** (optional service on HA Yellow):
```yaml
# Publish TimescaleDB events to NATS
- name: Deploy NATS publisher
  ansible.builtin.docker_container:
    name: timescale-nats-bridge
    image: timescale-nats-bridge:latest
    env:
      TIMESCALEDB_URL: "postgresql://postgres:password@localhost/telemetry"
      NATS_URL: "nats://desktop-k3s.tailnet-name.ts.net:4222"
      SUBJECT_PREFIX: "telemetry.ha"
```

**Retention**: 30-day rolling window (configurable)

**Health Checks**: `psql -c "SELECT 1"`

**See Also**: Section 2.3 (Data Flow), Section 3.3 (Data Plane)

## 6. Implementation Phases

Four-phase rollout with validation gates between phases. Each phase is independently deployable and verifiable.

### Phase 0: Ansible Provisioning + Hardware Audit

**Goal**: Bootstrap all machines, detect hardware capabilities, prepare for k8s deployments.

**Prerequisites**:
- Rancher Desktop / k3s installed on desktop
- Tailscale installed on desktop and HA Yellow
- SSH access to all machines (via Tailscale)

**Tasks**:
1. Run hardware audit on all machines
   ```bash
   ansible-playbook -i inventory/ homelab.yml --tags hardware_audit
   ```
2. Configure Tailscale ACL tags (`tag:control-plane`, `tag:worker`)
3. Verify TimescaleDB on HA Yellow (create `telemetry` DB)
4. Create `facts.d/` directories with hardware capabilities
5. Generate SOPS-encrypted secret templates

**Validation**:
- [ ] `/etc/ansible/facts.d/*.json` exists on all hosts
- [ ] `ansible-inventory --list` shows all hosts
- [ ] TimescaleDB: `psql -c "SELECT 1"` works
- [ ] Tailscale: `tailscale status` shows all nodes

**Exit Criteria**: Hardware facts available, SOPS secrets template ready.

**Estimated Time**: 30 minutes

---

### Phase 1: Core Infrastructure

**Goal**: Deploy storage spine (Garage, NATS) and databases (Supabase, Oxigraph).

**Pulumi Stacks**:
```bash
# Create new Nx project
bunx nx g @nx-extend/pulumi:init ai-infrastructure

# Deploy Phase 1 components
bunx nx run ai-infrastructure:deploy --stack phase1-core
```

**Components**:
- NATS + JetStream (with streams)
- Garage (S3-compatible storage)
- Supabase Postgres + pgvector
- Oxigraph (knowledge graph)
- LiteLLM proxy (without backend yet)

**Validation**:
```bash
# NATS
kubectl exec -n ai-infrastructure deploy/nats -- nc -zv localhost 4222

# Garage
aws s3 ls --endpoint-url http://localhost:3900

# Supabase
kubectl exec -it deploy/supabase-postgres -- psql -U postgres -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# Oxigraph
curl http://oxigraph.ai-infrastructure.svc.cluster.local:7878/
```

**Exit Criteria**:
- [ ] All pods `Running`
- [ ] NATS streams created (`INGEST`, `EMBED`, `KG`, `TELEMETRY`)
- [ ] Garage accepts S3 operations
- [ ] Supabase: `pgvector` extension installed, `embeddings` table exists
- [ ] Oxigraph: SPARQL endpoint responds

**Estimated Time**: 45 minutes

---

### Phase 2: Data Pipeline

**Goal**: Deploy ingestion and processing pipeline (Docling, Cognee).

**Components**:
- Docling workers (with HPA)
- Cognee/KG pipeline workers
- NATS consumers (all services)

**Validation**:
```bash
# Trigger test ingestion
echo '{"source_uri": "s3://raw-documents/test.pdf"}' | \
  kubectl exec -it deploy/nats -- nc localhost 4222

# Verify flow
# 1. Docling processes
# 2. Garage has processed artifacts
# 3. Supabase has embeddings
# 4. Oxigraph has triples
```

**E2E Test**:
```typescript
// tests/integration/document-pipeline.test.ts
describe('Document Pipeline', () => {
  it('should ingest PDF and produce embeddings', async () => {
    // Upload test PDF
    await garage.putObject('raw-documents/test.pdf', testPdfBuffer);

    // Trigger NATS event
    await nats.publish('doc.ingest.requested', {
      source_uri: 's3://raw-documents/test.pdf',
    });

    // Wait for completion (poll NATS)
    await waitForNatsEvent('kg.upsert.completed');

    // Query Supabase
    const embeddings = await supabase.query('SELECT COUNT(*) FROM embeddings');
    expect(embeddings[0].count).toBeGreaterThan(0);

    // Query Oxigraph
    const triples = await oxigraph.query('SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }');
    expect(triples[0].count).toBeGreaterThan(0);
  });
});
```

**Exit Criteria**:
- [ ] PDF → embeddings → KG flow works
- [ ] HPA scales Docling on load
- [ ] NATS JetStream retains messages
- [ ] OpenObserve shows logs from all services

**Estimated Time**: 60 minutes

---

### Phase 3: AI Inference

**Goal**: Provision Jetson AGX Orin and enable GLM-4.7-Flash inference via llama.cpp.

**Prerequisites**:
- Jetson AGX Orin 64GB hardware
- JetPack 6.x installed
- Tailscale SSH access to Jetson
- GLM-4.7-Flash GGUF model downloaded

**Tasks**:
1. `tailscale ssh jetson`
2. Run Ansible playbook for Jetson:
   ```bash
   ansible-playbook -i inventory/ jetson.yml --tags llama-cpp
   ```
3. Download GLM-4.7-Flash GGUF model:
   ```bash
   wget https://huggingface.co/api/models/THUDM/glm-4-9b-chat-gguf/resolve/main/glm-4-9b-chat-q5_k_m.gguf \
     -O /models/glm-4-9b-chat.gguf
   ```
4. Update LiteLLM config to point to llama-server
5. Re-deploy Phase 2 with llama.cpp backend

**Validation**:
```bash
# From Jetson
curl http://localhost:8080/health

# From k3s cluster (via Tailscale)
curl http://jetson.tailnet-name.ts.net:8080/v1/models

# Test inference
curl http://jetson.tailnet-name.ts.net:8080/v1/chat/completions -d '{
  "model": "glm-4-9b-chat",
  "messages": [{"role": "user", "content": "test"}],
  "max_tokens": 10
}'
```

**Exit Criteria**:
- [ ] llama.cpp built with CUDA (sm_87) on Jetson
- [ ] llama-server systemd service running
- [ ] GLM-4.7-Flash model loads successfully
- [ ] LiteLLM routes to llama.cpp via tailnet
- [ ] Inference responds at 5-12 tokens/sec
- [ ] Embeddings: generated via model (if embedding-capable variant)

**Estimated Time**: 90 minutes

---

### Phase 4: Tooling & Agents

**Goal**: Deploy developer tooling (Promptfoo, MCP Context Forge, OpenClaw clients).

**Components**:
- Promptfoo (k8s Job for evals)
- MCP Context Forge (tool server)
- OpenClaw (client-side, not k8s)

**Validation**:
```bash
# Promptfoo eval
just promptfoo-eval

# MCP server
curl http://mcp-forge.ai-infrastructure.svc.cluster.local:8000/health

# OpenClaw (local)
openclaw --query "test search" --endpoint http://litellm:4000
```

**Exit Criteria**:
- [ ] Promptfoo runs evals successfully
- [ ] MCP Context Forge exposes tools
- [ ] OpenClaw can query vector + graph
- [ ] Full E2E: query → retrieve → synthesize

**Estimated Time**: 45 minutes

---

### Phase Summary

| Phase | Components | Validation | Cumulative Time |
|-------|------------|------------|-----------------|
| 0 | Ansible + Hardware Audit | Facts exist, SOPS ready | 30 min |
| 1 | Core spine (NATS, Garage, Supabase, Oxigraph) | All pods running, DBs accept queries | 45 min |
| 2 | Data pipeline (Docling, Cognee) | PDF → embeddings → KG | 60 min |
| 3 | AI inference (Jetson + llama.cpp) | GLM-4.7-Flash serves, tool calling works | 90 min |
| 4 | Tooling (Promptfoo, MCP, OpenClaw) | Full E2E query flow | 45 min |
| **Total** | **All components** | **Complete platform** | **~4.5 hours** |

---

## 7. Pulumi Implementation Guide

### 7.1 Project Structure

Create new Nx package for AI infrastructure:

```
packages/
└── pulumi-ai-infrastructure/
    ├── Pulumi.yaml              # Stack configuration
    ├── package.json             # Nx project config
    ├── tsconfig.json            # TypeScript config
    ├── src/
    │   ├── index.ts             # Main entry point
    │   ├── hardware.ts          # Hardware audit (Section 4.4)
    │   ├── config/
    │   │   ├── nats.ts          # NATS streams
    │   │   ├── garage.ts        # Garage buckets
    │   │   └── supabase.ts      # Postgres init scripts
    │   ├── components/
    │   │   ├── nats.ts          # NATS Helm chart
    │   │   ├── garage.ts        # Garage Helm chart
    │   │   ├── supabase.ts      # Supabase deployment
    │   │   ├── oxigraph.ts      # Oxigraph deployment
    │   │   ├── litellm.ts       # LiteLLM Helm chart
    │   │   ├── docling.ts       # Docling deployment
    │   │   └── cognee.ts        # Cognee deployment
    │   └── ports/               # Port interfaces (Section 5)
    │       ├── embedding.ts
    │       ├── llm.ts
    │       └── storage.ts
    ├── tests/
    │   └── integration/
    │       └── document-pipeline.test.ts
    └── stacks/
        ├── phase1-core.ts       # Core infrastructure
        ├── phase2-pipeline.ts   # Data pipeline
        ├── phase3-inference.ts  # llama.cpp integration
        └── phase4-tooling.ts    # Developer tools
```

### 7.2 Stack Configuration

**Pulumi.yaml**:
```yaml
name: homelab-ai-infrastructure
runtime: nodejs
description: AI-native homelab platform
config:
  pulumi:tags:
    value: homelab,ai-infrastructure
```

**Stack files** (per phase):
```yaml
# Pulumi.phase1-core.yaml
config:
  kubernetes:context: rancher-desktop
  nats:jetstreamEnabled: true
  garage:replicationFactor: 3
  supabase:memoryPercent: 40
  oxigraph:memoryPercent: 8
```

**SOPS integration**:
```typescript
// Read secrets from SOPS
const sopsSecret = exec.command('sops', [
  '--decrypt', 'infra/ai-infrastructure/garage.env.sops'
]).stdout.trim();

const garageSecret = new k8s.core.v1.Secret('garage-credentials', {
  stringData: {
    's3-access-key': parseSops(sopsSecret, 'S3_ACCESS_KEY'),
    's3-secret-key': parseSops(sopsSecret, 'S3_SECRET_KEY'),
  },
});
```

### 7.3 Dynamic Resource Patterns

**See Section 4.4** for full examples. Key patterns:

- Read hardware facts from `/etc/ansible/facts.d/*.json`
- Calculate resources as percentages
- Apply HPA with hardware-aware thresholds
- Use ConfigMaps to expose hardware profile to pods

---

## 8. Ansible Provisioning

### 8.1 Role Definitions

```
infra/ansible-bootstrap/
├── roles/
│   ├── hardware_audit/          # Section 4.2
│   │   ├── tasks/main.yml
│   │   └── templates/profiles/
│   ├── tailscale/               # Tailscale config
│   │   └── tasks/main.yml
│   ├── k3s/                     # k3s provisioning
│   │   └── tasks/main.yml
│   ├── timescale/               # HA Yellow TimescaleDB
│   │   └── tasks/main.yml
│   └── llama-cpp/               # Jetson llama.cpp (Section 5.8)
│       └── tasks/main.yml
├── inventory/
│   ├── group_vars/
│   │   ├── control-plane.yml
│   │   └── workers.yml
│   └── hosts.yml
└── playbooks/
    ├── homelab.yml              # Master playbook
    ├── audit-hardware.yml
    └── jetson.yml
```

### 8.2 Inventory Setup

**inventory/hosts.yml**:
```yaml
all:
  children:
    control_plane:
      hosts:
        desktop-k3s:
          ansible_host: desktop-k3s.tailnet-name.ts.net
          ansible_user: sprime01
    workers:
      hosts:
        ha-yellow:
          ansible_host: ha-yellow.tailnet-name.ts.net
          ansible_user: root
        jetson:
          ansible_host: jetson.tailnet-name.ts.net
          ansible_user: jetson
```

**inventory/group_vars/control-plane.yml**:
```yaml
homelab_zone: control_plane
k3s_enabled: true
garage_replication: 3
postgres_ram_percent: 40
```

### 8.3 Hardware Audit Playbook

**See Section 4.2** for full playbook. Usage:
```bash
# All hosts
ansible-playbook -i inventory/ playbooks/audit-hardware.yml

# Specific host
ansible-playbook -i inventory/ playbooks/audit-hardware.yml --limit jetson
```

---

## 9. Security & Hardening

### 9.1 SOPS+Age Integration

**Secret Files**:
```
infra/ai-infrastructure/
├── garage.env.sops
├── supabase.env.sops
├── nats.env.sops
├── litellm.env.sops
└── timescale.env.sops
```

**.sops.yaml** (already exists in repo, extend):
```yaml
creation_rules:
  - path_regex: infra/ai-infrastructure/.*\.env\.sops$
    age: >-
      AGE_KEY_1,AGE_KEY_2
    encrypted_suffix: env
```

**Usage**:
```bash
# Encrypt
sops --encrypt --age "$AGE_RECIPIENT" \
  infra/ai-infrastructure/garage.env > infra/ai-infrastructure/garage.env.sops

# Decrypt (via just recipe)
just sops-decrypt infra/ai-infrastructure/garage.env.sops

# Edit
sops infra/ai-infrastructure/garage.env.sops
```

### 9.2 HOMELAB Guard Pattern

**Pulumi Stack Guard**:
```typescript
// src/index.ts
const homelab = config.require('HOMELAB');

if (homelab !== '1') {
  throw new Error(
    'HOMELAB != 1: Refusing to deploy. Set HOMELAB=1 for control-plane operations.'
  );
}

console.log('HOMELAB=1 confirmed: Proceeding with deployment...');
```

**Ansible Guard**:
```yaml
# roles/ollama/tasks/main.yml
- name: Check HOMELAB guard
  ansible.builtin.fail:
    msg: "HOMELAB != 1: Refusing to provision Jetson"
  when: lookup('env', 'HOMELAB') != '1'
```

### 9.3 Tailnet Trust Boundaries

**ACL Policy** (Tailscale):
```json
{
  "tagOwners": {
    "tag:control-plane": ["autogroup:admin"],
    "tag:worker": ["autogroup:member"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:control-plane"],
      "dst": ["tag:worker:*"]
    },
    {
      "action": "accept",
      "src": ["tag:control-plane"],
      "dst": ["tag:control-plane:*"]
    },
    {
      "action": "accept",
      "src": ["tag:worker"],
      "dst": ["tag:control-plane:4000"]  // LiteLLM only
    }
  ]
}
```

**Service Exposure**:
- All k3s services: ClusterIP only
- External access: Via Tailscale (`service.namespace.tailnet-name.ts.net`)
- No public Ingress/LoadBalancer

---

## 10. Resource Management

### 10.1 Memory Budget (32GB Desktop)

**Baseline (Always-on)**: 14-18GB
**Burst (Peak)**: Up to 28-30GB
**Headroom**: 2GB minimum

**Breakdown** (from Section 3.3):
| Service | RAM (GB) | % of 32GB |
|---------|----------|-----------|
| k3s + system | 2-4 | 6-12% |
| NATS + JetStream | 1-2 | 3-6% |
| Supabase Postgres | 6-10 | 19-31% |
| Oxigraph | 1-2.5 | 3-8% |
| LiteLLM | 0.5-1 | 2-3% |
| OpenObserve | 1-2 | 3-6% |
| Docling (burst) | 3-6/replica | 9-19% |
| Cognee (burst) | 2-6/replica | 6-19% |

### 10.2 HPA Configurations

**Docling**:
```yaml
minReplicas: 1
maxReplicas: 3
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Cognee**:
```yaml
minReplicas: 1
maxReplicas: 2
metrics:
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 10.3 Hardware-Tuned Configs

**See Section 4.3** for tuning profiles. All resources use percentages:

- Postgres: 40% of RAM (32GB → 12.8GB, 16GB → 6.4GB)
- NATS: 20% of RAM (32GB → 6.4GB, 16GB → 3.2GB)
- Oxigraph: 8% of RAM (32GB → 2.5GB, 16GB → 1.3GB)

**Portable across machines**.

---

## 11. Testing & Validation

### 11.1 Test Strategy

| Test Type | Tool | Purpose |
|-----------|------|---------|
| **Unit** | `pulumi test` | Validate resource configuration |
| **Integration** | pytest + kubernetes_asyncio | Verify pod communication |
| **E2E** | Custom test harness | Full pipeline validation |
| **Health** | Kubernetes probes | Liveness/readiness |

### 11.2 Health Checks

**All components** define:
- `livenessProbe`: Is the process running?
- `readinessProbe`: Is it serving traffic?

**Example patterns** (Section 5).

### 11.3 Hardware Validation Tests

**tests/python/test_hardware_audit.py**:
```python
import pytest
import json

def test_hardware_facts_exist(host):
    """Ansible wrote hardware facts"""
    facts_file = '/etc/ansible/facts.d/homelab.fact'
    assert host.file(facts_file).exists
    facts = json.loads(host.file(facts_file).content_string)
    assert 'total_ram_mb' in facts
    assert facts['total_ram_mb'] > 0

def test_postgres_memory_tuned(host):
    """Postgres uses 40% of RAM"""
    total_ram = int(host.check_output('free -b | grep Mem | awk \'{print $2}\'').strip())
    postgres_limit = int(host.check_output(
        "kubectl get deploy supabase-postgres -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}'"
    ).strip().replace('Gi', '')) * 1024 * 1024 * 1024

    expected = total_ram * 0.40
    assert abs(postgres_limit - expected) / expected < 0.10  # Within 10%
```

**Run**:
```bash
devbox shell
pytest tests/python/test_hardware_audit.py -v
```

---

## 12. Operational Procedures

### 12.1 Deployment

**Initial Setup**:
```bash
# Phase 0: Hardware audit
just ansible-hardware-audit

# Phase 1-4: Pulumi stacks
just pulumi-up --stack phase1-core
just pulumi-up --stack phase2-pipeline
just pulumi-up --stack phase3-inference
just pulumi-up --stack phase4-tooling
```

**Updates**:
```bash
# Preview changes
just pulumi-preview --stack phase2-pipeline

# Apply
HOMELAB=1 DEPLOY_CONFIRM=yes just pulumi-up --stack phase2-pipeline
```

### 12.2 Monitoring

**OpenObserve Dashboard**:
- Logs from all pods (via Fluent Bit)
- Metrics (CPU, memory, NATS consumer lag)
- Traces (Logfire SDK + oTel)

**Key Metrics**:
- NATS consumer lag (should be < 100 messages)
- Pod restarts (should be 0)
- Memory usage (should stay under limits)
- P95 query latency (Supabase, Oxigraph)

### 12.3 Troubleshooting

**NATS Consumer Lag**:
```bash
kubectl exec -n ai-infrastructure deploy/nats -- \
  nats consumer info INGEST CONSUMER_NAME
```

**Postgres Memory Pressure**:
```bash
kubectl top pod -l app=supabase-postgres
# Reduce concurrent Docling jobs if > limit
```

**llama.cpp Unreachable**:
```bash
# From Jetson
tailscale status
curl http://localhost:8080/health
systemctl status llama-server

# From k3s cluster (via Tailscale)
curl http://jetson.tailnet-name.ts.net:8080/health

# Check logs
journalctl -u llama-server -n 50
```

**Docling OOM**:
```bash
# Check HPA
kubectl get hpa docling

# Increase memory limit
just pulumi-up phase2-pulumi --diff
```

---

## 13. Appendices

### A. Dependencies & Versions

| Component | Version | Language | License |
|-----------|---------|----------|---------|
| NATS | 2.10-alpine | Go | Apache 2.0 |
| Garage | latest | Rust | AGPL-3.0 |
| Supabase Postgres | 15.1.0.147 | C | PostgreSQL |
| pgvector | 0.5.0 | C | PostgreSQL |
| Oxigraph | latest | Rust | MIT OR Apache-2.0 |
| LiteLLM | latest | Python | Apache 2.0 |
| Docling | latest | Rust | MIT |
| Cognee | latest | Python | Apache 2.0 |
| llama.cpp | latest (b1708+) | C++ | MIT |
| Promptfoo | latest | TypeScript | MIT |
| OpenObserve | latest | Rust | AGPL-3.0 |
| OpenTelemetry | 1.x | Go/Python | Apache 2.0 |
| Pulumi | 3.x | TypeScript | Apache 2.0 |
| Nx | 22.x | TypeScript | MIT |
| Ansible | 10.x | Python | GPL-3.0 |
| SOPS | 3.x | Go | MPL-2.0 |
| Age | 1.x | Go | BSD-3-Clause |
| Tailscale | 1.x | Go | BSD-3-Clause |

### B. NATS Subject Schema

| Subject | Payload | Publisher | Subscriber |
|---------|---------|-----------|------------|
| `doc.ingest.requested` | `{source_uri, metadata}` | CLI/webhook | Docling |
| `doc.ingest.extracted` | `{garage_key, structure}` | Docling | Chunker |
| `doc.chunked` | `{chunks[], doc_id}` | Chunker | Embedder |
| `embed.requested` | `{chunk_id, text}` | Embedder | Embedder (internal) |
| `embed.completed` | `{chunk_id, vector}` | Embedder | KG worker |
| `kg.upsert.requested` | `{entities[], relations[]}` | KG worker | KG worker (internal) |
| `kg.upsert.completed` | `{triples_count}` | KG worker | All (signal) |
| `telemetry.ha.*` | `{entity_id, value, ts}` | TimescaleDB bridge | Analytics |

### C. Acceptance Criteria by Phase

**Phase 0**:
- [ ] Hardware facts written to `/etc/ansible/facts.d/`
- [ ] SOPS secrets templates created
- [ ] Tailscale ACL tags configured

**Phase 1**:
- [ ] NATS: 4 streams created
- [ ] Garage: 3 buckets accessible via S3
- [ ] Supabase: pgvector enabled, `embeddings` table exists
- [ ] Oxigraph: SPARQL endpoint responds
- [ ] LiteLLM: health check passes

**Phase 2**:
- [ ] Docling: processes PDF → Garage
- [ ] Cognee: chunks → embeddings → KG
- [ ] E2E: PDF input → embeddings output
- [ ] HPA: Docling scales on CPU > 70%

**Phase 3**:
- [ ] llama.cpp: built with CUDA (sm_87) on Jetson
- [ ] llama-server: systemd service running
- [ ] GLM-4.7-Flash: model loads successfully
- [ ] LiteLLM: routes to llama.cpp via tailnet
- [ ] Inference: responds at 5-12 tokens/sec
- [ ] Tool calling: JSON mode works correctly

**Phase 4**:
- [ ] Promptfoo: eval runs successfully
- [ ] MCP Context Forge: tools exposed
- [ ] OpenClaw: queries work
- [ ] E2E: query → retrieve → synthesize

### D. Hardware Audit Output Schema

**`/etc/ansible/facts.d/homelab.fact`**:
```json
{
  "total_ram_mb": 32768,
  "cpu_cores": 8,
  "architecture": "x86_64",
  "os_family": "Debian"
}
```

**`/etc/ansible/facts.d/cpu_capabilities.json`**:
```json
{
  "flags": ["fpu", "avx", "avx2", "ssse3"],
  "has_avx": true,
  "has_avx2": true,
  "has_avx512": false,
  "has_neon": false
}
```

**`/etc/ansible/facts.d/gpu_info.json`**:
```json
{
  "has_gpu": false
}
```

**Or with GPU**:
```json
{
  "has_gpu": true,
  "gpu_name": "NVIDIA Orin",
  "gpu_vram_mb": 32768
}
```

---

**Document End**

Generated for homelab AI infrastructure implementation. Ready for AI agent execution.
