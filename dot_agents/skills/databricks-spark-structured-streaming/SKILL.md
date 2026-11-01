---
name: databricks-spark-structured-streaming
metadata:
  version: "0.1.0"
description: "Design and review Spark Structured Streaming within Databricks, including checkpoints, state, watermarks, joins, sinks and trigger choices for the selected runtime."
license: LicenseRef-Databricks
---

> Modified by dotfiles-ai: scoped for project policy, static review and authorized Databricks Services work. See `UPSTREAM.md` for provenance and changes.

# Spark Structured Streaming

## Scope and execution boundaries

Use this bundle only within or connecting to Databricks Services, under the
included `LICENSE.upstream` and `NOTICE.upstream`. It is not generic Spark guidance.

For a repository audit, review source, SQL, bundle configuration and declared
runtime/dependency evidence first. Do not install or upgrade tools, authenticate,
select or change profiles, query a workspace, execute notebooks/examples, or
deploy resources merely to complete a static review. Record unavailable runtime,
workspace and performance evidence as coverage gaps. Examples below illustrate
APIs; they do not authorize their side effects.

For requested live work, retain the already selected workspace, profile,
authentication provider, runtime and dependency constraints. Resolve a target only
when missing or conflicting; do not repeatedly ask for an already selected
profile. Check the selected tool's actual version/help and current official
documentation for the specific operation. Propose a necessary migration or tool
upgrade separately instead of requiring the newest CLI for every task.

Read only relevant references. If a named sibling skill is unavailable, state the
guidance gap and use current official documentation within scope; do not install
an entire skill bundle. Treat design defaults as workload-dependent recommendations,
not automatic defects. Keep review findings distinct from measured execution
results. DBSCTR owns authorized remediation and delivery.

For live CLI, authentication or workspace targeting, read
[databricks-core](../databricks-core/SKILL.md) and reuse the selected context.


Production-ready streaming pipelines with Spark Structured Streaming. This skill provides navigation to detailed patterns and best practices.

## Quick Start

```python
from pyspark.sql.functions import col, from_json

# Basic Kafka to Delta streaming
df = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "topic")
    .load()
    .select(from_json(col("value").cast("string"), schema).alias("data"))
    .select("data.*")
)

df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/Volumes/catalog/checkpoints/stream") \
    .trigger(processingTime="30 seconds") \
    .start("/delta/target_table")
```

## Core Patterns

| Pattern | Description | Reference |
|---------|-------------|-----------|
| **Kafka Streaming** | Kafka to Delta, Kafka to Kafka, Real-Time Mode | See [references/kafka-streaming.md](references/kafka-streaming.md) |
| **Real-Time Mode (RTM)** | Sub-second E2E latency — cluster setup, slot math, supported ops (incl. stream-stream inner join on DBR 18+), `transformWithState`, observability, error classes, delivery semantics | See [references/real-time-mode.md](references/real-time-mode.md) |
| **Lakebase Sink** | Write streaming records into Lakebase Postgres with transactional upserts. Native `format("postgresql")` sink (DBR 18.3+) and manual `foreach` sink as a fallback | See [references/lakebase-sink-python.md](references/lakebase-sink-python.md) |
| **Stream Joins** | Stream-stream joins, stream-static joins | See [references/stream-stream-joins.md](references/stream-stream-joins.md), [references/stream-static-joins.md](references/stream-static-joins.md) |
| **Multi-Sink Writes** | Write to multiple tables, parallel merges | See [references/multi-sink-writes.md](references/multi-sink-writes.md) |
| **Merge Operations** | MERGE performance, parallel merges, optimizations | See [references/merge-operations.md](references/merge-operations.md) |

## Configuration

| Topic | Description | Reference |
|-------|-------------|-----------|
| **Checkpoints** | Checkpoint management and best practices | See [references/checkpoint-best-practices.md](references/checkpoint-best-practices.md) |
| **Stateful Operations** | Watermarks, state stores, RocksDB configuration | See [references/stateful-operations.md](references/stateful-operations.md) |
| **Trigger & Cost** | Trigger selection, cost optimization, RTM | See [references/trigger-and-cost-optimization.md](references/trigger-and-cost-optimization.md) |

## Best Practices

| Topic | Description | Reference |
|-------|-------------|-----------|
| **Production Checklist** | Comprehensive best practices | See [references/streaming-best-practices.md](references/streaming-best-practices.md) |

## Production Checklist

- [ ] Checkpoint location is persistent (UC volumes, not DBFS)
- [ ] Unique checkpoint per stream
- [ ] Compute/scale policy matches the selected trigger, runtime support, latency and cost requirements; Real-Time Mode may impose narrower constraints
- [ ] Monitoring configured (input rate, lag, batch duration)
- [ ] End-to-end delivery semantics validated for each source, sink, checkpoint and retry path; transaction IDs alone do not prove exactly-once behavior
- [ ] State retention and late-data policy explicit; apply supported watermarks/timeouts where needed rather than dropping required late records by default
- [ ] Stream-static join type matches required unmatched-row semantics; inner and left joins serve different requirements
