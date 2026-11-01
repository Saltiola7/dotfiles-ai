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
