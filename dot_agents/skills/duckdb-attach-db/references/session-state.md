# Optional DuckDB session state

Apply [entrypoint boundaries](../SKILL.md). SQL init files are executable content:
they can perform extension, network, filesystem and secret operations. Inspect
the selected file before executing it; a session is not an authorization boundary.

Upstream conventions use `.duckdb-skills/state.sql` within a project or
`~/.duckdb-skills/<project-id>/state.sql` outside it. These are optional existing
conventions, not locations to search or create automatically. Resolve state from
the user's supplied path or established project policy. Do not silently choose
between competing files or execute either merely because it exists.

When persistence is requested:

1. Use the selected destination; preserve unrelated content and permissions.
   Changes to `.gitignore` or home-directory state require inclusion in the task.
2. Review statements/aliases and resolved database identities rather than fragile
   substring duplicate checks. Preserve read-only settings; avoid alias collisions.
3. Keep only necessary ATTACH/USE/LOAD or macro statements. No credentials, tokens
   or credential-bearing URLs; use approved runtime secret resolution.
4. Quote SQL literals/identifiers through the client's supported mechanism.
   Shell quoting does not escape SQL. Do not interpolate paths into shell code.
5. Review the concrete change. When authorized, a temporary read-only session can
   verify metadata, but does not prove another connection adopted the file.

A supported read-only attachment has the illustrative SQL shape
`ATTACH 'reviewed.duckdb' AS source (READ_ONLY)`. This is not an instruction to
open a file. The process must retain its connection for attachment state to
exist. An isolated `:memory:` session alone does not prohibit external access,
extension autoloading or filesystem writes.
