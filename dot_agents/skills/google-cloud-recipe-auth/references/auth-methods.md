# Identity methods and selection evidence

Use only the method relevant to the task. Existing authentication/provider policy
and task authorization control execution. The following examples do not authorize
login, local credential creation, role grants, keys or provider changes.

## Humans and workforce identities

Human administrators/developers can use Google-managed identities, synchronized
federation or Workforce Identity Federation. The organization owns this selection.
CLI login credentials and local Application Default Credentials (ADC) serve
different consumers. Client libraries commonly use ADC; do not infer their
identity solely from a successful CLI call.

For an explicitly selected local setup, inspect the supported method before using
`gcloud auth login` or `gcloud auth application-default login`; both change local
credential state. A headless browser flow requires a real user-mediated identity
step. Never fabricate consent or capture authorization codes in shared evidence.
Prefer existing supported short-lived credentials over new downloaded service-
account keys. Service-account impersonation needs its own authorized permission;
use a per-command impersonation flag when it suffices rather than rewriting
persistent defaults incidentally.

## Production and federated workloads

Choose a supported platform identity with narrow resource access. An attached
custom service account, a direct Workload Identity Federation principal, or
policy-selected service-account impersonation can fit different platforms.
Do not mandate a GSA impersonation layer when direct federation is selected.

A service account is a non-human identity selected for a workload. A service
agent is a Google-managed identity used by a service; they are not interchangeable.
Google default service accounts and broad predefined roles are not automatic
permissions for a new workload.

On Compute Engine and Cloud Run, supported attached identities can supply
credentials through the platform. On GKE, direct workload principal bindings and
legacy KSA-to-GSA impersonation have different configuration and authorization
requirements. External workloads can use federation from their existing identity
provider; it is not equivalent to distributing a static JSON key.

## ADC and credential discovery

Inspect the applicable library/version's documented discovery order. Common ADC
sources include the `GOOGLE_APPLICATION_CREDENTIALS` reference, a local ADC file,
and a supported attached identity's metadata service. A missing, stale or
unintended earlier source can explain why a workload does not use the intended
identity. Inspect non-secret provenance and file metadata; do not print the file
or token. Do not delete a competing credential source until its ownership and
change are resolved within task scope.

A credential authenticates a principal; the principal still needs permission on
the target resource. Quota/billing project, OAuth scope, IAM Conditions, deny
policy, organization controls, network/perimeter restrictions and service-level
rules can be separate causes. Confirm the actual failing boundary rather than
broadening a role after any 403.

## Authorization and end-user applications

Select a suitable existing predefined role when it meets least privilege; a
custom role can be appropriate when predefined roles are too broad. Scope a grant
to the intended resource, principal and condition. Role examples are not approved
grants. Policy search visibility and inheritance limit negative conclusions.

Application end-user authentication is distinct from developer/workforce access.
Identity-Aware Proxy or Identity Platform can address different application
requirements; they do not replace workload authorization automatically.
For an authenticated custom service, distinguish an OAuth access token from an
OIDC identity token and verify the intended audience and service policy through
the selected library. Never print either token as proof.

API keys identify supported API use and have service-specific limits; they do not
universally provide a workload identity. Keep selected keys in the approved
secret authority and apply relevant API/application restrictions. Creating,
rotating or restricting a key remains authorized configuration work.

## Diagnostic return

Report principal type and non-secret identity, execution environment, credential
provenance, target resource, observed failure and uncertainty. A successful local
credential check cannot prove a different production workload or target permission.
Propose the narrowest change and the actual confirmation evidence; preserve
missing access instead of switching identities or providers to hide failure.

## Primary sources

- [Authentication overview](https://cloud.google.com/docs/authentication)
- [ADC](https://cloud.google.com/docs/authentication/application-default-credentials)
- [Service-account impersonation](https://cloud.google.com/docs/authentication/use-service-account-impersonation)
- [Service-account practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Workload Identity Federation for GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
