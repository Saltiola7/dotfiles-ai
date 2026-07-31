---
description: Run one autonomous global-history R&D worker for chezmoi-dotfiles-ai.
---

Operate as one bounded native-Build R&D worker:

1. Require `DBSCTR_RND_WORKER_ID`, run `dbsctr-rnd lens-plan --worker-id
   "$DBSCTR_RND_WORKER_ID"`, and stop when its validated JSON says the pass is
   not due. Require exactly one returned versioned lens. Load `dbsctr-review`
   and apply only that lens. The five ordinary lenses exclude candidates whose
   `review_session` is true. Only `review_session_governance` selects those
   candidates and audits prior R&D sessions, duplicate yield, missed issues, and
   whether source-controlled lenses should be added, split, revised, combined,
   or retired. The ordinary families remain correctness/safety,
   reliability/recovery, performance/cost, operator experience, and
   architecture/R&D meta. When assigned `review_session_governance`, also load
   `dbsctr-lens-audit`.
2. Call `dbsctr_review_federated` with `limit=100` once
   without a `reviewedStatus` filter and follow every continuation. This full
   history pass must include the host and every federated workspace source and both
   previously reviewed and unreviewed sessions. Stop if any configured source is
   unavailable; never describe a partial manifest as global history.
   Pass the returned `sourceState` unchanged with each continuation so every
   source retains its original snapshot, ceilings, and database identity. Apply
   the assigned lens to every page while it is in context. Count pages, sources,
   selected sessions, selected review sessions, and excluded review sessions.
   Never let an ordinary lens reason from a review-session candidate.
   The federated tool's immutable private captures are the pass evidence; do not
   resubmit namespaced source cohorts to the live host database. Do not call
   `dbsctr_review_history_save`, `dbsctr_review_complete`, or change review markers. After each source page,
   reduce it to at most 10 concise issue signals and merge only the strongest 20
   into a running shortlist before continuing; never use context pressure as a
   reason to skip a page.
3. Synthesize one ranked shortlist across the complete lens pass. Compare each
   concrete issue with durable improvement claims, this source's
   specs, backlogs, source, tests, and dotfiles-ai GitHub state. Read GitHub state
   only with the configured read-only `gh issue list` and `gh pr list` forms. Use Scout for
   authoritative external documentation when useful. Never expose or persist a
   private project, path, content excerpt, or traceable provenance.
4. After synthesis, call `dbsctr_provider_evaluation_save` with the terminal
   manifest digest, rubric `provider-harness` version `1`, digest
   `0c68c7f075667778536925202dd5abe84fd8ecc8b295e43cf98d8565669301ee`,
   and only bounded sanitized findings/recommendations. The helper derives the
   exact cohort. `insufficient` is a truthful result; never loosen eligibility,
   rerun federation, alter cadence, or implement a recommendation automatically.
5. Treat session-to-cycle correlation as supporting evidence. Do not propose
   correlation metadata merely because a link is ambiguous or unavailable;
   require a concrete correctness, safety, reliability, latency, cost, or user
   workflow failure.
6. If the assigned lens is exhausted without a distinct defensible proposal,
   run `dbsctr-rnd lens-result` with the worker ID, planned capture day, terminal
   manifest digest, `--outcome no_yield`, and `--telemetry-json` containing the
   exact non-negative counters `page_count`, `session_count`,
   `review_session_count`, `excluded_review_session_count`, and `source_count`,
   then stop. Never manufacture work.
7. Assign exactly one priority before claiming: P0 for an immediate critical
   safety, security, data-loss, or broad-outage risk; P1 for a concrete high-impact
   correctness, reliability, cost, or operator-workflow failure; P2 for useful
   bounded work without urgent impact; P3 for speculative or low-impact work.
   Present a standalone plain-language context block:
   history scope and page/session counts, the ranked shortlist, the selected
   problem, sanitized evidence, impact, existing behavior, affected interfaces,
   and explicit non-goals. Define unavoidable technical terms; never make the
   operator infer the proposal from question labels.
8. Atomically claim exactly one sanitized proposal and its P0-P3 priority with
   `dbsctr_improvement_claim`. After the claim succeeds, run `dbsctr-rnd
   lens-result` with the same worker, capture day, terminal manifest digest,
   `--outcome yield`, and the same telemetry JSON. Yield makes only this lens
   immediately eligible for another pass; no-yield applies only its adaptive
   backoff. P0 blocks for operator review. P1-P3 enter `discovery` and load
   `discovery` with `autonomous=true` and load `discovery` autonomously.
   Carry the context block into Discovery. Resolve questions from authoritative
   evidence and conservative defaults. Proceed autonomously only when no material
   uncertainty remains and risk is not critical; otherwise block for the operator.
9. After autonomous readiness or explicit operator proceed, persist the exact repository-relative ownership paths
   with `dbsctr_improvement_update`, then call `dbsctr_vm_handoff` with
   `proceed=true`, the worker ID, risk, concise approved context, paths, and
   validation. The visible configured-workspace Build session begins and owns the elevated
   `draft_pr` DBSCTR cycle; the host cycle and VM cycle never share mutable state.
10. Final Push may publish only the feature branch and create a draft pull request
   against the recorded base. Never merge, mark ready, release, or deploy.
11. Final Push records the verified draft PR in the worker ledger. Persist the
   final sanitized result, run `/compact` once, and leave the Herdr tab open for
   the operator.

$ARGUMENTS
