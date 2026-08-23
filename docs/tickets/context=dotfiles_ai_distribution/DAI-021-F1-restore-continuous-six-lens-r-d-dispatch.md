---
schema_version: 1
id: "DAI-021-F1"
slug: "restore-continuous-six-lens-r-d-dispatch"
context: "dotfiles_ai_distribution"
title: "Restore continuous six-lens R&D dispatch"
kind: "task"
state: "in_progress"
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
completed: null
commits: []
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

Pending.

## Risks

The local gateway and cron schedule are operational state. Deployment must retain
one refinement job, one maintenance job, and existing per-lens cadence.

## Review

Pending.
