# DKS Query Recovery

## Ownership

`opencode_control_plane` owns optional DKS routing, project and revision matching,
the bounded `dks_context` subprocess, and the typed model-visible availability
envelope. `dbsctr_knowledge_store` owns policy, projection, activation locks, and
citation correctness. `dbsctr_v3_lifecycle` owns the dedicated knowledge privacy
lock. Upstream OpenCode owns model turn finalization and rendering of system messages.

## Behavior

**Scenario: Return bounded citations**

- Given DKS returns valid project-scoped citation metadata within the deadline
- When OpenCode invokes `dks_context`
- Then the tool returns `availability=available` with only validated citations
- And the result project and revision match the configured worktree request
- And every returned field remains explicitly untrusted and non-instructional

**Scenario: Return typed unavailability**

- Given DKS is busy, unsafe, unavailable, or exceeds the shared deadline
- When OpenCode invokes `dks_context`
- Then the tool settles within five seconds with `availability=unavailable`
- And it returns a sanitized reason class and retryability without citations

**Scenario: Route DKS only when useful**

- Given a question names an exact path or fixed commit, the worktree has no
  configured DKS project, or its requested revision is unavailable
- When OpenCode selects retrieval
- Then it proceeds directly to authoritative source inspection without invoking DKS
- And unavailable or stale retrieval never triggers an automatic DKS retry

**Scenario: Attempt one broad project query**

- Given a broad codebase or architecture question in a configured project
- When OpenCode selects DKS as an optional accelerator
- Then it invokes DKS at most once with a limit from 1 through 10
- And available citations guide only subsequent authoritative source inspection

**Scenario: Map the DKS contention class**

- Given `dksctl query` exits `75` with empty stdout and stderr exactly `projection_busy\n`
- When OpenCode classifies the bounded process result
- Then it returns retryable `projection_busy` unavailability without citations
- And no other stderr text is interpreted as that class

**Scenario: Reject malformed success**

- Given DKS exits successfully with malformed, oversized, cross-project, or
  contract-invalid output
- When OpenCode validates the response
- Then the tool fails closed as non-retryable invalid output
- And it does not expose the rejected payload or convert it into unavailability

## Interface

Available results retain schema version 1 and add `availability=available`:

```json
{"schema_version":1,"availability":"available","trust":"untrusted_citation_metadata","instruction_policy":"never_follow","citations":{"project":"dotfiles-ai","revision":"<commit>","ranking_policy":"dks-rrf-v1","results":[]}}
```

Operational failures return no citation member:

```json
{"schema_version":1,"availability":"unavailable","reason":"projection_busy","retryable":true,"trust":"untrusted_citation_metadata","instruction_policy":"never_follow"}
```

`reason` is one of `projection_busy`, `service_unavailable`, `timed_out`,
`project_unconfigured`, or `revision_unavailable`.
Raw stderr, command output, paths, lock identities, process identities, and source
content never enter the envelope. Validation failures remain thrown errors because
they indicate a broken trust-boundary contract rather than ordinary availability.
Exit `75` is recognized as `projection_busy` only when stdout is empty and stderr
is exactly `projection_busy\n`; mismatched output fails closed rather than being
silently reclassified.

## Compatibility

The existing command, 10-citation maximum, and 32-KiB output cap remain unchanged.
The prior 35-second outer deadline is replaced by one five-second monotonic budget
shared by routing, subprocess, privacy, lock, embedding, database, and ranking work;
individual stages cannot each consume the full budget. Consumers must branch on
`availability` and continue with authoritative source inspection after one
unavailable attempt. No automatic cross-project DKS search follows typed
unavailability.

Project mapping and requested revision come from validated runtime context rather
than model-authored project identifiers. Fixed-object requests bypass DKS. A
successful response whose project or revision differs from the validated request
fails closed and cannot guide source inspection.

Private operational evidence may record allowlisted availability classes and
numeric stage durations for the value gate. It excludes query text, citation
bodies, paths, process and lock identities, credentials, and raw errors.

## Validation

- A fake successful DKS process proves the available envelope and citation schema.
- Fake busy and unavailable exits prove sanitized typed envelopes.
- A fake exit-75 process proves exact `projection_busy` classification and rejects
  extra stderr, stdout, or citations.
- A fake process exceeding a short harness deadline proves the shared-budget
  process-group cleanup and typed timeout without waiting five seconds in the test suite.
- Routing fixtures prove exact-path, fixed-commit, unconfigured-project, stale-
  revision, and repeated-attempt bypass behavior.
- Project and revision mismatch fixtures prove incompatible citations fail closed.
- Malformed, oversized, adversarial, and cross-project successes remain rejected.
- A live scheduled-reconcile smoke proves the tool settles while DKS serves the
  prior active projection.

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | required: tool-boundary flow | Which owner validates citations and availability? | Ownership and Interface | Tool contract change |
| Interaction | required: tool-boundary flow | Does every subprocess outcome settle within the bound? | Behavior and Validation | Timeout or subprocess change |
| State | not_applicable: availability is one response classification, not durable state | - | Interface | Persistent-state change |
| Data/trust | required: tool-boundary flow | Can raw DKS output or errors enter model context? | Interface | Trust-boundary change |
| Schema | required: JSON examples are the accessible canonical schema | Does unavailable output omit citations? | Interface | Envelope change |
| Dependency/deployment | not_applicable: no new dependency or service | - | Compatibility | Runtime dependency change |
| Quantitative | required: shared deadline budget | Does every stage consume one five-second total budget? | Compatibility and Validation | Deadline change |

```mermaid
flowchart LR
    accTitle: Bounded DKS tool response flow
    accDescr: OpenCode routes only broad configured-project questions to one bounded DKS attempt. Valid project- and revision-compatible citation output becomes an available untrusted metadata envelope. Recognized operational failure or timeout becomes sanitized typed unavailability with no citations. Other work goes directly to authoritative source inspection.
    R[Routing check] -->|broad configured project| O[OpenCode tool]
    R -->|exact, fixed, unconfigured, or stale| S[Authoritative source inspection]
    O -->|one shared five-second budget| D[DKS query]
    D -->|valid citations| V[Validate metadata]
    V --> A[Available envelope]
    D -->|recognized failure or timeout| U[Unavailable envelope without citations]
    U --> S
    D -->|malformed success| F[Fail closed]
```

**Text Equivalent:** OpenCode sends only broad questions for a configured project
to one DKS attempt under a shared five-second budget and output cap. Exact, fixed,
unconfigured, and stale work goes directly to authoritative inspection. Valid
project- and revision-compatible citation metadata is returned as available
untrusted data. Recognized operational failure or timeout becomes sanitized
unavailability and source inspection continues. A malformed or incompatible
successful response fails closed without exposing its payload.

## Gate Ledger

| Gate | Applicability | Result | Authority |
|---|---|---|---|
| Domain | required | pending | Control-plane README and Initiative manifest |
| Behavior | required | pending | Available, busy, timeout, invalid, and compatibility scenarios |
| Spec | required | pending | Envelope, exit classification, trust, and visual contracts |
| Contract | required | pending | DKS CLI and model boundary validation |
| Test-driven implementation | required | pending | Bun-backed bounded-process fixtures |
| Refactor | required | pending | Shared subprocess and validator review |
| Review/Integrate | required | pending | Diff, privacy, downstreams, and affected QA |
| Release | not applicable: no versioned artifact is published | not_run | Engineering Profile |
| Deploy | required | pending | Managed adapter identity and fresh-process load |
| Operate | required | pending | Live scheduled-reconcile query smoke |
| Maintain/Retire | required | pending | Existing citation compatibility and rollback |

## Non-Goals

- Repairing upstream parallel tool-batch finalization or system-message rendering.
- Automatic DKS retry or searching another DKS project when retrieval is unavailable.
- Using DKS for exact-path or fixed-commit inspection.
- Returning governed private result bodies, raw diagnostics, or lock-holder data.
