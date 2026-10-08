# One-time signed Host volume repair

Context: shell_auth_startup. Profile: docs/specs/shell_auth_startup/PROFILE.md.
Risk: elevated. Requirements INT-002/003/010/012/033/035/036/037.
This closes the signed-Host portion of the still-broader INT-001 migration goal.
This is the selected one-time replacement-volume repair. The unfinished permanent
promotion helper and its registered failed cycle remain retained, without claiming
their completion. No new managed command or active Herdr ownership is introduced.

## Scope and ownership

Use the existing signed probe-only candidate and native ServiceManagement commands.
Preserve exact canonical/candidate identities, mutual designated requirements,
configuration equivalence except expected volume identity, registration preimage,
probe-only ownership, and fresh body-free pane/session/terminal metadata.
Keep the actual operator paths and volume identifiers in private evidence.
The configured chezmoi volume binding remains authoritative; verify it matches
the candidate before mutation. Do not change signing, Swift, launch arguments,
credentials, configuration routing, other services or deferred guest/Python work.

A retained, digest-identified one-time procedure lives with private qualification
and operation evidence. Reuse existing guarded promotion logic where correct;
qualify its interrupted-rename recovery before any live write. No installer/apply
hook installs or reruns this procedure. Source write scope is completion evidence
in shell_auth_startup README.md, CHANGELOG.md and OPERATION.md. New normative
behavior or additional production paths reopen readiness.

The receipt also carries shared native-update precedence, distribution/Codex
profiles, Product Intent and rolling-stable pointers from the existing Discovery
branch. These are read-only imported authority, not writable runtime scope.

## Ordered operation and recovery contract

| State | Guard | Operation and next state |
|---|---|---|
| Prepared | Both owned real bundles strictly verified; mutual signing requirements; same filesystem; enabled registration; matching live replacement volume; probe-only ownership | Retain preimages and private exclusive journal; record unregister intent |
| Unregister pending | Canonical identity unchanged | Native unregister; independently require not_registered; record completion |
| Unregistered | Fresh registration proof and unchanged identities | Record intent, rename canonical to unique retained rollback, fsync parent |
| Old bundle moved | Rollback is exact old bundle, candidate exact new bundle, canonical absent | Record intent, rename candidate to canonical, fsync parent |
| Interrupted old-moved layout | Exact unique layout and compatible journal, no unknown files or symlinks | Restore old bundle to empty canonical path with journaled intent; re-observe native registration before retrying the normal sequence; preserve both identities |
| Candidate canonical | Exact new canonical and retained old rollback, candidate path absent | Read native registration; register only when not_registered; preserve requires_approval as operator boundary |
| Registered | Fresh registered-host probe | Require healthy replacement-volume UUID, writable sentinel, probe_only; verify existing server and pane bindings unchanged |
| Complete | Health and preservation passed | Retain both signed bundles, journal, preimages and all failed attempts; report exact qualified outcome |

Record intent before every external mutation and completion afterward. Recovery
classifies actual bundle identities and native registration, never journal intent
alone. A recovery interruption during old-bundle restoration must itself be
recoverable from either uniquely verified layout. Unknown registration, identity,
ownership, volume, permissions or layout stops without cleanup or overwriting.
Do not infer Login Items or Full Disk Access consent. Keep new work and histories;
never restore an old database or restart the Herdr server for this repair.
If the native operation unexpectedly requires such a restart, stop for a revised
maintenance plan and exact-conversation recovery qualification.

## Acceptance and authorities

- Check-only qualification performs no registration or rename and creates no
  transaction. Reject bad signatures, active ownership, unsafe paths, changed
  configuration, mismatched volume and ambiguous/replaced artifacts.
- Exercise interruption before/after both renames, restoration recovery, native
  registration failure and consent-required retry; never duplicate successful
  registration or lose either bundle. Use local fixture state and mocked native
  authorities, then read-only live signature/volume/registration preflight.
- Before live writes, compare the current inventory and server PID against the
  private baseline. After repair, verify exact pane/terminal/session bindings and
  existing server PID, fresh health and unchanged probe-only mode. A restart or
  missing conversation needs positive UI recovery, not identity-only success.
- Validate affected signed-host rendering/operation tests, shell syntax and public
  completion documents. No whole-repository audit or external provider test prompt.
- Kernel, Review/Integrate, Deploy, Operate and Maintain/Retire are required;
  Release is not applicable because no independently published package is created.
  Retain the old failed helper cycle separately. Deliver one feature-branch draft
  PR to the configured main branch after exact-plan chat approval and all gates.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: scope explicitly separates probe-only Host, current server, managed source and private procedure |
| Interaction | required: ordered operation/recovery table |
| State | required: ordered operation/recovery table |
| Data/trust | not_applicable: signatures and private evidence boundaries are explicit; no history transport |
| Schema | not_applicable: private one-time journal is not a supported public schema |
| Dependency/deployment | required: ordered operation/recovery table |
| Quantitative | not_applicable: no comparative measurement claim |

**Text Equivalent:** verify and preserve both signed bundles; unregister before
replacement; journal each rename; recover the intermediate gap by restoring the
exact old canonical bundle and rechecking native registration; register and probe
the new canonical bundle; preserve the running server and all panes. Canonical
source: operation/recovery contract above. Owner: shell distribution maintainer.
Update trigger: changed ownership, signing, registration or recovery semantics.
