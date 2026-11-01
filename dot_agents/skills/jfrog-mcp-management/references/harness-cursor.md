# Cursor native ownership for selected JFrog governance

Use this reference only for an explicitly selected JFrog Agent Guard/governed
catalog task in Cursor. Read [common preflight](agent-guard-common.md) and the
[common harness contract](harness-common.md), then resolve the actual installed
Cursor version, active workspace and native configuration owner. Environment
markers such as `CURSOR_AGENT` identify a possible harness; they do not prove
configuration scope, permissions, authentication or an active connection.

## Configuration scope and entry identity

Cursor versions using the `mcpServers` configuration schema can have project
`.cursor/mcp.json` and user `~/.cursor/mcp.json` layers. Verify the current native
schema and effective layers before planning a change. An existing managed
project/user entry retains its owner and scope. Use explicit task/project policy
for a new entry; resolve missing scope only when it materially affects sharing
or trust. Do not create a project file, switch to user scope or replace another
same-name entry merely to make verification succeed.

For an authorized change, preserve private preimages and alter only the selected
entry through the existing native/source owner. Review whether a project file is
shared or committed; authentication values remain private. Preserve unrelated
servers, settings, approval state, hooks and native credentials. A retained
upstream JSON example is not permission to overwrite global configuration.

## Runtime and secret references

Agent Guard is a separate runtime. Use an already qualified executable or an
explicitly selected reviewed package version and registry through its installer
owner. Never run a floating `npx @jfrog/agent-guard` command to discover a version,
list a catalog or repair a connection. Catalog commands can download and execute
code; [runtime boundaries](runtime-permissions.md) apply before use.

For a Cursor version supporting `${env:VAR_NAME}`, configure the native secret
reference rather than a literal value; a Bearer header can reference
`Bearer ${env:TOKEN}` only when that syntax is supported by the selected native
owner. Resolve the real launch environment: a GUI session need not inherit an
interactive shell export. Verify required variable presence without printing its
value. Do not automatically persist exports, migrate tokens or edit shell startup
files; see [environment ownership](persisting-env-vars.md).

A selected governed stdio entry retains the qualified Agent Guard version,
registry, platform identity and inspected package/project contract. A Gateway
entry needs a returned supported Gateway route and the current native remote
transport. Do not derive a URL from the CLI default, retarget an existing entry
or bypass a required governance proxy because another connection works.

## Enablement, restart and verification

Native enablement and workspace trust may be separate from configuration. Use
Cursor's actual MCP controls and current task authorization; do not self-grant
trust, pre-approve servers, invoke `enable_*_tools` or start OAuth as a harmless
check. When the supported native UI requires operator interaction, state the
specific pending action and retain the current configuration state. An authorized
native reload, such as `Developer: Reload Window` on versions supporting it,
is distinct from rebooting the host or starting another MCP instance.

Use native status/catalog capabilities available in the selected version. If its
CLI supports `cursor agent mcp list`, that can provide a status observation; it
is not proof that the active IDE session has returned upstream tools. Cached
`~/.cursor/projects/<workspace>/mcps/<server>/tools/*.json` descriptors, when that
layout actually exists, are at most bounded diagnostic evidence. Do not scan
unrelated workspaces, expose descriptor contents indiscriminately or count stale
files as a live connected catalog.

Report these separately: effective entry, process/transport state,
authentication, actual returned upstream tool metadata and successful requested
target operation. A connected indicator, cached descriptor or only an
`enable_*_tools` tool does not establish usable upstream capabilities. For an
empty live catalog, use [bounded troubleshooting](key-rules-and-troubleshooting.md#connected-but-0-tools).

## Network or sandbox failure

A `403`, timeout or failed activation check does not identify Cursor's sandbox
allowlist as the cause. Distinguish package-registry fetch, selected platform,
proxy, credential/authorization and native policy failures from available
bounded evidence. Never infer that governance is disabled from an unknown check.

Respect the actual native permission policy and any denial. Do not automatically
retry with `full_network`/`all`, create or edit `.cursor/sandbox.json` or
`~/.cursor/sandbox.json`, add wildcard JFrog/S3 hosts, move execution outside the
sandbox or ask another harness to evade the block. Network-policy changes are
separately owned, reviewed work: resolve the exact required host/effect and
existing policy owner before any explicitly authorized change. If access remains
unavailable, retain the selected entry and report the capability gap without a
fallback install, login or URL retarget.
