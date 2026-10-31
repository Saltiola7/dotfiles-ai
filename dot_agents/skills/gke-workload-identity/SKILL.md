---
name: gke-workload-identity
metadata:
  version: "1.0.2"
  category: Security
description: Diagnose GKE pod authentication to Google Cloud APIs, including direct workload federation and legacy service-account impersonation. Use for workload identity failures; distinguish Google IAM from Kubernetes RBAC and protect credential output.
---

# GKE Workload Identity Diagnosis

Use for a Pod's Google Cloud identity path, not arbitrary Kubernetes API-server
RBAC failures or general scheduling/crash diagnosis. The current primary owns
scope, authorization, implementation and delivery; this method supplies evidence
and a bounded proposal.

## Establish the path and target

Resolve project ID/number, cluster/location, Kubernetes context and namespace,
Pod, Kubernetes service account (KSA), node/node pool, target resource/API and the
actual sanitized error. Reuse known task facts; do not infer an unknown target
from active configuration or silently select the default namespace.

Direct Workload Identity Federation principal bindings do not require a Google
service account (GSA) annotation. Legacy GSA impersonation does require its own
annotation and impersonation permission. Determine the configured path before
interpreting missing fields. Kubernetes RBAC and Google IAM are separate systems.

## Investigate the applicable boundary

Read [identity diagnostic patterns](references/identity-diagnostics.md) for the
specific symptom:

- Verify the KSA actually used by the Pod, not only the intended template.
- Check the cluster/workload pool and the applicable node-pool metadata mode,
  accounting for Autopilot/Standard and the supported cluster version.
- For direct federation, inspect the actual target principal and resource policy.
  For legacy impersonation, inspect KSA annotation, GSA policy and target access
  as separate checks.
- Distinguish token-exchange/impersonation errors from a target API permission
  failure, networking, credential discovery or metadata-server availability.
- Consider policy inheritance/conditions, deny controls and visibility limits.
  A policy search returning no row is not by itself proof that a role is absent.

Use bounded, explicitly scoped metadata and logs. Preserve unresolved alternatives;
name a confirmed cause only when evidence supports it. Never force a single RCA
or claim another cause was ruled out without an observation that excludes it.

## Protect the evidence

Do not print or persist bearer tokens, credential JSON, API keys or authorization
headers. Do not request a token endpoint merely as connectivity proof. Prefer
non-secret configuration and actual target-service permission results.

A permitted metadata connectivity probe can discard the response body and report
HTTP status for a non-token endpoint, but proves reachability only. Executing
inside a live Pod is itself an operation requiring the relevant task scope and
permissions; do not install tools or create a debug workload incidentally.

## Return a bounded remedy

Identity bindings, KSA annotations, node-pool changes, credential fetching and
cluster configuration are state changes. Diagnose first and return the smallest
reviewable proposal with expected identity, affected resources, recovery path and
confirmation evidence. Existing user authorization persists under the primary;
this skill neither grants new permissions nor creates another approval process.

If logs/access are unavailable or the failure remains unexplained, report the
limitation and the next discriminating check. Do not broaden IAM roles, disable
controls or switch credentials to manufacture success. Required unavailable
validation follows the existing gate ledger.

[Optional attribution](references/attribution.md) is project-selected; loading
this guidance does not alter metrics tags or request headers.
