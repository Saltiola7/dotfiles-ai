# Reuse proven gate evidence after target reconciliation

Discovery contract, INT-127. Owner: lifecycle maintainer. Apply the existing
[trusted evidence bindings](workflow-evidence-bindings.md) to `reconcile-target`
preview and draft `final-push`, including the published-feature follow-up
route. A merge date or the output paths in an evidence envelope cannot prove
which validations the change affected.

| Gate at the reconciled source | Disposition |
|---|---|
| Complete approved binding, unchanged inputs, requirement/prerequisite closure, authority, argv, toolchain and environment | Retain the original execution ID and time; record an applicability decision for this source, not a fabricated rerun. |
| Changed source/configuration/requirements, invalid custody, or incomplete dependency scope | Report the gate and bounded reason. Revalidate it and its affected dependants. Unbound legacy evidence keeps its original post-reconciliation freshness rule. |
| Runtime-dependent gate | Also require its existing target/artifact identity, approved probe and freshness rules; never treat an untouched source path as deployment evidence. |
| Review/Integrate | Require fresh review of the actual reconciliation merge and covered staged output paths. Retained upstream evidence cannot stand in for this review. |

Preview predicts which checks can be reused and which still require execution;
defer runtime-dependent decisions until their qualified observation. Final Push
rechecks protected target, reviewed lineage and the effective source bindings
under its existing locks. A second target advance invalidates the previous
decision. Preserve failed runs, approved exceptions and ordinary downstream
reopening. This policy neither weakens native PR CI nor implicitly enrolls an
old cycle into a new evidence policy.

For an enrolled draft cycle, a `diverged` preview adds `gate_evidence` keyed by
gate. A retained prediction is provisional: it compares the current binding
and incoming paths, not the eventual conflict resolution. Final Push checks
the actual reconciled tree and its Review/Integrate Gate Commit. The review
must be a fresh execution covering the changed paths, not a reference to an
earlier run. Runtime-dependent predictions require a probe before delivery.

Use real disposable Git merges with one bound unaffected gate, a changed
prerequisite and dependent, an unbound gate and an expired runtime observation.
Verify exactly which reruns remain, reject a stale merge review, then complete
the positive path with fresh evidence. Exercise both draft reconciliation
callers and an unchanged legacy fixture.

## Visual Evidence

State and data/trust: **required**, the table maps trusted bindings and
review authority to dispositions. Boundary, interaction and schema: **not
applicable** as separate visuals; the existing binding contract owns those
interfaces. Dependency/deployment: **not applicable**, no topology change.
Quantitative: **not applicable**, no claimed runtime saving.

**Text Equivalent:** Only proven unchanged validation inputs retain old
execution credit; unknown or changed dependencies need revalidation, and the
merge itself always needs review. The lifecycle maintainer updates the table
when the applicable proof or gate rules change.
