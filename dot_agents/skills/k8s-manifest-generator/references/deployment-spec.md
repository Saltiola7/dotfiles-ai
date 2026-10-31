# Deployment design and diagnostic reference

Use this resource for the actual supported Kubernetes distribution/version.
Examples describe field relationships and do not select images, namespace,
replicas, resource values, security exceptions or a production release. Validate
current API/admission support with project-selected authorities.

## Identity, selectors and ownership

An apps/v1 Deployment owns ReplicaSets and their Pods. Keep its selector stable
and matching template labels; a selector change can require replacement rather
than an ordinary rollout. Use ownership/revision evidence when distinguishing
old and new Pods. Labels used for discovery need not all be selector labels.
An HPA or another controller can own replica count; do not create competing field
owners or repeatedly overwrite its decision.

A representative shape is:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: <workload-name>
  namespace: <namespace>
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: <workload-name>
  template:
    metadata:
      labels:
        app.kubernetes.io/name: <workload-name>
    spec:
      serviceAccountName: <selected-service-account>
      containers:
        - name: application
          image: <approved-image>@sha256:<digest>
          ports:
            - name: http
              containerPort: 8080
```

Complete only the fields required by the workload and project policy. A digest
illustrates immutable identity; image provenance and supported architecture still
need their own evidence. Do not infer the service account from an ambient default.

## Rollout and availability

RollingUpdate `maxSurge` and `maxUnavailable` interact with replicas, capacity,
readiness, disruption policy and application compatibility. A zero-unavailable
setting alone does not guarantee zero downtime. Recreate can be appropriate for
a contract that tolerates interruption; do not adopt it to bypass constraints.

`minReadySeconds` controls how long readiness must hold before availability;
`progressDeadlineSeconds` exposes stalled progress rather than automatically
repairing the workload. A successful API update or completed controller rollout
still does not prove the user-facing service meets its acceptance criteria.

Review old/new application and serialized-data compatibility for a rolling change.
A rollback of a Deployment does not automatically reverse database or volume
changes. Preserve selected field management/GitOps ownership and record recovery.

## Resources, placement and storage

Requests influence scheduling; limits and runtime/cgroup behavior constrain
execution. Choose values from actual workload evidence and policy. CPU limits,
fixed ratios or a universal minimum are not imposed by this guide. Account for
init/sidecar containers, quotas, node capacity and target-version features when
making a scheduling or capacity claim.

Node selectors, affinity/anti-affinity, topology spread and taints/tolerations
express different placement constraints. A toleration permits a placement but
does not select a node. Do not remove constraints solely to make a Pending Pod run.

Choose PVC access mode, storage class, topology, backup/retention and restore
responsibility with the data owner. A sample provider's storage class is not
portable. Mount path, file permissions and security-context changes can alter
persistent-data access; preserve application contracts and recovery evidence.
An emptyDir lifetime differs from persistent storage; neither is a backup.

## Startup, readiness and shutdown

Startup, readiness and liveness probes have distinct purposes. Configure only
appropriate probes using meaningful application endpoints/commands. Startup
probes can protect slow initialization, readiness controls traffic eligibility,
and liveness can restart an unhealthy container. Do not use liveness as a
substitute for every downstream dependency failure.

Review timing/budgets against measured startup and failure behavior, including
termination grace and application signal handling. Kubernetes handles container
termination; avoid a generic preStop recipe that sleeps and sends an additional
kill to PID 1. Use a hook only when its bounded behavior belongs to the service
contract, and include it in the termination budget.

## Configuration, identities and security

Use ConfigMaps only for non-sensitive values. Secret references and mounted
credentials follow the selected secret authority and rotation mechanism. Do not
commit generated credential data or assume a pod environment refreshes when the
underlying Secret changes; application reload behavior needs verification.

Apply relevant non-root identity, capabilities, privilege-escalation, filesystem,
seccomp and admission requirements. Values such as UID, fsGroup and a read-only
root filesystem depend on the image and required writable paths. Do not grant
privilege or disable admission to make a copied example run. Automounting an API
credential is a workload decision, not an automatic need for every Pod.

## Bounded diagnostics and validation

Use explicit context/namespace and select the affected revision/resource. For
example, after target and workload identity are resolved:

```bash
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get deployment "$WORKLOAD" -o jsonpath='{.status.conditions}'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get pods --selector "$SELECTOR" \
  -o 'custom-columns=NAME:.metadata.name,PHASE:.status.phase,NODE:.spec.nodeName'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  logs "$POD" --all-containers --tail=100
```

Build the selector from actual ownership and selector fields, not a convenient
assumed label. Redact configuration/credential data from describe/log output.
Image-pull errors, crash loops, OOM/eviction, failed probes and a progress deadline
need different evidence; exit 137 or an empty log alone does not prove one cause.

Local syntax/rendering, server admission and rollout/service health are separate
claims. Server-side checks contact a real cluster under the selected access
policy. Do not apply changes, create debug Pods or execute inside a workload
merely to complete a guide example. Missing target evidence stays explicit.

## Primary references

- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
