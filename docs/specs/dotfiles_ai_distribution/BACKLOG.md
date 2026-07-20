# dotfiles-ai Distribution Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| DAI-004-F1 | Record the first complete real 30-day benchmark effect | medium | pending | V3.25-1 | One immutable effect-finalized event and distribution completion evidence | Verified activation time, retained benchmark, DAI-004 analytics contract | no | Synthetic and incomplete-window evidence cannot establish the first real post-activation outcome; run only after the verified activation plus 30 days and not before 2026-08-18 | S | `dbsctr-rnd analytics --json`, deterministic benchmark replay, exactly-once effect finalization, and BACKLOG/CHANGELOG closure |

## Completed

| id | title | completed | commit |
|---|---|---|---|
| DAI-004 | Add longitudinal analytics and adaptive cadence | 2026-07-19 | Gate Commit `b0568dc` |
| DAI-005 | Replace Hermes with native OpenCode scheduling | 2026-07-18 | DAI-005B corrective Gate Commit |
| DAI-003G | Apply every autonomous lens across full review history | 2026-07-18 | Gate Commit `bc2bb08` |
| DAI-003F | Harden R&D tabs and runtime PATH | 2026-07-18 | Gate Commits `74011f7`, `9c514a1`, `6694574` |
| DAI-003 | Add autonomous global-history R&D-to-draft-PR loop | 2026-07-18 | Gate Commits `f002712` through `6f9a112` |
| DAI-002 | Install and configure Hermes supervisor PoC | 2026-07-17 | Gate Commits `4133cc6` through `76269ed` |
| DAI-001 | Build and migrate portable AI configuration | 2026-07-13 | Gate Commits `ea9eaeb`, `224a483`; closure `d0d6f6f`; later deployed operation `225fa75` |
