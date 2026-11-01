# DuckDB reader selection

Apply [entrypoint boundaries](../SKILL.md). Select the actual format's reader,
not a macro binding every extension. Verify exact support in the selected
runtime and [official import docs](https://duckdb.org/docs/stable/data/overview).

| Input | Reader or approach | Checks |
|---|---|---|
| CSV/TSV/text | `read_csv` | Delimiter, quoting, headers, types, rejects and encoding; suffix alone is insufficient. |
| JSON/JSONL/NDJSON | `read_json` or `read_json_auto` | Record shape, nested types, inference and large integers. |
| Parquet | `read_parquet` | Logical types, decimals, row-group pruning and schema differences. |
| Avro | Supported Avro reader | Required extension and version. |
| Excel | `read_xlsx` where supported | `.xls` is a different format; confirm support, sheet, headers and range. |
| GeoJSON/GDAL files | `ST_Read` where supported | Spatial extension, CRS and geometry type. Plain JSON inspection can suffice without geometry interpretation. |
| SQLite | Supported scanner/ATTACH | Discover exact table; don't arbitrarily choose the first. Prefer read-only attachment. |
| Jupyter notebooks | Parse JSON as data | Never execute cells; saved outputs may contain secrets. |
| Other binary data | `read_blob` only if useful and bounded | Avoid emitting entire binary payloads. |

Check glob expansion, partition columns, union-by-name, missing columns and schema
evolution for multi-file inputs. Do not expand a single file into an entire
bucket/directory to make inference succeed. Samples do not establish stable order.

HTTPS/S3/GCS/Azure reads may need `httpfs` or provider extensions. Extension needs
are capability checks, not installation instructions. `LOAD` can trigger automatic
installation depending on configuration. Use existing reviewed extensions and
approved identity; do not auto-create secrets, scan credential chains or enable
persistence. Keep credential-bearing URLs out of reports.

Start with metadata and the narrowest useful schema/sample. `DESCRIBE`, `LIMIT`,
`count()` and `SUMMARIZE` have different costs. Record actual files, columns, rows
and bytes inspected when known; a sample is not a complete audit.
