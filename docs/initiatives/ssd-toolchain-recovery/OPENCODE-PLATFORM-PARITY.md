# OpenCode native manual-update platform parity

Source specification: **ready for primary verification**. Live activation: **OPEN**.
Context: `dotfiles_ai_distribution`; owner: distribution maintainers; risk: **elevated**.
Profile: `docs/specs/dotfiles_ai_distribution/PROFILE.md`; Product Intent: matching
`PRODUCT.md` (journeys 2, 9, 17). Applicability: `OPENCODE-PLATFORM-PARITY.plan.json`.
Readiness here is not a launch receipt, runtime qualification or passed gate.

## Outcome, precedence and delivery boundary

INT-048/049 resume OpenCode source parity across macOS ARM64, managed Fedora
aarch64 guests and CentOS Stream 10 x86_64 remote users, preserving the existing
Linux workstation role. Reuse the macOS wrapper/bootstrap/service guard for
supported Linux arm64/amd64 routes; unsupported platform routes stay unchanged.
Parity means equivalent ownership and local manual update, not version equality.
No new updater or dependency is needed.

Two independently scoped slices separate source delivery from deployment:

| Slice | Owner / state | Deliverable |
|---|---|---|
| `opencode-platform-parity-source` | Build / ready | Source and regression tests only; feature branch and draft PR into configured `main` |
| `opencode-platform-parity-activation` | Discovery / discovering, OPEN | Exact environment identities, drift/consumer inventory and qualified activation plan after source delivery |

INT-048 supersedes INT-023/024 and subsequent pauses **only for this OpenCode source
preparation**. Historical evidence, legacy live ownership and guest holds remain.
No live boot, SSH repair, provisioning reconciliation, native installation, chezmoi
apply or service restart belongs to the source slice. Source tests use rendered
fixtures and isolated fake installer/service boundaries, not current Linux runtimes.
Activation must separately qualify actual installer/update/restart behavior.

No scheduled/automatic updates, fleet polling, Codex, OS/package maintenance,
Python/project upgrades or hibernation changes. INT-050 leaves hibernation findings
research-only and deferred. Preserve enterprise-seo-tools, SDS GKE and shared
production exclusions. Unknown production coupling holds activation.

## Contracts and source acceptance

| Given / when | Required source behavior and test evidence |
|---|---|
| Selected supported platform renders | One native executable at `$HOME/.opencode/bin/opencode`, distinct managed wrapper at `$HOME/.local/bin/opencode`; managed inventory includes Fedora guest wrapper/bootstrap without enabling remote-user foundation tools for guests |
| Executable absent; explicit bootstrap/apply hook invoked in a fixture | Existing official stable missing-only installer runs with `--no-modify-path`, without caller VERSION pinning; no PATH edits or implicit service restart |
| Healthy existing executable, including newer version; bootstrap invoked twice | Preserve version/digest; no download, downgrade or old digest admission |
| Unsafe parent/target, invalid or unhealthy existing executable | Refuse; no silent reinstall, alternate owner or fallback profile |
| Native manual update, including `/update` | Only invoked platform/user changes; no guest availability or host/guest version equality prerequisite |
| Default interactive/run launch; absent, unsafe or mismatched service | Reuse authenticated matching-version guard; refuse with explicit coordinated start/restart guidance; never replace shared service implicitly |
| Safe matching service | Explicit authenticated attachment, matching endpoint/PID/version, original session/argv preserved; credentials child-environment-only, never argv/output |
| Maintenance/help/version/update/service or explicit `--standalone`/`--server` | Preserve native argv/semantics; managed wrapper alone handles Herdr interactive `--auto` |
| Root sandbox command | Check existing readiness marker, then delegate exact argv to managed wrapper; no duplicate command classifier or injected `--auto` |
| Selected native-owned route invokes legacy updater | Refuse before mutation, recovery, old-owner validation/restoration, remote helper installation or VM boot; covers default, guest, migration, admission, recovery and managed-exec entrypoints that can restore/revalidate legacy ownership |
| Nonselected/unsupported route or unrelated Codex operation | Existing behavior retained; no blanket deletion of shared helpers |
| Existing remote-user, guest, workstation or external-root state | Preserve its existing config/data/state/cache routing and sandbox markers; unavailable configured state fails before creating fallback state; no cross-account/history/credential copying |

Retain locks, migration journals, failed attempts and recovery archives as history,
not native launch admission. Never restore an old database over new conversations.
Binary rollback requires upstream schema compatibility evidence and separate
activation authority, not automatic legacy recovery.

## Exact Build source/test ownership

One serialized Build writer owns only these implementation candidates:

```text
dot_local/bin/executable_opencode.tmpl
dot_local/bin/executable_opencode-install.tmpl
dot_local/bin/executable_opencode-update-all
dot_local/bin/executable_sandbox-vm
.chezmoiignore
run_after_update-opencode.sh.tmpl
run_onchange_after_install-01-remote-opencode.sh.tmpl
private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl
tests/test_opencode_distribution.py
tests/test_portable_distribution.py
tests/test_remote_user_environment.py
tests/test_lima_sandbox.py
tests/test_opencode_v2_distribution.py
tests/test_opencode_v2_authority.py
tests/test_opencode_v2_session_recovery.py
tests/test_herdr_session_recovery.py
```

Discovery retains normative contracts, acceptance, scope, dependencies and this
plan/manifest. Build may record completion evidence, not rewrite those decisions.
Other active host/recovery writers must serialize overlapping paths. Additional
paths or a behavior-changing finding return `readiness_reopened`; no scope creep.

### Caller closure established by source inspection

- `opencode.tmpl` currently chooses native macOS or Linux `exec-managed`;
  `opencode-install.tmpl` has macOS missing-only bootstrap and legacy Linux archive
  install. Both apply hooks reach these owners; `.chezmoiignore` currently excludes
  guest managed wrapper/bootstrap unless remote/workstation roles are enabled.
- `opencode-update-all.main` only refuses default macOS today. `guest-verify` calls
  `recover`, creates/locks package state and upgrades validator ownership: it is
  **not read-only**. Recovery and `exec-managed` are not safe native fallbacks.
- `sandbox-vm` CLI `opencode-stage/activate/rollback` reaches `opencode_transaction`,
  which boots guests and installs the old updater before dispatch. `opencode-retire`
  reaches `retire_opencode_provision`, which refreshes guards, boots and calls
  mutating `guest-verify`. Native-route refusal must precede those side effects.
- `sandbox-vm parity` reaches `verify_opencode_parity`; host/guest probes currently
  use legacy libexec paths and demand equality. `update`/`update-all` reach
  `update_managed_workspace`/`update_all_workspaces`; the latter rolls back Codex on
  OpenCode inequality. Source compatibility must use selected native resolution
  where inspected and must not gate native OpenCode on fleet equality or trigger
  unrelated rollback. Preserve existing Codex checks/operations; add no new update
  behavior. A safe refusal is preferable to running legacy OpenCode mutation.
- Both `OPENCODE_GUARD_SCRIPT` and Lima template currently inject root-level `--auto`;
  update both definitions consistently. Retained deployed provisioning is not
  rewritten or qualified by changing either Git definition.

## Validation and gates

Use Profile authorities and existing pytest/rendering/shell-syntax checks. Exercise
the eight listed test files, adding focused fixture checks for every acceptance row.
Render macOS ARM64, Fedora aarch64 guest, CentOS amd64 remote-user, existing Linux
workstation and unsupported controls. Assert zero mutation/boot/helper-copy on
legacy refusals, argv preservation, both sandbox guard definitions, no downgrade
on two fixture applies, and unchanged nonselected/Codex/recovery contracts.

Kernel (`domain`, `behavior`, `spec`, `contract`, `test_driven_implementation`,
`refactor`) and `review_integrate` required. `maintain_retire` required for regression,
no-downgrade and documented migration handoff; no live owner is retired here.
`release` N/A: no independent package. Source `deploy`/`operate` N/A: no environment
changes. Activation separately requires Deploy and Operate, real native Linux
install/version-to-version update, explicit restart, positive exact-conversation
UI continuity and twice repeated targeted apply. All results remain unverified.
Primary must run existing publication authority on the exact candidate/import set,
validate manifest/plan and obtain fresh receipt/preflight before any launch.

## Activation questions (do not block source-only fixtures)

1. Which remote user, executable/state/service identities and consumers are valid?
   SSH is unavailable; no root/other-account substitution or repair is authorized.
2. Which stopped guest retained provisioning blocks can overwrite ownership?
   Classify content drift, retain preimages and authorize exact repair before boot;
   READY is not full provisioning evidence. Never blanket-force unknown drift.
3. Can current native Linux installer/updater satisfy target/architecture/no-PATH
   and dependency contracts (including historical `which`) without broader upgrades?
   Historical isolated ARM64 evidence does not qualify current Linux integration.
4. Which consumers permit coordinated restart, and what private preservation and
   positive conversation recovery evidence is required? Unknown coupling holds.

## Visual Evidence Plan

Canonical source: this contract; owner: distribution maintainers; update when
platform, owner, caller, service, state or activation sequencing changes.

| Concern | Decision / evidence |
|---|---|
| Boundary | required: slice and ownership tables; source writer versus live owner |
| Interaction | required: acceptance/caller closure; bootstrap, update, launch, explicit restart |
| State | required: transition text below; installed does not mean launchable |
| Data/trust | required: acceptance contracts; state stays local and credentials stay out of argv |
| Schema | N/A: no new schema; rollback compatibility remains mandatory |
| Dependency/deployment | required: slice table and activation questions; source precedes separately qualified activation |
| Quantitative | N/A: no performance or comparative measurement claim |

**Text Equivalent:** source delivery changes no environment. Legacy live routes
remain until separately qualified activation. Empty bootstrap yields installed,
not automatically launchable. A missing/unsafe/mismatched service blocks default
launch; a safe authenticated matching service permits attachment. Manual update
changes only the local executable and may block launch until explicit coordinated
restart. Unknown drift/coupling or any failure holds activation and preserves data.
