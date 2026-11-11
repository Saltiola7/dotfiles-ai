# Complete JFrog AI Catalog workflow

Use only the explicitly selected JFrog catalog/platform/project and existing
native source/install owner. Cover the base JFrog guards once; retain actual
errors, requested versions and project-required scan/provenance gates. Agent
Guard is a separate reviewed runtime: examples use a qualified owner-selected
executable/pin, never floating npx installation. Listing can execute downloaded
code; no tool installation or authentication follows from loading this file.

## Identity and operation

Distinguish local workspace, JFrog project key, platform server ID, repository,
skill/plugin slug and version. Reuse explicit verified task selection; resolve
only missing material identity. Do not choose a repository from unrelated/server-
wide discovery, auto-provision one or switch platforms after failure. A typed
project key is a selection, not proof of access. Never dump raw CLI configuration,
credentials, signing keys or environment values.

Skill bundles require root `SKILL.md`; plugin bundles require `plugin.json`.
Native catalog listing, allow-list policy, signatures/attestations, malware scan,
local installed files, native discovery and actual task behavior are separate
observations. Use only the operation-specific reference:

| Intent | Method |
|---|---|
| Discover skills/versions | [Discover skills](discovering-skills.md) |
| Discover plugins/versions | [Discover plugins](discovering-plugins.md) |
| Catalog policies | [List policies](listing-policies.md) |
| Install/update skill or plugin | [Skills](installing-skills.md), [plugins](installing-plugins.md) |
| Local inventory/removal | [Skills](managing-installed-skills.md), [plugins](managing-installed-plugins.md) |
| Publish skill or plugin | [Skills](publishing-skills.md), [plugins](publishing-plugins.md) |

Preserve the target's source/installer owner. For dotfiles-ai managed skills,
author/review source and deploy exact reviewed bundle files; direct catalog CLI
installation or recursive removal must not overwrite another owner's shared tree.
Existing explicit task authorization persists, so do not add a blanket repeated
confirmation ceremony. Publication/creation still requires concrete artifact,
destination and applicable lifecycle authority; resolve real ambiguity first.

Never auto-provision a catalog repo, widen to another project/server or bypass
required scans, attestations, signatures or release controls. Upload success does
not mean scanning passed. Report partial writes and unmet evidence honestly;
recovery retains the actual owner and separately authorized destructive scope.
