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

Kernel/review/deploy/operate/maintain required; release N/A. Remaining Discovery:
qualify the minimal supported promotion transaction and its failure recovery;
record exact writable source paths before marking Build-ready. Do not reinstall
all panes or replay the already completed conversation recovery batch.

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
