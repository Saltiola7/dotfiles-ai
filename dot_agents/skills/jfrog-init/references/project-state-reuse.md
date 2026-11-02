# Reusing existing setup hints

An existing `setup.json` hint may contain server ID, normalized JPD URL and
`currentActiveProject`; it is a pointer, not authorization or current validation.
Use it only when the current task lacks a selection and its server/URL identity
matches the selected platform. Resolve conflicting hints before dependent work.

Do not write setup state as a diagnostic side effect. Do not interpret a cached
project as proof of existence, entitlement, credentials or a live connection.
Read only the necessary non-secret fields and keep private identifiers out of
public source. Retain existing state unless its owner has an authorized update.
