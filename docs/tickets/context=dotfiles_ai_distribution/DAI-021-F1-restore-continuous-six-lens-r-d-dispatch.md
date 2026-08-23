---
schema_version: 1
id: "DAI-021-F1"
slug: "restore-continuous-six-lens-r-d-dispatch"
context: "dotfiles_ai_distribution"
title: "Restore continuous six-lens R&D dispatch"
kind: "task"
state: "done"
priority: "high"
points: 2
depends_on:
  - "DAI-021"
relations: []
owns:
  - "run_onchange_after_configure-hermes.sh.tmpl"
  - "run_onchange_after_load-dbsctr-rnd-launchagents.sh.tmpl"
  - "run_onchange_before_install-hermes.sh.tmpl"
  - "private_dot_hermes/private_managed/private_scripts/executable_dbsctr-catalog.py.tmpl"
  - "tests/test_dbsctr_rnd.py"
  - "docs/tickets/context=dotfiles_ai_distribution/DAI-028-F2-complete-guest-compose-tooling-and-validate-runtime-fallback.md"
  - "docs/tickets/context=shell_auth_startup/AUTH-012-manage-native-herdr-with-process-preserving-upgrades.md"
reads:
  - "dot_local/bin/executable_dbsctr-rnd.tmpl"
parallel_safe: false
validation:
  - ".venv/bin/python -m pytest -q tests/test_dbsctr_rnd.py"
  - "Hermes gateway, cron, and six-lens exhaustion smoke test"
created: "2026-08-23"
updated: "2026-08-23"
completed: "2026-08-23"
commits:
  - "1d86f9b"
  - "d6533c2"
  - "bd2a261"
  - "51bb164"
  - "9740a87"
  - "c9867ff"
  - "c637065"
  - "4fbf9e7"
  - "7871fbe"
  - "c4a8f6c"
  - "57a51bd"
  - "2e4ab64"
  - "163aada"
jira_publications: []
migration: null
---

## Outcome

Hermes continuously fills every eligible R&D lens after executable relocation,
gateway restart, or expired worker ownership.

## Context

The live Hermes LaunchAgent retained a deleted interpreter path. Its status
command returned success while reporting the gateway stopped, six expired lens
attempts remained pending, and repeated configuration left duplicate cron jobs.

## Scope

Force-refresh the managed gateway service, require launchd readiness before
cutover, serialize managed cron replacement, prove stale attempt reclamation, and
run one controlled six-lens exhaustion pass.

## Acceptance Criteria

- A stale gateway service definition is replaced with the current Hermes runtime.
- Cutover fails unless launchd reports the profile gateway running.
- Concurrent configuration cannot create duplicate managed cron jobs.
- Expired attempts whose workers are absent are reclaimed before lens selection.
- One scheduled invocation launches every eligible lens and ends at a no-op.

## Evidence

- The affected Python suite passes 102 tests; shell syntax, Python compilation,
  canonical ticket inventory, and diff checks pass.
- Launchd runs Hermes through the internal pinned Python, writes local logs, and
  reports a fresh cron heartbeat with exactly one refinement and one maintenance
  job.
- An isolated committed-source scheduler proof reclaimed all six expired
  attempts, registered six distinct lens workers and native sessions, and ended
  with `active_attempt_count=6` and `last_reserve_status=no_lens_due`.
- Production backlog projection remains fail-closed on the canonical `main`
  ticket tree until this branch's ticket normalization is merged.

## Risks

The local gateway and cron schedule are operational state. Deployment must retain
one refinement job, one maintenance job, and existing per-lens cadence.

## Review

Independent review found no remaining high- or medium-severity correctness
issues after fail-closed mode retirement and project-profile gateway refresh were
added. Executable fake-launchctl coverage for project profiles remains a test gap;
the equivalent base-profile path passed live deployment and readiness checks.
