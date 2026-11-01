# JFrog specialist guidance

## Domain and ownership

The distribution supplies the complete seven-root official JFrog skill collection
at `jfrog/jfrog-skills` commit
`e555af53c3f5ead14fcafb009380e76d3ddf17d1` (Apache-2.0). Portable guidance,
client discovery, CLI availability, MCP connection, selected platform identity and
successful platform operations are separate capabilities.

| Boundary | Owner and invariant |
|---|---|
| Skill source and resources | Distribution source, immutable upstream provenance and reversible local patches |
| Skill selection | Native discovery descriptions and the existing DBSCTR platform table; load only relevant references |
| Package, build and security operations | Project-selected JFrog target, permissions and validation; no invented server or fallback account |
| CLI prerequisite | Existing native installer owner; preserve compatible selected installations and report missing/incompatible versions |
| MCP registration and authentication | Existing native client/configuration owner and explicitly selected platform; no automatic activation |
| JFrog Agent Guard/catalog | Only explicitly requested JFrog-governed tasks; no takeover of unrelated MCP or skill management |
| Project enumeration | Selected current identity and live enumeration; no persistent credential-derived cache fingerprint |
| Upstream helper execution | Reviewed task-specific capability; installing resources does not execute scripts or grant mutations |
| Deployment and delivery | Current primary, shared portable skill location, exact-target chezmoi apply and protected PR workflow |

The seven roots are `jfrog`, `jfrog-setup-package-managers`,
`jfrog-package-curation`, `jfrog-reference-architecture`, `jfrog-ai-catalog`,
`jfrog-init` and `jfrog-mcp-management`. The official plugin, SessionStart hooks,
Agent Guard npm package and a remote JFrog MCP server are separate installations.
No JFrog target or credential is a public default. Installing this collection does
not provision a platform, enable governance or start a client/server connection.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: ownership table above |
| Interaction | required: selection/deployment handoff table in Spec |
| State | required: readiness transition table in Contract |
| Data/trust | required: trust and failure table in Contract |
| Schema | required: optional CLI interface table in Spec |
| Dependency/deployment | required: selection/deployment handoff table in Spec |
| Quantitative | not_applicable: no comparative reliability or token-cost claim is required for installation |

**Text Equivalent (ownership):** Distribution owns reviewed portable source and
exact-target deployment. Native discovery and the DBSCTR platform table select
relevant guidance. Existing installer, client, project and platform owners retain
CLI versions, configuration, authentication and mutations. JFrog governance is
selected explicitly. Project enumeration uses current identity without persistent credential-derived
fingerprints. Resources remain inert until task-specific review and use.
Canonical source: this feature and ownership table; owner: distribution
maintainer; update when any represented boundary or imported root changes.

## Behavior

| ID | Given / when | Observable outcome |
|---|---|---|
| B01 | Ordinary skill deployment | Install all seven complete bundles, license notices and dependencies without executing helpers, contacting a platform or installing a plugin |
| B02 | Actual JFrog artifact/build/security work | Select the base skill and relevant domain references; preserve configured project/QA authority |
| B03 | Explicit Artifactory package binding, Curation or topology work | Select only matching setup, curation or reference-architecture guidance |
| B04 | Unrelated GraphQL, MCP, skill discovery or package installation | Do not select JFrog guidance merely from generic terms |
| B05 | Explicit JFrog AI Catalog or Agent Guard workflow | Select that specialist; retain existing managed source, native config and target ownership |
| B06 | Explicit JFrog readiness/init request | Keep upstream manual invocation policy; report actual capability, never auto-login or overwrite client configuration |
| B07 | CLI-only check/download or MCP-only Curation troubleshooting | Use available appropriate capability; report missing MCP troubleshooting tools without claiming CLI equivalence |
| B08 | Missing or incompatible CLI/target/authentication | Report prerequisite gaps; never install tools from a copied recipe or switch target to obtain success |
| B09 | Public CLI installation defaults | No executable download, authentication, config write or MCP registration |
| B10 | Explicit optional CLI install with no existing owner | Verify pinned supported-platform binary before execution, install atomically and verify version using an isolated private home |
| B11 | Existing CLI, incompatible CLI, destination collision or failed download | Preserve existing bytes; retain supported owners, report incompatibility/collision/integrity failures without upgrading or fallback |
| B12 | Repeated unchanged deployment | Preserve exact file sets/modes, unrelated live edits, native configuration and credentials; repeat apply/diff remains empty |
| B13 | Project discovery invokes cache helpers or encounters a legacy cache | Cache always misses; helpers do not read credential properties or read/write cache files; selected discovery uses live enumeration |

The optional CLI owner is default-off and missing-only, independently of skill
installation. It selects official JFrog CLI 2.129.0 assets; an existing compatible
CLI remains owned by its current installer. Minimum capability is 2.106.0 for the
whole collection. Planning alone does not require a CLI or configured platform.
No credentials, platform identity or global default selection are provided.

## Spec

All seven source directories live at `dot_agents/skills/<upstream-name>` and
project to the existing shared `~/.agents/skills/<name>` location. Each root has a
compact `SKILL.md`, lazy complete upstream workflow material, unchanged supporting
resources except reviewed reversible adaptations, `LICENSE.upstream` and
`UPSTREAM.md`. Root descriptions use JFrog-specific task evidence. The init root
preserves upstream manual invocation through native invocation metadata.

`dbsctr/references/specialist-sources/sources.lock.json` appends seven records with
immutable source roots/commit, original SHA-256/Git blobs/modes, packaged hashes,
installed modes and reversible patches. Prior records retain identical values.
An optional `source_only_files` inventory list records reviewed VCS-only empty
placeholders that native chezmoi intentionally omits. The JFrog base bundle
retains original `assets/.gitkeep` in source/provenance; it is not a runtime
resource. Installed file hashes/modes exclude exactly that declared empty
placeholder. No workflow, helper, license or referenced resource is excluded.
Relocating entrypoint material must preserve relative links. Helpers are stored
as readable resources and invoked with their selected interpreter after review;
source execution bits and declared installed modes are separate facts.

| Interface | Shape and owner |
|---|---|
| Native discovery | Seven scoped descriptions; `jfrog-init` retains explicit invocation policy |
| DBSCTR platform table | One row per actual JFrog concern; no duplicate router in language modules |
| QA | Configured Xray remains existing vulnerability authority; link relevant base guidance without making JFrog mandatory |
| `.chezmoidata.toml` | Optional `dotfiles_ai.jfrog_cli.enabled=false`; no target or authentication fields |
| `run_onchange_after_install-jfrog-cli.sh.tmpl` | Independent default-off, missing-only native binary installer; supported Darwin/Linux ARM64/AMD64 assets for 2.129.0 with reviewed SHA-256 |
| CLI destination | Existing local-bin convention; refuse collisions/symlinks and preserve any existing selected CLI owner/version |
| CLI check | Existing CLI >=2.106.0 qualifies; older CLI is preserved and reported unmet; isolated private home and reporting/version checks disabled |
| Project enumeration cache API | `jfrog-init/scripts/lib/project-cache.mjs` keeps `readCachedProjectList(serverId, creds)` and `writeCachedProjectList(serverId, creds, body)` signatures; read returns `null`, write is a no-op, and neither accesses arguments or persistent state |
| Native MCP/client config | No new entries, hook/plugin installation or authentication changes |

| Selection/deployment handoff | Required evidence before proceeding |
|---|---|
| Native task to specialist | JFrog-specific description plus current task evidence; unrelated MCP/GraphQL/skill requests do not trigger governance |
| Specialist to reference/helper | Relevant lazy reference only; review helper side effects, actual selected tools/target and native config version |
| Reviewed source to rendered skills | Full provenance, license, closed resource links/imports and exact file/mode inventory |
| CLI opt-in to executable | Supported platform, no owner/collision, exact asset checksum, atomic staging and isolated version qualification |
| Rendered skill files to live shared directory | Prior-live reconciliation, exact targets, scripts excluded, reviewed preview, complete verification and repeat diff |
| Live guidance to platform operation | Explicit selected identity/permissions and task-specific capability; installation does not establish live readiness |

**Text Equivalent (selection/deployment):** Native task evidence selects one
relevant specialist, which loads only needed references. Source validation binds
complete reviewed bundles to exact rendered targets. Optional CLI installation
requires opt-in, target absence, checksum and isolated qualification before atomic
promotion. Shared deployment reconciles prior state and excludes scripts. Platform
operations separately need actual target/tool authority. Canonical source: this
feature, inventory, router and installer; owner: distribution maintainer; update
when selection, file layout, configuration, prerequisites or delivery changes.

Implementation order is dependency-aware: first failing bundle/routing/installer
regressions; then disjoint complete bundle adaptations and optional CLI owner;
then primary-owned inventory/patch reconstruction, routing and documentation;
finally integrated validation, exact deployment, native discovery and delivery.
The primary alone owns lifecycle, shared inventory, integration and native writes.

Project discovery retains its current cache-miss/live-enumeration branch and
selected identity. Compatibility exports preserve caller shape while removing
persistent credential-derived fingerprints. Source attribution, reversible helper
patches, installed hashes and the project-matching guidance change together.

## Contract

| Readiness state / transition | Guard and observation |
|---|---|
| Source reviewed to filesystem installed | Complete pinned bundles, closed dependencies and exact modes; no helper execution |
| Installed to natively discovered | Actual client skill catalog returns the seven shared roots; filesystem presence alone is insufficient |
| CLI missing to qualified executable | Explicit opt-in, supported platform, no existing owner/destination, pinned hash and isolated expected version |
| CLI pre-existing | Preserve its owner and bytes; qualify minimum version or report incompatibility, never auto-upgrade |
| CLI install fails | Nonzero status, bounded diagnostic, temporary cleanup and unchanged existing destination; no login or fallback download |
| Guidance to live platform ready | Separately selected server/authentication and successful task-specific operation; no transition is implied by this installation |
| MCP absent | Base CLI/API and planning remain usable; MCP-only troubleshooting remains unavailable |

| Trust/failure boundary | Required control |
|---|---|
| Public upstream to portable source | Immutable pin, exact licenses/original blobs, reversible changes, reviewed executable helpers and current vulnerability intake |
| Large upstream instructions to active context | Compact native entrypoints; upstream workflows load lazily under overriding local ownership rules |
| MCP governance | Restrict universal upstream instructions to explicitly selected JFrog Agent Guard/catalog tasks; unrelated native MCP owners remain authoritative |
| Legacy helper to client configuration | Do not execute install/detect/auth writers as harmless checks; old OpenCode V1 assumptions require current native V2 owner qualification |
| Runtime package resolution | No unpinned npm/Agent Guard installation during skill deployment; separate explicit task and reviewed version/provenance needed |
| CLI download to execution | Validate official SHA-256 before any execution; no shell-evaluated metadata, ambient plugin/config loading, credential access or global PATH mutation |
| Server/secret handling | No invented target, direct secret/config dump, cross-server fallback or preparatory mutation to make a read succeed |
| Shared deployment | Exact-target preview/apply with scripts excluded; preserve foreign live overlays and all client/authentication bytes |

Compatibility includes selected project runtimes, native client schemas and
existing installer owners. The source CLI hook uses Bash compatible with system
macOS Bash and existing Linux support; argument boundaries, subprocess status,
cleanup and destination collisions are meaningful regression cases. Supported
asset mappings and all four hashes are source-controlled; unsupported platforms
fail only when the optional installer is enabled.

The affected authorities are creator validation for all roots, pytest specialist
provenance/reconstruction/resource/delivery regressions, focused CLI failure and
idempotency tests, Bash syntax, static Node helper syntax, reviewed trust-boundary
content, native skill catalogs and exact deployment/repeated-diff evidence.
Source and installed inventories are verified separately when native projection
omits a declared empty VCS placeholder; tests require its original empty hash
and reject other exclusions. Offline tests do not establish platform connectivity
or security scan coverage.
Native automatic selection may be sampled separately; a catalog or lexical test
must not be called a successful automatic-trigger experiment.

Rollback restores reviewed source/inventory and private prior installed bytes for
only this capability. Preserve unrelated edits, native credentials/configuration
and existing CLI owners. A newly installed distribution-owned CLI may be retired
only after owner/version identity and dependent callers are reviewed; disabling
opt-in alone does not uninstall it. Do not delete branches, worktrees or caches.

Maintenance rechecks the entire upstream tree, licenses, helper side effects,
client-version assumptions, source patches and CLI asset integrity on a reviewed
update. JFrog-specific vulnerability intelligence remains conditional on actual
configured capabilities. No accepted risks, gate exceptions, external platform
changes or live MCP connection are part of this feature.


### Credential-cache repair contract

The compatibility cache functions do not inspect credential properties, derive a
verifier, touch a filesystem path, start a process or contact a network. Reads
always return `null`; writes return normally without retaining inputs. Legacy
cache files are ignored and remain untouched; no wildcard cleanup or credential
migration is introduced. The existing discovery caller therefore enumerates for
the selected current identity and keeps its existing live per-project access
check and error behavior. Installation still executes no helper.

Regression evidence uses only synthetic credentials and an isolated temporary
directory: a prior cache remains ignored and byte-identical, a write creates no
state, reads cannot return stale authorization metadata, and credential getters
are never accessed. The original implementation must fail these cases before the
repair. Reversible provenance and static helper/resource qualification remain
required. Native CodeQL must succeed on the repaired head; no suppression,
security-rule weakening, alert dismissal or gate exception is permitted.
