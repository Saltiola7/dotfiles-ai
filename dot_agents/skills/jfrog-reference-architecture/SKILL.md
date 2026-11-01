---
name: jfrog-reference-architecture
description: >-
  Plan actual JFrog Artifactory/Xray topology, sizing, hosting, HA or recovery
  using current official reference architecture. Preserve the selected SaaS,
  self-managed, host, Podman or Kubernetes target; planning requires no CLI login.
metadata:
  role: workflow
---

# JFrog reference architecture

Plan the selected JFrog deployment using relevant current
[official reference architecture](https://jfrog.com/reference-architecture/).
Resolve hosting model, supported target and material workload/recovery needs from
existing project evidence before asking for missing decisions. Planning does not
authorize installation, cloud provisioning, a Kubernetes migration or live calls
to a JFrog instance.

Preserve the user's selected runtime. Kubernetes/Helm guidance applies when that
is the selected supported route; do not make it the universal default for host,
Podman, SaaS or other requirements. Verify official support for the exact chosen
platform/version and report unsupported or unverified routes honestly.

Use [documentation access](references/doc-access.md) to fetch the smallest
relevant official pages. Read the full reference dump only for an actual
cross-site/broad comparison that needs it; cache relevant content within the
current conversation rather than injecting the entire manual into every task.
Cite the specific public page supporting each sizing, support or topology claim.
Unavailable documentation is an evidence gap; do not invent sizing values or
request blanket runtime permission changes to bypass a denied fetch.

For detailed sizing, topology, deployment and output steps, read the matching
section of the [retained workflow](references/upstream-workflow.md). Use existing
JFrog base guidance only if the task also needs actual platform operations.
A CLI, configured server, MCP connection and plugin are not prerequisites for
planning. Native package/configuration and infrastructure lifecycle owners remain
authoritative for any separately requested implementation.
