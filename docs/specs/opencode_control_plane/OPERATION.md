# OpenCode Control Plane Operation

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | not_applicable: the README trust-flow visual and Text Equivalent own the host, guest, and desktop authorization boundaries | Does this runbook change a trust boundary? | `README.md` | Control-plane owner; boundary change |
| Interaction | not_applicable: commands and expected textual results below fully define operation | Can an operator execute and verify the workflow? | This runbook | Control-plane owner; command change |
| State | not_applicable: no persistent state model is introduced | Is new lifecycle state created? | This runbook | Control-plane owner; state change |
| Data/trust | not_applicable: the README trust-flow visual and Text Equivalent remain canonical | Can secret values leave 1Password? | `README.md` | Control-plane owner; trust change |
| Schema | not_applicable: no schema is defined | Does operation alter a schema? | `README.md` | Control-plane owner; schema change |
| Dependency/deployment | not_applicable: the absolute launcher path and connection check below are the complete deployment evidence | Can the deployed server be identified? | This runbook | Control-plane owner; launcher change |
| Quantitative | not_applicable: this binary connected/not-connected operation has no decision-relevant quantitative data | Would a metric change an operator decision? | This runbook | Control-plane owner; SLO addition |

## Official 1Password MCP

The managed macOS config pins the desktop-installed launcher by absolute path:

```text
/usr/local/bin/1password-mcp
```

In 1Password, enable **Settings > Developer > Use the 1Password CLI**, then
enable **Settings > Labs > MCP Server** and OpenCode integration. Restart
OpenCode after applying the managed config; confirm the new process sees the
server with:

```sh
opencode mcp list
```

Only the primary Build agent may request these tools, and OpenCode asks for
permission before invoking one; other agents inherit a global deny. The expected
server state is `1password connected`. The desktop app owns authentication,
Environment selection, approval prompts, and lock expiry. Approve Environment
writes only after reviewing the desktop prompt. Disable the Labs integration to
revoke access.

If `1password_authenticate` reports `Request timed out`, unlock 1Password, keep
the desktop app visible, retry the request, and approve the prompt before it
expires. Connection alone does not bypass this approval.

This server manages 1Password Environments and local env-file mappings. It does
not return Environment secret values and cannot create/copy Password Manager
items, grant vault access, or administer service accounts. Continue to use the
separately approved `op` CLI/operator workflow for those tasks. Fedora Lima
guests intentionally receive no MCP entry because they lack the desktop approval
boundary.

The 2026-08-15 deployment authenticated through the desktop app and completed a
read-only Environment listing. The empty result is valid: no Environments existed
in the selected account at deployment time.
