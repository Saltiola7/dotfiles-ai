---
name: jfrog-init
description: Diagnose or prepare an explicitly requested JFrog setup, checking CLI, selected server, project, catalog and native MCP readiness while preserving existing installer and configuration owners.
metadata:
  role: workflow
---

# JFrog setup readiness

Invoke explicitly for JFrog readiness or setup work. This preserves the upstream
manual invocation policy; ordinary skill installation never runs init.

Resolve the selected CLI/client/platform owners first. Distinguish installed
files, compatible CLI, configured identity, reachable APIs, entitlements, native
MCP registration and returned tools. A missing optional capability does not make
an unrelated operation fail. Never invent a target or switch servers on failure.

Read [the readiness workflow](references/upstream-workflow.md) for the requested
checks and [helper boundaries](references/script-invocation.md) before considering
any bundled script. Helpers are preserved resources, not pre-approved commands.
Several named detectors write configuration or persistent state. Legacy OpenCode
writers/detectors do not qualify native V2 configuration or authentication.

Use existing native installer and client writers. Do not auto-install/upgrade
Node or CLI, reinstall the official plugin, enable hooks/Agent Guard, retarget a
client, launch login, register a marketplace, mutate a credential store or save
setup state merely because a diagnostic branch suggests it. Carry out already
authorized setup through its owner; ask only for missing material selection or
authority. Keep secrets and raw config exports out of tool output and evidence.

CLI 2.106.0 is the collection-wide minimum. Planning and ordinary filesystem
inspection need neither a CLI nor a platform connection. Read only references
for actual missing/failed capabilities; report observations and gaps separately.
