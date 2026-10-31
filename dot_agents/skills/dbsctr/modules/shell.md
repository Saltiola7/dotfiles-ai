# DBSCTR Module: Shell

## Applicability

- **REQUIRED:** Load for changes to executable shell scripts, shell commands or shell-based automation whose execution behavior is affected.
- **CONDITIONAL:** Load for embedded CI, installer, container or service shell code when quoting, status, signals, portability or side effects matter.
- **PROJECT POLICY:** The project selects dialect, supported shell versions, target OS/tools and test/lint authorities.
- **EXAMPLE:** A README spelling correction mentioning Bash does not need shell implementation guidance.

## Engineering Profile Extensions

- **REQUIRED:** Identify shell/dialect and version, execution identity/environment, argument/input/output contracts, supported platforms and affected callers.
- **CONDITIONAL:** Identify privileged operations, persistent state, concurrency, signal/cleanup and restart/retry requirements.
- **PROJECT POLICY:** Keep selected interpreters, tooling and environment ownership; do not install another shell to satisfy a copied recipe.
- **EXAMPLE:** A script supporting system Bash on macOS cannot assume Bash 4 array/input features.

## Required Outcomes

- **REQUIRED:** Preserve argument boundaries, data-versus-code separation, output streams and actual exit status across commands, pipelines and children.
- **REQUIRED:** Define failure, cancellation, cleanup and partial-state behavior appropriate to the operation; preserve caller-owned variables and traps in sourced code.
- **REQUIRED:** Bound filesystem, subprocess and external side effects to the task and target identity; protect credentials in commands and output.
- **CONDITIONAL:** Prove portability, idempotence, concurrency limits and recovery where the contract requires them.
- **PROJECT POLICY:** Strict mode, ShellCheck, Bats and particular command families are selected techniques, not universal gates.

## Conditional Controls

Use [specialist selection](../references/specialist-selection.md) at first relevant
selection; reuse loaded guidance while source and task evidence remain applicable.

| Current evidence | Preferred specialist |
|---|---|
| Changed shell execution, cleanup, traps, status or portability | `bash-defensive-patterns` |
| Substantial shell test design and Bats selected by project | `bats-testing-patterns` |
| Actual host/service/container concern | Matching Cloud module/platform specialist, only as needed |

- **CONDITIONAL:** Read only supporting resources relevant to the concern; ordinary bounded edits can use existing examples and tests.
- **REQUIRED:** Missing preferred guidance does not itself fail a gate; missing required execution evidence remains a capability gap.
- **EXAMPLE:** Existing pytest/subprocess tests can remain the shell behavior authority.

## Validation Capabilities

- **REQUIRED:** Use selected syntax/lint/test authorities against affected supported interpreters and caller contracts, or record missing capability.
- **CONDITIONAL:** Exercise meaningful failure, awkward-path/argument, child-status, cancellation and cleanup cases when affected.
- **PROJECT POLICY:** Offline fake-tool tests prove local control flow; they do not prove a real host, cluster or remote service accepted a change.

## Lifecycle Obligations

- **REQUIRED:** Carry dialect/platform compatibility, side effects and failure semantics through existing phases and QA evidence.
- **CONDITIONAL:** Release, Deploy and Operate apply when the task produces an artifact or changes/runs an environment, not merely because guidance is loaded.
- **PROJECT POLICY:** Existing lifecycle, permission, maintenance and rollback ownership remain unchanged.
