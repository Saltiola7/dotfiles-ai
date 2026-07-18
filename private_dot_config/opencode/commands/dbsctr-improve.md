---
description: Run one autonomous global-history R&D worker for chezmoi-dotfiles-ai.
---

Operate as one bounded native-Build R&D worker:

1. Load `dbsctr-review`. Process one unreviewed global page; when none exists,
   process one historical cohort with a lens not recently represented in the
   private ledger. Persist the sanitized result before continuing.
2. Compare defensible proposals with durable improvement claims, this source's
   specs, backlogs, source, tests, and dotfiles-ai GitHub state. Use Scout for
   authoritative external documentation when useful. Never expose or persist a
   private project, path, content excerpt, or traceable provenance.
3. If every configured lens is exhausted without a distinct defensible proposal,
   ask the operator where to research next and stop. Never manufacture work.
4. Atomically claim exactly one sanitized proposal with
   `dbsctr_improvement_claim`, then mark it `discovery` and load `discovery`.
   Interview until at least 95% confident. Wait for the operator to answer and
   explicitly instruct you to proceed; answers alone are not approval.
5. After explicit proceed, persist the exact repository-relative ownership paths
   and cycle ID with `dbsctr_improvement_update`, then begin an elevated
   `draft_pr` DBSCTR cycle for the matching context. Read the non-secret GitHub
   account and repository from `~/.config/dotfiles-ai/chezmoi.toml` and pass them
   to typed begin. Work only in the isolated worktree and complete every gate.
6. Final Push may publish only the feature branch and create a draft pull request
   against the recorded base. Never merge, mark ready, release, or deploy.
7. Record the draft-PR state, persist the final sanitized result, run `/compact`
   once, and leave the Herdr tab open for the operator.

$ARGUMENTS
