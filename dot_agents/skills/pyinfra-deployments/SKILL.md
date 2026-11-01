---
name: pyinfra-deployments
description: Author and diagnose pyinfra inventories and deploys, including idempotency, fact timing, privilege and bounded execution. Use for actual pyinfra code or runs.
---

# Pyinfra Deployments

Preserve the project's selected pyinfra version, inventory, connectors, deployment
owner and task authorization. Return actual evidence to the existing primary and
QA; loading this method does not install tools or authorize target operations.

## Bind the target and operation contract

- Establish the selected CLI/API version, deploy inputs, effective host selection,
  connector, user and privilege before a run. Inspect local help and version-matched
  operation signatures rather than copying current examples into an older project.
- Inventory, configuration and deploy files are Python code. Review their relevant
  effects before executing them, including local calls and imports. A diagnostic
  or dry run is not a sandbox or an offline operation.
- Prefer a declarative operation for desired state. Confirm its target-platform
  support and convergence behavior; shell, script and callback operations require
  explicit repeatability and failure reasoning. An operation's name does not make
  an imperative action idempotent.

## Respect preparation and execution

- Deploy Python runs locally for each host during preparation, before the target
  mutations. Facts used in Python branches can describe pre-deploy state rather
  than the effects of earlier operations in source order.
- Use selected-version execute-time conditions for work dependent on actual prior
  changes. Pass a supported callable, such as `operation.did_change`, rather than
  evaluating it during preparation. Read
  [timing and execution](references/timing-and-execution.md) for fact-dependent
  branching, operation output, conditional restarts, previews or partial failures.
- Keep ordering, host concurrency, privilege and command failure behavior explicit
  where they affect availability. Do not add retries, ignored errors or stronger
  privileges merely to obtain a successful run.

## Preview, execute and verify

Inspect the effective bounded inventory and proposed operations before the
authorized deployment. Dry-run evidence covers planning, connections and fact
collection, not an executed change or recovery. Avoid verbose command/output
capture that exposes credentials or sensitive inventory data.

After execution, inspect per-host results and the project's relevant state or
service checks. Distinguish no change, successful mutation, partial failure and
unavailable evidence. Reconcile completed effects before replaying failed work,
especially imperative operations. Report selected versions, actual targets,
results and recovery limits without claiming an unrun deployment or readiness.
