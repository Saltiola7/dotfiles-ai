# Retained helper execution boundaries

Bundled helpers are inert resources. Resolve paths from the actual selected skill
root; no Claude-only variable or allowed-tools list grants execution authority.
Review a helper and its imports before an authorized use, retaining real exit
status, stderr and bounded non-secret results. Do not append `true`, `exit 0` or
otherwise turn a failed detector into success. Bash and PowerShell require their
own argument and status handling; use the current harness's native facilities.

| Helper family | Material effects and qualification |
|---|---|
| `jfrog-install-jf-cli.mjs` | Installs/updates global npm or a downloaded CLI and can alter shell PATH; do not use instead of the selected native installer. |
| `jfrog-login-register-session.mjs`, `jfrog-login-save-credentials.mjs` | Network/OAuth and persisted credential changes; require actual explicit setup scope and existing credential owner. Never capture token-bearing output. |
| `jfrog-resolve-mcp-config.mjs` | Broad resolution can create/merge Kiro or Junie global configuration; not a harmless detector. |
| `jfrog-detect-jfrog-mcp.mjs`, `jfrog-substitute-mcp-placeholders.mjs`, `jfrog-write-opencode-mcp.mjs` | Can write/substitute native/plugin configuration or retarget a URL. Legacy OpenCode V1 schema is not qualified for V2; use the native owner. |
| `jfrog-detect-opencode-mcp-auth.mjs` | Uses an inferred older auth-store layout; do not inspect or repair credentials based on it. Native authentication/capability status owns readiness. |
| `jfrog-detect-all.mjs`, `jfrog-state-file.mjs` | Batch mode can persist setup state. Even read modes need exact path/target and private output review; no automatic writes. |
| `jfrog-add-claude-marketplace.mjs`, `jfrog-marketplace-headers.mjs` | Marketplace helper/config writes, network fetches and possible credential migration/netrc changes. Header helper deliberately prints live auth headers; never run/capture it as diagnostic evidence. |
| `jfrog-reinstall-jfrog-plugin.mjs` | Legacy installation instructions depend on client/version; its name or exit status is not evidence of an authorized repair. |
| Other detect/resolve scripts and `scripts/lib/` | May execute CLI, export credentials internally, request platform APIs or access caches. Review actual transitive effects; use only relevant bounded checks. |

Store only sanitized capability observations. Native trust/permission denials do
not authorize a second client, global policy change or an unsandboxed workaround.
