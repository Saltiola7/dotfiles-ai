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
| Schema | not_applicable: no persistent application/configuration schema is added |
| Dependency/deployment | required: selection/deployment handoff table in Spec |
| Quantitative | not_applicable: no comparative reliability or token-cost claim is required for installation |

**Text Equivalent (ownership):** Distribution owns reviewed portable source and
exact-target deployment. Native discovery and the DBSCTR platform table select
relevant guidance. Existing installer, client, project and platform owners retain
CLI versions, configuration, authentication and mutations. JFrog governance is
selected explicitly. Resources remain inert until task-specific review and use.
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

The optional CLI owner is default-off and missing-only, independently of skill
installation. It selects official JFrog CLI 2.129.0 assets; an existing compatible
CLI remains owned by its current installer. Minimum capability is 2.106.0 for the
whole collection. Planning alone does not require a CLI or configured platform.
No credentials, platform identity or global default selection are provided.
