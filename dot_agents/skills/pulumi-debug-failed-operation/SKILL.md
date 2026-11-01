---
name: pulumi-debug-failed-operation
description: Diagnose a specific failed Pulumi update or preview from its recorded events and affected program, state or environment. Use for actual operation failures; preserve the identified backend, stack and operation rather than assuming the latest one.
---

# Debug a Failed Pulumi Operation

Reuse the operation the user identified: backend, organization/project/stack and
update version or preview/operation ID. Existing resolved facts and authorization
persist. Resolve material ambiguity from available records or one focused
question; do not substitute the latest operation or match an actor login as proof.

Read [operation diagnosis](references/details.md) for record retrieval, pagination,
diagnostic interpretation and fix boundaries. Prefer the available immutable
record from the selected backend. Pulumi Cloud API commands are conditional
examples; another backend does not require a Cloud account or login.

- Preserve the real fetch/parse status and coverage. A successful formatter is
  not proof that a failed upstream command returned a record.
- Inspect relevant error and non-error diagnostics, including program stderr
  (`info#err`), with bounded non-secret evidence. Do not dump full state, secret
  outputs, credentials or unreviewed logs into the response.
- Tie each proposed cause to the actual program/resource/state/environment.
  Distinguish confirmed evidence, a hypothesis, partial changes and missing access.
- Make the smallest authorized fix through the current workflow. A recorded
  failure does not authorize retrying `up`, refresh/import, state/config/IAM/ESC
  changes, provider upgrades, SDK installation or a new PR coordinator.

Report the identified operation, causal evidence, change or next bounded check,
validation actually performed and any remaining coverage/access gap. A local edit
or preview alone does not prove deployment recovery.
