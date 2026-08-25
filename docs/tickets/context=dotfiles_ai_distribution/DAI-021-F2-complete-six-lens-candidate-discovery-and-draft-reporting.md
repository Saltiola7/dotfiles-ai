---
schema_version: 1
id: "DAI-021-F2"
slug: "complete-six-lens-candidate-discovery-and-draft-reporting"
context: "dotfiles_ai_distribution"
title: "Complete six-lens candidate Discovery and draft reporting"
kind: "task"
state: "done"
priority: "high"
points: 3
depends_on:
  - "DAI-021-F1"
relations: []
owns:
  - ".chezmoitemplates/opencode.json.tmpl"
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
  - "docs/specs/opencode_control_plane/README.md"
reads:
  - "docs/specs/dbsctr_knowledge_store/README.md"
parallel_safe: false
validation:
  - ".venv/bin/python -m pytest -q tests/test_dbsctrctl.py tests/test_dbsctr_rnd.py tests/test_lima_sandbox.py tests/test_opencode_control_plane.py"
  - "Complete six-lens federated runtime smoke test"
created: "2026-08-23"
updated: "2026-08-23"
completed: "2026-08-23"
commits:
  - "abb5be2"
  - "1d0b436"
  - "156dd6f"
  - "9a44048"
  - "2fd40ab"
  - "cdcdfd2"
  - "5e39aca"
  - "e6d83c9"
jira_publications: []
migration: "Private improvement schema 4 migrates in place to schema 5."
---

## Outcome

Each complete lens pass can produce measurable feature candidates, evidence-bound
P0/P1 Discovery interviews, and isolated implementation drafts for human review.

## Context

Continuous six-lens dispatch was restored, but complete candidate discovery and
draft reporting still required bounded full-capture summaries and typed receipts.

## Scope

Complete server-side lens summaries, candidate claiming, Discovery readiness,
draft-only delivery evidence, and three-source runtime validation.

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
  Lima sandbox 55, and OpenCode control plane 38.
- Scoped chezmoi deployment converges the six runtime targets and migrates the
  private improvement ledger from schema 4 to schema 5.
- A live three-source federated probe returns the host and both configured guests
  as `available`. The host's valid 1.7M-part snapshot takes about 10m21s, so the
  bounded host exporter now permits 900 seconds while guests remain at 120.
- Twelve stale or orphan lens workers and their six retained reservations were
  reconciled without changing claimed or Discovery work.
- Exact helper/runtime hashes were deployed to the host and both guests. The
  previously stopped guest was restored and the other remained running after
  the smoke.
- The controlled scheduler advanced from 10 to 19 retained passes with no active
  attempt: all six lenses completed the typed terminal-receipt path against all
  three configured sources. Performance-cost follow-up produced three distinct
  P1 claims for Fast-route cost estimates, a finite Build step budget, and fork-overlap
  accounting, then reached `no_yield`; review-session governance also reached
  `no_yield` over 540 attributed review sessions.

## Continuation Resolution

The controlled correctness pass showed that model-mediated traversal of the
host's 177 safe 25-member pages could not produce a terminal `lens-result`.
Discovery selected a verified server-side summary: every source now inspects all
members of its immutable capture locally, binds exact distributions and at most
20 evidence projections to a full-member digest, and returns one bounded terminal
manifest. The typed adapter writes a lens-bound receipt only after all configured
sources succeed. Fresh query-compatible base captures are reused for 24 hours;
the private writer lock creates one new 25-member-page base only when needed, so
parallel lenses do not repeat the 1.7M-part scan. Exact raw-envelope digest
binding preserves Python numeric tokens through TypeScript validation, closes
the terminal-receipt boundary, and rejects duplicate, reordered, or externally
padded JSON. A live scheduler run completed every lens with all three configured
sources available and no unattributed sessions.

## Risks

Private source evidence must remain local and sanitized; stale captures,
incomplete source coverage, or malformed receipts must fail closed.

## Review

Focused tests, deployment convergence, live six-lens execution, and exact receipt
validation passed without granting autonomous merge or deployment authority.
