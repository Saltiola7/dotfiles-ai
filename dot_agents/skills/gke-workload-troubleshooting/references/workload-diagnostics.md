# Workload diagnostic patterns

Examples below are scoped diagnostic patterns for the selected Kubernetes/GKE
versions. Verify the exact command's available flags when constructing a concrete
operation. Resolve all variables from current task authority; do not execute
literal placeholders or infer a target from an ambient default. The primary owns
any changes, source control and delivery.

## Evidence collection

Establish project, cluster/location, kubeconfig context, namespace, resource kind/
name and the relevant incident interval. Use user/project timestamps and timezone
when available; an arbitrary fixed window may miss a rollout or earlier failure.
Retain selection, pagination and visibility limits. Prefer narrow metadata before
requesting full manifests or logs containing configuration and secrets.

For a Deployment, inspect the actual selector and affected revision first:

```bash
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get deployment "$WORKLOAD" -o jsonpath='{.spec.selector}'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get pods --selector "$SELECTOR" \
  -o 'custom-columns=NAME:.metadata.name,PHASE:.status.phase,NODE:.spec.nodeName'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get pod "$POD" -o jsonpath='{.status.containerStatuses}'
```

Construct `SELECTOR` from supported matchLabels/matchExpressions and distinguish
old and new ReplicaSets/owner UIDs. Other controllers (StatefulSets, Jobs, DaemonSets)
have different completion/restart contracts; do not treat every completed process
as a failed Deployment. Resolve node/container identity before interpreting logs.

Read bounded current and previous-container logs only when relevant:

```bash
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  logs "$POD" --all-containers --tail=100
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  logs "$POD" --all-containers --previous --tail=100
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get events --field-selector "involvedObject.name=$POD" \
  --sort-by='.metadata.creationTimestamp'
```

A previous log may be unavailable; report that rather than assuming no prior
failure. Redact credential values, authorization headers, personal data and
sensitive configuration before retaining evidence. Node/cluster-wide evidence
needs the applicable access and a bounded reason.

For Cloud Logging, scope to the actual project, cluster, location, resource,
workload and interval. Use documented timestamp filter predicates rather than
assuming generic start/end flags exist. For example, construct a filter including
`resource.type`, `resource.labels.cluster_name`, `resource.labels.location`,
namespace/pod where supported, and `timestamp >= ... AND timestamp < ...`.
Query with an appropriate limit/projection, preserve pagination/retention gaps,
and distinguish no returned match from proof that an event never happened.

## CrashLoopBackOff

Inspect termination reason/code, restart count and events together with the
current and previous logs. A crash loop can follow application/configuration
failure, entrypoint completion under an Always restart policy, missing dependencies,
startup/liveness termination or a resource failure. Exit 137 alone means a killed
process and is not conclusive evidence of a memory-limit OOM.

Compare probe definitions and actual failure events with startup time and the
service contract. Startup probes can protect slow initialization, readiness
controls traffic eligibility, and liveness restarts a container. Increasing delay
or disabling a probe without evidence can conceal the real fault. Distinguish a
running Pod from ready endpoints and successful user-facing behavior.

## Memory and eviction

Correlate `OOMKilled`, container limits/usage and node pressure/eviction evidence.
A container-level cgroup kill, node-level memory exhaustion, eviction and another
SIGKILL cause are different findings. Child-process kills may not appear as the
main container's termination reason; inspect applicable node/runtime evidence
when access and the symptom justify it. Confirm version/cgroup-specific behavior.

Do not infer measured usage from configured limits or a single example. A proposed
memory/CPU change needs the observed workload, capacity/cost consequences and
correctness/recovery checks; a change may move pressure to other workloads.

## ImagePullBackOff

Use the actual event/error to separate:

- An invalid/deleted image, wrong digest/tag or unsupported image architecture.
- Registry DNS/network/perimeter reachability.
- Authentication (for example unavailable credentials) from authorization to the
  actual repository/resource.
- Rate limits, registry availability and a runtime/image-format compatibility issue.

Inspect the intended node/workload image-pull identity and any selected pull-secret
reference without printing Secret content. GKE node service-account/scopes, legacy
registry migration and VPC Service Controls can matter, depending on the target.
A 403 is not permission to grant a broad project role. Return a narrow supported
proposal with the repository, principal and evidence that actually failed.

## Pending and scheduling

Read Pod conditions and scheduler/PVC events. Compare requests with allocatable
capacity, placement constraints, affinity/anti-affinity, taints/tolerations, quotas,
resource classes and storage topology. A WaitForFirstConsumer PVC can be waiting
for scheduling by design. Do not remove constraints or recreate storage to make
scheduling succeed without preserving the intended isolation and persistent data.

## Dependency/network failures

Resolve the intended service name, namespace and port from project-owned source
or configuration. Inspect Service selectors, EndpointSlices, endpoint readiness,
DNS and relevant NetworkPolicies. Empty endpoints may reflect selector/readiness
problems, not only a process that cannot start. Present endpoints prove neither
reachability nor target-service health.

A timeout supports several hypotheses: DNS, routing/policy, target readiness,
application behavior or capacity. Do not synthesize a permissive egress policy
from an offline timeout alone. An execution probe inside an existing Pod, ephemeral
container or new debug Pod needs explicit task scope and suitable tools/image;
it is not metadata inspection. Do not install debug tools or create workloads
incidentally. If evidence is unavailable, give the next discriminating checks.

## Return and recovery

Separate observed facts, supported cause(s), remaining hypotheses and missing
capability. Propose the smallest patch/operation preserving selected identity,
GitOps/resource ownership, data, security and compatibility. The primary handles
existing authorized remediation, commits/PRs and deployment. Verify the actual
post-change outcome (including readiness and relevant service behavior) through
QA rather than treating a plausible YAML patch as recovery evidence.

## Primary sources

- [Deployed workloads](https://cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads)
- [Crash loops](https://cloud.google.com/kubernetes-engine/docs/troubleshooting/crashloopbackoff-events)
- [OOM events](https://cloud.google.com/kubernetes-engine/docs/troubleshooting/oom-events)
- [Image pulls](https://cloud.google.com/kubernetes-engine/docs/troubleshooting/image-pulls)
- [Artifact Registry access](https://cloud.google.com/artifact-registry/docs/access-control)
