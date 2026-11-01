---
name: hetzner-operations
description: Diagnose and operate actual Hetzner Cloud resources with hcloud, resolving effective project identity, action status, persistent data and recovery. Use for Hetzner-specific work.
---

# Hetzner Cloud Operations

Preserve the project's selected CLI/API, infrastructure owner, resource policy and
existing task authorization. Establish facts already available before asking about
a material missing target. Return findings and real evidence to the current
primary and project QA; this method does not add a delivery coordinator.

## Resolve the effective target

- Record the selected hcloud version, API endpoint, intended project and exact
  resource IDs. Use the project's existing context/configuration authority.
- Inspect configuration precedence without printing credentials. Selected-client
  help is authoritative: flags and environment can override named-context values.
  Selecting a context does not by itself clear an inherited `HCLOUD_TOKEN`.
- Reuse approved credential sources. A context name or successful login is not
  proof of the effective project, permission or resource. Resolve ambiguity with
  non-secret identity/resource facts rather than token or environment dumps.
- Output redaction varies by command/version. Current clients can redact config
  listings and require an explicit sensitive-output flag for token retrieval;
  neither fact justifies reading a real token as ordinary diagnostic evidence.

Use selected-version help and official [CLI setup](https://github.com/hetznercloud/cli/blob/main/docs/tutorials/setup-hcloud-cli.md)
or [context reference](https://github.com/hetznercloud/cli/blob/main/docs/reference/manual/hcloud_context.md)
when syntax or precedence is material. Verify changing resource availability,
pricing, image/type/location and API capabilities from current official sources.

## Diagnose and make bounded changes

- Read bounded status, action, network and storage facts for the identified
  resource. Keep verified causes distinct from hypotheses and missing evidence.
- Bind create/resize/rescue, attach/detach, protection, DNS and deletion work to
  actual targets, dependencies, network exposure, persistent data and recovery.
  Reconcile partial changes before retrying an operation.
- Preserve project firewall and access policy. Sample public SSH rules, locations,
  types, images or formatting commands are not production defaults. A volume's
  existence does not establish that its contents are disposable.
- Distinguish submitted/accepted cloud actions from completed actions and actual
  workload readiness. Inspect the selected action's final status and the relevant
  health checks; preserve errors and incomplete state.
- SDK/CLI installation, account/context changes and resource mutations follow the
  actual task and native permissions. Loading this guidance authorizes none of them.

## Verify and return

Use project-selected infrastructure or application checks for the affected
contract. Report effective non-secret target identity, actual commands/results,
remaining hypotheses, readiness and recovery status. Missing API/tool access is a
capability gap; do not create credentials, switch accounts or claim a cloud pass.
Use installed host/container guidance only when that additional concern exists.
