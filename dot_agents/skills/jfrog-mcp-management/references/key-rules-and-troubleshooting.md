# Key rules and bounded troubleshooting

This reference applies only to explicitly selected JFrog Agent Guard/catalog
work or an established project governance requirement. Unrelated MCP setup keeps
its existing native owner. The [active skill](../SKILL.md),
[common preflight](agent-guard-common.md) and actual native client/runtime versions
govern every retained example. Installing resources grants no execution,
authentication, configuration or permission-policy changes.

## Identity and invocation contracts

- The npm package scope is lowercase `@jfrog/agent-guard`. Use an already
  qualified runtime or an actual reviewed exact version and selected registry
  through its installer owner. No floating `npx` call is a harmless discovery or
  version check. If a qualified task uses npm execution, `--yes` and
  `--registry "<REGISTRY_URL>"` precede
  `"@jfrog/agent-guard@<APPROVED_VERSION>"`; placeholders must first be resolved
  to reviewed values and the operation remains capable of downloading code.
- Keep three contracts distinct: the retained `jfrog-agent-guard-check.mjs`
  helper takes an optional positional actual CLI server ID; catalog CLI calls
  use supported `--server`/`--project`/`--mcp` flags; a governed stdio native
  entry routes non-secret project/package identity through supported `_JF_ARGS`.
  Review helper imports, credential access and platform effects before an
  authorized use; do not run it automatically during skill installation.
- `_JF_ARGS` is for the launched stdio entry, for example
  `project=<JFROG_PROJECT_KEY>&mcp=<PACKAGE_NAME>`, with actual values validated
  against the selected runtime's contract. Do not mix it into catalog listing,
  inspection or login calls, or move catalog-only flags into the config entry.
- `<SERVER_ID>` is an actual selected `jf config` server ID, never a package
  name or a hostname derived from a URL. A workspace directory is not a JFrog
  project key. Reuse existing authorized selection; resolve material ambiguity
  before a request. Do not invent `default`, enumerate other tenants on failure
  or retarget a native connection to the CLI default.
- Package/version and route come from the selected project's actual inspected
  catalog, not a guessed package name. A required governance policy retains its
  approved catalog/proxy path. Native stdio/remote shapes and secret references
  belong to the current client owner; do not impose a generic legacy JSON shape.
  A Gateway route needs actual supported inspection evidence and native transport
  support. Unsupported or denied routes are gaps, not permission to bypass policy.
- Keep stdout structured output separate from stderr diagnostics. Capture only
  bounded relevant output; redact tokens, headers and private values before
  reporting. Do not print raw native config, credential exports or complete
  environment/log dumps. Base64 is not redaction.

## Classify qualified Agent Guard failures

Do not fetch or upgrade Agent Guard merely because an error fingerprint differs
from this reference. Record the actual selected runtime version and a sanitized,
bounded diagnostic; use current selected-version help/docs when available.
A nonzero result stays a failure until a justified correction succeeds. Never
switch server, credentials, harness or transport to bypass a denial.

| Observation | Interpretation and bounded next step |
|---|---|
| npm `E404`, fetch `403`, DNS, timeout or connection refusal before Agent Guard starts | Package/runtime fetch failed. Check the already selected registry and argument order from existing evidence. A `403` does not by itself prove proxy, policy, missing package or sandbox cause. Correct a demonstrated local input error at most once within current authority; otherwise stop and report the gap. |
| `not found in curated list` | Selected catalog did not approve/find that package for this project. If authorized and available, one bounded list for the same selected project can distinguish a name mismatch. Do not choose another project/server or ungoverned install to obtain success. |
| Missing `--project`/`--mcp`, unknown server ID or multiple unresolved servers | Input/identity prerequisite is unmet. Resolve the actual known task/entry selection without creating credentials or changing defaults. Retry only the corrected same-target operation when authorized. |
| `Unauthorized`, other `401`/`403`, failed catalog request, missing `_JF_ARGS`, 5xx or an unknown error | Preserve the failed result. Missing input may be corrected from verified configuration; authentication, permission and service failures need their existing owners. No automatic OAuth, cache removal, fallback install or repeated request loop. |
| Login reports `expected 401, got 200` | On a version where this indicates an anonymous endpoint, treat it only as that authentication observation after verifying the exact runtime behavior. It does not establish available tools or a successful target operation. |

A demonstrated registry/argument typo may justify one corrected request. A denied
or unknown operation does not justify repeated list/inspect/login calls, an
outside-sandbox run or a different token scope. Use
[runtime boundaries](runtime-permissions.md).

## Connected but 0 tools

A configured/connected process is different from actual returned upstream tools.
Do not report success because Agent Guard is running, a descriptor cache exists
or the native catalog exposes only `enable_*_tools`. That tool can start
authentication and must not be invoked as a read-only diagnostic.

1. Resolve the actual client version, current session, effective entry and
   selected platform/project/package. Do not start another client/MCP instance
   merely to obtain different evidence.
2. Query the actual native status/catalog once where available. Preserve returned
   tools, errors and missing capabilities. Use only the relevant harness's
   supported verification route; cached files are not a live catalog.
3. If a prior authorized config change requires an authorized native
   reload/restart, use that owner's supported action. Do not reboot the host,
   enable unrelated entries or silently start OAuth. If operator interaction is
   required, state the precise pending native action.
4. When relevant and already authorized, inspect the same selected catalog/runtime
   identity. Allowlist membership can change; unknown, denied or missing results
   do not prove governance is disabled or permit an ungoverned replacement.
5. Stop after bounded observation. Initialization timing alone is not a diagnosis
   or a reason to promise a fixed wait. If a further check is requested, retain
   earlier failures and recheck the same selected session/target; do not silently
   rerun until tools appear.

If deeper diagnosis is requested, inspect bounded existing native/runtime logs
through their owner and redact secret-bearing fields. Temporarily changing a
selected entry's log level or restarting a process is a configuration/runtime
change: preserve preimages, current authority and a restoration plan. Do not
copy a floating `npx` command into a terminal, write a wrapper, clear a cache or
run a second blocking stdio process as an automatic debug step. For an explicitly
selected standalone diagnostic, qualify the exact executable/arguments/environment
and bound process/output lifetime before launch.

## Troubleshooting by boundary

| Boundary | Evidence and owner-preserving response |
|---|---|
| Gateway versus governed stdio | Preserve inspected package/version/route and current native transport support. If an existing entry disagrees, report the mismatch and prepare a reviewed same-owner change; do not automatically convert transport, replace URLs or fall back around governance. |
| Entry missing from native status | Resolve effective configuration layers, trust/enablement and actual session state. Absence is not proof that one toggle is the cause. Do not self-approve or write another duplicate entry. |
| Entry remains after a configuration edit | Inspect current native precedence/ownership. Remove only the exact selected entry/approval state when removal is authorized; preserve unrelated files and credentials. npm cache deletion is not a general MCP repair. |
| Missing selected CLI server or project | Report the unresolved identity. An ordinary diagnosis does not authorize `jf config add`, default changes, token exports or copying authentication into MCP. |
| OAuth or static-token failure | Existing native/runtime authentication owner governs recovery. A `401`/`403` does not establish token expiry or an unset variable without evidence. Check secret-reference presence without displaying values; login/rotation/restart only within actual authorized scope. |
| Registry/proxy/DNS failure | Distinguish the failing endpoint and selected runtime before proposing change. Preserve current registry and policy owners; never substitute an unchecked registry, token or install route. |
| Cursor sandbox/policy suspicion | Use [Cursor ownership](harness-cursor.md). A JFrog-host `403` does not prove a sandbox allowlist block. Do not add broad JFrog/S3 wildcard access, edit sandbox policy or request blanket escalation automatically. |

Report configuration, process connectivity, authentication, actual tool metadata
and requested operation results separately. An unavailable component remains an
honest capability gap; it is not a reason to install plugins, global governance,
Agent Guard or credentials as an unrequested repair.
