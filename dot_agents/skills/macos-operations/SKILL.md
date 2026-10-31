---
name: macos-operations
description: Diagnose and maintain macOS launchd services, launch environments, privacy permissions, Keychain access and native command compatibility. Use for host automation and operational failures.
---

# macOS Operations

Resolve the actual process, launch context and expected operation. Keep existing
task authorization, security policy and lifecycle ownership.

## Target and context

Record macOS version/architecture, executable or bundle, account, launch mechanism
and affected resource. Distinguish interactive Terminal, SSH, GUI app, LaunchAgent
and system daemon. Their environment, session and security attribution can differ.

Prefer explicit executable paths and the project's supported shell/tools. Check
the installed versions: the system Bash and BSD utilities may differ from a
Homebrew Bash or GNU command used on Linux. A configured PATH is not evidence
that a launchd process receives it.

## launchd diagnosis

Resolve the exact label, plist owner/path and launch domain (`gui/<uid>`,
`user/<uid>` or `system`). Read the matching `launchctl print` target and relevant
logs. Validate plist syntax with `plutil -lint`; syntax success does not prove a
successful bootstrap, correct executable identity or readiness.

Inspect argument boundaries, working directory, environment, output paths and
exit/termination evidence. launchd does not interpret `ProgramArguments` as a
shell command. Long-running children should retain the intended foreground
process relationship; do not add another supervisor to mask a fork/exit problem.

Choose scheduling, KeepAlive and restart behavior from the actual requirement.
Avoid restart storms and overlapping jobs; define success, failure and recovery.
Bootstrap, bootout, kickstart, enable/disable and persistence changes are mutations
under existing task authorization, not prerequisites for inspecting the failure.

## Privacy, signing and credentials

For TCC/permission failures, identify the responsible executable or application
and its launch identity. A grant to Terminal does not establish access for a
daemon or newly signed binary. Preserve existing grants and security controls;
do not edit TCC databases, disable SIP/Gatekeeper or grant broad access as a
default diagnostic shortcut.

For Keychain failures, distinguish item lookup, account/session access, interaction
policy and the requesting identity. Inspect only necessary metadata and redacted
errors. Do not print secret values, change access controls or start a login flow
merely to make diagnosis pass.

When code signing, entitlements or notarization is the actual concern, use the
corresponding installed `build-macos-apps` skill if available. App architecture
and SwiftUI design are separate from host-service diagnosis.

## Verify and return

After an authorized change, verify the original operation in its real launch
context, bounded logs, process/health behavior and any required login/restart
persistence. A running PID alone is not application readiness. Return facts,
remaining hypotheses, changes, recovery and verification to the existing cycle.

Primary references: [Apple launchd guidance](https://support.apple.com/en-asia/guide/terminal/apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/mac),
[Apple background service design](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html),
and the installed `launchctl`, `launchd.plist`, `codesign` and `security` manuals.
Use target-version documentation; unavailable access remains an explicit gap.
