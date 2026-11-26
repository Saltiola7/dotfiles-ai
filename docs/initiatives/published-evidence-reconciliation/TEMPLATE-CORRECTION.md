# Preserve approved template evidence in isolation

Correct the required CI regression on [draft #368](https://github.com/Saltiola7/dotfiles-ai/pull/368)
at `2af75b4940f6a4f82325d9f8f85e29e3af6a9e16`. Preserve the completed R2
record and [failed partition](https://github.com/Saltiola7/dotfiles-ai/actions/runs/45721299846/job/139580011249).

- Given a regular `.env.template` whose bytes and index match the recorded
  upstream, isolated validation can read the exact approved bytes and earn
  evidence credit only if all existing checks pass.
- Given a dirty, unproven, or substituted template, an unsafe file, or capture
  drift, refuse evidence credit. Keep existing secret-path refusals, selected
  ignored witness checks, and pending merge provenance intact.

Keep live upstream admission authoritative. Inside the disposable checkout,
verify the captured template against the identity already established on the
live side. Do not copy the Cycle Record, upstream configuration, or credentials
into the sandbox. Do not run validation in the live checkout as a fallback.

Corrective scope: lifecycle CLI, focused template regressions, matching
benchmark fixture checksum, and lifecycle changelog. Reconcile the protected
default without separate workflow or comparator edits. Run the existing
large-inventory template test and negative provenance tests, plus affected
isolation, witness, and merge-provenance regressions. Requalify all required
local gates, including disposable apply and operation only, then publish to
the same draft for fresh exact-candidate CI. Advisory shadow results do not
substitute for required CI. No live activation or merge consent.
