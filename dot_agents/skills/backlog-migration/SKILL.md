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

The directly invoked command writes reporting tickets atomically under
`data/backlog/tickets/` and never deletes `BACKLOG.md`. Discovery and DBSCTR do
not consume the result. Preserve original rows in migration evidence; never
infer points, priority mappings, or missing completion evidence. DVC and Git
metadata remain operator-managed.
