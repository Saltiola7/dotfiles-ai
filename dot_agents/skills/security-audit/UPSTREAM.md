# Upstream provenance

Source: https://github.com/cloudflare/security-audit-skill/tree/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/skills/security-audit

Commit: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`. Reviewed 2026-10-28.

Attribution: Cloudflare, Inc.. License: MIT; see [LICENSE.upstream](LICENSE.upstream).
The upstream material retains this license, separately from the repository license.
No vendor endorsement is implied.

## Local packaging

All 20 upstream skill files preserved byte-for-byte. Added only license and provenance records. Existing Node.js is required for the structural validators; no sandbox is bundled.

Local modifications are marked in each changed file and recorded as exact patches
in the security-toolkit lock record. No upstream plugin, hook, installer, or MCP
server is installed by copying these files.
