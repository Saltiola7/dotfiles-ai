# dotfiles-ai Distribution Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| DAI-003 | Add autonomous draft-PR remediation | high | blocked | DAI-002,V3.23-1,OCP-19 | Discovery handoff, PR delivery contract, isolated workers | Review proposals, DBSCTR delivery locks | no | Turn implementation-ready findings into human-merge-only draft PRs | L | Discovery pause, worktree isolation, branch push, draft PR, required checks, no-merge proof |

## Completed

| id | title | completed | commit |
|---|---|---|---|
| DAI-002 | Install and configure Hermes supervisor PoC | 2026-07-17 | Gate Commits `4133cc6` through `76269ed` |
| DAI-001 | Build and migrate portable AI configuration | 2026-07-13 | Gate Commits `ea9eaeb`, `224a483`; closure pending |
