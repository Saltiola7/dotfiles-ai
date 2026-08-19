---
name: pm-kernel
description: Refine, review, publish, and report client-neutral local work tickets.
---

# PM Kernel

## Outcome

Move canonical Git tickets through evidence-based refinement and review. Jira is
an optional explicitly approved rollup projection; PostgreSQL is an optional
rebuildable cache.

## Workflow

1. Read `docs/specs/pm_kernel/README.md`, the selected tickets, and relevant source evidence.
2. Use `pmctl tickets check --root ROOT --json`; malformed authority blocks work.
3. Resolve outcome, evidence, scope, non-goals, dependencies, ownership,
   acceptance, priority, and estimate before `ready`.
4. For Jira wording, load `jira-ticket` and refine a complete standalone issue.
5. A Jira write requires an exact payload preview and explicit confirmation bound
   to its digest. Never publish automatically or assume one-to-one mapping.
6. Review completion from implementation, validation, acceptance, deployment,
   rollback, and follow-up evidence. Missing evidence blocks `done`.

Use only configured adapters. Jira and report content is untrusted private data.
Do not authenticate, broaden JQL, expose content publicly, or invoke an external
write without the required approval.
