# Python Policy Boundaries

Status: approved staged context map; first PM source slice in Discovery. This
Initiative is not an implementation, runtime activation, or lifecycle registration.
Coordinator and home repository for every context: `Saltiola7/dotfiles-ai`.
The existing dotfiles maintainer owns the plan; each existing context retains its
domain, contracts and validation authority. Do not create a new Python framework
or a shared cross-context state engine.

## Outcome And Approved Decisions

The PY-07 audit recommendation is to make pure policy and runtime-validated
boundaries reviewable, typed, and independently testable without changing CLI,
serialization, privacy, compatibility, or operational behavior. The operator
approved the staged map, affected-source/test ty, and test-only Hypothesis.

The [manifest](MANIFEST.json) assigns every material statement an `INT-NNN`
identity. This document owns the context map and sequencing. The first
[PM feature](../../specs/pm_kernel/features/python-policy-boundaries.md), existing
[PM profile](../../specs/pm_kernel/PROFILE.md), and
[source applicability plan](PM-SOURCE.plan.json) own its concrete interfaces,
tools, compatibility and acceptance. Existing Product Intent remains unchanged.

## Context Map And Serial Delivery

| Existing context | Approved responsibility | Prerequisites and disposition |
|---|---|---|
| `pm_kernel` | Pure restricted-frontmatter and sanitized-envelope validation boundaries; honest raw/approved types and meaningful properties inside standalone `pmctl`. | First source slice; independent of the other repairs. |
| `dbsctr_v3_lifecycle` | Repository-identity types/properties and remaining approved policy seams. | Discover after PY-02 gate-evidence invalidation is integrated and its actual remaining gaps are reconciled. Gate-transition extraction already belongs to that repair. |
| `continuous_validation` | Remaining storage-policy types/properties and affected consumers. | Discover after PY-03 journal-storage and PY-04 capacity work establish the accepted boundary. No competing record-store redesign. |
| `dbsctr_knowledge_store` | Pure offline chunking/ranking properties in its existing retained source. | Deferred until active slices finish; no reactivation, model execution, service or projection access. |
| `dotfiles_ai_distribution` (adjacent owner) | Existing installation/import/feature-gating contract. | Consulted compatibility owner; first slice adds no runtime module or target. A future layout/activation change requires its own approved scope. |

Home repository is the coordinator for each row. No code or context authority
is transferred to the coordinator. The primary discovers unfinished slices
serially; read-only research and explicitly owned document helpers confer no
independent Build or registration authority. Writers touching shared CLI or
environment files serialize even where conceptual policies are independent.

Prerequisite-readiness slices in the manifest only reconcile external repair
delivery evidence; they do not implement, duplicate, approve, or claim delivery
of PY-02/PY-03/PY-04. Their states stay blocked until merged source and relevant
acceptance prove the prerequisite. Later source slices cannot become ready by
changing those labels alone. PM source has no dependency on those unfinished
repairs. DKS remains an explicitly deferred context and release group.

## First Source Slice

`pm-source` owns the feature, profile, minimal PM README pointer, root test/checker
metadata, standalone PM policy changes and affected Python tests. No other
runtime or source file is selected. Keep pure policy in the existing executable;
source-loader tests and installed command resolution remain compatible. Keep
file reads, JSON decoding, byte limits/digests, SQL, subprocesses, Git and Jira
in their existing imperative shell.

Parsing establishes syntax only; source-envelope safety and source-contract
approval are distinct runtime guarantees. Annotations do not prove them. Preserve
accepted/rejected inputs, exception classes/text/order, finding order, original
byte hashes, serialization and all nine source contracts. Any exposed behavior
defect requires separate characterization and scope; it cannot become cleanup.

The profile selects pinned ty and Hypothesis in the existing root test group,
without application dependencies or a runtime-floor increase. Analyze complete
affected files, including the extensionless implementation, existing/new tests,
and any changed Python fixtures. Setup/coverage, diagnostic cleanliness and
unknown/suppression exposure are separate outcomes. Do not expand this choice
into a whole-repository typing migration or silently exclude noisy files.

Properties use bounded synthetic strategies, independent invariants and explicit
boundary examples. Retain useful existing real-Git, permission, recovery and
adapter-fake examples. No PM file inventory, private lifecycle evidence, Jira
content or credentials become generator inputs. Discovery and lifecycle remain
ticket-blind; this work reads PM source/specifications, never actual PM tickets.

## Dependencies And Deferred Design

- PY-02 owns gate-result mutation and downstream invalidation. Reuse its landed
  shared policy and tests; later identity work still serializes writes to the
  standalone lifecycle helper.
- PY-03/PY-04 own record serialization, aggregate replay and observation-capacity
  reservations. Preserve the runner compatibility facade and exception identity
  for checkpoint/review consumers. Reconcile the effective-code cache fingerprint
  before any future extraction into additional modules: hashing only the runner
  must not leave changed policy outside cache identity.
- DKS owns its canonical JSONL export and injected-token-counter chunking/ranking.
  PM owns a different sanitized-envelope wrapper and restricted frontmatter.
  Do not unify them. Actual tokenization is an I/O adapter, not a pure counter
  assumption. Source reconstruction applies to source chunking, not omitted
  Markdown headings/blank regions.
- Module relocation, a new packaging layout, new runtime dependencies, framework
  adoption, schema changes, stricter validation, broad annotation cleanup,
  performance optimization and runtime reactivation are outside the first slice.

## Evidence And Readiness

Public source baseline inspected: `12f5959701f8c075699b69ee5b4bac2cc5c2c535`.
The original audit used the earlier tree at `3e68301`; later source and parallel
repair boundaries were reconciled before choosing this independent first slice.
No old test or audit result is claimed as a new implementation pass.

PM README, PROFILE, PRODUCT and CHANGELOG were reviewed. Only README/profile
truth about this selected source slice changes. Product Intent remains valid;
CHANGELOG gets a completed implementation entry only after that cycle closes.
Other context profiles/specifications were consulted for boundaries and remain
unchanged; later Discovery must revisit their final post-repair source.

The existing publication/instruction authority must inspect the complete
candidate, including new indexed documentation, before receipt or preflight.
Use `dbsctrctl initiative-check` after material manifest changes. A ready first
slice requires its complete committed document closure, selected commands and
no material unresolved scope/contract/tool decision. Actual tool resolution,
diagnostic census, property execution and runtime behavior are Build evidence,
not Discovery accomplishments. No gate exception is granted.

Before launch, a Build primary obtains a fresh receipt and runs `begin --preflight`
against one clean Worktrunk-owned code-only checkout at the approved fetched base.
Preserve this Discovery authority and import its complete document closure into
the implementation PR. No preliminary documentation publication, conversation
move, synthetic session identity, or reset of retained authority is required.
Preflight establishes feasibility, not consent. A later exact digest-bound
approval is required before registration; approval of this map and tools is not
registration approval. Private receipt/preflight details stay outside Git.

## Visual Evidence

| Concern | Decision and canonical representation |
|---|---|
| Boundary | required: Context Map ownership table above. |
| Interaction | required: serial source/repair/launch handoff described in Serial Delivery and Evidence And Readiness. |
| State | required: the manifest's ready PM, blocked prerequisite/later-source, and deferred DKS dispositions; table below. |
| Data/trust | required: first-slice ownership and the directional trust table in the PM feature; no private content imported into this Initiative. |
| Schema | not_applicable: no new runtime schema; existing manifest and context contracts remain canonical. |
| Dependency/deployment | required: Context Map prerequisite table and first-slice source-only boundary above. |
| Quantitative | not_applicable: no measured speedup, coverage percentage, or comparative claim. |

| Handoff | Required proof | Resulting authority |
|---|---|---|
| Approved map to first source specification | Complete PM contracts, profile, commands, population and publication checks. | Specification readiness only. |
| Specification to launch preflight | Committed closure, fresh receipt, exact base and native target. | Feasibility and a launch digest only. |
| Preflight to registration | Explicit approval of that exact current launch digest. | One bounded registered source cycle. |
| Source to managed use | Reviewed merged source plus separately scoped installation/operation evidence. | Only the specific approved managed change. |
| Repair prerequisite to later Discovery | Actual integrated repair source and acceptance evidence. | Remaining boundary design may proceed; no automatic source readiness. |

**Text Equivalent:** Each existing context retains its policy. PM starts without
waiting for other repairs. Lifecycle and validation must consume their respective
repair outcomes before later Discovery; DKS stays deferred and offline. Source
specification, preflight feasibility, registration, source delivery and managed
use are separate proofs. No transition confers the next transition's authority.
Canonical sources: this map, the manifest, and the PM feature. Owner: coordinating
maintainer. Update trigger: changes to approved scope, dependencies or handoff.
