---
name: jfrog-ai-catalog
description: Discover or manage skills and plugins in an explicitly selected JFrog AI Catalog, including versions, repositories, policy and publication. Use for actual Artifactory catalog work; preserve managed skill sources and scan gates.
metadata:
  role: workflow
---

# JFrog AI Catalog

Use for a selected JFrog skills/plugins catalog. Generic skill discovery does not
select this workflow. MCP governance uses `jfrog-mcp-management`; ordinary
Artifactory/Xray uses the base `jfrog` skill.

Cover the base skill's target, bounded execution and secret rules once. Keep one
selected server/project/repository and requested version; do not invent a target
or switch servers after failure. Catalog availability, installability, signature
verification, scan status and installed/discovered state are separate facts.

Read only the matching reference:

| Operation | Reference |
|---|---|
| Browse skills or versions | [Discover skills](references/discovering-skills.md) |
| Browse plugins or versions | [Discover plugins](references/discovering-plugins.md) |
| Applicable catalog policy | [List policies](references/listing-policies.md) |
| Install/update skill | [Install skills](references/installing-skills.md) |
| Install/update plugin | [Install plugins](references/installing-plugins.md) |
| Installed skill inventory/removal | [Manage skills](references/managing-installed-skills.md) |
| Installed plugin inventory/removal | [Manage plugins](references/managing-installed-plugins.md) |
| Publish skill | [Publish skills](references/publishing-skills.md) |
| Publish plugin | [Publish plugins](references/publishing-plugins.md) |

The [complete workflow](references/upstream-workflow.md) covers identity and
manifest differences. Agent Guard/npm is a separate reviewed runtime: catalog
listing must not silently fetch floating code. Helpers remain inert resources.

Preserve existing source/install owners. For dotfiles-ai managed skills, author
and review source before exact-target deployment; do not overwrite shared skills
with direct catalog installation/removal. Publication requires the selected exact
artifact/destination and applicable lifecycle authority. Existing task consent
persists; do not add repetitive prompts when authority is already concrete.

Preserve project-required scanning, signing, provenance and release gates. Do not
set skip-scan or missing-evidence override flags merely to make a command pass.
An uploaded artifact is not a passed scan or approved release. Report pending,
failed and absent security evidence honestly, including partial uploads and
recovery needs. Never print credentials, signing keys or raw platform config.
