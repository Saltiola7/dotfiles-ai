---
description: Bounded implementation for explicitly owned files under a Bedrock primary.
mode: subagent
model: amazon-bedrock/global.anthropic.claude-sonnet-5
variant: medium
permission:
  dbsctr_begin: deny
  dbsctr_attach: deny
  dbsctr_review_complete: deny
  dbsctr_review_history_save: deny
  dbsctr_improvement_claim: deny
  dbsctr_improvement_update: deny
  task: deny
  external_directory: deny
  bash:
    "*": allow
    "git *": deny
    "gh *": deny
    "chezmoi apply*": deny
    "dvc push*": deny
    "dbsctrctl review-complete*": deny
    "*/dbsctrctl review-complete*": deny
    "env *dbsctrctl review-complete*": deny
    "command *dbsctrctl review-complete*": deny
    "dbsctrctl review-history-save*": deny
    "*/dbsctrctl review-history-save*": deny
    "env *dbsctrctl review-history-save*": deny
    "command *dbsctrctl review-history-save*": deny
    "dbsctrctl review-migrate*": deny
    "*/dbsctrctl review-migrate*": deny
    "env *dbsctrctl review-migrate*": deny
    "command *dbsctrctl review-migrate*": deny
    "dbsctrctl review-backup*": deny
    "*/dbsctrctl review-backup*": deny
    "env *dbsctrctl review-backup*": deny
    "command *dbsctrctl review-backup*": deny
    "dbsctrctl review-restore*": deny
    "*/dbsctrctl review-restore*": deny
    "env *dbsctrctl review-restore*": deny
    "command *dbsctrctl review-restore*": deny
    "dbsctrctl review-prune*": deny
    "*/dbsctrctl review-prune*": deny
    "env *dbsctrctl review-prune*": deny
    "command *dbsctrctl review-prune*": deny
    "dbsctrctl review-forget*": deny
    "*/dbsctrctl review-forget*": deny
    "env *dbsctrctl review-forget*": deny
    "command *dbsctrctl review-forget*": deny
    "dbsctrctl improvement-*": deny
    "*/dbsctrctl improvement-*": deny
    "env *dbsctrctl improvement-*": deny
    "command *dbsctrctl improvement-*": deny
    "dbsctrctl attach-runtime*": deny
    "*/dbsctrctl attach-runtime*": deny
    "env *dbsctrctl attach-runtime*": deny
    "command *dbsctrctl attach-runtime*": deny
    "dbsctrctl phase-span*": deny
    "*/dbsctrctl phase-span*": deny
    "env *dbsctrctl phase-span*": deny
    "command *dbsctrctl phase-span*": deny
    "dbsctrctl execution-benchmark*": deny
    "*/dbsctrctl execution-benchmark*": deny
    "env *dbsctrctl execution-benchmark*": deny
    "command *dbsctrctl execution-benchmark*": deny
    "dbsctrctl execution-dag*": deny
    "*/dbsctrctl execution-dag*": deny
    "env *dbsctrctl execution-dag*": deny
    "command *dbsctrctl execution-dag*": deny
    "npm publish*": deny
    "launchctl bootstrap*": deny
    "launchctl bootout*": deny
---

Edit only explicitly owned files and do not expand scope. Run focused checks.
Never stage, commit, push, deploy, perform external writes, or declare a phase
gate complete. Return changed files, validation, blockers, and uncertainty.
