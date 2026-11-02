---
name: jfrog-setup-package-managers
description: Bind a selected package manager or workspace to an explicit JFrog Artifactory repository using jf setup and workspace binding state. Use for actual Artifactory package routing changes; preserve chosen tools, target and configuration owner.
metadata:
  role: workflow
---

# Artifactory package-manager binding

Use for explicitly requested binding or actual missing Artifactory routing under
an already selected project policy. A manifest's presence alone does not authorize
onboarding, installing packages, changing runtime tools or enabling a plugin hook.

Cover the base `jfrog` skill's target, execution and secret rules once. Preserve
the selected package manager/runtime and one server/repository/project identity.
Use explicit user selection or a verified existing resolver/binding; do not pick
an arbitrary discovered repository or silently replace a selected server.

Read [the binding workflow](references/upstream-workflow.md) for the relevant
branch, [command semantics](references/jf-setup-command.md) before execution and
[binding state](references/workspace-binding.md) when recording a decision. Use
[global cache](references/global-cache-file.md) only if that separately owned
plugin/cache actually exists and matches the selected platform.

`jf setup` writes native package-manager configuration, potentially credentials.
Preview affected paths and preserve existing config owners/preimages. Carry out
the authorized binding without repeated permission requests; resolve missing
material target/authority before mutation. Existing same-repository bindings can
skip unchanged setup, but verify relevant configuration rather than treating a
stale binding as proof of readiness.

Before running reviewed helpers, inspect their contracts and pass data through
quoted argument boundaries. `scripts/check-repo-key.sh` validates printed repo,
server and project values; `scripts/merge-workspace-binding.sh` writes only the
non-secret workspace decision after successful setup. Preserve actual child
status; failure does not update binding or permit a server switch.

Standalone skills do not include the upstream package-resolution SessionStart
hook or its policy renderer. Do not search arbitrary plugin caches for code to
execute. Refresh an already selected hook only through its verified owner, or
report that optional capability unavailable. No CLI install/login, plugin setup,
MCP configuration or global tool upgrade is part of package binding.
