# dotfiles-ai Distribution Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| DAI-023 | Add an opt-in machine-local Lima state root without changing teammate defaults | high | implementing | - | Sandbox config, controller environment, tests, and distribution lifecycle docs | Existing Lima workspace contracts | no | Storage migration and deployment share one sensitive runtime boundary | S | Focused rendering/controller tests, full affected suite, and live relocated VM checks |
| DAI-004-F1 | Record the first complete real 30-day benchmark effect | medium | pending | V3.25-1 | One immutable effect-finalized event and distribution completion evidence | Verified activation time, retained benchmark, DAI-004 analytics contract | no | Synthetic and incomplete-window evidence cannot establish the first real post-activation outcome; run only after the verified activation plus 30 days and not before 2026-08-18 | S | `dbsctr-rnd analytics --json`, deterministic benchmark replay, exactly-once effect finalization, and BACKLOG/CHANGELOG closure |
| DAI-012-F1 | Record the first real provider-native five-cycle report | medium | pending | DAI-012 | One immutable report and operational evidence | Five unused completed cycles under one exact activated harness identity | no | The helper must wait for the normal weekly run and cannot manufacture or loosen eligibility | S | Exact five-member replay, availability/confounders, and no automatic harness mutation |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| DAI-021 | Delivered six independent continuous R&D lenses, isolated review-session governance, session-bound telemetry and readiness, controlled live pass validation, and five-minute Hermes scheduling | 2026-08-02 | `560650d..1e86bc8` |
| DAI-016-F3 | Preserved bounded process-group cleanup through release failure and exited-leader races | 2026-07-31 | `5aa248a..857e7af` |
| DAI-016-F2 | Accepted OpenCode's successful empty session inventory while preserving malformed-output rejection in the subprocess E2E | 2026-07-31 | `12d83c6` |
| DAI-016-F1 | Repaired plugin-free exact-session launch, pinned argparse-safe Hermes dispatch, bounded large host capture, added subprocess E2E coverage, and completed one 644-session three-source live round with a persisted P2 yield | 2026-07-31 | `24d0fd0..4db52d4` |
| DAI-020 | Add guarded no-fast-forward batch integration, explicit queued-claim promotion, and private 30-day Herdr history retention | 2026-07-29 | `748265d` |
| DAI-019 | Persist P0-P3 claim authority and expose waiting P2/P3 claims through a report-only operator backlog | 2026-07-29 | `3e293b8..3cb3e19` |
| DAI-018 | Govern one shared immutable capture through five fixed adaptive R&D lenses with recoverable ownership and no-yield backoff | 2026-07-29 | `83b0cd8..c834fd3` |
| DAI-017-F2 | Run one feature pull-request matrix and stabilize the concurrency benchmark test signal | 2026-07-29 | `a4027d5..079276b` |
| DAI-017-F1 | Make external-tool validation, bounded-command cleanup, and existing same-repository draft-PR delivery reliable | 2026-07-29 | `fc20e0f..c7d9981` |
| DAI-017 | Protect main, retain published teammate feature baselines, and require verified draft-PR delivery with fresh reconciliation evidence | 2026-07-28 | `706711d..b7dedfe` |
| DAI-016 | Deploy context-isolated Hermes orchestration, bounded backlog refinement, direct OpenCode Discovery launch, and guarded global maintenance | 2026-07-28 | `269125b..dc6d284` |
| DAI-015 | Deploy default-off rootless Tailscale SSH and native remote Herdr to managed Lima guests | 2026-07-27 | `818f83c..6f06090` |
| DAI-014 | Launch guest Herdr directly while preserving Starship and Atuin hooks | 2026-07-26 | `c3d32b9..4c85a4d` |
| DAI-013 | Provision durable Atuin history in every managed Lima guest | 2026-07-26 | `19921b1..3709006` |
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
