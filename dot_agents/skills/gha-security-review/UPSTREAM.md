# Upstream provenance

Source: https://github.com/getsentry/skills/tree/d12f250460ffd961f549dbebf7eeb0cf4afd4c2e/skills/gha-security-review

Commit: `d12f250460ffd961f549dbebf7eeb0cf4afd4c2e`. Reviewed 2026-10-28.

Attribution: Functional Software, Inc. dba Sentry. License: Apache-2.0; see [LICENSE.upstream](LICENSE.upstream).
The upstream material retains this license, separately from the repository license.
No vendor endorsement is implied.

## Local packaging

Complete ten-file Markdown bundle. Adapted entrypoint to retain the external-contributor threat model while removing categorical safe-pattern and complete-clearance claims. No scripts, runtime tools or hooks.

Local modifications are marked in each changed file and recorded as exact patches
in the security-toolkit lock record. No upstream plugin, hook, installer, or MCP
server is installed by copying these files.
