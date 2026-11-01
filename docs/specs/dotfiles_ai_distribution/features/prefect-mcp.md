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
