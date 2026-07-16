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
   ceiling, and part ceiling. Pass that same snapshot and both row ceilings with
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
row ceilings, limit, and cursor plus the concise structured findings. Each permission-gated operation
writes one private review report and review marker. If any completion is denied
or fails, return the report and identify the pages not marked reviewed.
Skip completion for pages with no candidate IDs.

Detailed reports expire after 90 days while compact opaque reviewed-ID
tombstones remain until explicit forget. Scans never prune or write this state;
completion and maintenance serialize changes under the private review lock.

Completion is not approval. Every proposed fix requires user approval and a
separate DBSCTR cycle. Never perform automatic remediation.

## Report

Return ranked findings, scorecards, trends, caveats, reviewed identifiers by
count, completion status, and separately approvable cycle proposals. Raw local
evidence remains private and non-authoritative.
