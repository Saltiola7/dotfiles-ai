---
name: pulumi-best-practices
description: Design and review Pulumi programs, Output/Input dependencies, secrets and identity-preserving resource refactors. Use for actual Pulumi code or a selected preview workflow; keep project language, versions, backend and stack.
---

# Pulumi Best Practices

Preserve the project's selected language, CLI/SDK/provider versions, dependency
manager, backend, stack and existing delivery workflow. Resolve only missing facts
that affect the change. Keep the current task primary and acceptance authority.

- Pass Outputs as Inputs; use `apply` for transformations. A valid string
  transformation is not a defect merely because interpolation is shorter.
- Prefer resource declarations outside `apply`. Resources inside a callback can
  be absent from preview when its input is unknown; this is not a universal
  claim that they can never be previewed or tracked.
- Give actual component children their intended parent/provider ownership and
  register outputs. Introduce a component when an abstraction serves the task.
- Preserve secret marking through transformations; never log plaintext values or
  expose secret outputs to diagnose them.
- Treat resource names, parents, type tokens and aliases as identity-bearing.
  Review replacement/deletion and stateful-data implications of a refactor.
- A preview executes the selected program and provider reads. Distinguish code
  review, local checks, preview, config/state writes and an authorized deployment.
  Loading this guidance does not authorize installs, logins or mutations.

Read the relevant sections of [detailed practices](references/details.md) when
reviewing Output flow, component ownership, secrets, aliases or a preview/CI
change. It retains adapted examples and version-sensitive caveats; it is not an
instruction to run every example. For substantive component API or packaging
work, `pulumi-component` supplies focused guidance if available. A specific failed
operation can use `pulumi-debug-failed-operation`; neither is a required extra hop.

Return the actual change, affected identity/secret boundaries, validation evidence
and remaining gaps to the existing workflow. A successful source check does not
establish provider execution or deployment health.
