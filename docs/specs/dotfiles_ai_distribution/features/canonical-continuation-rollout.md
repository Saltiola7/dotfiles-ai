# Canonical Continuation Rollout

Status: delivered to the host and configured guests with installed-byte and native
qualification; live conversation enrollment remains operator-controlled.

## Profile And Scope

Use `../PROFILE.md` and `../PRODUCT.md`. Risk: critical; modules Python, Security
and Cloud. Owner: dotfiles owner. Dependencies: merged continuation core and
qualified OpenCode adapter. Preserve all native history, authentication and Cycle
Records. Delivery is a feature-branch draft PR plus targeted host-first deployment,
then configured guest qualification. No broad apply, new service, model call,
automatic OpenCode restart, or cross-boundary private-state copy.

## Deployment Contract

Deploy only these managed targets, excluding any target ignored by the target's
existing machine configuration:

| Target | Purpose |
|---|---|
| `.local/bin/dbsctrctl` | Core admission and storage recovery |
| `.local/bin/opencode-update-all` | Future runtime qualification |
| `.local/bin/opencode-continuation-deploy` | Narrow preview/apply/verify/rollback |
| `.local/share/opencode-continuation/native_probe.py` | Existing qualified native probe, promoted to a managed asset |
| `.config/opencode/lib/dbsctr-runtime.ts` | Per-call helper environment |
| `.config/opencode/lib/continuation.ts` | Native identity/routing/control translation |
| `.config/opencode/plugins/continuation.ts` | Native admission hooks |
| `.config/opencode/tools/dbsctr.ts` | Typed controls |
| `.config/opencode/agents/build-gpt.md` | Provider-affine approval rules |
| `.config/opencode/agents/build-claude.md` | Provider-affine approval rules where configured |
| `.config/opencode/opencode.json` | Registry reference and continuation permissions |

The deploy helper takes an explicit source and machine config, with preview,
apply, verify and rollback modes. Source is a committed clean checkout or a
commit-marked public Git archive. It must not change the canonical source branch
or machine TOML. Chezmoi receives explicit target paths and `--exclude scripts`;
never invoke unbounded apply, update-all, or unrelated installation hooks.

Preview renders privately and reports only target aliases, hashes and bounded
status. For the configuration target, permit only the new registry reference,
preflight/continuation permission keys and continuation CLI denial. Refuse any
other semantic change before deployment. Preserve providers, model selections,
existing explicit denies and unrelated machine-local configuration. Do not print
rendered configuration bodies or unknown private field names.

The configuration projection selects only the continuation-owned fields from
rendered source before planning; unrelated full-template differences are left
untouched. Its resulting semantic delta still passes the independent allowlist.
This is not a claim that unrelated pre-existing Chezmoi drift was reconciled.

Before apply, retain exact prior target bytes/modes in an owner-private local
backup with a source-bound receipt. Recheck target identities after preview and
before mutation. Drift, unsafe file custody or an unsupported source blocks the
apply. Refuse unknown local edits rather than force-overwrite them. Apply helper,
libraries and tools before the plugin; configuration activation is last. Verify
all selected rendered target bytes and idempotence. Failure restores prior target
bytes/modes or explicitly reports rollback failure, never touches private runtime
databases, and never restarts an incompatible writer.

Host qualification precedes guests. Resolve guests from existing machine-local
configuration; preserve each guest's fresh pre-rollout running/stopped state.
Transfer only commit-marked public source/validation assets to temporary guest
storage. Use guest-local config, SDK code and authentication boundary; no host
credentials, histories, backups or native databases are transferred. Do not use
the broad sandbox update path or rewrite guest TOML. Restore an initially stopped
guest after bounded qualification; leave an initially running guest running.

## Qualification And Future Updates

Reuse the adapter's loopback scripted-provider native probe, with an installed
layout mode. It exercises real attach/write/bash/preflight, same-session resumption
under a changed same-provider model, and reader write denial while proving that
canonical fixture files remain untouched. It makes no hosted-provider request and
uses no production conversation. Keep only public dependency code in fixture
staging; never symlink writable fixture dependencies into the live SDK tree.

Advance the OpenCode semantic validator revision while retaining readable prior
lock revisions. When the managed continuation plugin is installed, runtime
qualification must also load the continuation controls and pass the managed
native probe. Missing assets or failed hooks reject the candidate using existing
rollback/healthy-release behavior. Do not infer readiness from version/help/config
alone or from an on-disk binary while an old process remains running.

Deploy and Operate evidence distinguish installed bytes, successful fresh-process
qualification, and live conversation activation. Existing OpenCode processes keep
their loaded tools until an operator-controlled restart; reopen the exact
conversation. Never claim a real incident cycle was repaired from disposable
fixture evidence. Actual enrollment/ownership recovery still requires exact
quiescence/provider consent. No feature edits, lifecycle completion or merge in
those incident cycles are authorized by testing attachment.

## Retention And Recovery

Keep activation/operation history and storage-recovery receipts without automatic
pruning. Owner monitors the private database and backups; storage repair has a
64 MiB bound and explicitly refuses larger state pending separately approved
maintenance. Retain pre-deploy target backups for operator-reviewed rollback;
do not automatically delete an unknown, failed or dirty artifact. Missing or
corrupt state never authorizes creation of an empty replacement database.

Rollback restores only snapshotted targets whose installed identity still matches
this deployment. Later drift blocks rollback. Once live enrollment exists,
restoring unmediated older tools is not a safe resume path: keep mutation paused
and fix forward or obtain a separately validated compatibility recovery.

## Acceptance And Gates

Kernel, Review/Integrate, Deploy, Operate and Maintain/Retire are required. Release
is not applicable: no separately versioned artifact is published. No exception.
Use scoped pytest, Python compilation, Chezmoi rendering/verification, exact
installed hashes, native probes and guest state checks. Include denied consent,
drift refusal, unsafe paths, restricted JSON differences, apply failure and rollback
tests. Repository-wide QA remains explicit-only; existing configured CI still runs.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: deployment order below separates host and guest state |
| Interaction | required: deployment order below names verification before progression |
| State | required: rollback table below guards recovery |
| Data/trust | required: only public source crosses the guest boundary |
| Schema | not_applicable: source-bound private deployment receipt is not a new lifecycle schema |
| Dependency/deployment | required: deployment order below |
| Quantitative | not_applicable: no comparative measurement is claimed |

```text
Clean source + existing local machine config
  -> private preview + source-bound prior-target backup
  -> host targeted apply -> hash/idempotence checks -> native probe
  -> public-source transfer -> guest-local targeted apply -> native probe
  -> restore each guest's prior running state
Live conversation activation remains a separate operator-controlled step.
```

**Text Equivalent:** Preview and backup precede host apply. Host byte verification
and native qualification precede guest-local deployment. Only public source is
transferred; guest state stays local. Each guest returns to its prior running
state. Installed files and test fixtures do not prove live conversation activation.
Distribution owner updates this flow whenever target ownership or ordering changes.

| Condition | Required outcome |
|---|---|
| Preview mismatch or unrelated config delta | Refuse before apply |
| Apply/verification failure with unchanged owned targets | Restore exact prior bytes/modes and report failure |
| Later drift or failed rollback | Preserve evidence, block completion, request operator recovery |
| Live enrollment already active | Never resume an unmediated older runtime as rollback |

**Text Equivalent:** Refuse unexpected changes before mutation. After an owned
apply failure, restore only provably owned targets. Unknown drift or rollback
failure stays blocked. Live coordinated state must not be handed to an old writer.
