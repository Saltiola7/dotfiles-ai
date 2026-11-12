> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](UPSTREAM.md) for attribution and adaptation details.

# ClickHouse Best Practices

Agent skill providing comprehensive ClickHouse guidance for schema design, query optimization, and data ingestion.

## Managed delivery

This complete selected bundle is distributed through the existing dotfiles-ai
skill owner. Loading it does not run an installer, configure a connection or
install a plugin. See [task boundaries](SKILL.md#task-boundaries).
The upstream authoring template is retained as provenance material.

## What's Included

**31 atomic rules** organized by prefix:

| Prefix | Count | Coverage |
|--------|-------|----------|
| `schema-pk-*` | 4 | PRIMARY KEY selection, cardinality ordering |
| `schema-types-*` | 5 | Data types, LowCardinality, Nullable |
| `schema-partition-*` | 4 | Partitioning strategy, lifecycle management |
| `schema-json-*` | 1 | JSON type usage |
| `query-join-*` | 5 | JOIN algorithms, filtering, alternatives |
| `query-index-*` | 1 | Data skipping indices |
| `query-mv-*` | 2 | Incremental and refreshable MVs |
| `insert-batch-*` | 1 | Batch sizing (10K-100K rows) |
| `insert-async-*` | 2 | Async inserts, data formats |
| `insert-mutation-*` | 2 | Mutation avoidance |
| `insert-optimize-*` | 1 | OPTIMIZE FINAL avoidance |
| `agent-connect-*` | 1 | MCP + CLI connectivity, credentials, output formats |
| `agent-discovery-*` | 1 | 7-step schema discovery workflow |
| `agent-query-*` | 1 | Query safety limits, progressive exploration |

## Trigger Phrases

This skill activates when you:
- "Create a table for..."
- "Optimize this query..."
- "Design a schema for..."
- "Why is this query slow?"
- "How should I insert data into..."
- "Should I use UPDATE or..."
- "Connect Claude to ClickHouse..."
- "Set up MCP for ClickHouse..."
- "Query ClickHouse from an agent..."

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Quick reference and decision frameworks |
| `AGENTS.md` | Complete rule reference (auto-generated) |
| `rules/*.md` | Individual rule definitions |

## Related Documentation

All rules link to official ClickHouse documentation:
- [ClickHouse Best Practices](https://clickhouse.com/docs/best-practices)
