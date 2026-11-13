# Linux verification of native CI artifacts

## Outcome and ownership

Profile: [../PROFILE.md](../PROFILE.md). Product Intent:
[../PRODUCT.md](../PRODUCT.md), reliable source delivery and maintenance.
`dotfiles_ai_distribution` owns the workflow runner placement;
`dbsctr_v3_lifecycle` retains the existing complete-lane evidence contract and
`tests/ci_shard.py` verifier. Risk is elevated; Python, Security and Cloud apply.
Delivery is a source-only draft PR, with hosted qualification before merge.

The full-suite workers retain `macos-26`, every supported Python/Worktrunk lane,
four partitions, native Swift validation, existing checks and worker deadlines.
Only the artifact-summary job moves to `ubuntu-24.04`. Its job/check names,
matrix, always-run behavior, worker dependency and native success requirement
stay intact. Security and RHEL workflows and branch protections are unchanged.

## Behavior and contract

- Given successful native workers with complete matching artifacts, Linux runs
  the existing verifier and reports the same complete population and outcomes.
- Given a failed, canceled, skipped or unavailable worker, the summary fails even
  when a caller provides apparently complete artifacts.
- Given missing, extra, stale, wrong-source/run/attempt/lane artifacts, incomplete
  or overlapping collection, invalid execution, unsafe files or malformed JUnit,
  the unchanged verifier rejects the evidence. Existing subtest and skip
  accounting remain exact.
- Given a Linux summary, its platform describes verification only. It does not
  replace native macOS test execution or assert that tests executed on Linux.
- Given qualification or verification fails, the existing required check fails;
  unavailable evidence never becomes success. Runtime/setup/artifact failures
  retain their actual result and do not change protections.

The summary installs only the existing frozen test group under its selected
Python runtime. It runs `tests/test_ci_shard.py` on Linux before consuming native
artifacts, including existing rejection and synthetic-receipt cases. Worktrunk-dependent
integration fixtures remain on the native workers and may report explicit
capability skips on the artifact-only Linux runner. The portable cases qualify
verifier behavior; they do not constitute native macOS coverage.
The unchanged CLI then independently derives its expected checkout, tree and
source-authority hashes and verifies artifacts from the current run/attempt.
Artifact names, schemas, source/run identity, action pins, permissions and
retention do not change. No new result cache, signing policy or Dagger authority
is introduced. Artifact data is parsed, never executed.

## Qualification and measurement

First replay the retained successful worker artifacts and existing rejection
cases locally. Linux qualification then uses both the same rejection suite and
fresh artifacts from the unchanged native workers in this PR. Default-branch
activation requires those hosted results; local macOS success alone proves no
Linux portability. No new VM or developer-runtime installation is required.

The reported PR #305 baseline is [run 43040118499](https://github.com/Saltiola7/dotfiles-ai/actions/runs/43040118499)
on 2026-11-11. The handoff reports roughly 3h06m total, summary execution of
16/18 seconds and a 41-minute tail after the final worker. Recollect native
metadata and artifact digests before using those figures. This is one historical
observation, not an account concurrency limit or guaranteed savings.

Report worker/summary job creation, start and finish separately; derive readiness
from the last worker and distinguish ready-to-start waiting, setup, verifier
execution, artifact handling, final tail and aggregate job time. Include the
extra qualification step in the new summary cost. Compare equivalent matrices
and workload identities; no speedup claim from a different workload or a single
queue snapshot. Preserve unavailable values. Partition rebalance, repeated
worker setup, qualification fanout and Dagger/shared evidence reuse remain
separate later slices. Do not cancel or reorder another session's runs.

## Maintenance and rollback

The distribution maintainer owns supported-runner and Python/dependency changes.
Preserve the configured frozen lock and pinned action owners. Requalify when the
verifier, receipt contract or runtime changes. Revert this bounded workflow/test
change to restore the prior summary placement; preserve existing artifacts,
failed evidence, native coverage and protections. This source slice installs no
managed local files and publishes no independent package or production service.

## Visual Evidence

| Producer / consumer | Platform and authority | Required relation |
|---|---|---|
| Full-suite workers | Native macOS; unchanged runtime/Worktrunk matrix | Execute every partition and retain current source/run/attempt evidence |
| Summary qualification | Linux; frozen test group and existing rejection tests | Qualify parsing, completeness and negative cases; no native coverage claim |
| Summary verification | Linux; unchanged complete-lane verifier | Accept only complete matching artifacts from successful native workers |
| Required check | Existing GitHub Actions producer and name | Pass only after qualification and verification both succeed |

**Text Equivalent:** Native macOS workers produce the existing evidence. Linux
first exercises the verifier's rejection behavior, then verifies only the current
workers' matching evidence. The existing required check preserves every failure.
Source: `.github/workflows/test.yml` and `tests/ci_shard.py`; owner: distribution
maintainer; update on runner, identity, dependency or receipt changes.

Visual plan: boundary, interaction, trust and dependency concerns use this table.
State is the fail-closed behavior above; schema is unchanged and stays with the
existing verifier. Quantitative visuals are not applicable until equivalent
before/after evidence supports a measured comparison.
