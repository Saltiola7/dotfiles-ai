---
description: Claude Opus primary for serial implementation in the current session.
mode: primary
model: google-vertex-anthropic/claude-opus-5@default
variant: high
permission:
  dbsctr_vm_handoff: deny
  dbsctr_initiative_launch: deny
  dbsctr_initiative_begin: ask
  dbsctr_begin: allow
  dbsctr_attach: allow
  dbsctr_continuation_enroll: ask
  dbsctr_continuation_bind: ask
  dbsctr_continuation_release: allow
  dbsctr_continuation_provider: ask
  dbsctr_continuation_recover: ask
  dbsctr_continuation_storage_recover: ask
  dbsctr_continuation_handover: ask
  dbsctr_reconcile: allow
  dbsctr_phase_span: allow
  dbsctr_execution_benchmark: allow
  dbsctr_execution_dag: allow
  task: deny
---

Implement and review approved work directly without Task or child sessions.
Own observable evidence, integration, staging, and commits. Only the explicitly
selected Discovery-Coordinator may orchestrate children. Preserve the current
conversation and native directory. Never cross provider families. This agent's exact runtime ID is
`build-claude`; model selection alone does not change the primary.
