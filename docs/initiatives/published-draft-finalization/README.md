# Recover a verified draft after the default advances

Critical-risk lifecycle source slice. An interrupted Final Push can leave an
exact feature tip published while the record remains `finalizing`. A default
advance then blocks normal Final Push reconciliation, which itself requires an
active record. This slice recovers draft-publication custody only.

Under the existing target lock, verify the authenticated account, native open
draft and same repository and refs. Both PR and feature-ref readback must match
the exact recorded owned tip and clean original checkout. Recheck before local
closure. Derive the qualification base from the unambiguous recorded final
reconciliation, not the PR's cached base. Verify exact owned lineage and required
gate evidence through the existing reconciliation validator, including #374's
evidence semantics. Require the observed default to descend from the qualified
base. Preserve the launch binding, commits, passes, and failed-attempt history.

| Observed state | Allowed result |
|---|---|
| Exact owned tip already published as the same open draft; retained proof valid | Close draft-publication record locally, without a Git push or PR mutation. |
| Feature ref still at approved old prefix | Ordinary publication still requires current-base reconciliation and fresh applicable evidence. |
| Ref and PR disagree, checkout or evidence drifts, default is rewritten, or readback is unavailable | Refuse and preserve `finalizing`. |
| Completion already recorded | Existing idempotent completed result; do not complete twice. |

Text equivalent: authenticate and verify native draft and retained local proof
before writing only the local completion record; otherwise refuse or use the
unchanged ordinary publication path. Neither path grants merge or cleanup
authority. Distinguish prior qualification base from later observed default.

Scope: `dbsctrctl`, published-feature follow-up specification, lifecycle
changelog, focused Git and mocked native publication tests, and benchmark pin.
Verify base advance, replay, no push/PR writes, stale views, invalid or ambiguous
proof, and the unchanged unpublished path. Test with disposable fixtures, not
live credentials or records. Update the owning feature's existing visual
evidence for changed states and boundaries. No CI workflow changes, Auto changes,
live installation, or application to an existing draft follows from this slice.
