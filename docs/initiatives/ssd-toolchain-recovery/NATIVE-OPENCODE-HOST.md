# Native OpenCode ownership on macOS ARM64

Context: dotfiles_ai_distribution. Risk: elevated. Profile:
`docs/specs/dotfiles_ai_distribution/PROFILE.md`. Product Intent:
`docs/specs/dotfiles_ai_distribution/PRODUCT.md`. Parent contract:
NATIVE-UPDATES.md and `features/native-platform-updates.md`.

This independently deliverable portion of native-tool-updates transitions only
the macOS ARM64 OpenCode executable. Codex and deferred Linux/guest routes retain
their current owners. This is implementation readiness; live deployment remains
blocked until affected gates and explicit session-maintenance checks pass.

## Selected interfaces and ownership

- Native installer target: `$HOME/.opencode/bin/opencode`. Official installer:
  `https://opencode.ai/v2/install`, with `--no-modify-path`.
- Existing managed `opencode` command remains the state/Herdr guard and forwards
  native maintenance arguments unchanged. Its macOS ARM64 launch target becomes
  the native executable; preserve current environment and absence-of-volume checks.
- Reuse `opencode-install` for missing-install bootstrap on this platform. A
  healthy existing native target is never overwritten during chezmoi apply;
  an invalid existing target fails clearly rather than silently reinstalling.
  Explicit native update is separate from bootstrap. Bootstrap failure must not
  select Homebrew or create an empty alternate state profile.
- Restrict automatic `--auto` injection to interactive launch/run semantics;
  version, help, update, service, API and other maintenance commands retain their
  argument vector. Recognize `-s`, `--session` and `--session=` for interactive
  resumption pacing. Do not add permissions to unrelated maintenance commands.
- macOS ARM64 run-after update hook calls missing-install bootstrap only;
  other platforms retain the existing updater. Remove the competing Homebrew
  OpenCode declaration. Preserve unrelated Brewfile tools.
- Retain legacy updater code and admission records for deferred guest routes,
  original cutover evidence and rollback. Its default fleet-update invocation on
  a native-owned host must fail clearly before mutating host or guests. Explicit
  historical inspection/guest verification remains available. The PM provisioning
  caller must report this boundary rather than silently launch fleet mutation.
  Do not execute deferred PM/guest provisioning during deployment.
- No automatic shared-service restart. A live transition uses a saved exact
  inventory, canary, independently verified conversation UI, bounded client
  restart sequence and operator coordination for this maintenance conversation.

## Writable source scope

`Brewfile`; `.chezmoiignore`; `dot_local/bin/executable_opencode.tmpl`;
`dot_local/bin/executable_opencode-install.tmpl`;
`dot_local/bin/executable_opencode-update-all`;
`run_after_update-opencode.sh.tmpl`;
affected cases in `tests/test_opencode_distribution.py`,
`tests/test_portable_distribution.py`, `tests/test_herdr_session_recovery.py`
and `tests/test_opencode_v2_authority.py`, `tests/test_opencode_v2_distribution.py`,
`tests/test_opencode_v2_session_recovery.py`; distribution README/CHANGELOG/BACKLOG
completion evidence. Builder does not change normative contracts or slice scope.
If another caller requires material interface changes, return readiness_reopened.

Discovery caller review found that `.chezmoiignore` currently excludes the
bootstrap on macOS. Include it only on the selected macOS ARM64 platform while
preserving deferred platform exclusions. Rendered managed-file inventory is a
required check, in addition to executing the rendered bootstrap itself.

The probe-only Host promotion helper is not a dependency of this slice. Preserve
the existing Host preflight behavior; do not activate Host ownership or change
its signing/registration as part of native executable migration. Preserve the
separate failed Host cycle and its worktree.

## Behavior and acceptance

| Owner | Responsibility | Preserved boundary |
|---|---|---|
| Official installer/updater | Native executable | Invoked macOS ARM64 host only |
| Chezmoi guard/bootstrap | State routing, missing-install bootstrap | Existing external state and missing-volume refusal |
| Recovery controller/operator | Bounded client restart and UI verification | Exact session/terminal mapping and current work |
| Legacy updater | Retained deferred-platform and historical operations | No host fleet mutation after native ownership |

| Given | When | Required result |
|---|---|---|
| Valid external state, native executable absent | Bootstrap runs | Official native installation; managed guard and state paths preserved |
| Healthy native release already present | Apply twice | Same executable digest/version, no downgrade or fleet update |
| Missing volume or unsafe existing target | Launch/bootstrap runs | Clear failure, no alternate local profile |
| Herdr maintenance command | Guard forwards it | No injected `--auto` or session pacing |
| Exact session with any supported session flag | Interactive launch runs | Existing pacing and explicit identity preserved |
| Native-owned host, legacy fleet update requested | Command begins | Refuse before host/guest mutation with native update guidance |
| Deferred Linux/guest route | Rendering and existing tests run | Prior owner/arguments preserved; no guest activation |
| Native update fails | Operator inspects state | Existing conversations and state remain; report actual binary/server versions |
| Clients reconnect or restart | Recovery verifies them | Positive conversation UI and exact identity/terminal mapping, not ID-only success |

Qualification already establishes native 2.0.22-to-2.0.24 update and isolated
service restart with unchanged synthetic session metadata and paths. A plain
synthetic service restart did not reproduce the reported route loss on either
version; do not claim 2.0.24 fixes the incident. Initial PTY teardown needed output
draining; the corrected fixture completed both versions. Live transcript integrity
and managed-wrapper integration require their own evidence.

Build validation: focused pytest suites; rendered macOS/Linux command contracts;
shell syntax; absent-volume and unsafe-target fixtures; two no-op bootstrap
applications; isolated native update through the rendered wrapper; exact-session
live canary and complete post-restart mapping/UI verification. No provider prompt
is submitted solely for testing. Private conversation content stays local.

## Deployment, operation and rollback

Preserve wrapper, executable, package/admission, service and configuration preimages.
Install candidate before routing change. Publish deployed source only after gates.
Do not mix fresh native executable with legacy digest admission. A binary rollback
must first establish schema compatibility; never roll back the database over new
work. Keep old package artifacts until the native route, restart and targeted
reapply qualify. Retire redundant Homebrew executable ownership only after that
point without data-purging flags. No DVC output changes are expected.

Kernel, Review/Integrate, Deploy, Operate and Maintain/Retire are required. Release
is not applicable: consume upstream binaries, do not publish an independent package.
Remaining operator boundary: fresh receipt, preflight and exact BEGIN confirmation.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: selected interface list separates native executable and managed guard |
| Interaction | required: deployment ordering above and behavior table |
| State | required: absent, existing, failed and updated cases in behavior table |
| Data/trust | not_applicable: existing external-state boundaries remain, no data relocation |
| Schema | not_applicable: no new persistent schema |
| Dependency/deployment | required: install before routing, qualify before retirement |
| Quantitative | not_applicable: no performance claim |

**Text Equivalent:** bootstrap only a missing native executable, retain the
managed state guard, forward maintenance unchanged, then qualify update, restart
and reapply before retiring redundant ownership. Failures preserve current data.
Canonical source: this contract. Owner: distribution maintainer. Update trigger:
installer, guard, platform, session-recovery or ownership change.
