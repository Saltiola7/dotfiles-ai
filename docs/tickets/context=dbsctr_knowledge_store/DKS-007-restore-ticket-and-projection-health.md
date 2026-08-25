---
schema_version: 1
id: DKS-007
slug: restore-ticket-and-projection-health
context: dbsctr_knowledge_store
title: Restore ticket and projection health
kind: task
state: done
priority: high
points: 3
depends_on:
  - DKS-005
relations:
  - dbsctr_knowledge_store:DKS-006
owns:
  - .chezmoidata.toml
  - config.example.toml
  - docs/specs/dbsctr_knowledge_store/README.md
  - docs/specs/dbsctr_knowledge_store/CHANGELOG.md
  - docs/specs/dbsctr_knowledge_store/OPERATION.md
  - docs/tickets/context=dbsctr_knowledge_store/DKS-005-silver-retrieval-trial.md
  - docs/tickets/context=dbsctr_knowledge_store/DKS-007-restore-ticket-and-projection-health.md
  - dot_local/bin/executable_dksctl
  - private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-knowledge-reconcile.plist.tmpl
  - private_dot_config/dotfiles-ai/knowledge/projects.json.tmpl
  - run_onchange_after_load-dbsctr-knowledge-reconcile.sh.tmpl
  - tests/test_dbsctr_knowledge_store.py
reads:
  - configured origin/main remote ref and exact committed blobs
  - live DKS status, doctor output, reconcile stdout/stderr, and launchd metadata
  - typed sanitized DBSCTR authority and active ranking identity
parallel_safe: false
validation:
  - python3 dot_local/bin/executable_pmctl tickets check --root . --json
  - uv run --group test pytest tests/test_dbsctr_knowledge_store.py
  - dksctl reconcile --project dotfiles-ai
  - dksctl doctor --project dotfiles-ai
  - dksctl status --project dotfiles-ai
  - launchctl print gui/$(id -u)/dev.dotfiles-ai.dbsctr-knowledge-reconcile
created: 2026-08-25
updated: 2026-08-25
completed: 2026-08-25
commits:
  - 5fb1931
  - d82be68
  - 46caf86
jira_publications: []
migration: null
---

## Outcome

Canonical DKS ticket authority validates, and the unattended local projection
converges to merged `origin/main` with every channel fresh and `dks-rrf-v1`
unchanged.

## Context

DKS-005 is delivered and merged at `d9b09ec`, but its ticket uses the unsupported
PM state `completed` instead of `done`. After merge, doctor reported Git, graph,
and authority drift while launchd retained the prior active projection and a
nonzero previous exit. Historical logs show successful convergence plus transient
authority, lock, credential, embedding, and database failures; a new scheduled
reconcile was active during discovery.

## Scope

Correct only DKS-005's canonical completion state. Observe the active reconcile;
if it fails, run one manual runbook retry. Escalate only a reproduced failure to
the smallest code or configuration repair, with focused regression coverage.
Merge any repository correction, then prove the live projection converges to the
resulting `origin/main` commit and completes a subsequent unchanged run.

## Acceptance Criteria

- DKS-005 uses PM state `done` and retains its completion date and commit evidence.
- PM validation reports no finding for any `dbsctr_knowledge_store` ticket;
  unrelated repository ticket findings are recorded but remain out of scope.
- Recovery resolves only the configured immutable `origin/main` ref and never
  projects uncommitted worktree content.
- A successful in-flight run is accepted without a redundant manual reconcile;
  otherwise one runbook-prescribed manual reconcile is attempted.
- A repeated failure is diagnosed from bounded local evidence and receives only
  the minimal code or configuration fix needed for its reproduced root cause.
- Failed or partial recovery preserves prior valid channel rows and source
  authorities; logs contain no source bodies, prompts, vectors, or credentials.
- `doctor` is healthy with active and target revisions equal to merged
  `origin/main`; Git, code, graph, and authority identities are fresh.
- The active ranking policy remains baseline `dks-rrf-v1` with evidence class
  `baseline` and no trial expiry; no quality candidate activates.
- Launchd records exit 0, and one later reconcile reports every stage unchanged.
- DKS-006 remains blocked and no PostgreSQL extension, model, benchmark, or schema
  migration is introduced.

## Risks

Reconciliation touches a private production projection and local model/database
services. Recovery must preserve immutable authorities, prior valid activations,
project isolation, bounded logs, baseline ranking, and rebuild rollback. A long
graph update can legitimately span scheduler intervals; busy overlap is not a
failure and must not trigger concurrent work.

## Evidence

Discovery inspected merged commit `d9b09ec`, the DKS Engineering Profile,
operation runbook, PM validator, live doctor/status output, launchd metadata, and
bounded reconcile logs. The live projection remained active at `b96dd297` while
targeting `d9b09ec`; doctor named `authority_stale`, `git_stale`, and
`graph_stale`. PM validation reported three DKS-005 findings because `completed`
was not a supported state.

Before this cycle started, upstream reconciliation PR #50 corrected DKS-005 to
`done`; affected PM validation then returned no DKS findings. The scheduled run
safely advanced from `b96dd297` to `d9b09ec` but retained that prior-valid result
when authority changed during the long refresh. One runbook retry converged Git,
code, graph, and authority to merge commit `87d20d0`. Doctor reported healthy,
`dks-rrf-v1` remained the baseline policy with no trial expiry, launchd recorded
exit 0, and the next reconcile reported all four stages unchanged. All 84 focused
DKS tests passed.

## Review

Independent review found one unbound-detail issue. Exact run and count details
were removed; re-review found no remaining findings. No code, configuration,
schema, model, benchmark, or ranking change was required. Final delivery must
reconcile once more after the pull request merge advances `origin/main`.
