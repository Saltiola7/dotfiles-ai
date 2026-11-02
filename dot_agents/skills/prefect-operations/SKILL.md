---
name: prefect-operations
description: Inspect and diagnose existing Prefect flows, runs, deployments and work pools using an explicitly selected API and available tools. Use for concrete Prefect operations; preserve project SDK and CLI ownership.
---

# Prefect operations

Preserve the project's Prefect/Python versions, deployment owner, target and task
authorization. Flow authoring or source review can use its existing SDK, CLI and
tests without MCP. Do not install or connect MCP merely to edit flow code.

## Bind the operational target

Inspect available capabilities and existing selection before querying live state.
The managed local adapter exposes inspection tools for a selected self-hosted API;
it omits Cloud workspace discovery and the external docs proxy. Other connections
may have different capabilities. Distinguish their server names and identities.

Use `get_identity` to verify the intended API and backend version before further
queries. Inspect structured `success`, `identity` and `error` fields: a successful
MCP transport call can still report an API failure. Missing configuration, failed
authentication or an unavailable backend remains a gap; do not start a backend,
use an ephemeral replacement, switch global profiles or select another account.
Keep credentials and private settings out of transcripts.

Self-hosted calls omit `workspace_id`. For a separately selected Cloud OAuth
connection, use its actual workspace-discovery capability and consented identifiers.
Use the only authorized workspace when that connection supports it; otherwise
resolve the intended workspace from context. Never invent an ID or copy one from
an unrelated connection. Cloud OAuth is not required for the local adapter.

## Diagnose with bounded evidence

- Start from known run/deployment IDs. Use `get_dashboard` for an actual overview
  question, then narrow to affected runs, tasks, deployments, work pools or events.
- Inspect `get_flow_runs`, `get_flow_run_logs`, `get_task_runs`, `get_deployments`,
  `get_work_pools` or `read_events` at the implicated layer. Preserve complete UUIDs
  and bound filters, time ranges and log/result limits to the question.
- Reuse selected identifiers instead of repeatedly fetching broad lists. Resolve
  schema/filter differences against the selected backend and available tool schema.
- Distinguish observed failures, hypotheses, proposed repairs and verified results.
  Logs and parameters can contain secrets; return only relevant non-secret evidence.

## Use version-matched guidance

Resolve CLI/SDK/deployment syntax from the project's selected versions and official
documentation. The local adapter does not provide documentation-search tools;
use available primary documentation or installed source/help when needed. For
release questions, obtain the exact release/version/date from an authoritative
source rather than treating semantic search or a remembered version as current.

Flow code remains under project validation and lifecycle ownership. Review task
boundaries, retries, caching, concurrency and side effects against the actual
workflow; this operational snapshot is not a universal architecture prescription.

## Keep mutations explicit

The managed adapter is read-only. Do not claim that it triggered, cancelled,
created, updated or deleted anything. A project-selected CLI/SDK is a separate
path for an operation already authorized by the task. Verify its version and
effective target/authentication independently; MCP identity does not prove the
CLI uses the same profile or environment.

Prefer complete UUIDs from verified results, supported noninteractive flags and
structured output. Inspect selected-version help for operations such as deployment
run, flow-run cancellation or automation creation. If execution is unavailable,
return a proposed command with its target assumptions and do not imply it ran.
Never use a truncated table identifier or change global authentication to avoid
a target mismatch.

Return the diagnosis or change, actual target/version evidence, checks performed
and remaining gaps to the existing primary and QA. Runtime installation, tool
discovery, backend connectivity and workflow readiness are distinct observations.
Provenance and exact license: [UPSTREAM.md](UPSTREAM.md).
