# Agent Guard common preflight

Read for an explicitly selected JFrog-governed operation. Workspace directory,
JFrog project key, platform server ID and catalog package identity are separate.
Reuse known task/entry selections; ask only when unresolved material identity
blocks work. Do not invent keys or derive a server ID from a URL/package name.

## Registry and runtime

Agent Guard is a separate executable dependency. Official upstream registry is
`https://releases.jfrog.io/artifactory/api/npm/coding-agents-npm/`; an existing
explicit registry selection retains its owner. Do not blindly trust an ambient
registry override, fetch floating code, or assume listing is free of installation
side effects. Select and review a concrete runtime version/provenance through its
native installer owner before execution. Example package arguments use
`@jfrog/agent-guard@<APPROVED_VERSION>`; resolve the placeholder first.
No Node/npm/Agent Guard installation follows from loading this reference.

## Identity and credentials

1. Keep the platform/project already selected by the current task or verified
   existing Agent Guard entry.
2. If necessary, inspect only redacted native CLI configuration to resolve actual
   server identifiers; never read raw credential files or print config export.
3. Multiple plausible selections require clarification. Missing configuration,
   auth denial and catalog errors do not justify switching servers or changing
   defaults. An ambient URL/token pair does not silently override an explicit ID.
4. Resolve an actual required project key from verified task/entry/configuration
   evidence; do not invent `default`, assume a workspace name, or use admin-only
   enumeration as a workaround for missing selection.
5. Keep secret entry/storage and forwarding with the actual native client owner.
   Verify current client's environment behavior instead of universal assertions
   that it forwards all/no ambient variables. Do not expose tokens or raw headers.

The preserved environment/guard helpers can inspect credentials and contact a
platform; review their imports, effects and selected target before an authorized
use. An unknown/failed guard is not proof of disabled governance. Required policy
cannot be bypassed to make an operation succeed. Existing task consent persists;
do not ask repeatedly when selection and authority are concrete.

## Execution and freshness

Preserve argument boundaries and real exit codes. Quote substituted shell values;
never evaluate a catalog-provided command string. Use bounded output and sanitize
errors. Cached local state, catalog data and current connection state have distinct
freshness. Reuse adequate same-task evidence, and make a bounded fresh query when
the requested decision needs current state. Do not mandate repeated network/npm
execution for every follow-up or automatically reopen OAuth.
