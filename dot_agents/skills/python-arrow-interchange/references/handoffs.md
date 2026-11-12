# Transport and Conversion Decisions

## IPC and bounded consumption

An IPC stream is sequential; the IPC file format supports random batch access
and requires a seekable source. Batches in a stream share its schema. Select the
existing protocol and consume incrementally when the interface promises bounded
memory. A row-count batch limit alone does not bound bytes for variable-width
values; account for oversized rows and retained downstream batches.

IPC reads can share buffers when the source and encoding permit it. Compression
or conversion may allocate. An in-memory output sink still retains the complete
serialized payload even if writes happen batch by batch.

Source: [Arrow IPC](https://arrow.apache.org/docs/python/ipc.html).

## Parquet compatibility

Parquet is an encoded storage format, distinct from Arrow's in-memory format.
Memory mapping a Parquet file does not eliminate decoding/allocation. Check
project-selected file version, compression, row groups and reader support;
do not treat an IPC test as a Parquet compatibility test.

Timestamp coercion and Parquet format versions affect supported precision.
Reject unwanted truncation rather than enabling it to make a write succeed.
Verify dictionary, timezone and extension metadata with the actual target
reader. Arrow schema metadata can help compatible readers reconstruct types;
it does not guarantee that every reader honors it.

Sources: [file I/O and memory mapping](https://arrow.apache.org/docs/python/parquet/parquet.html),
[Parquet type handling](https://arrow.apache.org/docs/python/parquet/parquet_type_handling.html).

## pandas and native handoffs

For pandas, verify selected nullable dtypes and conversion options. Arrow nulls
can change the default pandas dtype; multiple chunks or representation changes
can require copies. Avoid introducing `self_destruct=True` as a routine memory
optimization: it invalidates further use of the Arrow object and may not release
shared buffers immediately.

The Arrow C data interface shares arrays within one process using release
callbacks. It is not an IPC transport. For native wrappers, establish who owns
the exported resources and releases them exactly once; prefer established
high-level adapters to handwritten ownership code.

Sources: [pandas conversion](https://arrow.apache.org/docs/python/pandas.html),
[C data interface](https://arrow.apache.org/docs/format/CDataInterface.html).
