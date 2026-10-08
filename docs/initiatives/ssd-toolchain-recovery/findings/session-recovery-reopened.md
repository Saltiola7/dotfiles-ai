# Recovery verification reopened

Operator steering on 2026-10-07 pauses all further Python environment updates and
live activation for a separate session. Completed deliveries remain preserved;
SDS PR #197 merged, but live environment activation is deferred.

The operator reported empty OpenCode screens in previously recovered Herdr panes.
Investigation confirmed native Herdr identity can retain the last selected
conversation after the TUI returns home. Earlier identity-only recovery evidence
was insufficient and is reopened.

All 74 durable recovery entries resolve through native session metadata and
match reported pane identities; all retain historical usage. This is metadata
retention evidence, not complete transcript-integrity evidence. Visible-screen
classification positively identified 58 empty home screens. Narrow remaining
panes were not assumed healthy. Private evidence remains outside Git.

Logs show a shared disconnect interval across 74 clients. Reconnect-induced route
loss remains a hypothesis pending isolated reproduction. A bounded client-only
canary restored the original title and visible conversation in the same terminal.
Recover affected idle panes with fresh identity, process-exit and positive UI
checks; exclude focused, working, blocked and independently changed panes.

Completed recovery pass: all 74 panes retain the same session and terminal IDs,
all have conversation-specific terminal titles, and none show an empty-home
prompt. Previously healthy conversations remained running. Client-exit and initial
integration reporting needed bounded waits; initial stops and successful retries
remain in the private journal. No shared live service restart occurred.

The original temporary verification inventory was not found at its documented
location. A saved historical Herdr layout independently reconciles all original
73 IDs with the durable 74-entry manifest: 72 retain original pane mappings,
the ongoing maintenance conversation occupies its current pane, and one newer
SSD-diagnosis conversation accounts for the additional entry. Preserve that
current conversation rather than moving it back. Never restore old databases over
current work or submit synthetic prompts into real conversations for verification.

INT-034 supersedes blanket hibernation deferral in INT-017/020: qualification may
resume after exact-session recovery. It does not authorize an unqualified watcher.
Upstream v0.4.1 still lacks verified process-exit evidence, durable wake ordering
and full cwd/launch-option preservation. Repair/fork scope remains unresolved.

OpenCode 2.0.22 is behind verified official native package 2.0.24. Native installer
transition and signed Host replacement-volume registration remain required.
The Host reports wrong_volume in probe-only mode and is not the live server owner.

Fresh credential-free native 2.0.22-to-2.0.24 update and isolated service restart
passed, with identical synthetic session metadata and state paths. One installer
fetch failed HTTP 403 through Python; native curl succeeded, failed evidence
retained. This does not establish live native-owner transition or authenticated
TUI update qualification.

Credential-free synthetic TUI service-restart probes completed on both 2.0.22
and 2.0.24: session title remained displayed, no home-screen marker appeared,
and the original synthetic session record survived. Plain service restart alone
did not reproduce the incident; integration/configuration-event interaction is
still unresolved. Do not claim a proven root trigger or a version-specific fix.
