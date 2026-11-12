---
name: python-arrow-interchange
description: Design or review actual Arrow columnar handoffs in Python, including schemas, batches, conversions and buffer ownership. Use for dataframe, database or IPC interchange; preserve the selected engine and storage format.
---

# Python Arrow Interchange

Identify the producer, consumer, transport, selected versions and resource
owner at the actual handoff. Preserve project library and format choices. Arrow
integration does not require migrating transformations, installing PyArrow or
rewriting database access. Contribute to the current task or audit; keep SQL,
transactions and engine-specific behavior with their existing owners.

## Preserve meaning and bounds

- Establish the boundary schema explicitly: field names/order, physical and
  logical types, nullability and required metadata. Inspect empty and all-null
  inputs; inferred types may differ from populated data. A declared schema does
  not prove application value invariants or consumer enforcement of nullability.
- Distinguish nulls from floating NaNs, timestamp units from timezone semantics,
  and decimal precision from binary floating point. Check dictionary/extension
  type support on both sides before casting. Make any lossy conversion explicit.
- A `RecordBatch` groups equal-length arrays under one schema; a `Table` can
  contain chunked columns. Do not assume one contiguous buffer per table column
  or identical chunk boundaries across columns. Preserve bounded batch flow;
  collecting a reader into a table or a Python list can defeat streaming.
- Treat zero-copy as a property to verify for the exact conversion. It does not
  imply no allocation anywhere, a bounded working set or ownership transfer.
  Inspect rechunking, casts, decompression and conversion to Python/pandas objects
  before promising memory savings. A small slice can retain a large parent.
- Identify which object retains buffers and who closes the reader, database
  cursor, mapping or stream. Preserve valid lifetime through consumption and
  deterministic cleanup on exhaustion, early stop and failure.

For IPC, Parquet, pandas or native-interface details, read
[handoff decisions](references/handoffs.md) only as needed.

## Evidence

Use small fixtures at the real adapter boundary: null/all-null and empty batches,
multiple chunks, timestamps with meaningful precision/timezone, dictionary values
and unsupported or incompatible types. Verify decoded values plus the schema
and metadata the consumer actually requires. Exercise partial consumption and
failure cleanup. Measure peak memory for the selected path when performance is
part of the task; a round trip alone does not demonstrate zero-copy.

Report actual producer/consumer versions, tested transport and limitations.
Mark runtime checks unavailable when dependencies are missing; static review
does not establish engine compatibility.

Primary references: [Arrow data model](https://arrow.apache.org/docs/python/data.html),
[timestamps](https://arrow.apache.org/docs/python/timestamps.html).
Match documentation to the project's supported versions.
