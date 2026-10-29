# Upstream provenance

Source: https://github.com/getsentry/skills/tree/d12f250460ffd961f549dbebf7eeb0cf4afd4c2e/skills/secret-serialization

Commit: `d12f250460ffd961f549dbebf7eeb0cf4afd4c2e`. Reviewed 2026-10-28.

Attribution: Functional Software, Inc. dba Sentry. License: Apache-2.0; see [LICENSE.upstream](LICENSE.upstream).
The upstream material retains this license, separately from the repository license.
No vendor endorsement is implied.

## Local packaging

Selected entrypoint and both language references. Replaced entrypoint with bounded holder-to-sink review, actual unauthorized-exposure criteria and primary severity policy. Corrected logger/toJSON and hidden-property assumptions. Omitted upstream internal evaluation/spec documents; those evaluations do not validate this toolkit.

Local modifications are marked in each changed file and recorded as exact patches
in the security-toolkit lock record. No upstream plugin, hook, installer, or MCP
server is installed by copying these files.
