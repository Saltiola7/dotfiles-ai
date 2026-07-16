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

1. Call `dbsctr_review` repeatedly until its continuation is empty. Start from
   V3.3 isolated-worktree adoption and include DBSCTR, Discovery, QA, parent,
   child, fork, reviewer, and builder sessions selected by the helper.
2. Prioritize blocked candidates, then abandoned, dormant, active, and completed
   candidates. Treat inferred state and cross-cycle cost attribution as caveats.
3. Use only returned sanitized metadata. Do not quote, copy, or persist a raw
   transcript or raw transcript excerpt, tool payload, machine path, email
   address, credential, or URL.
4. Rank findings by correctness and safety, then latency and cost, then
   completion reliability. Include cycle scorecards, trend comparisons,
   uncertainty, and bounded improvement proposals.
5. Optional user notes may inform a finding but are not persisted verbatim.

## Complete

After the full report is successfully formed, call `dbsctr_review_complete` for
each scan page with that page's exact session IDs, cycle IDs, digest, limit, and
cursor plus the concise structured findings. Each permission-gated operation
writes one private review report and review marker. If any completion is denied
or fails, return the report and identify the pages not marked reviewed.

Completion is not approval. Every proposed fix requires user approval and a
separate DBSCTR cycle. Never perform automatic remediation.

## Report

Return ranked findings, scorecards, trends, caveats, reviewed identifiers by
count, completion status, and separately approvable cycle proposals. Raw local
evidence remains private and non-authoritative.
