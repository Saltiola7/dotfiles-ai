# dotfiles-ai Distribution Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| DAI-002 | Install and configure Hermes supervisor PoC | high | active | V3.18-1,V3.19-1 | Hermes bootstrap, policy, schedules, tests, distribution artifacts | Herdr/OpenCode integration, DBSCTR review and cycle status | no | Babysit approved DBSCTR workflows and establish one daily review loop | L | Render, focused tests, shell/plist lint, installer dry checks, gateway/integration/cron smoke |
| DAI-003 | Add autonomous draft-PR remediation | high | blocked | DAI-002,V3.23-1,OCP-19 | Discovery handoff, PR delivery contract, isolated workers | Review proposals, DBSCTR delivery locks | no | Turn implementation-ready findings into human-merge-only draft PRs | L | Discovery pause, worktree isolation, branch push, draft PR, required checks, no-merge proof |

## Completed

| id | title | completed | commit |
|---|---|---|---|
| DAI-001 | Build and migrate portable AI configuration | 2026-07-13 | Gate Commits `ea9eaeb`, `224a483`; closure pending |
