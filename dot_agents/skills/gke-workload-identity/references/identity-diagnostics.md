# GKE workload identity diagnostic patterns

Resolve the intended project ID/number, cluster/location, context/namespace,
workload/Pod/KSA, node pool, target resource/API and sanitized error first. Commands
are patterns for the selected versions and authority. All configuration changes
remain proposals returned to the primary; the skill creates no permission or
source-control workflow.

## Actual identity and metadata path

Inspect the live Pod's `serviceAccountName`, namespace, owner and node, rather than
assuming the intended manifest is what ran. For example:

```bash
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get pod "$POD" -o jsonpath='{.spec.serviceAccountName}'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get pod "$POD" -o jsonpath='{.spec.nodeName}'
kubectl --context "$KUBE_CONTEXT" get node "$NODE" \
  -o jsonpath='{.metadata.labels.cloud\.google\.com/gke-nodepool}'
gcloud container clusters describe "$CLUSTER" --project="$PROJECT_ID" \
  --location="$LOCATION" --format='value(workloadIdentityConfig.workloadPool)'
```

For an applicable Standard node pool, inspect its documented
`config.workloadMetadataConfig.mode` with `gcloud container node-pools describe`
using explicit project, cluster and location. Interpret Autopilot versus Standard,
node-pool/runtime and cluster-version restrictions from current product docs.
An unexpected node identity can have several causes; inspect actual configuration
before concluding that an annotation or role is wrong. Fetching credentials or
changing local kubeconfig is a separate state change, not a discovery default.

## Direct principal binding

A direct federated KSA principal can use a supported principal identifier such as:

```
principal://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/PROJECT_ID.svc.id.goog/subject/ns/NAMESPACE/sa/KSA_NAME
```

It does not require a GSA annotation or a legacy workloadIdentityUser binding.
Confirm the actual project number, namespace, KSA and target resource; similarly
named accounts across namespaces/projects are distinct principals. Inspect the
policy at the actual resource and relevant inheritance/conditions. A broad search
is a finding input, not proof that no permission exists or that an observed grant
is effective under deny/organization controls.

## Legacy GSA impersonation

When the selected setup uses `iam.gke.io/gcp-service-account`, inspect the actual
KSA annotation, GSA identity and its IAM policy separately. The legacy binding
commonly grants `roles/iam.workloadIdentityUser` to
`serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA_NAME]` on the intended GSA.
The GSA then needs suitable target-resource access. Do not confuse impersonation
permission with resource permission or Kubernetes API-server RBAC.

An `iam.serviceAccounts.getAccessToken` failure can indicate an impersonation
boundary problem, while a target API 403 can indicate effective resource access
or another applicable control. Distinguish by the actual failing operation and
sanitized error. Do not force a single diagnosis or exclude alternatives without
evidence. Policy visibility/retention gaps stay explicit.

## Metadata service and connectivity

Inspect relevant `gke-metadata-server` health/events/logs on the actual node when
scope/access allows it. Workload startup races, resource pressure, DNS, supported
host-network/runtime behavior and dataplane-specific network paths can differ by
cluster version. Confirm current official requirements before proposing changes.
A fixed service-account count or address/port recipe is not a universal threshold.

Prefer existing non-secret metadata, library errors and target-service permission
results. If an in-Pod connectivity probe is authorized, resolve the intended CONTAINER
and confirm it already has the selected tool. A non-token endpoint can report
status while discarding its body, for example:

```bash
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  exec "$POD" --container "$CONTAINER" -- \
  curl --silent --show-error --connect-timeout 2 --max-time 5 \
  --output /dev/null --write-out '%{http_code}\n' \
  --header 'Metadata-Flavor: Google' \
  'http://169.254.169.254/computeMetadata/v1/'
```

This proves reachability/status only; it does not establish a token identity or
permission on the target API. In-Pod execution is not read-only metadata access.
Never query a bearer-token endpoint just to prove connectivity, print tokens or
headers, inject debug images, or install a package incidentally. Missing permitted
tooling/access remains a capability gap.

Bound logs by target/time and request only relevant fields. Redact credentials,
keys, sensitive configuration and personal data before retaining evidence. Where
Cloud Logging is used, include the actual project/cluster/location and applicable
namespace/pod/resource/time predicates. An absent result can reflect retention,
filtering or visibility rather than absence of an event.

## Version-specific identity behavior

Some legacy clients/operations require an IAM service-account email rather than a
federated principal identifier. An `Invalid form of account ID` error may warrant
checking the selected legacy GSA path and the documented
`iam.gke.io/return-principal-id-as-email` behavior. It is not automatic evidence
that Workload Identity should be disabled or roles broadened. Verify the current
service/client/cluster behavior before proposing an annotation change.

## Remedy and confirmation

Return facts, supported cause(s), unresolved alternatives, source/visibility limits
and a concrete bounded proposal. IAM grants, KSA annotations, node-pool modes and
network changes require the primary's existing task authority and a recovery
plan appropriate to impact. Verify the actual workload identity and target
operation afterward without emitting credential material. Successful token
acquisition alone cannot prove the intended target permission or service health.

## Primary sources

- [Authentication troubleshooting](https://cloud.google.com/kubernetes-engine/docs/troubleshooting/authentication)
- [Workload identity concepts](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [Workload identity configuration](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
