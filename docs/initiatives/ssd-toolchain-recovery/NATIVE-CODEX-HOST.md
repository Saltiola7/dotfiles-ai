# Native Codex ownership on macOS ARM64

Context: dotfiles_ai_distribution. Risk: elevated. Profile:
`docs/specs/dotfiles_ai_distribution/PROFILE.md`; adjacent Codex profile:
`docs/specs/codex_control_plane/PROFILE.md`. Product Intent: distribution PRODUCT.md,
journey 3. Parent: NATIVE-UPDATES.md; requirements INT-002/003/010/012/014/015/023.
The receipt also carries the historical rolling-stable Initiative/feature pointers
referenced by the shared native-platform successor contract; these are precedence
authority, not permission to modify OpenCode implementation.
Status: specification-ready; fresh receipt/preflight and exact chat approval are
required before Build. Live activation remains gated by managed-wrapper and
exact-session qualification.

## Selected interfaces and ownership

- Official standalone installation owns CLI packages and update selection inside
  the existing managed CLI CODEX_HOME. Export `CODEX_INSTALL_DIR` as
  `$HOME/.local/libexec/dotfiles-ai/codex-native`; never replace the public managed
  `$HOME/.local/bin/codex` guard or point installation at the shell/GUI home.
- Keep existing CODEX_HOME selection, sentinel/home validation and configuration
  projection/recovery. Replace only the macOS ARM64 launch dependency on legacy
  fixed-digest package locks with native-owned symlink/package validation.
- Reuse `codex-project` for bounded native validation and daemon-policy merging.
  Native selection may follow owned symlinks only into the selected CLI home's
  standalone release tree. Require owned non-writable-by-others directories and
  executable regular targets; refuse missing, escaping or unsafe selections.
  Preserve legacy validation and projection entry points for deferred platforms.
- Merge only `updater.autoUpdateEnabled=false` in the CLI home's native daemon
  settings, preserving unrelated keys. Use existing atomic/private-file helpers
  and coordinated home locking; refuse unsafe paths or invalid JSON. Never replace
  config.toml, authentication, histories, or GUI settings. Native manual update and
  startup notifications remain available. Launch verifies this policy; drift
  requires explicit managed reapply rather than silent enabling.
- `codex-install` performs missing-install bootstrap only on macOS ARM64. Existing
  healthy native versions survive apply without installation or downgrade.
  Export the distinct install directory and managed CLI home for native updates;
  use noninteractive installation with its bin directory already on PATH so the
  installer cannot edit shell profiles. Restore the managed wrapper's precedence.
- The macOS ARM64 update hook calls bootstrap, not a fleet update. Enable the
  bootstrap in the managed-file inventory. Legacy default host fleet mutation
  refuses after native transition; explicit deferred-platform and historical
  inspection interfaces remain. Do not run sandbox-vm provisioning.
- CLI and dedicated app-server daemon packages are distinct native owners.
  `codex update` updates CLI selection. Report CLI and daemon versions separately;
  ordinary daemon restart is not an upgrade. A needed daemon upgrade uses explicit
  `codex app-server daemon update` only after inventory and coordination. Preserve
  disabled scheduled updates before/after service operations.

## Writable source scope

`.chezmoiignore`; `dot_local/bin/executable_codex.tmpl`;
`dot_local/bin/executable_codex-install.tmpl`;
`dot_local/bin/executable_codex-project`; `dot_local/bin/executable_codex-update-all`;
`run_after_update-codex.sh.tmpl`; affected cases in
`tests/test_codex_distribution.py`, `tests/test_codex_control_plane.py`,
`tests/test_portable_distribution.py`, and `tests/test_native_codex_sandbox.py`;
distribution README/CHANGELOG completion evidence. Keep install-onchange and
project-onchange hooks compatible; widening their interfaces reopens Discovery.
OpenCode and Herdr sources are outside this slice.

## Behavior, deployment and acceptance

| Given | Action | Required outcome |
|---|---|---|
| Missing native CLI, valid existing state | Bootstrap | Official native installation; guard and CLI/GUI separation preserved |
| Existing healthy native CLI | Apply twice | No downgrade or installer rerun; existing config and unrelated daemon settings preserved |
| Missing volume, unsafe home, selection or settings | Launch/bootstrap | Refuse without creating an alternate profile or following unsafe paths |
| Native CLI update | Invoke managed `codex update` | Only host CLI changes; selected installer directory and state remain |
| Older dedicated daemon | Restart | Report actual daemon version; do not claim CLI update activation |
| Coordinated daemon update | Invoke native daemon update | Qualified new daemon version and disabled scheduled updates; preserve exact conversations |
| Deferred Linux/guest route | Render/check | Existing owner and behavior retained; no live guest change |
| Existing work or failed update | Recover | Preserve histories and current work; no database rollback or unqualified binary rollback |

Before live writes, retain exact executable/config/settings preimages, package
selection and body-free native session inventory. Qualify native installation,
version-to-version CLI update, daemon policy and explicit daemon update in a short
isolated path; macOS Unix sockets impose path-length limits. Then test the managed
wrapper, absent-volume refusal, native symlinks and twice-repeated targeted reapply.
Resume an existing selected conversation through supported native interfaces with
positive UI/identity evidence; never submit a provider prompt solely for testing.
Working sessions and GUI state remain untouched. Retain legacy binaries, locks,
archives and failed attempts; do not uninstall another owner during this slice.

Project authorities: focused Codex distribution/control-plane/projection tests,
portable rendering/publication tests, shell syntax, official version metadata,
native doctor plus explicit daemon versions, and exact-session/UI evidence.
Unauthenticated fixture doctor failure is not an authenticated-health pass. All
kernel, Review/Integrate, Deploy, Operate and Maintain/Retire gates are required;
Release is not applicable because this consumes upstream packages.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: interface list names native, managed and GUI ownership |
| Interaction | required: ordered deployment table below |
| State | required: behavior table above |
| Data/trust | not_applicable: no history/config transfer; existing state stays local |
| Schema | not_applicable: native settings key is specified without a new schema |
| Dependency/deployment | required: ordered deployment table below |
| Quantitative | not_applicable: no comparative performance claim |

| Order | Guard | Next action |
|---|---|---|
| 1 | Isolated CLI/daemon checks pass | Capture live preimages and session inventory |
| 2 | Home separation and disabled auto-update policy verified | Bootstrap native CLI and preview targeted guard apply |
| 3 | Managed launch and CLI update qualified | Explicit coordinated daemon update if needed |
| 4 | Exact conversation and both versions verified | Reapply twice, record operation and retained rollback artifacts |

**Text Equivalent:** qualify isolated CLI and daemon operations first; preserve
live state before switching the guard; update a daemon explicitly if needed;
verify exact conversation recovery before closing deployment. Canonical source:
Selected interfaces and Behavior above. Owner: distribution maintainer. Update
trigger: installer, daemon lifecycle, state routing, policy or ownership changes.
