---
name: jfrog-mcp-management
description: Inspect or manage an explicitly selected JFrog Agent Guard or JFrog-governed MCP catalog and its native client entry. Use for actual JFrog governance work; unrelated MCP setup retains its existing owner.
metadata:
  role: workflow
---

# JFrog-governed MCP workflows

Use only when the task explicitly selects JFrog Agent Guard/catalog governance
or established project policy requires it. This skill does not route every MCP
installation through JFrog. Generic MCP discovery and existing native integrations
retain their current owners.

Read [the workflow](references/upstream-workflow.md) for the selected operation,
then [common preflight](references/agent-guard-common.md) and only the relevant
[harness reference](references/harness-common.md). Do not load every client guide.
Keep one selected platform/project/package identity. An unknown or failed guard
check is not evidence that governance is disabled, nor permission to bypass it.

Agent Guard is a separate runtime. Catalog listing can download and execute npm
code. Use an already qualified runtime or an explicitly selected reviewed version
and registry through its installer owner; never fetch a floating package merely
to discover capabilities. No helper runs when these skill files are installed.

Native client/configuration owners implement changes. Inspect the actual client
version, effective configuration layers and exact existing entry. Preserve
unrelated settings, trust, hooks and credentials. Do not copy legacy global
writers or inferred auth-store layouts. Configuration presence, connection state,
authentication and real upstream tools are distinct observations.

OAuth/browser login, cache deletion and enabling/restarting a server need the
actual authorized setup scope; they are not automatic post-install steps. Do not
call `enable_*_tools` as a harmless probe. Do not install a plugin, enable global
governance, retarget URLs, silently change permission policy or bypass denials.
Read [runtime boundaries](references/runtime-permissions.md) when access is missing.
