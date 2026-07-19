# dotfiles-ai Distribution Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| DAI-004 | Add longitudinal CLI/JSON analytics and adaptive cadence | medium | ready | DAI-005,V3.20-1,V3.21-1,V3.22-1 | Effect reports, private scheduler state, transactional fixed-tick spawn gating, halt/reset | Worker, merge, activation, and benchmark outcomes | no | Enrich the native loop without weakening human delivery boundaries | M | Deterministic monthly cohort/denominator, cadence ladder, atomic 3-worker cap, halt/reset, baseline, recurrence, confounder, regression, malformed state, and report-only cost scenarios |

## Completed

| id | title | completed | commit |
|---|---|---|---|
| DAI-005 | Replace Hermes with native OpenCode scheduling | 2026-07-18 | DAI-005B corrective Gate Commit |
| DAI-003G | Apply every autonomous lens across full review history | 2026-07-18 | Gate Commit `bc2bb08` |
| DAI-003F | Harden R&D tabs and runtime PATH | 2026-07-18 | Gate Commits `74011f7`, `9c514a1`, `6694574` |
| DAI-003 | Add autonomous global-history R&D-to-draft-PR loop | 2026-07-18 | Gate Commits `f002712` through `6f9a112` |
| DAI-002 | Install and configure Hermes supervisor PoC | 2026-07-17 | Gate Commits `4133cc6` through `76269ed` |
| DAI-001 | Build and migrate portable AI configuration | 2026-07-13 | Gate Commits `ea9eaeb`, `224a483`; closure pending |
