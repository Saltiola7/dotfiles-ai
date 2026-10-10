# Host reliability and migration-checkout cleanup

## Approved scope

INT-042 selects host reliability investigation and cleanup only. Hibernation,
guests, Python, SDS activation, the Safari update and deferred project upgrades
remain paused. INT-043 permits removal of completed, delivered checkouts and
their branches after preservation checks and archival disposition; unfinished
work and active owners remain protected.

## Verification on 2026-10-09

- The transient CCC snapshot mount is no longer mounted. Native `lsof` returned
  exit zero with no warnings. The prior incomplete-inventory blocker is cleared
  for this observation, not permanently waived.
- All **17** workspace-removal and native Worktrunk policy tests passed, including
  open-file detection and refusal of unavailable/malformed process evidence.
- Inventoried **12** SSD migration and early-delivery checkouts in the two owning
  repositories. The first native check admitted one; six were blocked only by
  ignored files. The remaining five had additional preservation blockers.
- Before disposition, privately archived all **90** ignored files from the six
  completed checkouts. SHA-256 verification checked archive contents against
  source files, then rechecked identities and contents immediately before deleting
  only the approved local copies. Both evidence and test caches were retained in
  the archives; credentials and recovery preimages were not published to Git.

## Removed

Every worktree removal used Worktrunk in the owning primary and executed the
managed user pre-remove preservation hook. No force, hook bypass, process reaping
or remote branch deletion was used.

| Checkout suffix | Result |
|---|---|
| SSD-HERDR-HOST-RECOVERY | Removed older clean checkout; branch retained under its specific approval |
| EARLY-DELIVERY-CHECKS | Removed checkout and approved local branch |
| SSD-OPENCODE-PREFERENCES-1 | Removed checkout and approved local branch |
| SSD-HOST-RETIRED-SOURCES | Removed checkout and approved local branch |
| SSD-HOST-UV-SHELL | Removed checkout and approved local branch |
| SSD-HOST-SDK-BOOTSTRAP | Removed checkout and approved local branch |
| SSD-HOST-OWNERSHIP | Removed checkout and approved local branch |

All six associated cycles are completed with required gates passed. Deployment
passed where applicable; EARLY-DELIVERY-CHECKS had source-only deployment
applicability. Their changes are delivered into the protected base; there is no
remaining implementation assigned to those six branches. Worktrunk's configured
default retained branches, so separately authorized local deletions used native
non-force Git deletion after verifying ancestry in the delivered base.

Cycle records remain in the common Git directory. Their historical draft-PR
snapshots were not rewritten to impersonate fresh lifecycle evidence. Private
archive manifests retain original paths, commit IDs, file hashes and contents.

## Retained checkouts

| Checkout suffix | Native preservation blockers |
|---|---|
| SSD-NATIVE-CODEX-HOST | Private data, 24-hour retention, active process references |
| SSD-NATIVE-OPENCODE-HOST | Private data, 24-hour retention, active process references |
| SSD-HOST-VOLUME-REPAIR | Private data, 24-hour retention, active process references |
| SSD-OPENCODE-PREFERENCES | Private data, cycle-commit delivery verification, active process references |
| SSD-HERDR-HOST-RECOVERY-1 | Active failed cycle, modified/untracked helper work, private data, delivery verification |

Fresh process evidence identifies the shared OpenCode process holding open
references in four retained checkouts, plus one 1Password MCP process with cwd in
each. These are concrete owners, not stale inventory warnings. Releasing those
references requires a separately bounded session-preserving operation, followed
by fresh checks; do not kill the shared service for cleanup.

The unfinished checkout contains `dot_local/bin/executable_herdr-host-promote`
and modified `tests/test_herdr_launchagent.py`. The operator previously selected
the one-time signed repair instead of finishing that permanent helper. Preserve
the failed implementation and its evidence; it is not an unmerged prerequisite
for the completed repair. No cleanup exception has been granted for it.

## Host reliability result

The registered signed Host remains probe-only, signature-valid and enabled. Fresh
doctor/health evidence reports the expected volume, readable sentinel and
successful write probe. Its healthy transition remains **2026-10-08T18:53:20.806Z**;
the final observed healthy sample is **2026-10-09T01:37:48.431Z**. This establishes
over six hours without a recorded state transition, not a permanent reliability
guarantee. No registration change or server restart was needed in this follow-up.

The earlier `errno:5` record had no observed UUID and `sentinel:false`. Source
inspection of `.chezmoitemplates/herdr-host.swift` narrows that failure to opening
the state root or identifying its filesystem/volume before the sentinel read
(lines 518–535). `volumeUUID` maps generic `diskutil` failure to EIO (lines
335–363); `classify` also maps non-POSIX failures to EIO (lines 420–451). Therefore
the recorded value does **not** establish a physical disk I/O fault.

Bounded unified-log queries around the recorded onset returned no relevant
entries for the Host or disk utilities/kernel error filter. The retained health
schema lacks the failing operation and subprocess result needed to distinguish
these paths. **Root cause remains unproven; no speculative runtime fix applied.**
On recurrence, preserve fresh failing health and registered-agent evidence before
recovery. Any stage-specific diagnostic change requires its own affected-scope
contract and qualification; this cleanup does not authorize automatic restarts.

## Subsequent follow-up

Documentation delivery completed through PR #209 with all three hosted Python
checks passing. Privately archived the remaining five checkouts, including the
unfinished helper bundle, patch and failed cycle copy; originals remain preserved.
The preferences delivery-verification blocker cleared after refreshing its stale
remote-tracking ref. No active/failed cycle evidence was rewritten.

INT-045 approved bounded release of four unused migration-location caches. Fresh
native session queries and Herdr metadata found no session/pane assigned to those
directories. The first preferences-location eviction succeeded, but replacement
services immediately booted and reacquired resources. The operation stopped;
remaining targets and all checkouts stayed untouched. Exact conversation/layout
and cwd identities remained intact.

Pinned OpenCode source shows global location events can trigger client catalog
refreshes without a selected session there. An isolated installed-server check
confirmed that eviction remains effective without consumers, while a catalog GET
recreates a session-empty location. This proves the server re-acquisition path,
not the exact live initiating client. Successful-request metadata is absent from
the normal server log. Zero sessions/panes is therefore insufficient retirement
admission; require consumer quiescence or a qualified admission barrier. Do not
repeat eviction, kill MCP processes or remove referenced directories.

A later registered-agent observation remains degraded after recurrence on
2026-10-09, despite enabled registration and valid signature. Prior healthy
evidence above remains historical, not current recovery proof. Preserve private
recurrence evidence; cause remains undetermined. INT-044 selects preparation of
[bounded diagnostics](../HOST-DIAGNOSTICS.md), with implementation and signed
deployment still subject to fresh readiness and exact-plan approval.
