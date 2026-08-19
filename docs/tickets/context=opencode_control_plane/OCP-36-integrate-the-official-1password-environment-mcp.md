---
schema_version: 1
id: "OCP-36"
slug: "integrate-the-official-1password-environment-mcp"
context: "opencode_control_plane"
title: "Integrate the official 1Password Environment MCP"
kind: "task"
state: "review"
priority: "high"
points: null
depends_on:
  - "OCP-16"
relations: []
owns:
  - "Host OpenCode MCP config, Environment boundary, tests, deployment and restart evidence"
reads:
  - "Desktop-bundled `1password-mcp`, existing managed config and MCP validation"
parallel_safe: false
validation:
  - "Source, deployment, 47 focused tests, resolved config, MCP connection, desktop authentication, and read-only Environment listing pass; no Environments currently exist"
created: "2026-08-17"
updated: "2026-08-17"
completed: null
commits: []
jira_publications: []
migration: "docs/specs/opencode_control_plane/BACKLOG.md:7:2f63a8481cf89bc8e80b63bd65a700751938754d3200b1a1f8e64956476fde57"
---

## Outcome

Integrate the official 1Password Environment MCP

## Context

Migrated from `docs/specs/opencode_control_plane/BACKLOG.md` Active row 7 at `31d6c0c92d3dfd6db93af15f54e3919238ff788f`.

## Scope

Configuration, security contract, live desktop authorization, and deployment must remain one coherent change

## Acceptance Criteria

Source, deployment, 47 focused tests, resolved config, MCP connection, desktop authentication, and read-only Environment listing pass; no Environments currently exist

## Evidence

```json
{"depends_on": "OCP-16", "effort": "S", "id": "OCP-36", "owns": "Host OpenCode MCP config, Environment boundary, tests, deployment and restart evidence", "parallel_safe": "no", "priority": "high", "reads": "Desktop-bundled `1password-mcp`, existing managed config and MCP validation", "reason": "Configuration, security contract, live desktop authorization, and deployment must remain one coherent change", "status": "done", "title": "Integrate the official 1Password Environment MCP", "validation": "Source, deployment, 47 focused tests, resolved config, MCP connection, desktop authentication, and read-only Environment listing pass; no Environments currently exist"}
```

## Risks

Legacy values are preserved without inferred semantics.

## Review

Migrated deterministically; further refinement remains explicit.
