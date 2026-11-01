# Self-hosted Prefect guidance and MCP

## Domain and ownership

This optional distribution capability supplies Prefect guidance and a local stdio
MCP client adapter for an existing self-hosted Prefect API. It follows the earlier
specialist expansion; that wave's Prefect exclusion remains historical. Flow
authoring can use project SDK/CLI tools without MCP. MCP adds structured inspection
of existing state and does not provision or operate the Prefect API service.

| Boundary | Owner and invariant |
|---|---|
| Flow code and orchestration semantics | Project-selected Prefect/Python versions, dependencies, tests and lifecycle |
| Operational guidance | A reviewed official `prefect-operations` bundle; actual capabilities and target identity govern recipes |
| Managed MCP runtime | Distribution-owned immutable upstream pin and frozen dependency lock in an isolated generation |
| Target and authentication | Private machine selection and existing Prefect profiles; values remain outside public source and command arguments |
| MCP process | Native client starts local stdio on demand; launcher binds the selected target before importing the server |
| Codex registration | Native user configuration writer and existing explicit projector reconciliation; managed source remains hooks-only |
| OpenCode registration | Existing managed native MCP template/merger, preserving unrelated local entries and native Code Mode |
| Existing Prefect API | Separately owned backend; no implicit start, upgrade, credential change or ephemeral replacement |
| Delivery | Current primary, existing QA, native protected PR workflow and distribution owner |

Public defaults are disabled. Installation, MCP initialization/catalog, selected
target identity, backend health and workflow readiness are distinct observations.
An unreachable existing API is reported honestly without inventing a live query
pass or starting another backend. It does not make an installed adapter a service
deployment or select a cloud account.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: ownership table above |
| Interaction | required: source/install/registration/inspection handoff table in Spec |
| State | required: generation and backend-observation transition table in Contract |
| Data/trust | required: target/credential transfer table in Contract |
| Schema | required: optional configuration interface table in Spec |
| Dependency/deployment | required: handoff table in Spec |
| Quantitative | not_applicable: no comparative cost, latency or reliability claim |

**Text Equivalent (ownership):** Project policy owns flow behavior and validation.
The distribution owns a pinned isolated MCP runtime, while private configuration
selects the existing API and credentials. Native clients own registration and
stdio lifetime. The API's service owner retains backend operations. The primary
and QA own reviewed delivery. Canonical source: this feature and the ownership
table; owner: distribution maintainer; update when a represented boundary changes.

## Behavior

| Given / when | Observable outcome |
|---|---|
| Public defaults are applied without opt-in | No runtime download, MCP startup, backend request or client registration |
| Explicit installation has an existing compatible interpreter | Install the frozen runtime in a new isolated generation and mark it complete only after offline qualification |
| A generation is incomplete or disagrees with its lock | Refuse reuse and retain it for deliberate recovery; no destructive replacement |
| A client invokes the adapter without an installed runtime or selected API | Return a bounded non-secret unavailable result before importing Prefect or opening a transport |
| A private profile is selected | Resolve only that profile, preserve the global active profile and reject an unresolved/ambiguous target |
| A repository contains `.env` or Prefect configuration | Use a controlled working directory and explicit child target; repository settings cannot silently redirect the adapter |
| Transport initializes against a selected self-hosted target | Expose exactly twelve inspection tools; omit cloud workspace selection and external documentation proxy |
| Experimental publication is requested directly or through altered ambient flags | Refuse it without contacting the backend or performing a write |
| A backend is unreachable, unauthorized or incompatible | Report the actual failure; do not start an ephemeral API, switch profiles/accounts or claim workflow readiness |
| A native client entry is added | Preserve unrelated settings, hooks, plugins and servers; reconcile only the selected native configuration owner |
| A different same-name MCP entry already exists | Retain it and report the collision rather than overwrite its transport or credentials |
| A real Prefect operation is diagnosed | Load operational guidance, verify identity and use bounded relevant evidence; API failure and hypothesis remain distinct |
| Only flow code needs authoring or review | Keep project-selected SDK/CLI and tests; MCP installation is not a requirement for flow code |
| Installation and registration repeat unchanged | Reuse the qualified generation and preserve client configuration without extra dependencies or duplicate entries |

Discovery, native client registration, returned tool metadata, backend connectivity
and demonstrated task behavior remain separate claims. Local installation can be
qualified while an existing backend is unavailable; that availability gap remains
explicit and is never reported as a successful live query.

## Spec

The MCP implementation is the official `PrefectHQ/prefect-mcp-server` source at
`48efd289bdb2b94a78e35b1331fbefc4fa3f6411`, not an unqualified floating PyPI
release. A dedicated managed dependency project and frozen `uv.lock` select the
runtime closure, compatible FastMCP 3 and MCP SDK 1, and constrained isolated build
dependencies. Use an existing Python 3.13 interpreter; installation may fetch the
reviewed packages, but never downloads Python or modifies a project environment.
The installer requires an existing uv 0.13.6 or newer supporting hash-qualified
isolated build constraints; it never upgrades that separately owned executable.

| Interface | Shape and owner |
|---|---|
| `.chezmoidata.toml` optional `dotfiles_ai.prefect_mcp` | `enabled=false`; private target/profile and credential-selector fields default empty |
| `~/.config/dotfiles-ai/prefect-mcp.toml` | Schema 1 private rendered settings; `enabled`, `profiles_path`, `profile`, `api_url`, `api_auth_string_env`, `api_key_env` |
| Target selection | Either explicit `api_url`, or explicit `profiles_path` plus `profile`; reject conflicting modes, missing target, unsupported schemes and credentials embedded in the URL |
| Authentication selection | Selected profile credentials or one named caller environment variable; no secret values in public data, client arguments or status output; no inactive-profile fallback |
| `~/.config/dotfiles-ai/runtime/prefect-mcp/` | Managed `pyproject.toml`, `uv.lock` and `server.py`; readable source plus isolated lock-addressed runtime generations |
| `~/.local/bin/prefect-mcp` | Explicit `install`, offline `check-runtime`, non-secret `status`, and on-demand `serve`; no package resolution during serving |
| `run_onchange_after_install-prefect-mcp.sh.tmpl` | Default-off package installer owner invoking the explicit install path when opted in |
| Native client entry | `prefect_local`, using only the installed absolute launcher path and `serve`; no literal endpoint/authentication in client arguments |
| Codex | Native `mcp add/get/list` for each process- and native-layer-bound host; explicit projector reconciliation applies to the managed CLI host, while a distinct Desktop home retains its own native owner; hooks-only owned source remains unchanged |
| OpenCode | Native V2 `mcp.servers.prefect_local` through existing template/merger; keep native Code Mode and refuse an incompatible same-name local declaration |
| Skill | `dot_agents/skills/prefect-operations/`: complete official workflow root, renamed entrypoint, exact MIT notice, attribution and reversible adaptations |
| Routing | Existing platform table selects Prefect state/operation diagnosis; Data guidance continues to treat orchestration tools as project-selected |

The stock executable imports a default server with additional optional surfaces.
The managed bootstrap sets child-only environment controls before importing that
package, then uses its pinned `build_prefect_mcp_server` factory with cloud tools,
cloud OAuth tools and the docs proxy disabled. FastMCP's public visibility API
restricts the returned server to exactly `orientation`, `get_identity`,
`get_dashboard`, `get_deployments`, `get_flows`, `get_flow_runs`,
`get_flow_run_logs`, `get_task_runs`, `get_work_pools`, `read_events`,
`get_automations` and `get_object_schema`. Experimental execution plans are also
explicitly disabled. No HTTP MCP listener or persistent daemon is added.

| Handoff | Required evidence before the next step |
|---|---|
| Reviewed source to runtime files | Immutable pin, complete skill/resources/license, frozen runtime/build inputs and offline source checks |
| Runtime files to isolated generation | Explicit installation, existing interpreter, successful frozen sync and offline qualification; incomplete work retained |
| Generation to native clients | Bound native configuration origin, reviewed exact entry, preserved preimages, unrelated settings/hooks/plugins unchanged |
| Native client to stdio adapter | Bounded initialization and exact inspection catalog; no install, project `.env`, docs-proxy connection or ephemeral API |
| Adapter to existing API | Explicit selected target and process-only authentication; identity/health/results reported separately |
| Source to protected main | Existing gate, publication, current-base CI and ordinary merge authorities; no branch/worktree cleanup |

**Text Equivalent (interfaces and handoff):** Disabled public defaults cause no
installation or registration. Explicit opt-in projects reviewed runtime files,
then installs a frozen isolated generation. Native clients register the launcher
without taking ownership of unrelated configuration. The client starts stdio;
only twelve inspection tools can reach the explicitly selected existing API.
Backend observations do not replace source, protocol or deployment evidence.
Canonical source: the tables and interfaces in this section; owner: distribution
maintainer; update with configuration, runtime, tool or delivery changes.

## Contract

Installation and serving are separate commands. Serving never resolves packages,
downloads an interpreter, creates a generation or starts a Prefect backend. All
subprocess arguments are structured data. Installation uses an existing Python
3.13, frozen dependency/build inputs and private, owner-controlled directories.
The runtime digest covers the project, lock and bootstrap. A completion marker is
written only after offline qualification and an unchanged input digest. Partial
or mismatched generations are retained and refused; concurrent installation must
not reuse partial state. Paths, files and markers reject unsafe ownership, links
and write permissions where they control executable code or credentials.

| State / event | Transition and observation |
|---|---|
| Disabled / ordinary apply | Remain disabled; no installer or native registration effects |
| Missing generation / explicit install | Create a new private generation, frozen-sync and qualify |
| Incomplete generation / retry | Refuse and retain for explicit operator recovery |
| Qualified generation / unchanged install or serve | Reuse only after marker, input and interpreter qualification |
| Changed source/lock/bootstrap | Select a new digest; retain previous generation for rollback |
| Qualified generation / missing or invalid selection | Fail before Prefect import or MCP startup |
| Selected target / stdio initialization | Publish only the twelve inspection tools; no backend-health claim |
| Selected target / API failure | Return failure; preserve selection and backend state |
| Selected target / successful identity and bounded query | Report that observation, without claiming general workflow readiness |

**Text Equivalent (state):** Only explicit installation creates a generation.
Incomplete work remains unavailable. Qualification permits on-demand stdio after
target validation. API success or failure is a separate observation and never
changes target selection. Canonical source: this table; owner: distribution
maintainer; update when installation or observation transitions change.

| Data crossing boundary | Validation and permitted sink |
|---|---|
| Private settings to launcher | Strict schema/types, explicit enabled flag, exactly one target mode; authentication is absent, selected-profile credentials, or one named caller variable, never multiple credentials |
| Selected profiles file to launcher | Owner-controlled regular file; named profile only, no global active-profile mutation or inactive-profile fallback |
| API URL to child environment | HTTP(S), hostname, no embedded credentials or query/fragment; private selection, never public client arguments |
| Selected credentials to child | Process environment only; do not serialize settings, print raw errors, include credentials in status, or inherit unrelated Prefect/Logfire settings |
| Project environment to child | Neutral private CWD, explicit Prefect target and ephemeral-server disablement before any Prefect import; prevent project dotenv redirection |
| Bootstrap to upstream factory | Disable cloud/docs/OAuth proxy, experimental execution plans and telemetry; enforce fixed server-side allowlist, including direct invocation |
| MCP server to client | Read-only catalog and bounded tool errors; preserve process exit status and stderr/stdout protocol separation |
| Native configuration writer to existing config | Preimage, exact owner/entry checks and explicit reconciliation; refuse incompatible same-name server |

**Text Equivalent (data and trust):** The launcher resolves private selection,
passes only the selected target and credentials into an isolated child, and
never writes those credentials into source or registration. The bootstrap
restricts upstream capabilities before stdio. Native configuration owners retain
all unrelated client state. Canonical source: this table; owner: distribution
maintainer; update with trust boundaries or permitted sinks.

Process-only controls disable Prefect ephemeral mode, inherited external tracing
and the experimental write surface. The selected pinned versions must validate
these controls in the real runtime; static strings alone are insufficient. The
catalog must initialize offline without the docs proxy or telemetry network.
Direct calls to experimental publication must fail before backend access.

Validation covers disabled rendering, missing/ambiguous target rejection, secret
canaries in errors/status, process environment/CWD isolation, immutable-generation
failure/idempotence, exact read-only catalog/direct-call denial and native config
preservation. Use existing pytest/typing/shell authorities, the original skill
validator, source provenance verification, targeted chezmoi preview/apply and
second-apply empty diff. Real installation and stdio protocol evidence are
distinct from mocked control-flow tests. Backend unavailability is recorded,
without a fabricated live identity/query pass. Existing full CI and protected
ordinary merge gates remain mandatory.

Rollback disables private opt-in and removes only the exact verified native
entry through its native owner, then reconciles the existing Codex projector.
Retain runtime generations, preimages, task branches and worktrees. Requalify on
upstream, lock, Python, bootstrap, native client schema or target-policy changes.
No automatic package upgrade, backend start, account switch or global Prefect
profile change is permitted.

## Qualification and maintenance

The source gate covers 241 affected tests, including instruction/publication
contracts and existing Codex preservation behavior; one unrelated native opt-in
check is skipped. Synthetic Git fixtures disable inherited commit signing and
use their expected ordinary umask without changing repository configuration.
The original skill validator and exact offline provenance reconstruction pass.
The selected macOS ARM64 and Linux AMD64/ARM64 dependency closures report zero
OSV advisories for 149 packages; this is dependency evidence, not a runtime or
full security audit of those platforms.

Deployment separately records exact source/installed bytes and modes, retained
preimages, unrelated native configuration preservation and empty second-apply
diffs. `prefect-mcp check-runtime` must observe actual parsed SDK controls as well
as offline catalog/direct-call behavior. Native stdio initialization and catalog
checks use only the selected adapter, with no model call. Report backend identity
failure separately when the existing service is unavailable. Native CI and the
ordinary protected merge bind the final head and current base; source checks do
not substitute for those delivery gates.

Distribution metadata detects added, removed, changed-version or changed-origin
packages before serving. It does not sandbox code installed by the same account
or detect arbitrary package-byte changes preserving that metadata; the existing
host execution and dependency trust boundary remains. Runtime dependency changes,
bootstrap changes and native client schema changes require explicit qualification.
