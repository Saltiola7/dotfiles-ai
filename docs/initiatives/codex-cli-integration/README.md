# Codex CLI Integration

This Initiative makes Codex CLI a fully managed peer to OpenCode across the
macOS host, Fedora Lima guests, Herdr, Hermes, and DBSCTR. Both runtimes remain
supported. Parity means equivalent outcomes and safety, not copied client
internals.

The coordinator repository is `Saltiola7/dotfiles-ai`. The canonical machine
ledger is [`MANIFEST.json`](MANIFEST.json).

## Success

- A normal apply installs and configures both OpenCode and Codex CLI.
- Interactive users explicitly run `opencode` or `codex`; automation defaults to
  OpenCode until `rnd.runtime` or a workspace override selects Codex.
- Codex uses one dedicated `CODEX_HOME` without changing desktop `~/.codex`.
- OpenCode and Codex implement one DBSCTR V3 lifecycle through conforming
  adapters and preserve the same gate, evidence, approval, and delivery outcomes.
- Every requested parity capability is native, reused, adapted, or explicitly
  not applicable. A missing requested outcome blocks parity readiness.
- Host and guest credentials, sessions, logs, private evidence, and worker state
  remain isolated.

## Context Map

| Context | Responsibility | Dependency |
|---|---|---|
| `dbsctr_v3_lifecycle` | Generic harness contract, proposed Cycle Record schema 5, compatibility, and conformance | None |
| `codex_control_plane` | Codex instructions, skills, agents, approvals, hooks, sessions, and lifecycle adapters | DBSCTR lifecycle |
| `dotfiles_ai_distribution` | Host/guest installation, managed config projection, runtime selection, worker distribution, and rollback | Codex control plane |
| `shell_auth_startup` | External-volume health, signed Herdr ancestry, and exact Codex session recovery | Codex control plane and distribution |
| `opencode_control_plane` | Unchanged coexistence and regression baseline | DBSCTR lifecycle |
| `dbsctr_knowledge_store` | Existing DKS and Graphify interfaces | None |
| `pm_kernel` | Existing canonical ticket workflow | DBSCTR lifecycle |
| `writing_skills` | Existing writing skills and external-write boundaries | None |
| `opencode_inference_cost` | OpenCode-only cost baseline; no premature generalization | OpenCode control plane |

The user approved this complete context map on 2026-08-29.

## Architecture

```mermaid
flowchart LR
    accTitle: Dual-runtime DBSCTR architecture
    accDescr: OpenCode and Codex remain independently managed runtimes. Codex native instructions, skills, hooks, and supported thread interfaces enter a short-lived Codex adapter. OpenCode retains its typed adapter. Both reach the same DBSCTR lifecycle and private evidence contracts, while distribution and shell-auth components preserve host, guest, desktop, and external-volume boundaries.
    U[User or worker] -->|explicit runtime| R{Runtime}
    R --> O[OpenCode control plane]
    R --> C[Codex control plane]
    C --> N[Native skills, hooks, CLI JSONL, app-server]
    N --> A[Short-lived Python adapter]
    O --> T[OpenCode typed adapter]
    A --> D[DBSCTR V3]
    T --> D
    D --> G[Cycle Records and Git delivery]
    H[Host CODEX_HOME] -. isolated from .-> V[Guest CODEX_HOME]
    H -. separate from .-> P[Desktop default state]
```

**Text Equivalent:** A caller explicitly selects OpenCode or Codex. OpenCode
keeps its existing typed adapter. Codex uses native skills, hooks, CLI JSONL, and
supported app-server methods through a short-lived Python adapter. Both adapters
use one DBSCTR V3 lifecycle and Git delivery authority. Host Codex state, each
guest Codex state, and desktop default state remain separate.

## Delivery Slices

| Slice | Execution owner | Outcome | Depends on |
|---|---|---|---|
| `multi-harness-lifecycle` | `build` | Proposed schema-5 generic harness identity and conformance while schemas 3/4 remain readable | None |
| `codex-host-foundation` | `build` | Managed host Codex config, native skills, sandbox, and bounded CLI adapter | `multi-harness-lifecycle` |
| `codex-distribution` | `build` | Homebrew host install, pinned Fedora install, atomic config projection, and runtime selection | `codex-host-foundation` |
| `codex-identity-probe` | `discovery` | Cross-platform decision for hook session identity versus app-server thread identity | `codex-distribution` |
| `codex-history-parity` | `build` | Supported thread history, incidents, review, telemetry, and benchmarks | `codex-identity-probe` |
| `codex-worker-routing` | `build` | Explicit Herdr/Hermes/autonomous-worker runtime binding without fallback | `codex-distribution`, `codex-identity-probe` |
| `codex-state-recovery` | `build` | External-volume circuit breaking and exact supported-session resume | `codex-worker-routing`, `codex-identity-probe` |
| `codex-federation-parity` | `build` | Bounded host/guest history federation and handoff | `codex-history-parity`, `codex-worker-routing` |
| `codex-parity-readiness` | `discovery` | Outcome-parity assessment with no unexplained unavailable capability | All preceding slices |

Discovery owns normative contracts, parity disposition, dependencies, and slice
scope. Build owns only the implementation paths in an approved DBSCTR
applicability plan and Cycle Record. Late changes to lifecycle semantics, context
ownership, state isolation, parity meaning, or dependencies reopen readiness.

This Initiative creates no PM Kernel tickets. The ticket-optional manifest marks
only `multi-harness-lifecycle` receipt-ready. No other Initiative Build launch is
authorized. Applicability plans and Cycle Records cannot substitute for an
Initiative readiness receipt.

## Release Groups

| Group | Members | Exit condition |
|---|---|---|
| `contract-foundation` | `multi-harness-lifecycle` | Generic lifecycle adapter contract is delivered without OpenCode regression |
| `installable-peer` | `codex-host-foundation`, `codex-distribution` | Host and guest Codex runtimes are installed, isolated, and explicitly selectable |
| `native-lifecycle` | `codex-identity-probe`, `codex-worker-routing`, `codex-state-recovery` | Exact identity, worker routing, and recovery pass on both platforms |
| `history-federation` | `codex-history-parity`, `codex-federation-parity` | Bounded review, incident, telemetry, and federation outcomes pass |
| `parity-readiness` | `codex-parity-readiness` | Every requested capability has an evidence-backed passing disposition |

## Constraints

- Desktop Codex remains separately managed at default `~/.codex`.
- A configured centralized root maps CLI state to `<root>/codex`; an empty root
  maps it to `~/.local/state/dotfiles-ai/codex`.
- Chezmoi projects only digest-owned managed files into `CODEX_HOME`; it never
  owns auth, sessions, logs, plugins, or unrelated state.
- OpenCode remains installed and supported. Runtime presence never changes a
  default and runtime failure never falls back to the other client.
- Codex private SQLite and JSONL storage are not contracts. Supported CLI, hook,
  and app-server interfaces are authoritative.
- Hooks collect only bounded sanitized identity and event evidence and never
  mutate lifecycle state.
- No MCP, plugin package, SDK-bundled second runtime, Rust rewrite, or private
  Codex fork is introduced without a separately approved proven need.
- No performance claim or language rewrite is accepted without representative
  benchmark evidence.

## Current Evidence Boundary

Codex CLI is not installed on the current host. The proposed frozen baseline is
Codex `0.151.0`; Fedora would use
`codex-aarch64-unknown-linux-musl.tar.gz` with SHA-256
`c1cf2baf375e261c1469381a52dc2c8fd05b6fb45cfff83fed0988fd6c5369b6`.
Implementation must revalidate the release tag, asset, and digest before use.
The identity probe must compare hook `session_id`, app-server `thread.id`, and
`thread.sessionId` on macOS and Fedora before exact attach, recovery, or history
correlation becomes ready.
