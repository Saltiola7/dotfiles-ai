# OpenCode Control Plane Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| OCP-36 | Integrate the official 1Password Environment MCP | high | blocked | OCP-16 | Host OpenCode MCP config, Environment boundary, tests, deployment and restart evidence | Desktop-bundled `1password-mcp`, existing managed config and MCP validation | no | Configuration, security contract, live desktop authorization, and deployment must remain one coherent change | S | Source, deployment, 47 focused tests, resolved config, and MCP connection pass; fresh Environment probe awaits desktop authentication approval after two timeouts |
| OCP-31 | Expose isolated lens attribution and autonomous readiness | high | in_progress | DAI-021 | Worker command, typed autonomous transition, federation candidate classification, lens-audit skill | Improvement ledger, federated history, DBSCTR delivery | no | Continuous workers need one-lens scope and deterministic review-session exclusion | M | Command contract, adapter validation, transition tests, parser and affected QA |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| OCP-34 | Added session-scoped cycle routing and inherited centralized worktree permissions for provider Build primaries | 2026-08-10 | `fae3b76`, `22d548b` |
| OCP-33 | Routed title generation and read-only OpenAI exploration to Luna while retaining Terra implementation and Sol review tiers | 2026-08-09 | `b7339ea`, `1c8353a` |
| OCP-32 | Added configurable centralized durable state, fail-closed runtime routing, portable cycle records, and reversible live migration | 2026-08-08 | `4fe1680..62f1010` |
| OCP-30 | Add source ACLI read guardrails for writing skills without live deployment | 2026-07-28 | `761d01e`, `6904ff6`, `4b00081` |
| OCP-29 | Add exact reservation-bound Hermes launch and resumable OpenCode Discovery without Herdr dependency | 2026-07-28 | `269125b..dc6d284` |
| OCP-27/OCP-28 | Add exact loaded harness identity, provider-local prompts and entry commands, Opus 5 high, and five-cycle evaluation adapters | 2026-07-26 | `c0289f8`, `b08540b` |
| OCP-27D | Specify provider-native harness contracts | 2026-07-26 | `d65d2ad` |
| OCP-26 | Add VM-only always-auto control plane and bounded federation adapters | 2026-07-25 | `ae72606` |
| OCP-25 | Ask before every shell form of explicit improvement retirement | 2026-07-23 | `ec9cbc4`, `732ae79` |
| OCP-24 | Preserve exact reference root and subtree rules | 2026-07-19 | `4b52a21` |
| OCP-23 | Preserve reference access after global deny | 2026-07-19 | `d0c3942` |
| OCP-22 | Render a portable local repository reference | 2026-07-19 | `ef70477` |
| OCP-21 | Make custom Build selection and routing exact | 2026-07-18 | `8870229` |
| OCP-20 | Allow Build to maintain standalone local config | 2026-07-17 | `b96dd0d` |
| OCP-19 | Expose autonomous R&D worker behavior | 2026-07-18 | `9b77969` |
| OCP-18 | Expose compact history, telemetry, and benchmark interfaces | 2026-07-19 | `0611451` |
| OCP-17 | Expose runtime attachment and advisory Herdr health | 2026-07-19 | `c96093d` |
| OCP-16 | Add Scout-only Context7 and prompt-free safe begin | 2026-07-16 | `791bc22` |
| OCP-15-1 | Pass optional history-save page identity | 2026-07-18 | `920156b` |
| OCP-15 | Add repeatable historical DBSCTR review tools | 2026-07-16 | `e61a150` |
| OCP-14 | Record structured OpenCode and advisory Herdr correlation | 2026-07-15 | `537c3a2` |
| OCP-13 | Preserve review progress across bounded report retention | 2026-07-15 | `6e072b2` |
| OCP-12 | Preserve immutable review snapshots through typed tools | 2026-07-15 | `e04aa78` |
| OCP-11 | Add provider-neutral private DBSCTR review tools and command | 2026-07-15 | `f2eb3f1` |
| OCP-10 | Retire unsupported Pro aliases and restore native Build | 2026-07-13 | Historical `dcebd6c`; imported by `ea9eaeb` |
| OCP-9 | Finalize artifacts | 2026-07-11 | `ea9eaeb` |
| OCP-8 | Deploy and validate | 2026-07-11 | `ea9eaeb` |
| OCP-7 | Clean approved machine runtime | 2026-07-11 | `ea9eaeb` |
| OCP-6 | Preserve Graphify without duplicate plugin | 2026-07-11 | `ea9eaeb` |
| OCP-5 | Remove managed legacy integrations | 2026-07-11 | `ea9eaeb` |
| OCP-4 | Curate OpenCode skills | 2026-07-11 | `ea9eaeb` |
| OCP-3 | Align routing and permissions | 2026-07-11 | `ea9eaeb` |
| OCP-2 | Add control-plane contract test | 2026-07-11 | `ea9eaeb` |
| OCP-1 | Persist approved domain and behavior | 2026-07-11 | `ea9eaeb` |
