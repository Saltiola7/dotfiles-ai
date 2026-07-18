---
description: Run one autonomous global-history R&D worker for chezmoi-dotfiles-ai.
---

Operate as one bounded native-Build R&D worker:

1. Load `dbsctr-review`. Name and version the current review lens from this
   command's current rubric, then call `dbsctr_review_history`
   without a `reviewedStatus` filter and follow every continuation. This full
   history pass must include both previously reviewed and unreviewed sessions.
   Save each nonempty sanitized cohort under that same rubric with
   `dbsctr_review_history_save`; do not call `dbsctr_review_complete` or change
   review markers. Reviewed status remains filterable metadata, not a default
   exclusion. After each saved page, reduce it to at most 10 concise issue signals
   and merge only the strongest 20 into a running shortlist before continuing;
   never use context pressure as a reason to skip a page.
2. Synthesize one ranked shortlist across the complete lens pass. Compare each
   concrete issue with durable improvement claims, this source's
   specs, backlogs, source, tests, and dotfiles-ai GitHub state. Use Scout for
   authoritative external documentation when useful. Never expose or persist a
   private project, path, content excerpt, or traceable provenance.
3. Treat session-to-cycle correlation as supporting evidence. Do not propose
   correlation metadata merely because a link is ambiguous or unavailable;
   require a concrete correctness, safety, reliability, latency, cost, or user
   workflow failure.
4. If every configured lens is exhausted without a distinct defensible proposal,
   ask the operator where to research next and stop. Never manufacture work.
5. Before invoking Discovery, present a standalone plain-language context block:
   history scope and page/session counts, the ranked shortlist, the selected
   problem, sanitized evidence, impact, existing behavior, affected interfaces,
   and explicit non-goals. Define unavoidable technical terms; never make the
   operator infer the proposal from question labels.
6. Atomically claim exactly one sanitized proposal with
   `dbsctr_improvement_claim`, then mark it `discovery` and load `discovery`.
   Carry the context block into Discovery before asking questions. Interview until
   at least 95% confident. Wait for the operator to answer and explicitly instruct you to proceed;
   answers alone are not approval.
7. After explicit proceed, persist the exact repository-relative ownership paths
   and cycle ID with `dbsctr_improvement_update`, then begin an elevated
   `draft_pr` DBSCTR cycle for the matching context. Read the non-secret GitHub
   account and repository from `~/.config/dotfiles-ai/chezmoi.toml` and pass them
   to typed begin. Work only in the isolated worktree and complete every gate.
8. Final Push may publish only the feature branch and create a draft pull request
   against the recorded base. Never merge, mark ready, release, or deploy.
9. Final Push records the verified draft PR in the worker ledger. Persist the
   final sanitized result, run `/compact` once, and leave the Herdr tab open for
   the operator.

$ARGUMENTS
