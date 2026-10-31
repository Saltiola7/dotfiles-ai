---
name: gcloud
metadata:
  version: "1.0.3"
  category: CloudInfrastructureAndServices
description: Construct and inspect Google Cloud CLI operations with version-appropriate syntax, explicit targets and bounded evidence. Use for actual gcloud work, not ordinary client-library code or unrelated cloud tasks.
---

# Google Cloud CLI Guidance

Use the selected native CLI or connected capability without changing provider,
credentials or tooling merely because this skill was loaded. The current primary
retains scope, lifecycle, permissions and gate ownership.

## Resolve context and syntax

Use task/project facts to establish the intended identity, project, resource and
applicable region/zone/location. Active CLI configuration is evidence to compare,
not permission to select an unknown target. Preserve explicit user flags and
report incompatible syntax or material ambiguity instead of silently retargeting.

Check exact leaf-command help against the installed version when constructing
unfamiliar or version-sensitive syntax. Parent-group help does not establish all
leaf flags. If local help is unavailable, use current official documentation for
the applicable version and report the limitation; do not invent flags or install
a CLI solely to complete a lookup. A conceptual plan need not copy a fixed
four-step template or run every possible command first.

## Construct a bounded operation

- Supply project/location and identity flags where supported and relevant; avoid
  persistent `gcloud config set` or kubeconfig changes for incidental context.
- Quote shell arguments correctly or use structured argv. Filters and projections
  have their own syntax; validate them instead of removing quoting to fit an
  example. Scope queries and retain pagination/completeness limitations.
- Request only relevant non-secret fields. Use filters, limits and projections
  appropriate to the question; a small sample is not an inventory of all objects.
- Use a supported preview/validation operation when it meaningfully tests the
  proposed change. A dry-run can still contact remote services and need access.
- `--quiet` is not authorization. Use non-interactive flags only when the action
  and all consequential targets/defaults are already resolved and authorized.
- A successful asynchronous submission is not resource readiness. Retain the
  operation identity, poll within the task's bounded policy, then check relevant
  health/acceptance outcomes before claiming completion.

## Identity, mutation and missing capabilities

CLI login, ADC, impersonation, local configuration and cloud IAM are different
concerns. Preserve the selected authentication path. Never print credential
files, bearer tokens or sensitive configuration as proof of access.

Resource writes, IAM changes, API enablement, billing, deletion and CLI/component
installation require the authority appropriate to the concrete task. Skill
loading grants none. Existing user authorization persists; ask only for genuinely
missing permission or a material unresolved choice. Keep failures visible rather
than switching identities, projects or provider families to get a green result.

## Read only the applicable resource

- [CLI usage](references/cli-usage.md): authentication/configuration distinctions
  and deliberately selected local setup.
- [MCP usage](references/mcp-usage.md): an available Cloud CLI connector's API-host
  project versus command resource project, response status and capability limits.
- [Command patterns](references/command-patterns.md): bounded queries and operation
  evidence examples.
- [Optional attribution](references/attribution.md): only when project policy
  explicitly selects request tagging; no tracking/configuration change by default.

Return the resolved target, proposed/performed operation, actual evidence and
limits to the existing primary. Product guidance can refine a service-specific
question without becoming a second coordinator or validation authority.
