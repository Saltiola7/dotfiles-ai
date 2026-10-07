# Standalone SDK bootstrap and duplicate retirement

Home: Saltiola7/dotfiles, host_tool_maintenance. Profile:
docs/specs/host_tool_maintenance/PROFILE.md in that repository. Risk: elevated.
Requirements: INT-002, INT-003, INT-012, INT-022. Scope: current macOS ARM64 host;
other architectures and guests retain their existing routes. No production/cloud
operation, Python minor change or authenticated cloud request belongs here.

## Contract

Chezmoi supplies an after-stage bootstrap hook, after the existing before-stage
Homebrew bundle hook. Brewfile already declares python@3.12 and contains no Google
SDK declaration, so no SDK Brewfile removal is needed. Use the existing declared
Python; never install an additional Python through the Google installer.

| Given | When bootstrap runs | Required outcome |
|---|---|---|
| Healthy existing standalone SDK | Any apply | Return without download, update or configuration writes; preserve newer versions and extra components |
| Absent SDK and compatible Python | Bootstrap runs | Verify official archive, stage installation, validate it, then publish under HOME/google-cloud-sdk |
| Existing unhealthy directory or conflicting filesystem entry | Bootstrap runs | Fail visibly without overwriting or removing it |
| Missing compatible Python | Bootstrap runs | Fail with prerequisite guidance; do not fall back to unsupported system Python |
| Failed download, checksum, installer or validation | Bootstrap runs | Preserve existing state and failed staging evidence; do not publish an unqualified SDK |
| Unsupported platform | Hook renders/runs | No installation or removal; existing route remains unchanged |
| Successful install followed by another apply | Hook runs again | No reinstall, downgrade, component loss or credential/config mutation |

Use a checksum-qualified baseline only for an absent SDK. Baseline 588.0.0 official
darwin-arm archive has SHA-256
`0f580f1323d0465b11d1d7c506e701c27729e9c5ea0e1d0f855a4dc3e665db89`.
Official source: dl.google.com/dl/cloudsdk/channels/rapid/downloads/
google-cloud-cli-588.0.0-darwin-arm.tar.gz. Native gcloud components update remains
the explicit maintenance owner; the bootstrap must not pin an installed version.

Run the official install.sh with quiet, usage-reporting=false, path-update=false,
command-completion=false and install-python=false. Use isolated staging HOME and
CLOUDSDK_CONFIG, with only the selected prerequisite Python and required system
tools on PATH. Do not inherit cloud credential/config overrides into installation.
Staging stays on the destination filesystem; publish only when the destination is
still absent. Retain failed attempts for diagnosis and avoid clobbering concurrent
installation. No general updater, background service or new state registry.

Writable host source: one run_onchange_after bootstrap template and focused tests;
context completion documentation may record evidence. SDK shell selection is
already delivered by dotfiles PR #18. Preserve all unrelated dirty primary files,
including Brewfile removals and the external mise setting. Do not apply all scripts.

## Qualification and retirement order

1. Regression tests cover healthy/newer no-op, absent installation, unsupported
   platform, wrong checksum, missing Python, unhealthy destination and repeat apply.
2. Render and syntax-check hook; run it against empty isolated HOME using the real
   qualified archive, with no credentials. Then prove repeat execution is a no-op.
3. Deploy only the bootstrap script and invoke its healthy-existing no-op on host.
4. Compare installed component IDs and fresh shell selection with the retained
   duplicate; archive installation evidence before native non-zap Homebrew uninstall.
   Uninstall only after the standalone path and bootstrap pass. Preserve credentials,
   unrelated components and retained binaries outside active selection. Never use zap.
5. Recheck host CLI startup and all four login-shell resolutions without cloud calls.
   Preserve failure evidence and report any remaining duplicate path explicitly.

Discovery evidence: official archive checksum matched. Empty-home install passed
with Python 3.14 and with only the declared Python 3.12 exposed. The latter SDK also
passed after staged relocation with an empty new config. A system-only PATH attempt
selected unsupported Python 3.9 and failed, establishing the prerequisite boundary.
No live state was used. Hook integration and retirement remain Build gates.

Kernel, review, deploy, operate and maintain/retire required; release not applicable.
Validation: affected pytest, shell syntax, real isolated installer, targeted
chezmoi repeat execution, component and shell-resolution checks. No gate exception.

## Visual Evidence

State: required; canonical behavior table above. Interaction: required; numbered
qualification/retirement sequence above. Boundary, data/trust, schema,
dependency/deployment and quantitative: not_applicable; explicit owner and isolated
state constraints answer those concerns without an additional diagram.

**Text Equivalent:** keep healthy installations unchanged; stage and verify only
when absent; failure never overwrites existing state. Qualify bootstrap and shell
selection before retiring Homebrew ownership. Owner: dotfiles maintainer. Update
on installer, prerequisite, destination or retirement-policy changes.
