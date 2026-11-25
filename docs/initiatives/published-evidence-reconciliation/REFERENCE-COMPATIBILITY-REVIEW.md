# #360: evidence reference compatibility after #363

**Discovery reopened.** In the staged reconciliation against
`4c8f037a28661fa6ff8019c923c804d43d8762d0`, the schema-6 reader admits both
parents' fields. The evidence-reference consumer in
`dot_local/bin/executable_dbsctrctl` still calls the old absence helper
signature and expects a bare absence map. Source review shows that
an otherwise eligible reference cannot reach ledger publication. Adding
the missing argument alone does not fix the returned envelope shape.

The reference path also captures output paths through the generic helper
and checks only predecessor disposition. Review how reference issuance
and validation should share the approved literal-path and predecessor
proof rules without granting credit for stale executions, aborted merges,
or ignored paths outside the existing exception.

**Proposed bounded remediation:** preserve both parent contracts, validate
the proof envelope through the same custody rules, and keep reference
admission fail-closed. Retain an ordinary reference positive, a schema-6
round trip with both evidence types, and explicit cases for merge-only
deletion, literal `.dbsctr/` witnesses, and invalidated merge predecessor
evidence. Do not assume that accepting a stored record makes its evidence
eligible for gate credit. If either owner excludes a combined path, require
an explicit refusal rather than a crash, malformed record, or silent pass.
Review writable scope before adding regression files.

The staged candidate and prior evidence remain in custody. No publication,
rollout, or Auto behavior change follows from this review.
