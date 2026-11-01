# Python Policy Boundaries

Status: approved Discovery contract; implementation and runtime qualification are pending.
Owner: dotfiles-ai maintainer. Risk: elevated. Delivery: source-only draft PR first.

## Purpose And Authority

This is the first PM Kernel slice of the approved staged PY-07 policy-boundary
map. It makes existing pure parsing and validation policies explicit and typed
inside the standalone `dot_local/bin/executable_pmctl`. The desired outcome is
reviewable runtime trust transitions and meaningful property evidence while
preserving the behavior of directly invoked PM commands.

[PROFILE.md](../PROFILE.md) supplies context defaults;
[PRODUCT.md](../PRODUCT.md) supplies durable users and outcomes;
[README.md](../README.md) remains authoritative for PM behavior and interfaces.
The coordinating Initiative owns slice dependencies and launch readiness. This
feature does not authorize lifecycle registration, PM ticket access, deployment,
Jira activity, or a new reporting workflow.

The staged map starts here. Lifecycle identity follows PY-02; continuous
validation follows PY-03/PY-04. DKS work is deferred while offline. This slice
does not make those adjacent contexts prerequisites for standalone PM parsing.

## Scope And Non-Goals

The source change is limited to the existing `scalar`, `frontmatter`,
`safe_envelope`, `validate_envelope_contract`, and `validate_envelope_field`
policies, their type-bearing data representations, and the minimal call-site
wiring needed to establish those boundaries. The policies remain in the existing
extensionless executable; no importable runtime package or installed companion
module is introduced.

Filesystem reads, JSON decoding, raw-byte size checks, digest calculation,
subprocess invocation, Git access, Jira access, SQL assembly, projection, and CLI
serialization stay in the imperative shell. Ticket identity, dates, completion,
relations, dependency graph checks, and inventory behavior remain existing rules;
they are not newly generalized into this first policy slice.

No new schema version, YAML grammar, sanitization rule, source contract, CLI
option, dependency at runtime, database migration, service, cache, telemetry,
repository-wide typing migration, or automatic PM invocation is in scope.
Hypothesis is test-only. The installed `pmctl` remains Python-stdlib-only.

## Affected Population And Environments

The independent affected-file inventory must include these whole files, rather
than counting only annotated functions or matching `*.py` discovery:

| Artifact | Role and required treatment |
|---|---|
| `dot_local/bin/executable_pmctl` | Extensionless production Python; analyze the entire file explicitly. |
| `tests/test_pm_kernel.py` | Existing PM behavior and shell-integration coverage; analyze the entire file. |
| `tests/test_pm_kernel_policies.py` | Proposed pure policy properties and counterexample regressions; analyze the entire new file. |
| Any changed Python fixture or helper | Add to the same inventory before acceptance, including extensionless Python fixtures when changed. |
| Root `pyproject.toml` and `uv.lock` | Root test/checker environment authority; implementation may update only the approved test/checker configuration and lock. |

The root project declares Python `>=3.12`, no application dependencies, and a
`test` dependency group. PM Kernel supports macOS and configured Fedora Lima
workspaces. This slice uses that root environment and existing runtime/platform
commitments; it does not create a nested project or silently raise the minimum
Python version. Type-checking targets and test interpreter evidence must make
the Python 3.12 compatibility floor explicit.

The [profile's selected tool contract](../PROFILE.md#selected-typing-and-property-authorities)
binds the inventory, `ty==0.0.95`, `hypothesis==6.170.14`, exact commands, root
environment, settings, evidence location and passing criteria. Explicit CLI paths
include the extensionless implementation. New fixtures expand coverage rather
than becoming implicit exclusions. Implementation resolves the approved root
test dependencies and lock before running those commands; Discovery does not
install them or claim they pass.

Coverage evidence separates completed analysis, diagnostic cleanliness, and
`Any`/unknown/suppression exposure. Establish the inventory and conflict census
before broad annotation work. Successful checker setup may report diagnostics;
it does not satisfy a required passing typing gate. Whole-file analysis cannot
be replaced by function-level exclusions. Any exception needs explicit lifecycle
authority, rationale, owner, and review condition.

## Domain Language And Trust Transitions

| Term | Guarantee |
|---|---|
| Raw text | Untrusted decoded ticket text supplied by the shell. |
| Parsed frontmatter | Syntax accepted by the existing restricted parser, plus its exact normalized body; no ticket-schema or domain-validity guarantee. |
| Raw envelope | Untrusted result of the existing JSON decoder; an annotation alone grants no validity. |
| Safety-approved envelope | Existing recursive content policy and top-level shape checks succeeded. |
| Source-contract-approved envelope | Safety checks and the existing selected source/version payload checks succeeded. |
| Source bytes | Original envelope input bytes retained by the shell for size and digest identity. |

Conceptual interfaces are `text -> parsed frontmatter and body`,
`raw envelope -> safety-approved envelope`, and
`selected source plus safety-approved envelope -> source-contract-approved
envelope`. These describe proof obligations, not required function names or
source stubs. Existing helper names may remain compatibility adapters.

The concrete domain uses `ParsedFrontmatter(values, body)`. Parsed scalars include
the existing empty-list value, and block-list values can therefore include an
empty list; no stronger ticket validity is implied. `SafetyApprovedEnvelope`
retains the original mapping and the checked integer schema version, string
source ID and dictionary payload. It makes no new string/type promise for values
that existing equality checks alone accepted. `SourceApprovedEnvelope` binds that
safety proof to the selected source while exposing the same original mapping.
Proof objects are internal policy results and never replace payload containers
or appear in serialized output.

Raw and approved representations must be distinguishable to ty. Raw boundaries
use an honest broad input type and explicit narrowing; they must not be declared
approved through `Any`, unchecked casts, assertions, `TypedDict` construction, or
other annotation-only claims. Approved types state only predicates actually
checked at runtime. They preserve current scalar value types and optionality
without claiming that parsed frontmatter is a fully valid ticket.

The runtime boundary must establish each advertised predicate before returning
its approved value. A type checker establishes static consistency; it does not
validate file contents, sanitize private data, prove a digest, authorize an
external operation, or replace runtime checks. No new coercion, default filling,
field dropping, or reconstruction may alter downstream serialization.

Keep original scalar/container objects across the exact built-in type checks;
proof wrappers cannot replace those objects before validation. Preserve direct
`SourceFileLoader` imports without assuming that tests registered the module in
`sys.modules`; any internal type representation must pass that existing import
contract on supported Python versions.

## Concrete Interfaces

The standalone file owns these pure interfaces:

```python
def scalar(value: str) -> ParsedScalar: ...
def parse_frontmatter(text: str) -> ParsedFrontmatter: ...
def approve_envelope_safety(value: object) -> SafetyApprovedEnvelope: ...
def approve_envelope(source: str, value: object) -> SourceApprovedEnvelope: ...
```

`parse_frontmatter` returns named `values` and `body` fields. The legacy
`frontmatter` adapter returns an ordinary tuple of those same values and body.
`approve_envelope_safety` performs the existing recursive and shape checks before
constructing its proof; `approve_envelope` first rejects unsupported source
selections, then obtains safety approval and runs the existing selected-source
contract before constructing its distinct proof. Each envelope proof retains the
original dictionary through `.value`; source approval also identifies `.source`.
Proofs are internal synchronous results, not persistent schemas or serialized
payloads. Consumers must not mutate an approved value between checking and use.

Legacy `safe_envelope`, `validate_envelope_contract`, and
`validate_envelope_field` retain their direct-call behavior and `None` success
returns. In particular, direct source-contract validation does not add safety or
source-selection checks. The shell consumes a parsed result for ticket checks
and a source-approved result for envelope projection; it retains all I/O and raw
bytes. Spec-phase stubs are intentionally incomplete and remain unwired until
runtime validation and regression evidence are in place.

## Compatibility Contracts

1. Preserve the accepted and rejected input population, current exception classes
   and error text, validation order, finding codes/order, CLI exit status,
   stdout/stderr ownership, and JSON output shape. Existing incidental failures
   must not become silent success or be normalized during this extraction.
2. Preserve scalar interpretation, restricted block-list syntax, duplicate-key
   refusal, delimiter handling, body normalization, and quote behavior. Do not
   adopt a general YAML parser or tighten existing edge cases as cleanup.
3. Preserve all nine current envelope source contracts, available/unavailable
   branches, exact runtime type checks, optional fields, byte-length bounds,
   list limits, nested allowlists, and recursive forbidden-content detection.
   Source allowlists and field maps remain canonical existing data.
4. Preserve envelope shell order: read source bytes, reject inputs above 1 MiB,
   decode JSON, check the selected source, run safety validation, run source
   contract validation, then compute the original-byte SHA-256 and serialize.
5. Preserve `json.dumps(value, sort_keys=True, separators=(",", ":"))` and SQL
   stdin behavior. Equivalent decoded JSON with different source whitespace may
   have equal canonical payloads and different source-byte digests.
6. Preserve standalone execution, direct source-loader imports used by tests,
   help/CLI interfaces, optional PostgreSQL operation, and PM/lifecycle authority
   separation. Importing or calling a pure policy performs no I/O.

The baseline source deliberately remains authoritative for compatibility quirks,
including `bool` versus `int` differences between checks, numeric parsing, and
unusual quote handling. A discovered weakness receives a separate decision and
regression proposal; this slice cannot quietly strengthen the contract.

## Behavior

**Scenario: Retain legacy helper compatibility**
- Given a caller using `frontmatter`, `safe_envelope`, or source/field validators
- When the typed policy boundary is introduced
- Then `frontmatter` still returns an ordinary two-item tuple
- And successful legacy envelope validators still return `None`.

**Scenario: Preserve characterized edge behavior**
- Given single-quoted input without a closing quote or a block list containing `[]`
- When frontmatter parsing runs
- Then existing quote slicing and nested empty-list results remain unchanged.
- Given an unhashable availability, a lone surrogate, or a nonfinite metric
- When the existing corresponding policy runs
- Then its prior exception or acceptance is retained rather than silently repaired.

**Scenario: Parse without granting ticket validity**
- Given text accepted by the existing restricted frontmatter grammar
- When the pure parser runs
- Then it returns the same scalar/list values and normalized body
- And required ticket fields, identity, and completion remain separately checked.

**Scenario: Preserve deterministic rejection**
- Given a duplicate key, unsupported scalar/structure, missing delimiter, or
  unterminated frontmatter
- When the policy boundary runs
- Then it raises the same failure at the same validation stage
- And the calling shell preserves its finding or CLI error behavior.

**Scenario: Approve an envelope only after both policies**
- Given a decoded envelope and an existing supported source selection
- When safety and source-contract validation both succeed
- Then the shell receives a source-contract-approved value
- And a safety-only value cannot be passed as if source-contract-approved.

**Scenario: Reject unsafe content before projection**
- Given a forbidden field or unsafe string at any existing traversed depth
- When the envelope passes through the pure safety boundary
- Then the current failure is preserved before source projection
- And no subprocess, SQL execution, file write, or network operation occurs.

**Scenario: Preserve an explicitly unavailable source**
- Given an otherwise valid unavailable envelope with one bounded reason
- When selected source validation runs
- Then the same unavailable representation is approved without inventing payload
  facts or requiring the available-source required fields.

**Scenario: Keep byte identity outside semantic validation**
- Given two accepted JSON byte strings with equal decoded values but different
  whitespace
- When the shell projects each through a fake adapter
- Then canonical payload serialization is unchanged
- And each reported digest remains the SHA-256 of its own original bytes.

## Property And Counterexample Strategy

Properties must express independent observable contracts, not duplicate policy
branches or merely compare a function with itself. Use bounded generators for
the supported grammar and all existing envelope source families. Include exact
boundary values and deliberately invalid mutations; avoid filtering arbitrary
inputs until only easy valid cases remain.

| Property family | Significant evidence and counterexamples |
|---|---|
| Frontmatter interpretation | Generated supported scalars and lists preserve value type/value; scalar-looking quoted strings remain strings; body text and delimiter/newline cases retain current normalization. |
| Frontmatter rejection | Duplicate/invalid keys, unsupported nesting, delimiter failures, and empty block collections produce characterized errors; preserve the baseline's unusual quote outcomes and retain smallest distinguishing failures. |
| Envelope approval | Each supported source has valid available examples; unavailable reasons exercise empty, exact byte bound, and over-bound inputs; missing/extra fields and wrong exact types are rejected as before. |
| Recursive safety | Forbidden keys and unsafe strings inserted in supported nested dict/list paths preserve rejection before projection; approved inputs remain unmodified. |
| Nested source fields | Gate names/fields/exceptions, metrics, rubric, harness identity, members, nodes, phase profiles, prose lists, UTF-8 byte bounds, and 500-item limits retain their existing boundary outcomes. |
| Compatibility distinctions | `True` versus `1`, Unicode character count versus byte count, empty versus absent optional fields, numeric edge cases, and decoder-supported unusual values preserve observed baseline outcomes. |
| Shell integration | Existing CLI fixtures and small explicit new cases establish error framing, serialization, original-byte digest identity, and no adapter invocation on rejection. |

Bound strategies directly: ordinary parser cases use at most 16 keys, 16 list
members and 512 Unicode characters per scalar/body fragment; nested safety cases
use depth at most four and at most eight children per container. Add explicit
small fixtures at the existing 256/2048-byte and 500-item boundaries, including
valid multi-byte characters. These are test-generation limits, not new runtime
acceptance limits. Do not randomly execute I/O or generate unbounded recursion.
The profile's per-property settings retain health checks and stable local/CI
behavior. Its supervising-runner requirement bounds local execution; bare pytest
has no inherent wall-clock timeout. CI retains its existing overall job bound.

Characterize baseline outcomes before refactoring. A temporary differential
comparison may use the fixed baseline source during development, but durable
properties require reviewed expected outcomes or independent invariants. Do not
ship a second production parser or validator as the oracle.

Hypothesis examples must be bounded and reproducible. Shrink failures, retain
the smallest meaningful synthetic counterexample as an explicit regression, and
record the failure/reproduction evidence. A new minimized example does not
authorize changing acceptance behavior. Property-generated inputs stay inside
pure calls; filesystem, Git, Jira, SQL, and service effects use existing explicit
fixtures/fakes rather than randomized execution.

Use only synthetic public-safe data. Do not seed generators, persist examples,
or publish failure output using real PM files, private paths, credentials,
Jira content, or runtime lifecycle records. Local example-database state is not
portable evidence; retained regression cases and recorded settings provide it.

## Validation And Gate Ledger

Use the exact commands and settings recorded in the Engineering Profile.
Evidence must bind the candidate commit, complete affected-file inventory,
checker/test versions and configuration, environment, exit results, and any
diagnostics or exclusions. Discovery document checks, actual implementation
typing/tests, and later runtime qualification are independent evidence.

The existing publication authority is
`tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers`.
It must cover the full candidate documentation/source set, including new files
through its existing inventory mechanism. A manifest check cannot substitute for
publication safety. Relevant PM pytest coverage, typing, properties, instruction
contracts, and affected distribution checks remain distinct evidence.

| Gate | Applicability | Result | Required evidence or reason |
|---|---|---|---|
| Domain | required | pending | Raw/approved language, ownership, and compatibility reviewed in the registered cycle. |
| Behavior | required | pending | Characterization and scenarios cover observable outcomes. |
| Spec | required | pending | Profile-bound tool contract, complete inventory, and interfaces resolved. |
| Contract | required | pending | Runtime proofs, trust transitions, failure precedence, and byte identity preserved. |
| Test-driven implementation | required | pending | Focused examples/properties, affected pytest, and required ty evidence pass. |
| Refactor | required | pending | Narrow extraction and annotations introduce no contract drift or duplicate policy. |
| Review/Integrate | required | pending | Independent review, publication authority, and affected distribution checks pass. |
| Release | not_applicable | not_run | Source-only draft delivery publishes no versioned package or image. |
| Deploy | not_applicable | not_run | This slice stops at reviewed source; managed installation is a separate delivery decision. |
| Operate | not_applicable | not_run | No installed command or service changes in this source-only slice. |
| Maintain/Retire | required | pending | Tool ownership, counterexample maintenance, and rollback obligations recorded. |

No Gate Exception is granted by this document. Discovery readiness, lifecycle
preflight, registration, and later integration authority remain the primary's
responsibility.

## Delivery, Recovery, And Risks

First deliver documentation and approved source/test changes through the same
source-only draft PR route. Do not apply chezmoi, overwrite an installed CLI,
activate PostgreSQL, invoke Jira, or mutate reporting data to demonstrate this
slice. A later managed-install slice must independently establish its affected
deployment scope, dry-run, source identity, runtime smoke, and rollback evidence.

Rollback before merge means withdrawing the candidate change; after integration,
revert the feature commits through normal review. There is no persistent schema
or reporting-data migration to reverse. A later installation requires its own
installed-source rollback; reverting repository source alone does not prove that
an installed command changed.

Elevated risk follows from compatibility and private-data validation boundaries.
Negative side effects include accidental acceptance drift, changed first error,
body normalization changes, canonicalized rather than raw-byte digests,
mutation of raw values, broader test dependencies, and annotation work escaping
the selected policies. Whole-file ty diagnostics may reveal work beyond this
slice; record that conflict before expanding behavior or suppressing errors.
Generated tests can become slow or flaky without bounded settings; exact settings
and retained counterexamples are acceptance inputs, not measured benefits.

The maintainer owns canonical source maps and property regressions. Change this
spec and its evidence in the same PR whenever represented interfaces, trust
transitions, source contracts, accepted grammar, or delivery boundaries change.

## Visual Evidence

| Concern | Decision | Review question and source |
|---|---|---|
| Boundary | required: directional responsibility table below | Which responsibilities stay in the standalone shell? Scope and Trust Transitions. |
| Interaction | not_applicable: ordered shell contract and scenarios above provide the complete synchronous sequence; no new retry or approval protocol. | Compatibility contract 4. |
| State | not_applicable: this slice introduces no lifecycle state machine; approved data guarantees are represented by the flow and domain table. | Domain Language And Trust Transitions. |
| Data/trust | required: directional responsibility table below | Which runtime checks precede trusted consumption? Trust Transitions and Compatibility. |
| Schema | not_applicable: no persistent entities or cardinalities change; existing source maps remain canonical. | Scope And Non-Goals. |
| Dependency/deployment | not_applicable: standalone topology stays unchanged and installation is separately scoped. | Delivery, Recovery, And Risks. |
| Quantitative | not_applicable: no comparative metric or forecast supports this decision. | Property strategy defines proof obligations, not measured gains. |

| Producer | Input or guarantee transferred | Consumer and retained responsibility |
|---|---|---|
| Standalone shell | Decoded ticket text | Pure frontmatter parser; no I/O or ticket-validity claim. |
| Pure parser | Same syntax-approved values and normalized body | Existing separate ticket/domain validation in the shell. |
| Standalone shell | Decoded JSON; original bytes retained by shell | Pure recursive safety and top-level shape checks. |
| Safety boundary | Same safety-approved value | Pure selected-source payload validation. |
| Source-contract boundary | Same source-contract-approved value | Shell serialization and optional projection. |
| Standalone shell | SHA-256 of original input bytes | Existing projection identity and CLI result. |

**Text Equivalent:** The standalone shell owns all input/output. It gives decoded
ticket text to a pure parser and receives syntax-approved values and normalized
body for existing separate ticket checks. For envelopes it retains original bytes,
decodes JSON, and supplies the raw value to pure safety checks. Only after safety
and selected-source payload checks succeed does an approved envelope return to
shell serialization and projection. The shell derives its digest from original
bytes. Any failing policy blocks the corresponding consumption path.

Canonical sources: this feature's Scope, Trust Transitions, and Compatibility
sections plus the named existing `pmctl` functions. Owner: PM Kernel maintainer.
Trigger: any represented responsibility, validation order, or trust transition
changes. Review labels, direction, source freshness and Text Equivalent parity.
The table is canonical editable evidence and needs no external graph renderer.

## Tool Qualification References

Tool selection is supported by the pinned
[ty release metadata](https://pypi.org/pypi/ty/0.0.95/json),
[Hypothesis release metadata](https://pypi.org/pypi/hypothesis/6.170.14/json),
[ty CLI](https://docs.astral.sh/ty/reference/cli/) and
[configuration](https://docs.astral.sh/ty/reference/configuration/).
The exact ty release's
[file-selection implementation](https://github.com/astral-sh/ruff/blob/7cb935d94e5ccdaefd4efee86ba454e8673a3fa6/crates/ty_project/src/walk.rs#L236)
and upstream extensionless-file regression establish why explicit file paths are
required. This is source/documentation qualification, not a local checker pass.
Hypothesis [settings](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings)
and [replay guidance](https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html)
support bounded generation and durable minimized examples. Actual environment
resolution, local CLI acceptance and diagnostic census remain Build work.
