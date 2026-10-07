# Herdr Host replacement-volume recovery

Home: shell_auth_startup. Profile: docs/specs/shell_auth_startup/PROFILE.md.
Risk: elevated. Source authority: matching README.md and OPERATION.md, signed-host
build assets and session-recovery helpers. Preserve native Herdr layout and exact
conversation identities; use the official OpenCode integration.

## Known gap

Existing operations explicitly stage a signed versioned candidate when a canonical
bundle exists. OPERATION.md's probe-only contract has no approved promotion command;
it requires retained canonical rollback, mutual designated requirements and
coordinated unregister/promote/re-register before activation. The replacement-volume
candidate alone does not fix the canonical wrong-volume binding.

This slice repairs the canonical signed host's correct-volume health and registration.
It does not silently turn a probe-only host into the active owner of Herdr. If active
ownership is necessary, return that behavior change to Discovery before implementation.

## Behavior and operation contract

| Given | When | Required outcome |
|---|---|---|
| Signed candidate for replacement identity | Qualification runs | Strict signature and designated-requirement equivalence pass |
| Existing canonical bundle/registration | Promotion is requested | Preserve exact old bundle and registration evidence before replacement |
| Candidate qualifies | Supported promotion completes | Canonical health probes expected volume; correct registration and unchanged ownership mode |
| Registration/promotion step fails | Recovery runs | Identify reached state; preserve both bundles and avoid duplicate service ownership |
| Running Herdr sessions | Host binding is repaired | Existing server/panes survive unless an authorized bounded restart is required |
| Restart required | Sessions resume | Exact native sessions in original panes; no most-recent-session guessing |

Keep Full Disk Access and ServiceManagement consent separate from shell permissions.
Probe-only repair never grants new execution ownership. Do not hand-copy over a
registered application or suppress failed health checks.

## Validation and write ownership

Native signed-host build/configuration, operation interface and matching tests are
owned by this lane. The primary coordinates live unregister/promote/re-register.
Recovery helpers and launcher arguments are shared with native-tool-updates and
deferred hibernation; serialize those edits. Existing server and pane snapshots are
private recovery evidence, not public test fixtures.

Validate shell/Swift compilation and rendered plist, codesign verification,
registration-status, probe/doctor/status, correct-volume and missing/wrong-volume
cases, interruption recovery and exact-session resumption. Run affected existing
Herdr launchagent/session-recovery tests. A synthetic probe does not replace live
signature, consent and registration evidence.

Kernel/review/deploy/operate/maintain required; release N/A. Selected implementation
and failure-recovery boundary follows. Do not reinstall
all panes indiscriminately. INT-033 reopens prior identity-only recovery claims:
positive visible conversation evidence is required, not a retained Herdr ID.
Recover only affected idle panes with fresh terminal/session binding, preserve
new work, and record unresolved outcomes when UI evidence is unavailable.

## Selected promotion interface and write scope

Implement a managed `herdr-host-promote` shell command with:

- `--candidate PATH --check`: read-only validation and exact planned paths;
- `--candidate PATH`: guarded probe-only promotion;
- `--recover JOURNAL`: inspect and resume only a uniquely classified interrupted
  transaction; otherwise stop with the reached state and retained artifacts.

The candidate must be an explicit real user-owned pending bundle under the same
Applications directory as canonical, without group/world write permissions.
Reject symlink paths, unknown registration/ownership, active hosting, invalid
strict signatures, unequal bundle identifiers/designated requirements, incorrect
replacement-volume configuration and non-unique rollback/journal destinations.
Use existing `codesign`, `plutil`, native `herdr-host` operations and same-filesystem
renames; do not edit a signed bundle, TCC records or ServiceManagement databases.

An exclusive transaction lock and private internal-disk journal preserve the
candidate identity, canonical identity, registration preimage and reached states.
Before mutation, revalidate all inputs. Native `unregister` must establish
not_registered before canonical replacement. Rename canonical into a unique
retained rollback bundle, then candidate to canonical; verify signature again,
invoke native `register`, and require fresh registered-host probe health for the
replacement volume. Preserve probe_only ownership and running Herdr server/panes.

Record pending intent before each external operation and completion afterward.
On interruption, classify actual files and native registration against the
journal; never infer success from an intent record. If classification is unique,
resume at that state. Otherwise stop without cleanup, overwrite or retry. If
macOS requests Login Items or Full Disk Access approval, retain the new bundle and
report that operator boundary. Do not silently roll back across an uncertain
registration or claim consent. Explicit rollback uses the same checks and native
unregister/register sequence; never deletes either signed bundle.

Source ownership: new `dot_local/bin/executable_herdr-host-promote`, affected cases
in `tests/test_herdr_launchagent.py`, and the implemented-operation section of
`docs/specs/shell_auth_startup/OPERATION.md`, README/CHANGELOG/BACKLOG completion
evidence. The signed build/Swift implementation need not change. If they do,
return readiness_reopened before expanding scope. Builder may replace the old
"no approved promotion command" operational status only with tested command usage;
normative behavior and scope remain Discovery-owned.

Validation: shell syntax; existing rendered signed-host tests; mocked native
signature/registration/rename interruption cases; read-only live preflight;
strict candidate/canonical signature and mutual designated requirements; actual
native registration, replacement-volume probe and unchanged live pane/terminal
mapping. No unrelated service restart or guest work. Build registration requires
the committed profile and exact operator BEGIN confirmation.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: signed host versus current server owner is explicit |
| Interaction | required: promotion sequence in behavior table |
| State | required: table covers qualified, promoted and failed paths |
| Data/trust | not_applicable: signing and consent boundaries retained |
| Schema | not_applicable: no new registry schema is selected |
| Dependency/deployment | required: WORKSTREAMS.md activation table |
| Quantitative | not_applicable: no measurement-based claim |

**Text Equivalent:** qualify signed candidate, preserve canonical rollback, perform
supported registration replacement, then prove volume health and session preservation.
Failures retain evidence and cannot grant new ownership. Owner: shell maintainer.
Canonical source: this contract; update trigger: promotion or ownership semantics.
