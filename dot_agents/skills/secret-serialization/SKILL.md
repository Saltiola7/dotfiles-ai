---
name: secret-serialization
description: Trace Python and JavaScript credential holders through repr, generated serialization, logs, spans and response sinks when reviewing secret leakage or changes to credential fields and whole-object serialization.
---

<!-- Adapted by dotfiles-ai, 2026-10-28; see UPSTREAM.md and security-toolkit provenance. -->
# Secret Serialization Review

Trace both the credential holder and receiving serializer/sink in the approved
change and its authorized dependency scope. The holder and sink may predate the
diff; do not broaden to a repository audit silently. Confirm the value is a real
credential rather than a public identifier, token counter or fixture.

Read [references/python.md](references/python.md) for Python dataclasses, attrs,
Pydantic and telemetry. Read [references/javascript-typescript.md](references/javascript-typescript.md)
for JavaScript/TypeScript enumeration, JSON, inspection and logger behavior.

1. Identify affected holders and generated/default/custom serialization paths.
   `repr=False` does not block `asdict`; Pydantic repr and export exclusions are
   separate. TypeScript `private` is not runtime access control.
2. Trace callers to concrete log/span/error/response/cache/queue sinks and
   inspect actual serializer version/configuration. Check both sides within
   scope, including relevant unchanged paths; report any missing closure.
3. Evaluate the effective redaction/allowlist at each sink. Custom `toJSON`,
   inspection hooks, serializers, getters and explicit property access can
   change default behavior. Non-enumerable properties can appear in Node
   `util.inspect` with `showHidden: true` or `%o`; a table is never exclusion proof.
4. Establish who receives the serialized value and whether that disclosure is
   unauthorized. Deliberate credential transport to an intended authenticated
   endpoint (for example an OAuth request body) is not automatically a leak.
5. Report confirmed holder-to-sink exposure with source evidence, affected
   principal, control and concrete impact. Assign severity using the primary
   workflow's policy. Holder-only or sink-only observations stay unconfirmed
   hardening candidates; unresolved reachability/disclosure is needs-validation
   with no vulnerability severity. Upstream example labels are illustrative.

Raw access such as `vars`, `__dict__`, `pickle` and custom serializers needs its
own sink review: field-level display flags do not protect all consumers.
For a confirmed exposure, propose a narrow allowlist/redaction or holder change
and a regression fixture that uses the actual serializer with dummy credentials.
Direct leakage outside this technique goes to the selected primary workflow;
missing tests alone are not findings. Never print actual secret values in
evidence. No scans, target execution, installs, external reporting or credential
changes are authorized by loading this skill.
