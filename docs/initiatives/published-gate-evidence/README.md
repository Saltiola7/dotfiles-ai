# Integrate the published gate-evidence fix

The gate-evidence repair is already published as [draft #360](https://github.com/Saltiola7/dotfiles-ai/pull/360).
Its standalone cycle and earlier failed records are historical. This one-slice
Initiative exists only to use the [published-feature follow-up](../../specs/dbsctr_v3_lifecycle/features/published-feature-followup.md)
on that same draft. The current default includes the separate Initiative
continuation implementation from [#357](https://github.com/Saltiola7/dotfiles-ai/pull/357).
Both touched the lifecycle CLI. The previous tested merge and its helper
checksum cannot establish the behavior of their combination.

**One writer, one target.** The lifecycle builder reconciles `main` into
the selected published feature, preserves both sets of changelog entries,
records this integration in the lifecycle changelog, and pins the benchmark
fixture to the exact combined `dot_local/bin/executable_dbsctrctl` bytes.
The incoming controller, its tests and its authority remain owned by the
continuation change. Any semantic conflict goes back to the owners.
Independent review may inspect the functions and test results in parallel.
No second writer is needed on this branch.

**Acceptance.** Verify the actual merge parents and explicitly account for
every incoming and resolved path. Exercise tracked-deletion provenance,
literal ignored witnesses, pre-staging refusals, continuation grant and
controller behavior, the benchmark checksum, disposable managed CLI apply
and changed-source publication checks. Reconcile the whole required gate
set to the integrated revision and use fresh Linux CI on the resulting draft.
No package is released. Gate evidence is not merge approval. After protected
delivery, the separately owned Mac apply must compare actual installed state
with that merged revision and report its installed checksum.

**Visual evidence / text equivalent:** published feature and observed default
→ one reviewed merge in the feature → union tests and checksum → same draft
→ current candidate CI → separately approved ordinary merge. The existing
record relates each gate to its run; this handoff adds no schema, host input,
runtime activation or performance claim.
