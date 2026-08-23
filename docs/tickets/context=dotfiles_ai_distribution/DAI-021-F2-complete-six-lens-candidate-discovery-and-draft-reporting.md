---
schema_version: 1
id: "DAI-021-F2"
slug: "complete-six-lens-candidate-discovery-and-draft-reporting"
context: "dotfiles_ai_distribution"
title: "Complete six-lens candidate Discovery and draft reporting"
kind: "task"
state: "blocked"
priority: "high"
points: 3
depends_on:
  - "DAI-021-F1"
relations: []
owns:
  - "dot_local/bin/executable_dbsctrctl"
  - "dot_local/bin/executable_dbsctr-rnd.tmpl"
  - "dot_local/bin/executable_sandbox-vm"
  - "private_dot_config/opencode/commands/dbsctr-improve.md"
  - "private_dot_config/opencode/lib/dbsctr-runtime.ts"
  - "private_dot_config/opencode/tools/dbsctr.ts"
  - "tests/test_dbsctrctl.py"
  - "tests/test_dbsctr_rnd.py"
  - "tests/test_lima_sandbox.py"
  - "tests/test_opencode_control_plane.py"
reads:
  - "docs/specs/dbsctr_knowledge_store/README.md"
parallel_safe: false
validation:
  - ".venv/bin/python -m pytest -q tests/test_dbsctrctl.py tests/test_dbsctr_rnd.py tests/test_lima_sandbox.py tests/test_opencode_control_plane.py"
  - "Complete six-lens federated runtime smoke test"
created: "2026-08-23"
updated: "2026-08-23"
completed: null
commits:
  - "abb5be2"
  - "1d0b436"
  - "156dd6f"
  - "9a44048"
jira_publications: []
migration: "Private improvement schema 4 migrates in place to schema 5."
---

## Outcome

Each complete lens pass can produce measurable feature candidates, evidence-bound
P0/P1 Discovery interviews, and isolated implementation drafts for human review.

## Acceptance Criteria

- Federated history accepts the explicit unavailable project-attribution sentinel
  without weakening malformed digest rejection.
- Feature claims require a testable measurement plan; other claim kinds reject it.
- Evidence-ready P0/P1 claims persist Discovery interviews and may reach only a
  draft pull request; P2/P3 wait for promotion and uncertainty blocks.
- Final Push records a generated diff digest, changed paths, passed gates, and
  draft URL.
- DKS citation metadata is optional, untrusted, source-verified, and nonblocking.

## Evidence

- Affected suites pass: `dbsctrctl` 159 tests with one optional skip, R&D 37,
  Lima sandbox 54, and OpenCode control plane 37.
- Scoped chezmoi deployment converges the six runtime targets and migrates the
  private improvement ledger from schema 4 to schema 5.
- A live three-source federated probe returns host, personal, and MGM as
  `available`. The host's valid 1.7M-part snapshot takes about 10m21s, so the
  bounded host exporter now permits 900 seconds while guests remain at 120.
- Twelve stale or orphan lens workers and their six retained reservations were
  reconciled without changing claimed or Discovery work.

## Blocker

The controlled correctness pass completes its host snapshot but exits without a
`lens-result`. At the safe 25-candidate output bound, the current host capture has
177 continuation pages. Manually recording `no_yield` would fabricate completion.
The six-lens smoke remains blocked until the worker can exhaust that immutable
capture within one bounded run or the runtime provides an equivalent verified
server-side traversal summary.
