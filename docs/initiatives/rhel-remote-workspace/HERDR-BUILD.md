# RRW-007K: downstream Herdr build qualification

**Proposed slice:** `rrw-007k-herdr-build`. **Cycle:** `RRW-007K-HERDR-BUILD`.
Distribution owns the build in `Saltiola7/dotfiles-ai`. The remote-workspace
coordinator owns this scope and the existing INT-088 restore acceptance.
This build-only draft is elevated risk: public build source and an executable
test artifact, with no release, installation pin, or live deployment.

## Contract

- Build `x86_64-unknown-linux-musl` on two independent standard GitHub-hosted
  Linux x86_64 jobs. Emulation, the workstation, and the shared remote
  workspace are not qualification venues.
- Start from Herdr `e8d7d9705a7a2c89cef4dd42079379f05685af87`, the reviewed
  final-save proof patch, Rust/Cargo 1.96.1, Zig 0.16.0, and the Cargo and Zig
  dependency pins. Use a distinct downstream version. Before execution,
  bind the exact source archive, patch, toolchain, dependency manifests,
  build image platform digest, and any native package inputs to reviewed
  build source. Stage verified inputs, then compile offline. No shared
  writable cache, host state, write token, or deployment secret.
- Given identical reviewed inputs, independently build and hash both raw
  binaries. Accept only equal SHA-256 values and matching version/target.
  A mismatch, missing provenance, stale candidate, or failed fixture is
  a block, not permission to pick one binary. Run the disposable startup
  and final-save smoke against the exact matched bytes in a compatible
  Linux fixture; keep the binary, provenance, license and notices as
  time-limited CI test artifacts. No release endpoint or installer uses them.
- Keep implementation limited to build recipe, pinned inputs, patch and
  notices, focused tests, dedicated workflow, and Distribution docs.
  No changes to the existing consumer cycle, installer, stock runtime
  pins, shared service, branch protection, or production environment.
  The existing INT-088 requirements, two edited 50-client boots and
  rollout remain with the consumer and Fork A. No upstream submission.

Use the committed Distribution Engineering Profile and existing publication
checks. Validate recipe syntax, exact patch applicability, input verification
and failure paths before draft CI. Review CI code and artifact custody against
the exact tested candidate. No source from the private coordinator checkout,
fixture identities, or machine paths belongs in the public draft.

## Visual Evidence

Boundary, interaction, state, data/trust, and dependency/deployment are
required and captured in this transition table. Schema is not applicable
(no new durable runtime schema in this slice). Quantitative chart is not
applicable (exact digest equality, not a statistical comparison).

| Owner | Input | Transition | Result |
|---|---|---|---|
| Distribution | Reviewed build definitions and pinned public inputs | Verify and stage inputs for each clean runner | Two independent offline build environments, or refuse |
| Hosted jobs | Same staged input identities | Compile, inspect binary, compare output digests, smoke-test matched bytes | Temporary test evidence, or refuse |
| Consumer owner | Verified producer evidence | Review artifact custody and separately scope distribution | No automatic pin, live rollout, or INT-088 completion |

**Text Equivalent:** Distribution stages verified inputs independently for
both runners. The jobs must produce matching binaries and validate those
exact bytes. A failure blocks reuse. Temporary evidence is not a release.
Distribution updates this table if custody, runner, or handoff rules change.
