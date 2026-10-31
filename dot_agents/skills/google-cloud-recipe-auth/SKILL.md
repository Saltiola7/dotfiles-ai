---
name: google-cloud-recipe-auth
metadata:
  version: "1.0.2"
  category: GettingStarted
description: Select or diagnose Google Cloud authentication and authorization for humans, applications and federated workloads. Use for identity/ADC/IAM questions; preserve existing credentials, provider and permission boundaries.
---

# Google Cloud Authentication and Authorization

Authentication establishes identity; authorization determines that identity's
permitted actions on a resource. Keep those questions distinct when a request
fails. A loaded skill supplies methods, not permission to log in, change roles,
create keys or alter an authentication provider.

## Establish the identity path

Resolve these facts from the current task and project configuration before asking:
who or what authenticates, where it runs, the target service/resource, and whether
an SDK/client library manages credentials. Ask only when a missing fact changes
the recommendation or authorized scope.

Distinguish:

- Human/workforce identities from application end-user identities.
- CLI credentials from Application Default Credentials (ADC); logging the CLI in
  does not necessarily provide credentials to a local client library.
- An attached service account from a workload-federated principal. A production
  workload can use a supported direct federated identity without a Google service
  account impersonation layer.
- Service accounts from Google-managed service agents.
- Authentication failure from missing permissions, IAM Conditions/deny policy,
  organization controls, network restrictions or a service-specific constraint.

## Select the least-surprising supported path

Preserve the project-selected human/workload mechanism. Prefer supported short-lived or platform-provided credentials over introducing long-lived keys. Reuse
existing client-library ADC support rather than manually exporting tokens.
Federation and impersonation are different mechanisms; direct GKE principal
bindings and legacy KSA-to-GSA impersonation have distinct contracts.

For a concrete setup, identify the required principal, target resource and narrow
permission. An example role is not a universal permission grant. Scope any local
configuration change deliberately; prefer per-command impersonation when it
suffices. Do not change persistent CLI defaults as incidental troubleshooting.

Read [identity methods and examples](references/auth-methods.md) for the relevant
human, workload, federation, ADC or OIDC case. For GKE pod authentication failures,
installed `gke-workload-identity` can supply more specific diagnostic techniques;
Kubernetes API-server RBAC failures remain a separate concern.

## Evidence and execution boundaries

Inspect bounded identity/configuration metadata and actual sanitized errors.
Never emit tokens, API keys, credential JSON or authorization headers. A metadata
server response or successful token acquisition does not by itself establish
permission on the target resource.

Login/ADC creation, key management, IAM bindings, API enablement and workload
configuration are state changes. Carry a concrete proposal to the primary under
existing authorization; do not invent a new approval workflow or repeat a settled
question. Missing access or expired evidence stays a capability gap, not a reason
to broaden roles, switch accounts or manufacture a diagnosis.

Return the selected principal/environment/target, the distinction between observed
facts and hypotheses, a bounded proposed fix and the evidence needed to verify it.
Project policy and QA determine acceptance.

[Request attribution](references/attribution.md) is optional and project-selected;
loading this skill does not enable tracking or change request headers.
