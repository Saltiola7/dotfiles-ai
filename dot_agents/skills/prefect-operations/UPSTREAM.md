# Upstream and adaptation

This complete selected bundle derives from
[PrefectHQ/prefect-mcp-server](https://github.com/PrefectHQ/prefect-mcp-server/tree/48efd289bdb2b94a78e35b1331fbefc4fa3f6411/plugins/prefect/skills/workflows)
at immutable commit `48efd289bdb2b94a78e35b1331fbefc4fa3f6411`,
path `plugins/prefect/skills/workflows`, tree
`7949196878e18c9b8a9f7cd79094b067c6b989a7`. Its single original entrypoint is
retained as an adapted `SKILL.md`, renamed from generic `workflows` to
`prefect-operations` for shared discovery. The root MIT notice is retained byte
for byte as [LICENSE.upstream](LICENSE.upstream).

No other upstream skill, plugin manifest, hosted connection or SDK is included
in this guidance bundle. The separate managed MCP runtime has its own pinned
source, frozen dependency/build inputs and qualification; importing this skill
does not install or launch it.

## Original identities

Both original files have Git mode `100644`; all packaged files remain 0644.

| Packaged path | Original Git blob | Original SHA-256 |
|---|---|---|
| SKILL.md | 6fcd6026751220eedc2c72565fcc992f7ddbdeaf | 2baec42119d41cf295a7557ac328dbd53ce555d23199f618bfc9400f72c44951 |
| LICENSE.upstream | 42074d733ac127c19df5b6e0c4ea25a9a02ad3c2 | a94bb959c019300d59f97d948705d17b1cc0cd137e50364a2b93ed06e4453a4a |

The shared DBSCTR specialist source inventory records packaged identities and
reversible patches, including the renamed entrypoint and the adaptations below.
This attribution does not claim that a backend connection or workflow ran.

## Reviewed adaptations

- Retain the upstream operational workflow while making target/capability
  selection explicit. Verify identity and structured API success before other
  live queries. Bound result/log scope and preserve complete identifiers.
- Separate self-hosted inspection from the original hosted Cloud OAuth recipe.
  The local adapter omits Cloud discovery, external docs proxy and experimental
  publication. Keep optional Cloud guidance conditional on an independently
  selected, actually available connection; never require Cloud sign-in locally.
- Preserve project-selected SDK/CLI authoring, validation and lifecycle ownership.
  Static flow-code work does not require MCP, a live connection or a tooling
  migration. Documentation follows selected versions; the local tool catalog
  does not imply documentation search is present.
- Keep CLI mutations under existing task authorization and independently verified
  CLI target/authentication. Replace snapshot command assumptions with selected
  help and structured results; no global profile switch, backend provisioning,
  ephemeral fallback or unsupported success claim follows from loading guidance.

## Primary references

- [Official MCP setup and transport choices](https://github.com/PrefectHQ/prefect-mcp-server/blob/48efd289bdb2b94a78e35b1331fbefc4fa3f6411/README.md)
- [Pinned factory and tool boundary](https://github.com/PrefectHQ/prefect-mcp-server/blob/48efd289bdb2b94a78e35b1331fbefc4fa3f6411/src/prefect_mcp_server/server.py)
- [Pinned credential selection](https://github.com/PrefectHQ/prefect-mcp-server/blob/48efd289bdb2b94a78e35b1331fbefc4fa3f6411/src/prefect_mcp_server/_prefect_client/client.py)
- [Pinned identity result semantics](https://github.com/PrefectHQ/prefect-mcp-server/blob/48efd289bdb2b94a78e35b1331fbefc4fa3f6411/src/prefect_mcp_server/_prefect_client/identity.py)

Resolve consumer-specific behavior against its selected Prefect release rather
than treating the runtime adapter's dependencies as project upgrade policy.
