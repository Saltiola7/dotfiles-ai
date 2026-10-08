# Maintenance follow-up — 2026-10-06

Discovery evidence only; no additional slice is implementation-ready.

## Package maintenance

Operator approved publication and CI-gated merge of remaining dependency-only
maintenance: dotfiles PR #22 (Aider/nginx retirement), dotfiles-ai PR #202 (test
dependencies) and #203 (Hermes Python patch). Published; required checks and
verified-head merges are pending.

SDS root development compatibility candidate, using copied manifests only, resolves
LiteLLM 1.89.0 to 1.104.0 on Python 3.14.8. Dependency and SSL/SQLite/import checks
passed with FastAPI 0.136.3 and Prefect 3.7.4. Shared-library manifest and worker
inputs are unchanged; live environments have not been replaced. Synthetic mocked
LiteLLM completion and an ephemeral Prefect flow are the next runtime checks,
followed by full allowed-constraint refresh qualification. Candidate execution uses
an isolated home without inherited provider or production credentials.

Aider tool qualification found a minor-version conflict: installed and newly
resolved aider-chat 0.86.2 both declare Python >=3.10,<3.13, but the existing tool
uses Python 3.13.2. An isolated same-minor 3.13.16 candidate resolves but fails
uv pip check on that explicit Python requirement. Live tool unchanged. Moving
this tool alone to supported Python 3.12 requires an operator exception to the
minor-preservation rule; do not widen or bypass package constraints.

Operator instead retired unused Aider (INT-029). Native uv uninstall removed the
live tool; the managed installer, Brewfile declaration and aider-local helper were
removed from task and configured sources. The live helper was archived; histories
and user configuration were not removed. Source commit b1105c5 retains the removal;
shell/Ruby syntax and command-absence checks passed. Publication remains pending.

Operator also retired unused nginx/Valet and confirmed spatie/http-status-check is
unused (INT-030). Nginx's old Valet configuration referenced an absent log directory;
native brew service stop and uninstall succeeded without autoremove or configuration
purge. Native Composer removal could not run because PHP is absent. With explicit
operator approval, the global Composer tool installation/configuration and Valet
launcher were archived. Both commands are absent; nginx/Valet site configuration
and data remain in place. Brewfile retirement commit 40fc4ca passed Ruby syntax;
publication remains pending.

Hermes 0.19.0's pinned, digest-verified wheel passed isolated Python 3.13.16
dependency, SSL/SQLite and CLI version/help qualification. Preserve its exact
package pin and internal-disk macOS interpreter contract. Managed interpreter
declaration and live tool/service activation remain pending.

Hermes follow-up: interpreter declaration updated in commit 6c51518; three affected
Hermes rendering tests passed. Activated the exact qualified dependencies on
internal-disk Python 3.13.16, retaining the previous tool environment and launcher
definitions. Native gateway start unexpectedly regenerated its plist without the
existing state-root guard. Verification caught the change; the regenerated plist
was retained as failure evidence and the original guarded plist was restored using
native launchctl bootout/bootstrap. Guarded registration is byte-identical to its
preimage, reports running, and native deep status succeeds. Two executions of the
rendered updated installer leave the receipt unchanged. Configured source carries
the interpreter update; publication is pending. No gateway state snapshot was
restored over current state.

Delivery follow-up: residual SDK declaration PR #199 passed Python 3.12/3.13/3.14
CI and merged at 20a6f235261aeaf378b5658911c642b8b6ab0a0a with operator approval.
Existing orphan-recovery source and Discovery documents are published as draft
PRs #200 and #201 respectively; neither draft is a completed merge or new launch.

Dotfiles-ai Python candidate completed 1040 passing tests, seven skips and seven
failures, with 51 passing subtests. Focused reruns reproduce the same seven failures
under both original Python 3.13.2 and candidate 3.13.16: one legacy installed-CLI
session-list check, three bounded-probe timing checks, and three native workspace
process-inventory checks. Native lsof exits zero but warns it cannot stat a CCC
transient read-only APFS snapshot mount and its output may be incomplete. The
preservation guard correctly refuses that inventory; no hook was bypassed and no
backup mount was altered. The operator explicitly accepted these seven verified
pre-existing failures for this Python upgrade. Scope: test-environment activation
only; owner: repository operator; review again during host process-inventory and
OpenCode cutover completion. This does not waive preservation checks or mark those
tests passed. Activated Python 3.13.16 after retaining the original environment and
lock. Dependency checks, SSL/SQLite/import smoke and repeat frozen sync passed.
Unlike dotfiles, dotfiles-ai tracks uv.lock; exact qualified dependency resolution
is committed in maintenance/test-python-refresh at 884fc35. Source publication is
pending; unrelated primary changes remain intact.

Isolated Python 3.13.16 candidates for content-evidence-workbench and
search-taxonomy-lab passed dependency checks, respectively 35 and 47 tests, Ruff
lint and strict Marimo validation. Content Evidence resolves Marimo 0.25.1,
NumPy 2.5.3, scikit-learn 1.9.1 and SciPy 1.18.1 within existing constraints.
Search Taxonomy preserves all exact direct pins and refreshes allowed transitive
dependencies. Formatting, session execution and WASM export validation passed for
both candidates. Search Taxonomy also passes committed/fresh snapshot comparison.
Content Evidence fails that comparison because Marimo metadata advances from
0.23.15 to 0.25.1; snapshot format, script metadata hash and every cell identity/code
hash remain unchanged. Its static preview must be refreshed through project-owned
delivery with the dependency update; do not weaken the validator. Content Evidence
browser qualification could not launch because its required Chromium executable
was missing. Search Taxonomy launched Chromium but timed out waiting for its app
heading; the cause remains undiagnosed. The operator subsequently deferred both
project upgrades until needed (INT-028). Both live environments and tracked locks
remain unchanged; these results are candidate evidence, not activation or publication.

Later 2026-10-07 batch upgraded 27 remaining formulae: libomp, cryptography,
Databricks CLI, glib, libpng, xorgproto, harfbuzz, hdrhistogram_c, libheif, luv,
mlx, mlx-c, Moshi, simdjson, node, nss, Ollama, OpenEXR, OpenJPEG, OpenVINO,
Poppler, Pulumi, SDL3, SDL2 compatibility, Syncthing, Tcl/Tk and yt-dlp.
Before/after package receipts and upgrade log are retained privately. Cleanup and
autoremove stayed disabled. Brew linkage checks passed for all requested dynamic
packages. Node, Pulumi, Databricks, yt-dlp, Syncthing, Poppler, Moshi and
cryptography startup/import checks passed; MLX array arithmetic and OpenVINO import
passed. Ollama client starts at 0.40.0 but reports no running server; server/model
operation was not tested. CLI checks do not prove running service version activation.
The excluded environment's 334 native libraries were inspected read-only with
successful otool exits and no direct Homebrew linkage; no project application ran.

Remaining formula inventory lists only legacy Homebrew OpenCode, reserved for
native-owner migration. ChatGPT upgraded to 26.1002.52244 (bundle verified) and
ClickHouse to 26.9.12.8 (startup verified). Homebrew reports reopening the application
it closed for the ChatGPT upgrade. User conversation continuity inside that app
was not inspected. Previously reported current-app/stale-receipt cases remain distinct.
The AI source still declared the retired Google SDK cask; dependency-only PR #199
removes that residual declaration (36 portable-distribution tests and Ruby syntax
passed). Configured source was reconciled; CI/merge remain pending.

Test-only dotfiles and dotfiles-ai environment candidates use external Python
3.13.16, preserving their existing 3.13 minor. Isolated dependency checks and
SSL/SQLite checks passed. Dotfiles resolves iniconfig 2.3.1 and typer 0.27.3;
dotfiles-ai resolves iniconfig 2.3.1, packaging 26.3 and pygments 2.21.0, all within
existing constraints. Project tests are running; no live environment replacement
or lockfile publication has occurred yet.

Dotfiles candidate subsequently passed 244 tests with one skip against the merged
retirement source. The primary test environment was activated at Python 3.13.16
after preserving its original environment and lock. Dependency/import/SSL/SQLite
checks and repeat frozen sync passed. Its .gitignore deliberately excludes uv.lock,
so refreshed dependency resolution remains local rather than forcing a new tracked
lockfile. Dotfiles-ai candidate test execution remains pending; its live environment
has not been replaced.

2026-10-07 follow-up after INT-027 consumer clarification: Homebrew Python 3.12.15,
Python 3.14.8, pipx 1.17.11 and DuckDB 1.5.6 installed. The dry run selected only
those four packages; automatic cleanup/autoremove stayed disabled. Both previous
Python kegs remain. New interpreter SSL/SQLite checks, pipx version, an in-memory
DuckDB aggregate and 23 affected host tests passed. Protected primary interpreter
routes still resolve to Framework/mise installations rather than Homebrew.

Homebrew reported a previously unmanaged local DuckDB 1.2.1 symlink shadowing its
declared installation. The symlink was archived, with the native installation
retained. All four host login modes now resolve Homebrew DuckDB 1.5.6. No database
was opened; SQL qualification used an in-memory database.

Recent host deliveries are recorded in HOST-SDK-SHELL.md, HOST-SDK-BOOTSTRAP.md,
HOST-UV-SHELL.md and HOST-RETIRED-SOURCES.md. They supersede the earlier unresolved
SDK precedence, uv selection and retired-launcher findings below. Delivery-helper
PR #198 passed all three Python jobs and smoke and merged at
80a15d57183685dc00130aa2b5f6951a4231af38.

Latest follow-up: moshi-hook upgraded from 0.4.10 to 0.4.18 with automatic cleanup
disabled. Native dry run selected only that dependency-free formula. CLI version
reports 0.4.18 and its probe reports installed/running/gateway true. No explicit
daemon restart or hook reinstallation was performed; running process executable
identity and pending approval continuity are not established by that probe.

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

Fresh guest inventory still reports the client guest stopped and personal running. Personal
chezmoi status lists five pending scripts and no ordinary file drift. Its system
failed-unit list contains cloud-init-main; cloud-init reports the previous
per-boot script failure. User failed-unit list contains default-buildkit; status
shows a SIGTERM during stop and a changed unit requiring daemon reload. These
observations do not prove current boot provisioning or justify clearing failures.
Herdr Host doctor still reports a valid signature and enabled registration but
probe-only degraded health due to the old expected volume identity.

## Subsequent reconciliation

PR #197 passed all three CI versions after the validator update and merged at
`e59dfec4ddd4b35babe3e01f79092b4e8765b4bf`. PR #187's previous Python 3.13 job
failed only the eighty-session spacing assertion: all sessions launched, but at
least one observed interval was below 4.8 seconds. Python 3.12 and 3.14 passed.
The failure is retained; no exception or assertion weakening was approved.
PR #187 was updated against the newly merged base and its new CI remains pending.

Final follow-up: all three jobs passed on the updated PR #187 head; it merged at
`ee63d74a6ee89d2c9853de4a017c5a36f4740049`. The earlier failed timing run remains
historical evidence and does not establish that the underlying timing concern was
repaired. Both requested current PRs are merged; superseded PRs remain closed.

Four casks have current installed application bundles despite older Homebrew
receipts: 1Password 8.12.40, RustDesk 1.5.0, Tailscale 1.102.4 and SF Symbols
27.0 build 140. Report receipt drift separately from executable version. The
standalone Tailscale CLI reports 1.102.5; no network service restart was performed.

Google Cloud SDK has two independent installations, not symlinks to one owner.
The shell-selected standalone SDK reports 583.0.0. Operator INT-022 selects that
owner and requires chezmoi bootstrap before duplicate Homebrew retirement.
An isolated installation-only copy with a separate empty CLOUDSDK_CONFIG passed
native update from 583.0.0 to 588.0.0. Corrected native JSON inventory proves all
nine component IDs remain present. The first inventory filter used a nonexistent
`state.name` field and returned no records; that attempt was not counted as parity
evidence. BigQuery, Storage, kubectl client and GKE auth-plugin startup probes pass.
Component metadata and binary-reported versions differ for some components, so
record each evidence source rather than treating receipt versions as executable
identity. The authorized live native update completed at 588.0.0 with all nine
component IDs preserved and the original SDK archived. Explicit-path BigQuery,
Storage and GKE auth-plugin startup checks pass. A kubectl client probe also loaded
existing kubeconfig and attempted authentication against the empty scratch Google
configuration; its zero exit was not sufficient evidence. Repeating with
KUBECONFIG=/dev/null passed without stderr. No cluster operation was requested.

Fresh-shell selection fails the ownership contract: Bash login (interactive and
noninteractive) and noninteractive Zsh select Homebrew; interactive Zsh selects
the standalone SDK. The managed common profile prepends Homebrew, while the
upstream Bash SDK helper does not reprioritize an SDK directory already present
later in PATH. Durable shell correction, standalone bootstrap and duplicate
retirement remain incomplete. Noninteractive Bash still selects the old local uv.

The owning distribution changelog confirms DAI-033-1 retired host Colima/Docker.
Removed their five stale Brewfile declarations; Ruby syntax validation passed.
The source's legacy Colima LaunchAgent/bootstrap hook remains a separate behavioral
retirement issue, so a blanket chezmoi apply is still not qualified.

Original V2 cutover cycle remains active and already has native workspace adoption.
Its preserved dirty template change changes limactl permission from deny to ask.
No source edits or lifecycle-state writes were made to that cycle in this follow-up.

## Guest follow-up

Subsequent operator decision INT-024 defers remaining guest work. INT-025 defers
the 1Password for Safari update after App Store ISErrorDomain Code=4. Operator
reported successful updates of BlueWallet 8.0.2, Final Cut Pro 12.4, PDF Expert
3.13.4, Slack 4.52.178 and WhatsApp 26.38.74; these are operator-reported results.

Personal guest still reports cloud-init scripts_per_boot failure in
00-lima.boot.sh. Privileged cloud-init log inspection stopped because native sudo
requires an operator password. User daemon reload completed; default-buildkit is
now explicitly not-found, with its previous failed state retained. Its unit file
was already absent before reload; do not recreate it from the stale manager record.
Podman socket is active, Atuin is running, and pm-postgres reports healthy. This
does not qualify a complete boot or fresh provisioning.
