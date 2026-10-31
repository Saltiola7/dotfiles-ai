---
name: gke-workload-troubleshooting
metadata:
  version: "1.0.1"
  category: Containers
description: Diagnose GKE workload failures using bounded status, event and log evidence. Use for crashing, pending or image-pull failures; distinguish verified causes from hypotheses and return fixes to the existing primary.
---

# GKE Workload Diagnosis

Diagnose the affected workload before proposing a change. The diagnostic method
starts with read-only metadata/logs; it grants no cluster/cloud mutation or
separate branch, commit, PR or deployment workflow.

## Resolve the target

Use current user/project authority to establish project, cluster, location,
Kubernetes context, namespace, workload/controller and time window. Compare
ambient CLI/kubeconfig state as evidence; do not silently choose a project,
cluster or `default` namespace. Ask only about a consequential unresolved target.

Fetching cluster credentials changes local kubeconfig. Do not do it merely to
inspect context or because the skill was loaded. Prefer existing correctly scoped
access; report missing capability and carry any setup proposal to the primary.

## Diagnose the failure signature

Read [diagnostic patterns](references/workload-diagnostics.md) only for the
applicable signature:

- **CrashLoopBackOff:** inspect termination reason/code, restart count, current
  and previous bounded logs, startup/liveness behavior and configuration changes.
- **OOMKilled:** distinguish a container limit kill from node pressure/eviction;
  exit 137 alone is not conclusive proof of the cause.
- **ImagePullBackOff:** classify image reference/architecture, registry reachability
  and authentication/authorization from the actual event. Do not grant registry
  roles just because an image cannot be pulled.
- **Pending:** inspect scheduler conditions/events, requests versus capacity,
  selectors, affinity/taints, quotas and storage binding before changing them.
- **Dependency timeouts:** inspect Service/EndpointSlice membership, DNS, intended
  ports and applicable policy; endpoint presence does not prove application health.

Use explicit context and namespace for live Kubernetes queries, and project/
cluster/location/time filters for cloud evidence. Bound output and redact secrets
before retaining or sharing it. Reading a manifest/log can expose literal
credentials; avoid broad dumps when targeted metadata answers the question.

## Preserve uncertainty and the remediation boundary

If access is unavailable, retain observations already supplied, rank hypotheses
only as evidence supports them, and provide the next discriminating checks.
Offline symptoms cannot establish an RCA, justify a permissive NetworkPolicy or
pass required target validation. Avoid repeated connection attempts without new
information; state what remains unverified.

`kubectl exec`, debug containers, credential fetching and resource changes are not
read-only metadata inspection. Use them only within the concrete task's scope and
existing permissions. Do not install tools inside workloads as a diagnostic
shortcut or change identity/project to obtain a passing result.

Return findings with evidence, unresolved alternatives, a scoped patch/operation
proposal and the validation needed to confirm recovery. The primary handles
already-authorized implementation and delivery through the existing lifecycle;
QA retains gate decisions. Do not create or merge a PR merely because the
technique reference includes a remediation example.

[Optional attribution](references/attribution.md) applies only when selected by
project policy; this skill does not enable tracking by default.
