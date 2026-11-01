# Dependency contract techniques

Use these techniques for the selected Python packages and accepted architecture.
Verify configuration syntax against the project's installed checker version and
matching official documentation. No layout, layer count or tool is universal.

## Establish intent and evidence

For each candidate rule, identify its owner/authority, purpose, exact package or
module population, permitted access, relevant consumers and review condition.
Separate accepted decisions from observed conventions and proposed alternatives.
If code and a current ADR disagree, report the contradiction; do not rewrite the
ADR simply to match code. Where authority conflicts or intent is unclear, propose
bounded alternatives and keep the uncertainty visible.

Trace concrete imports with source locations and the full relevant witness chain.
Review `__init__.py` re-exports, relative imports, public facades, type-checking
guards and plugin registries. `__all__` does not prevent explicit imports of other
names. A documented public API may still depend internally on protected modules;
choose a rule that expresses permitted access rather than banning every indirect
implementation dependency.

## Choose the rule's actual meaning

| Accepted intent | Optional Import Linter contract | Important limit |
|---|---|---|
| A package must not depend on selected packages | `forbidden` | Includes descendants and indirect chains by default; options can change that scope. External-package checking needs the selected external graph setting. |
| Only designated modules may directly access an internal module | `protected` | Checks direct imports. It can allow an approved facade to use an implementation without banning callers of that facade. |
| Defined layers may depend downward, not upward | `layers` | Order is highest to lowest; includes indirect chains. Repeated containers do not themselves impose independence across different contexts. |
| Selected contexts must have no dependency in either direction | `independence` | Includes indirect dependencies. Use only when this stronger separation is actually intended. |
| Sibling components must avoid dependency cycles | `acyclic_siblings` | Package-level cycles can exist without a direct module cycle. Ancestors, depth, skipped descendants and ignores determine coverage. |

Do not infer that Clean Architecture requires a particular folder hierarchy,
that every dependency needs an interface, or that a shared utility violates a
boundary. Establish the actual dependency and change cost. Import relationships
cannot prove transaction ownership, state consistency, domain cohesion, latency,
security isolation or distributed-system reliability; hand those questions to the
relevant architecture, component, database or runtime technique.

## Example proposal, not an audit-side edit

Suppose an accepted project decision says the domain must not depend on adapters.
For a project that already selects a compatible Import Linter version, this is a
possible TOML representation; substitute actual package roots and rule ownership:

```toml
[tool.importlinter]
root_package = "sample_app"

[[tool.importlinter.contracts]]
id = "domain-boundary"
name = "Domain does not depend on adapters"
type = "forbidden"
source_modules = ["sample_app.domain"]
forbidden_modules = ["sample_app.adapters"]
```

A path such as `sample_app.domain.orders`, `sample_app.shared`, then
`sample_app.adapters.storage` can break that contract even without a direct domain
to adapter import. Confirm actual imports and applicable options before reporting
it. If the intended rule is only controlled direct access through a facade,
consider `protected` instead; it expresses a different contract.

An authorized existing check might select this contract with
`lint-imports --config pyproject.toml --contract domain-boundary --no-cache` when
those flags are supported. Inspect the configured project command first. This
example is neither proof that the tool exists nor permission to run it, install
it, create the file or replace the project's current validation authority.

## Coverage and exceptions

Reconcile owned roots and environments with the graph/check population. Record
unexamined packages, generated or vendored code, namespace portions, unsupported
inputs and configuration exclusions. Treat tests and notebook imports according
to the declared scope rather than assuming the production package covers them.

In `acyclic_siblings`, depth and skipped descendants limit recursive drill-down;
deeper imports can still create dependencies between the siblings checked at an
earlier level. Do not interpret a depth limit as excluding those import edges.

State whether type-checking imports are included. Grimp's documented guard
recognition is syntactic; an excluded edge is not evidence that no type dependency
exists. External packages can be represented as squashed nodes without analysis
of their internal imports. Dynamic import names, runtime plugin selection and
non-Python connections need separate source/contract evidence; do not import
application code to fill a static analysis gap. Include cache/configuration
freshness in any evidence reused after a source or environment change.

Use exceptions only for justified project decisions. Give an ignored edge a
reason, owner, exact scope and review/removal condition; disclose its excluded
coverage. Broad wildcards and silent unmatched-ignore handling can conceal drift.
Do not add an ignore merely because the proposed rule exposes existing findings.
A staged adoption may retain broken checks as advisory under explicit project
policy; it cannot pass a required architecture capability by calling setup done.

## Meaningful validation and reporting

When implementation of an accepted contract is selected, check a representative
allowed dependency and a prohibited witness in an isolated fixture using the
actual chosen authority. Include indirect/facade or type-only cases where their
semantics matter. Check that the intended roots were analyzed; an empty or partial
population does not become complete because the command exits successfully.
Keep the original failure and subsequent evidence. A source audit can propose
these cases without running or writing them.

Report manual source review, graph coverage and executed-contract results as
separate claims. Include accepted rule versus proposed rule, actual source path,
confidence and limitations, compatible repair options and the validation still
needed. Feed existing audit/QA artifacts; a clean import graph alone is not an
architecture pass.

## Primary reference starting points

- [Configuration](https://import-linter.readthedocs.io/en/stable/get_started/configure/) and [running the linter](https://import-linter.readthedocs.io/en/stable/get_started/run/).
- [Forbidden](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/), [protected](https://import-linter.readthedocs.io/en/stable/contract_types/protected/), [layers](https://import-linter.readthedocs.io/en/stable/contract_types/layers/), [independence](https://import-linter.readthedocs.io/en/stable/contract_types/independence/) and [acyclic siblings](https://import-linter.readthedocs.io/en/stable/contract_types/acyclic_siblings/).
- [Grimp graph semantics](https://grimp.readthedocs.io/en/latest/usage.html) and [custom contract code](https://import-linter.readthedocs.io/en/stable/custom_contract_types/).
- [Python import statement and `__all__`](https://docs.python.org/3/reference/simple_stmts.html#the-import-statement).

These are lookup starting points; selected versions and project contracts determine
which features and assumptions apply.
