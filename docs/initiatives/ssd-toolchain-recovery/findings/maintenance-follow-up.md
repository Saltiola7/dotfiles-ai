# Maintenance follow-up — 2026-10-06

Discovery evidence only; no additional slice is implementation-ready.

## Package maintenance

Seven isolated Homebrew CLI upgrades completed with automatic cleanup disabled:
direnv 2.38.1, hcloud 1.70.1, mole 1.58.0, pandoc 3.12, sevenzip 26.04,
usage 6.12.1, and scrape 1.10.1. The dry run listed only these requested
packages. Six native version probes passed; scrape does not support `--version`
and its supported `--help` command passed. These checks prove executable startup,
not complete integration behavior. Old formula kegs were retained.

The subsequent no-auto-update inventory reported 30 outdated formulae and
13 outdated casks. This includes the legacy Homebrew OpenCode V1 installation;
it must not become a competing executable owner. Of eight GUI cask upgrades,
five completed: Brain.fm 0.0.327, ChatGPT 26.930.61225, Obsidian 1.14.4,
Paste 7.0.1 and Signal 8.29.0. Installed bundle metadata confirms those versions;
application-state checks remain pending. Homebrew could not quit the app identified
as `com.openai.codex` during ChatGPT upgrade, so running-version activation is unproven.
Unlike the retained formula kegs, Homebrew purged the old cask versions despite the
no-cleanup environment setting; no application data purge was requested.

Loop and Shortcat upgrades failed because their old application bundles are missing
from both system and user Applications directories. The operator confirmed both
should remain removed, preserving preferences. Their Brewfile declarations were
removed; native non-zap uninstall reconciled both receipts. SF Symbols package maintenance
failed at interactive sudo; its actual installed bundle already reports 27.0 build
140, newer than Homebrew's recorded receipt. Reconcile metadata rather than claiming
this failed invocation installed that version. Earlier App Store inventory reported
six available updates, not installed updates.
The explicit six-app `mas upgrade` attempt subsequently failed because sudo needs
an operator terminal; no App Store update completion was reported.

## Shell and tool environments

Noninteractive login Bash still resolves unmanaged local uv 0.8.15. Mise lists
uv 0.12.23 as active, and its architecture-specific installed executable works.
Source explains the mismatch: common profile prepends local bin, while Bash's
mise activation occurs below the interactive-only early return. A durable change
must also account for Zsh login-only startup and preserve guarded AI launchers.

Default uv tool inventory uses the external XDG tool directory and reports no
tools. Explicit inventory of the retained legacy tool directory finds Aider
0.86.2 and Hermes 0.19.0. Do not infer that empty current inventory authorizes
duplicate installations or deletion of the legacy environments.

Pipx inventory fails because cookiecutter-data-science 2.2.0 references a missing
Homebrew Python 3.13 interpreter. Its installation metadata records Python 3.13.1,
an unpinned package, and no injected packages. A generic `reinstall-all` would
select the current Python 3.14 default, violating the approved minor-preservation
policy. Repair requires an explicit qualified 3.13 interpreter and retained old
environment evidence.

Follow-up repair completed: isolated Python 3.13.16 and cookiecutter-data-science
2.3.0 passed the 23-package dependency check, SSL/SQLite imports, and offline
project rendering. The initial fixture lacked the required `ccds.json`; correcting
the fixture produced a pass without changing candidate code. Installed Python
3.13.16 side by side under the existing external uv interpreter root without
changing default Python executables. Archived the original pipx environment with
symlinks preserved, then used targeted native pipx reinstall with the explicit
3.13 interpreter and shared-library maintenance disabled. Activated environment
passed dependency/interpreter checks and a separate offline render; pipx list now
reports healthy cookiecutter-data-science 2.3.0. Original package metadata was
unpinned; no project constraints or production environments changed.

## Linked checkout inventory

Native Git worktree lists from non-excluded repositories were inspected at five
known environment locations: root `.venv`, root `venv`, `iac/.venv`, `adb/.venv`,
and `ci/.venv`. The bounded scan returned 230 checkout records with environments
or missing paths, 236 environment configurations, and 15 missing checkout paths.
All 236 sampled interpreter links resolve. Recorded configuration versions span
Python 3.11 through 3.14; these are creation metadata, not fresh runtime versions.

This inventory includes retained archives and production-adjacent environments.
It does not classify all consumers or authorize mass activation. Additional nested,
tool and guest environments remain outside this bounded scan. Excluded project
directories were skipped. Raw paths and inventory remain private.

Both previously failing SDS worktree locations are absent directories, rather than
existing directories with broken `.git` files. No registrations were pruned and no
checkout was recreated. Distinguish intentional disposal from missing retained
work before proposing recovery.

## Delivery

Operator approved closing superseded PRs instead of reconciling retired behavior.
PR #160 was closed with merged #163 as replacement; #69 was closed with merged
#193/#194 as replacements. Branches and commit history were retained.
PR #187 received a base update. PR #197 was marked ready for review. Their merge
checks have not passed; repository auto-merge is disabled. Neither is claimed merged.
PR #197's Python 3.14 job completed with 1043 passed, 10 skipped and one failure:
the isolated writing-command configuration test invokes `opencode debug config
--pure` against CI's OpenCode 1.18.9. This is a delivery blocker requiring diagnosis,
not authority to skip the check.

Isolated reproduction confirms 1.18.9 rejects the `mcp.servers` shape. Both the
existing 1.18.34 executable and isolated npm 1.18.35 accept the same rendered
configuration; 1.18.35 resolves all three asserted writing commands. The preferences
branch CI dependency pin was advanced to 1.18.35 without changing test assertions.
This is compatibility-validator maintenance, not completion of the pending native
V2 runtime/CI cutover. A first local probe incorrectly reused chezmoi's state-file
path as an XDG state directory; it failed with ENOTDIR before validation. The corrected
probe used distinct isolated XDG directories and retained the failed attempt.
All six writing-skill tests passed with the isolated 1.18.35 validator. Commit
`ffe2f89` was pushed to the existing preferences PR branch; fresh CI is pending.

## Guest and host health

Fresh guest inventory still reports MGM stopped and personal running. Personal
chezmoi status lists five pending scripts and no ordinary file drift. Its system
failed-unit list contains cloud-init-main; cloud-init reports the previous
per-boot script failure. User failed-unit list contains default-buildkit; status
shows a SIGTERM during stop and a changed unit requiring daemon reload. These
observations do not prove current boot provisioning or justify clearing failures.
Herdr Host doctor still reports a valid signature and enabled registration but
probe-only degraded health due to the old expected volume identity.
