# Portable ownership qualification

Use these retained mechanics only for an explicitly selected JFrog-governed task
and a current version-qualified native configuration owner. Examples do not grant
mutation, plugin/runtime installation, OAuth, cache deletion or trust changes.
Use a reviewed Agent Guard pin and actual native secret controls; legacy schema
examples require current-client verification. Do not auto-run `enable_*_tools` or
login. Preserve unrelated entries, settings and credential state.

# Harness: Claude Code

Claude Code-specific config for the `jfrog-mcp-management` skill. Read this
together with [harness-common.md](harness-common.md) (shared entry shape and
success criterion). You reached this file because the harness is Claude Code
(`CLAUDECODE` / `CLAUDE_CODE_ENTRYPOINT`).

## Config files

- **Default scope: project.** `.mcp.json` in the project root — shareable via
  git. Create if missing: `{ "mcpServers": {} }`.
- **User (global):** `~/.claude.json`, top-level `mcpServers`. Use ONLY if the
  user says "personal only" / "do not commit". Do NOT use
  `projects.<path>.mcpServers` — that subkey is per-project runtime state, not a
  registry.
- Do not ask which scope unless the user brings it up.

## Top-level key

`mcpServers`

## Value reference (env / secrets)

Plain `${VAR_NAME}`, resolved from the shell that launched Claude Code. For
`Bearer` headers: `"Bearer ${TOKEN}"`. The user must export the variable in the
launching shell (see [persisting-env-vars.md](persisting-env-vars.md)); values
are picked up on next launch. Never write a raw secret — always `${VAR}`.

## Gateway entry shape

Use this shape ONLY when Step 2's `--inspect` output carried
`routing.target: "gateway"` and a non-empty `routing.url`. In every other case,
whatever the output looked like, write the Agent Guard entry from
[harness-common.md](harness-common.md) instead, exactly as you would if this
section did not exist. Never infer this from a URL that looks like a Gateway
URL.

```json
{
  "mcpServers": {
    "<spec.packageName>": {
      "type": "http",
      "url": "<routing.url, copied verbatim>"
    }
  }
}
```

- The entry **key** is the raw, unencoded `spec.packageName` — the same key the
  Agent Guard entry uses.
- `url` is `routing.url` copied verbatim. Never build it, never normalise it,
  never re-encode it, never append a path. It always points at the tenant's own
  JFrog Platform. A `%2F` in the URL is correct and must be written through
  unchanged.
- No `command`, no `args`, no `env`, no `${VAR}` — the Gateway holds the
  upstream credential, so there is nothing for the user to export. A `${VAR}` in
  a Gateway entry is a bug.
- Skip Install Step 5 (`--login`): OAuth runs between Claude Code and the
  Gateway on first use, not against the upstream.
- Enable, Restart and Verify are unchanged, including the ≥1-tool criterion.
- A managed denial blocks the affected registration. Do not write an unusable
  entry or change `allowedMcpServers`/policy to bypass it; report the native gap.

## Enable

Use the existing native approval/configuration owner for the exact selected
server. Do not pre-approve servers, edit trust/settings arrays or create team-wide
approval as an automatic install step. Permission/write failure remains a gap;
do not suppress it or change a managed policy to obtain success.

## Restart

`/exit` or `/reload-plugins` in the same directory. On first launch accept the
workspace-trust and per-server prompts only within actual authorized native
activation. This skill cannot grant trust or approve those prompts itself.

## List installed

`claude mcp list` for live connection status (one row per server). For JFrog
metadata, read `mcpServers` from `.mcp.json` (project) and `~/.claude.json`
(user).

## Verify

If you can already see or call at least one upstream tool from this
server, skip this check. Otherwise: you run `/mcp` → **drill into the
server entry** (arrow into it, not just the top-level row) → read
`Capabilities:`. Do not ask the user to report `Capabilities:`.

Success: `Capabilities:` lists at least one upstream tool. Top-level `✓ connected`
alone is not success (green whenever the proxy started).

Empty tool list: not success, not a diagnosis — follow
[Connected but 0 tools](key-rules-and-troubleshooting.md#connected-but-0-tools).
Do not invent another debug path until that section is finished.

## Approval / stuck-state precedence

If a server "still appears approved (or won't go away)", approval state lives in
plain JSON arrays read at session start (nothing cached; `npm cache clean` is
unrelated). Check, in precedence order:

1. `<cwd>/.claude/settings.local.json` — per-user, gitignored (where Enable writes by default)
2. `<cwd>/.claude/settings.json` — team-shared, committed to git
3. `~/.claude/settings.json` — user-global, applies to every repo
4. `~/.claude.json` → `projects["<absolute cwd>"].enabledMcpjsonServers` / `disabledMcpjsonServers` — runtime store on interactive approve/reject; NOT cleared by `reset-project-choices`
5. Managed `managed-settings.json` (`/Library/Application Support/ClaudeCode/` on macOS, `/etc/claude-code/` on Linux, `%ProgramData%\ClaudeCode\` on Windows) — can't be overridden

Also check `enableAllProjectMcpServers: true` in any of (1)–(3) — it
auto-approves every entry. Preserve that separately owned policy; use the actual
native owner to retire only the selected exact entry and review surviving layers.
Do not remove settings across every file as an automatic cleanup. A missing entry from `claude mcp list` is usually
a JSON parse failure (undefined `${VAR}`) or an `allowedMcpServers` /
`deniedMcpServers` policy in `managed-settings.json`.
