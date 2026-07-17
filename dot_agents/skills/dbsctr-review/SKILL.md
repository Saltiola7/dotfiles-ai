---
name: dbsctr-review
description: Review private local DBSCTR session evidence and propose separately approved lifecycle improvements.
trigger: /dbsctr-review
---

# DBSCTR Review

## Outcome

Turn unreviewed local DBSCTR observability into a sanitized report. Never change
repository artifacts, cycle status, gates, code, or backlogs during review.

## Scan

1. Call `dbsctr_review` for the first page and retain its `snapshot`, session
   ceiling, part ceiling, database digest, and exclusion digest. Pass that same snapshot and both row ceilings,
   plus both digests, with
   every continuation until it is empty. Continue when a page
   has no candidates but still has a continuation. Start from V3.3
   isolated-worktree adoption and include DBSCTR, Discovery, QA, parent, child,
   fork, reviewer, and builder sessions selected by the helper.
2. The helper orders each page by blocked, abandoned, seven-day dormant
   attention, completed, active, and unknown urgency. Report every returned
   cycle state independently; never collapse multiple cycles into one state or
   treat dormant attention as lifecycle authority. Candidates without a matched
   Cycle Record are unknown. Never infer state from session prose. Treat
   cross-cycle cost attribution as a caveat.
3. Use only returned sanitized metadata. Do not quote, copy, or persist a raw
   transcript or raw transcript excerpt, tool payload, machine path, email
   address, credential, or URL.
4. Rank findings by correctness and safety, then latency and cost, then
   completion reliability. Include cycle scorecards, trend comparisons,
   uncertainty, and bounded improvement proposals.
5. Optional user notes may inform a finding but are not persisted verbatim.

## Complete

After the full report is successfully formed, call `dbsctr_review_complete` for
each scan page with that page's exact session IDs, cycle IDs, digest, snapshot,
row ceilings, database digest, exclusion digest, limit, and cursor plus the
concise structured findings. Each permission-gated operation
writes one private review report and review marker. If any completion is denied
or fails, return the report and identify the pages not marked reviewed.
Skip completion for pages with no candidate IDs.

Detailed reports expire after 90 days while compact opaque reviewed-ID
tombstones remain until explicit forget. Scans never prune or write this state;
completion and maintenance serialize changes under the private review lock.

## History and replay

Privacy boundary: no mode argument means the unreviewed operational inbox. A history request calls
`dbsctr_review_history`, defaults to the latest 100 including reviewed sessions,
and follows its continuation with the same snapshot, row ceilings, and database
digest. Use composable filters only to narrow sanitized metadata and allowlisted
aggregate counts. Never request or reconstruct raw transcript,
tool payload, path, URL, command argument, or prose from history.

`dbsctr_review_history_save` is a standing local write: save only a named,
versioned rubric and a strict sanitized cohort after review. Pass the history
digest, snapshot, both row ceilings, and database digest so still-live evidence
can be revalidated and backfilled without raw content. It stores immutable
cohort evidence so replay remains available after live/archive removal; it does
not mutate reviewed tombstones. Builders are denied history save and all direct
helper forms. `review-forget` removes session evidence and dependent cohorts and
reports. Malformed history state fails closed.

A replay request calls `dbsctr_review_history` with the saved report ID and
uses only that report ID plus its cursor for continuation. It evaluates the exact
immutable cohort under the new named rubric version, never substitutes a fresh
query, and never changes operational inbox tombstones.

Completion is not approval. Every proposed fix requires user approval and a
separate DBSCTR cycle. Never perform automatic remediation.

## Report

Return ranked findings, scorecards, trends, caveats, reviewed identifiers by
count, completion status, and separately approvable cycle proposals. Raw local
evidence remains private and non-authoritative.
