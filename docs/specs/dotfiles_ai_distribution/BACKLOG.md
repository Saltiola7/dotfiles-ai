# dotfiles-ai Distribution Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| DAI-013 | Provision durable Atuin history in every Lima guest | high | active | DAI-010 | Guest Atuin installer, config, Bash integration, tests, and deployment evidence | Existing portable shell and workspace config contracts | no | Shared config, schema, tests, and both deployments must move together | S | Focused pytest, isolated rendering, shell syntax, pinned checksum, and live personal/mgm history/search/sync checks |
| DAI-004-F1 | Record the first complete real 30-day benchmark effect | medium | pending | V3.25-1 | One immutable effect-finalized event and distribution completion evidence | Verified activation time, retained benchmark, DAI-004 analytics contract | no | Synthetic and incomplete-window evidence cannot establish the first real post-activation outcome; run only after the verified activation plus 30 days and not before 2026-08-18 | S | `dbsctr-rnd analytics --json`, deterministic benchmark replay, exactly-once effect finalization, and BACKLOG/CHANGELOG closure |
| DAI-012-F1 | Record the first real provider-native five-cycle report | medium | pending | DAI-012 | One immutable report and operational evidence | Five unused completed cycles under one exact activated harness identity | no | The helper must wait for the normal weekly run and cannot manufacture or loosen eligibility | S | Exact five-member replay, availability/confounders, and no automatic harness mutation |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| DAI-012 | Persist atomic report-only provider harness evaluations with privacy propagation and weekly operation | 2026-07-26 | `b08540b` |
| DAI-012D | Specify provider-native evaluation persistence and operation | 2026-07-26 | `d65d2ad` |
| DAI-011 | Restore operational federated autonomous review | 2026-07-26 | `f933afa..6fd56a5` |
| DAI-010 | Reproduce personal terminal visuals in managed guests | 2026-07-26 | `030b201..5c5d9a5` |
| DAI-009 | Add safe machine-local shell aliases for dynamic workspaces | 2026-07-25 | `e967b7a`, `a4798b8` |
| DAI-008 | Replace fixed sandbox identities with dynamic local workspaces | 2026-07-25 | `3743919..ba427ac` |
| DAI-007A | Deploy client-specific Lima sandbox runtimes and protected mounts | 2026-07-25 | `ae72606` |
| DAI-007B | Federate host/VM history and add configured-workspace implementation handoff | 2026-07-25 | `ae72606` |
| DAI-006 | Restore exact large-session recovery and watchdog health signaling | 2026-07-22 | `63a9c34` |
| DAI-004 | Add longitudinal analytics and adaptive cadence | 2026-07-19 | `b0568dc` |
| DAI-005 | Replace Hermes with native OpenCode scheduling | 2026-07-18 | `8870229` |
| DAI-003G | Apply every autonomous lens across full review history | 2026-07-18 | `bc2bb08` |
| DAI-003F | Harden R&D tabs and runtime PATH | 2026-07-18 | `74011f7`, `9c514a1`, `6694574` |
| DAI-003 | Add autonomous global-history R&D-to-draft-PR loop | 2026-07-18 | `f002712`, `6f9a112` |
| DAI-002 | Install and configure Hermes supervisor PoC | 2026-07-17 | `4133cc6`, `76269ed` |
| DAI-001 | Build and migrate portable AI configuration | 2026-07-13 | `ea9eaeb`, `224a483`, `d0d6f6f`; later operation `225fa75` |
