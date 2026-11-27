# DBSCTR2 Domain Module: Cloud / Platform / IaC

**Applies when:** Task involves infrastructure-as-code (Pulumi, Terraform), cloud resources (GCP, AWS,
Hetzner), deployment (Kamal, k8s), scaling (KEDA), networking (firewalls, Tailnet), or platform services
(managed databases, object storage, registries).

This module extends Phases 1 and 4 of core DBSCTR2 with cloud/platform-specific patterns.

---

## Phase 1 Extensions (Domain)

### Infra-as-Domain-Types

Cloud resources ARE domain concepts. Every IaC component returns a typed, documented output:

```python
@dataclass
class GkeOutput:
    """Output of create_gke_cluster().

    Provides the GKE cluster resource and Fleet metadata needed by
    downstream components (K8s provider, Helm releases, KEDA).
    """
    cluster: container.Cluster
    endpoint: pulumi.Output[str]
    ca_cert: pulumi.Output[str | None]
    membership_id: pulumi.Output[str]
```

**Rules for component outputs:**
- Replace ad-hoc tuples, dicts, and raw resource references with typed dataclasses
- Each field has a docstring explaining what downstream consumers need it for
- TYPE_CHECKING imports for Pulumi resource types (avoid import-time SDK loading)
- Group outputs by bounded context (GKE, Storage, Networking, Identity, Orchestration)

### Resource Topology

Sketch the dependency graph of infrastructure components:

```
IaC Component Graph:
  create_iam() → WorkloadIdentityOutput
    ↓ (SA bindings)
  create_gke_cluster() → GkeOutput
    ↓ (k8s provider)
  create_shared_infra(gke) → SharedInfraOutput (postgres, redis, keda)
    ↓ (connection strings)
  create_workload(shared, identity) → WorkloadOutput
    ↓ (application service)
  create_tailnet_access(gke) → AccessOutput (ingress)
```

Document dependency flow — which component output feeds which downstream component's input.
This IS the infra lineage.

### Environment Model

Declare environments upfront:

| Environment | Purpose | Differences from prod |
|-------------|---------|----------------------|
| **prod** | Live workloads | Full resources, real data, alerts enabled |
| **dev** | Local development | Docker Compose, minimal resources, mocked externals |
| **staging** (if exists) | Pre-prod validation | Reduced scale, prod-like topology |

**Rule:** Pipeline logic and IaC component logic MUST be environment-agnostic. Differences handled
ONLY by: Pulumi stack config, env vars, and resource sizing parameters.

### ADR Practice

When an infrastructure decision has meaningful tradeoffs, record it:

```
docs/adr/ADR-NNN-<slug>.md

Format:
- Title
- Status (proposed / accepted / superseded by ADR-NNN)
- Context (what problem, what constraints)
- Decision (what we chose)
- Consequences (tradeoffs accepted)
```

Reference ADRs in code comments and IaC component docstrings (e.g., "ADR-NNN stateful
resource protection"). This creates bidirectional traceability.

---

## Phase 4 Extensions (Contract)

### Deletion Protection Contracts

Every stateful resource (databases, buckets, volumes) requires documented protection:

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| **Resource-level** | `protect=True` (Pulumi) / `deletion_protection` | Prevent accidental `pulumi destroy` |
| **Retain-on-delete** | `retain_on_delete=True` | If removed from code, orphan don't destroy |
| **Force-destroy guard** | `force_destroy=False` | Prevent deletion of non-empty buckets/DBs |

**Rule:** All three layers required for production stateful resources. Document which ADR mandates this.

### Identity Contracts

| Principle | Implementation |
|-----------|---------------|
| **Workload Identity over key-files** | K8s SA → GCP SA binding; no JSON key files in pods |
| **Least-privilege IAM** | Each SA gets only the roles it needs; document role list |
| **Protected bindings** | IAM bindings set `protect=True` to prevent accidental removal |
| **Multi-org WIF** | Attribute conditions restrict cross-org token exchange |

Example contract:
```
## Identity Contract: example-worker SA
- Roles: only the actions required on the example workload's selected resources
- Binding protection: all protect=True
- Access method: Workload Identity (no key files)
- K8s SA: example-worker in example-workloads namespace
- ADR: ADR-NNN (identity access boundaries)
```

### Blast-Radius Contracts

Limit the damage any single misconfiguration can cause:

| Contract | Implementation |
|----------|---------------|
| **Firewall allow-list** | Only SSH + HTTP(S) + ICMP inbound; all else blocked |
| **Network isolation** | Private cluster endpoint; access via Connect Gateway or Tailnet only |
| **Namespace isolation** | Each workload in its own K8s namespace; no cross-namespace access without explicit NetworkPolicy |
| **Volume locality** | Server location == volume location (invariant; prevent cross-region latency/cost) |

### Locality Invariants

Physical constraints that MUST be enforced:

```python
# Contract: volume must be in same location as server
assert volume.location == server.location, "Volume/server location mismatch"

# Contract: builder architecture must match server type
# cpx11 = x86_64 → Kamal builder.arch: amd64
```

Document these in spec as invariants; enforce via assertions in IaC code or Pulumi policy packs.

### Cost Contracts

Treat cost like volume bounds in data pipelines:

| Contract | Example |
|----------|---------|
| **Instance ceiling** | Server type ≤ cpx21 in dev; ≤ cpx41 in prod |
| **Storage ceiling** | Volume ≤ 50GB (resize-on-demand, never over-provision) |
| **Scale-to-zero** | KEDA cron scaler: 0 replicas outside work window; alert if pods running off-hours |
| **Autoscale bounds** | min=0, max=3 for workers; never unbounded |

### Scale-to-Zero / Cost-Optimization Patterns

| Pattern | When to use | Implementation |
|---------|-------------|----------------|
| **KEDA Cron Scaler** | Batch workloads with known schedule | ScaledObject with cron trigger (e.g., an explicitly configured UTC maintenance window) |
| **KEDA HTTP Scaler** | Request-driven apps with idle periods | Scale to 0 when no HTTP traffic |
| **Spot/Preemptible** | Fault-tolerant batch jobs | Node pool with spot VMs + Prefect retries |
| **Volume detach** | Dev environments | Detach volumes when server stopped |

### State Persistence Contracts

| Resource | Contract |
|----------|----------|
| **Block volume** | Survives server destruction; attached via IaC with automount |
| **GCS bucket** | Triple-layer deletion protection; lifecycle rules for archival |
| **Database** | Volume-backed; backup schedule documented; restore procedure tested |
| **Secrets** | Pulumi state or external secret manager; never in code/env files committed to git |

### Deployment Contracts (Kamal / K8s)

| Contract | Rule |
|----------|------|
| **Zero-downtime deploy** | Rolling update or blue-green; health check must pass before traffic shift |
| **Rollback procedure** | Document how to revert (Kamal: `kamal rollback`; k8s: previous ReplicaSet) |
| **Health checks** | Liveness + readiness probes defined; startup probe for slow-init containers |
| **Resource limits** | CPU/memory requests and limits set for all containers; no unbounded pods |
| **Image provenance** | Images from own Artifact Registry; tag = git SHA; no `:latest` in prod |

### Audit & Compliance Contracts

| Contract | Implementation |
|----------|---------------|
| **Data access audit logging** | Enabled on all storage buckets handling user data |
| **IAM audit** | Changes to IAM bindings trigger alert |
| **No hardcoded credentials** | Secrets via env injection (Pulumi config, 1Password, k8s secrets); scan for leaked creds |
| **Encryption at rest** | Default for managed services; explicit for self-managed (volume encryption) |

---

## Rules (Cloud / Platform)

- Every IaC component returns a typed dataclass output — never raw resources or dicts
- All stateful resources have triple-layer deletion protection (or documented exception with ADR)
- Workload Identity over key-files — no SA JSON keys in containers
- All IAM bindings are protected (`protect=True`) and documented per-SA
- Server/volume/resource locality is an enforced invariant, not a suggestion
- Cost bounds are explicit contracts: instance types, autoscale ceilings, scale-to-zero windows
- Single Pulumi project per logical platform; stacks separate environments
- Private-by-default networking; public access requires explicit allow-list + ADR justification
- Secrets never committed to git — use Pulumi config (encrypted), external secret managers, or 1Password injection
- ADRs required for: new cloud provider, access-model changes, cost-significant architecture decisions, deletion-protection exceptions
- Infrastructure changes go through same DBSCTR2 pipeline as application code — Domain types first, then contracts, then implementation

---

## Worked Example: Synthetic Application Server

The following values are illustrative, not a deployed environment inventory.

```
# Domain (Phase 1)
Component: example_app_server (provider and size selected by the project)
Volumes: example-web-data, example-api-data
Network: example-app-firewall
Deployment: rolling application deployment
Topology: application server with persistent data volumes

# Contracts (Phase 4)
Locality: server.location == volume.location
Architecture: application build target matches server architecture
Firewall: only explicitly approved management and application ports are reachable
Volume persistence: survives server replacement
Cost ceiling: selected by project policy; increases require an explicit decision
State: persistent data stays outside ephemeral application storage
Deployment: health checks pass before traffic moves; documented rollback
Secrets: injected from a secret manager; never in Git
```

## Worked Example: Synthetic Managed Cluster

```
# Domain (Phase 1)
Components: managed cluster, example storage bucket, workload identities
Environments: production and isolated development
ADRs: project-owned decisions for access, retention, scaling and deletion protection

# Contracts (Phase 4)
Deletion protection: documented safeguards for every stateful resource
Identity: short-lived workload identity for service access
Network: private endpoint with explicitly authorized administration access
Scale: project-defined minimum, maximum and optional idle schedule
Audit: data-access logging on resources holding protected data
Registry: example.invalid/project/images; immutable image references
Secrets: injected at runtime, absent from source and image layers
```
