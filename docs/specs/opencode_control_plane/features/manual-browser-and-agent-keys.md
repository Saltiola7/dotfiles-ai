# Manual browser MCPs and agent keys

## Scope and authority

Engineering Profile: ../PROFILE.md. Product Intent: ../PRODUCT.md.
Owner: dotfiles owner. Risk: routine. Delivery: managed host deployment and draft
pull request. Existing provider routing and unrelated local preferences survive.
This slice owns only native V2 preferences and MCP declarations, not browser
automation, session hibernation, guest upgrades or the original V2 migration.

Native V2 configuration is authoritative: keybinds belong in cli.json, and MCP
servers use disabled=true under mcp.servers. Compatibility with locally preserved
legacy configuration must be qualified against the admitted runtime. Do not
introduce mixed duplicate server declarations or silently discard local servers.

## Behavior

1. Given the managed host configuration, when a fresh OpenCode client opens,
   Tab selects the next available agent and Shift+Tab selects the previous one.
   Native autocomplete/dialog behavior remains usable in its own focused context.
2. Given configured Chrome DevTools and Playwright MCP servers, fresh OpenCode
   work connects to neither automatically. Both remain visible in /mcps for
   explicit manual connection and disconnection.
3. Given unrelated local CLI settings, servers and credentials, a targeted
   chezmoi apply preserves them and changes only the declared managed settings.
4. Given a malformed local configuration, rendering fails without replacing it.
5. Given a repeated apply, the managed result is unchanged and no browser starts.

## Interfaces and trust

Use native keybind IDs agent.cycle and agent.cycle.reverse with tab and shift+tab.
Use official Chrome DevTools and Playwright MCP packages with qualified stable
versions; retain browser commands without launching them during routine apply.
Manual MCP activation remains subject to existing tool permissions. This slice
adds no credentials, remote upload, automatic browser navigation or global
permission grants. The requested Lima ask rule is separate completed maintenance.

## Validation and gates

Required: domain, behavior, spec, contract, test-driven implementation, refactor,
review/integrate, deploy, operate and maintain/retire. Release is not applicable:
configuration is distributed through chezmoi, with no independent package.
Render against representative existing settings; verify exact native keys,
disabled server flags, idempotence and preservation. Run affected existing
configuration tests and native V2 resolution. Inspect native MCP status and
operator UI behavior; do not infer key handling from JSON validity alone.
Review README, CHANGELOG and affected backlog. Rollback restores the prior
managed declarations while retaining unrelated local configuration and sessions.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: local configuration ownership is fully specified above |
| Interaction | not_applicable: a single explicit native connection action needs no sequence diagram |
| State | required: transition table below defines automatic versus manual connection |
| Data/trust | not_applicable: no new transfer or credential mechanism is introduced |
| Schema | not_applicable: native configuration schema is reused without a new persistent entity |
| Dependency/deployment | not_applicable: existing chezmoi and native OpenCode deployment are reused |
| Quantitative | not_applicable: no quantitative comparison informs this change |

| Initial state | Event | Result |
|---|---|---|
| Configured, disabled | Fresh client/workspace startup | Disconnected |
| Disconnected | Operator connects via /mcps | Native connection attempt; errors stay visible |
| Connected | Operator disconnects via /mcps | Disconnected |

**Text Equivalent:** startup does not connect either browser MCP; the operator
initiates connection and disconnection, and native errors remain visible.
Canonical source: this behavior contract. Owner: dotfiles owner. Update trigger:
change to startup policy or manual connection semantics.
