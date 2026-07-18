# dotfiles-ai Distribution Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| DAI-003 | Add autonomous R&D-to-draft-PR loop | high | active | DAI-002 | Hermes workspace/spawner/watchdog, operator docs | V3.23 coordination and OCP-19 worker contracts | no | Turn distinct global-session patterns into human-merge-only improvements of this source | L | Concurrent claims, Discovery pause, exact-session recovery, branch push, draft PR, no-merge proof, live smoke |
| DAI-004 | Add longitudinal loop analytics | medium | ready | DAI-003,V3.20-1,V3.21-1,V3.22-1 | Effect dashboards and adaptive scheduling | Worker and PR outcomes | no | Enrich a proven loop without delaying its first useful delivery | M | Baseline, recurrence, confounder, regression, and cost scenarios |

## Completed

| id | title | completed | commit |
|---|---|---|---|
| DAI-002 | Install and configure Hermes supervisor PoC | 2026-07-17 | Gate Commits `4133cc6` through `76269ed` |
| DAI-001 | Build and migrate portable AI configuration | 2026-07-13 | Gate Commits `ea9eaeb`, `224a483`; closure pending |
