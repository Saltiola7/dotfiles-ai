# Backlog: Writing Skills

**Last updated:** 2026-07-28

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| WS-1 | Add failing writing-skill contracts | high | pending | - | `tests/test_writing_skills.py` | writing spec, OpenCode conventions | no | Fix the public behavior and safety boundary before implementation | M | Focused red tests |
| WS-2 | Implement Jira refinement and completion | high | pending | WS-1 | `dot_agents/skills/jira-ticket/**`, two command files | writing spec | no | Deliver the evidence-driven Jira workflows | M | Focused green tests and synthetic smoke |
| WS-3 | Implement explicit Pyramid workflow | high | pending | WS-1 | `dot_agents/skills/pyramid/**`, pyramid command | private conceptual source, writing spec | no | Deliver original reader-first structural reasoning | M | Focused green tests and source comparison |
| WS-4 | Add global ACLI guardrails | high | pending | WS-1 | OpenCode config and control-plane tests/specs | ACLI help, control-plane conventions | no | Restrict direct Jira access to bounded reads | M | Rendered permission assertions |
| WS-5 | Integrate and validate public distribution | high | pending | WS-2, WS-3, WS-4 | writing/control-plane docs and portability tests | all affected artifacts | no | Prove privacy, compatibility, and isolated behavior | M | Affected QA and isolated smoke |
| WS-6 | Complete lifecycle records and delivery | high | pending | WS-5 | writing backlog/changelog/gate ledger | cycle evidence | no | Preserve traceability and perform authorized final push | S | DBSCTR status and upstream evidence |

## Parallel Execution Guide

No implementation item is marked parallel-safe because the compact change shares
tests, public contracts, and final integration ownership. WS-2, WS-3, and WS-4
may be reasoned about independently but remain serialized to avoid stale tests.

Sequential chain: WS-1 -> WS-2/WS-3/WS-4 -> WS-5 -> WS-6.

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
