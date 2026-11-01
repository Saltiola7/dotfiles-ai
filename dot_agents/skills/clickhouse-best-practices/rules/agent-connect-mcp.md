---
title: Select an Existing ClickHouse Connection
impact: HIGH
impactDescription: Reuse approved identity and transport without implicit setup
tags: [agent, mcp, cli, connectivity, setup]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

## Select an Existing ClickHouse Connection

Apply [task boundaries](../SKILL.md#task-boundaries). Static source/schema reviews
need no connection, schema discovery queries or credentials.

For authorized live work, identify the exact service/database, read/write scope
and resource budget. Prefer a sufficient configured connector/MCP. The managed
skill remains portable with an already installed/configured `clickhouse-client`
or project's existing client; check actual client/version options before use.
Use a single selected transport and reviewed skill copy per task.

An unavailable tool is a capability gap, not permission to install MCP/CLI,
provision Cloud services, enable writes, alter profiles or reset credentials.
Setup belongs to the existing installer/connection owner when explicitly chosen.
Hosted MCP capabilities and authentication can change; verify the actual tool
contract rather than assuming every Cloud endpoint is read-only or OAuth-enabled.

Use existing credential resolution or a selected protected client configuration.
Never put passwords/tokens in SQL, shell arguments, URLs, prompts or committed
files. Don't dump environment variables, search unrelated configuration or scan
credential providers. Preserve TLS verification and the approved identity.
An HTTP fallback is suitable only when a configured authenticated client and
policy already cover it; don't reconstruct authentication by exposing headers.

Choose structured output supported by the client: JSON/JSONCompact for typed
metadata, JSONEachRow for streams, or TSV with names for suitable bounded tables.
Select only needed columns and bound result bytes/rows. Token counts and transport
latency vary by payload/tool; no fixed ranking proves which path is faster.

A sleeping service may need bounded recovery, but distinguish transient readiness
from authentication/permission errors. Retry only safe reads within the same
budget; never blindly retry uncertain writes. Continue with
[schema discovery](agent-discovery-schema.md) and
[query bounds](agent-query-safety.md) when execution is in scope.

References: [MCP](https://github.com/ClickHouse/mcp-clickhouse),
[CLI](https://clickhouse.com/docs/interfaces/cli),
[formats](https://clickhouse.com/docs/interfaces/formats).
