# Native harness selection and ownership

Use the actual native client/version and its effective configuration origin, not
an environment label as authentication. Read only the matching reference:

| Actual client | Reference |
|---|---|
| Codex CLI/Desktop/IDE | [Codex](harness-codex.md) |
| OpenCode | [OpenCode](harness-opencode.md) |
| Claude Code | [Claude](harness-claude.md) |
| Cursor | [Cursor](harness-cursor.md) |
| VS Code editor | [VS Code](harness-vscode.md) |
| Devin | [Devin](harness-devin.md) |
| Kiro | [Kiro](harness-kiro.md) |
| Junie | [Junie](harness-junie.md) |

These references describe selected JFrog-governed entries, not universal MCP
ownership. Prefer current native documentation/schema and the existing managed
configuration writer. Never infer that surfaces share a home, clone another
client's config shape or use a stale generic writer to edit current state.

For a stdio Agent Guard route, keep the reviewed version/registry, selected
platform ID and exact inspected package. Route project/package through the
supported non-secret `_JF_ARGS` field; required secret inputs use native secret
references. Do not print credentials or cache values. Gateway routes require an
actual inspected supported route and native transport, not a constructed URL.

Registration, enabled/connected status, authentication, actual upstream tools
and a successful target operation are separate observations. A lone
`enable_*_tools` tool is an authentication action, not upstream readiness; invoke
it only within concrete authorized login scope. Native trust, permission denials,
restart and cache retirement retain their existing owners.

For an unlisted client, consult that client's current native documentation before
planning a change. Missing native capability is a gap, not permission to write a
look-alike config file or switch clients. Existing unrelated MCP owners remain.
