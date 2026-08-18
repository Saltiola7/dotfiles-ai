---
name: backlog-migration
description: Deterministically migrate canonical DBSCTR backlog tables to PM Kernel tickets.
---

# Backlog Migration

Run `pmctl migrate-backlogs --root ROOT --json` first. Review count, normalized
legacy IDs, paths, and digests. Apply only after the complete manifest validates:

```text
pmctl migrate-backlogs --root ROOT --apply --json
pmctl tickets check --root ROOT --json
```

The command writes tickets atomically and never deletes `BACKLOG.md`. Remove old
files only in the same DBSCTR cycle after Discovery, audit, refinement consumers,
tests, and documentation use tickets. Preserve original rows in migration
evidence; never infer points, priority mappings, or missing completion evidence.
