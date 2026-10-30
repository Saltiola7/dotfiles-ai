# Global Graphify ownership

Status: source-ready normative contract; candidate qualification and all source
gates pending. Owner: distribution maintainers. Profile: [PROFILE.md](../PROFILE.md).
Product Intent: [PRODUCT.md](../PRODUCT.md), ownership-transfer and maintenance
journeys. Initiative: [graphify-ownership](../../../initiatives/graphify-ownership/README.md).
Method: DBSCTR V3 revision 3.29. Risk: elevated, changing executable/dependency
ownership and a managed adapter integration. Delivery: source-only draft PR into
configured `main`. Modules: Python, Security, Cloud; review changed agent guidance
without making provider requests.

## Ownership and recipe

`dotfiles_ai_distribution` owns the global `graphify` CLI through one native
`uv tool install` owner, its direct dependency recipe, matching upstream-packaged
OpenCode skill and [update runbook](../../../UPDATES.md). `graphifyy` is the package
name; `graphify` is its native executable. No second CLI wrapper, project
`pyproject.toml`/`uv.lock` ownership, updater helper/daemon or speculative switch.
Host `host_tool_maintenance` removes only its duplicate declarations in the
dependent source slice; it does not own the new recipe or uninstall a live tool.

The new installer hook holds the **single executable version/dependency recipe**;
the runbook references it rather than maintaining another install recipe. The
missing-install candidate is exact `graphifyy==0.9.97`, not an unbounded latest
release. Its direct additions must include:

| Requirement | Purpose / compatibility obligation |
|---|---|
| `anthropic[vertex]` | Preserve the existing extra; installation grants no provider/credential access |
| `boto3` | Adapter-required `boto3` import |
| `tree-sitter-hcl` | Adapter-required `tree_sitter_hcl` import |
| `tree-sitter-language-pack==0.11.0` | Adapter-required `tree_sitter_language_pack`; upstream 0.9.97 pins this prebuilt pack for its R/Erlang extras |
| `tree-sitter-sql` | Adapter-required `tree_sitter_sql` import |
| `tree-sitter>=0.25,<0.26` | Honor upstream 0.9.97's grammar ABI range, including direct additions |

Exact-release PyPI metadata observed on 2026-10-29 declares Python `>=3.10`, the
grammar range and R/Erlang pin above. This is metadata evidence, not successful
installation or runtime qualification. Use a compatible **already-installed**
Python; the distribution profile's test-runtime commitment is unchanged. Direct
pins/constraints and native uv receipts are **not a full transitive hash lock**.
Retain resolved package/interpreter evidence and qualify the actual resolution;
do not claim hash-complete reproducibility or inherit DKS's separate guarantee.

## Bootstrap, reapply and skill behavior

| Order | Given / when | Required action and boundary |
|---|---|---|
| 1 | Default non-Mac, Intel Mac or headless profile | Exclude the new hook; existing supported-platform behavior remains unchanged |
| 2 | Supported Mac ARM64 profile | Resolve existing CLI, actual interpreter and native ownership before managed runtime/skill writes; missing uv or compatible installed Python refuses visibly |
| 3 | CLI/runtime is broken, ownership ambiguous, or a required module is missing | Fail visibly before managed writes; never force replacement, repair dependencies silently or select a second environment |
| 4a | CLI absent and no conflicting installation/receipt remains | Bootstrap the exact recipe once with native uv and installed Python; prohibit Python downloads and propagate failures |
| 4b | Existing CLI/runtime is healthy and unambiguously owned | Retain its actual version/interpreter/dependencies, even when different from the bootstrap candidate; no requested upgrade, downgrade, reinstall or ownership migration |
| 5 | Retained/new runtime passes health and required-import checks | Run that runtime's native skill installer from private scratch; refresh only its matching packaged OpenCode user-skill bundle |
| 6 | Identical reapply | Preserve runtime/version and unrelated targets; matching skill bytes remain stable, with no project-local side effects |
| 7 | Operator later requests a native update | Follow the runbook's exact-candidate qualification, active-cycle preservation and separate exact approval; reapply is not update authority |

**Text Equivalent:** Excluded profiles do nothing. Supported Mac ARM64 resolves
real ownership and prerequisites first. Broken or ambiguous state refuses before
managed writes. Only a genuinely absent installation may bootstrap the candidate;
healthy existing versions remain installed. Only a healthy actual runtime may
refresh its matching packaged OpenCode skill from private scratch. Reapply never
forces a runtime transition; later updates require separate qualification and
approval. Scope: global CLI and OpenCode skill, not DKS or project configuration.
Canonical source: this contract and the source recipe. Owner: distribution
maintainers; update when platforms, ownership, native interfaces or guards change.

Health means executable/package/interpreter identity and required imports agree,
not merely a successful version command. An orphan receipt, broken executable,
conflicting executable owner or unresolved installation root is not an absent
installation. Do not use an ephemeral tool invocation as a runtime locator if it
could install another environment. A known retained owner is not silently migrated
by this hook; unqualified ownership requires explicit reconciliation.

The packaged skill must match the **actually selected** CLI version, not always
0.9.97. Validate its version marker, complete reference bundle and native discovery
without inference. Native skill installation must run outside the caller and
managed repositories in private scratch. It must not create or modify their
project plugin/configuration/hooks, nor install a global plugin or rewrite
unrelated OpenCode settings. Unsafe/unexpected installer output refuses publication
of the skill. Preserve prior skill recovery evidence privately; do not publish
scratch paths, inventories or runtime receipts.

## Existing adapter compatibility

The implementation may repair only
`dot_local/bin/executable_dbsctr-project-graphify` and its focused tests when
needed to preserve its current functional contract. Current source at the cache
snapshot hard-codes `v{version}-s2`; the 0.9.97 candidate uses schema 29 plus a
grammar fingerprint. Recognize the actual qualified cache generation without
counting another schema/fingerprint or partial entry as a hit. Existing fake
0.9.50 fixtures alone cannot qualify the candidate.

Preserve the exact CLI/options and mode/version environment contract; six-file
bounded graph output; report/receipt provenance; `cache_hits` and `cache_misses`
JSON meanings; sanitized execution; local-only DVC behavior; path/ownership guards;
atomic no-replace publication; finalize rollback and existing lifecycle/controller
interfaces. Test genuine warm/cold/partial cache counters and native no-change /
topology-no-change output, including valid ancestor reports normalized to current
full HEAD and refusal of stale/non-ancestor/malformed provenance. Retain behavior
for exact versions already committed by active cycles.

This is implementation-only compatibility work, not permission to change lifecycle
policy, schema, acceptance criteria or receipt/counter contracts. Any finding
requiring a material normative change returns `readiness_reopened`; Build reports
it without editing the normative authority.

## Maintenance and recovery

Extend `docs/UPDATES.md`, the sole operator procedure, to distinguish source
candidate, PATH CLI, actual interpreter/package version, uv receipt root and
matching skill. Resolve the PATH executable's real runtime and corresponding uv
receipt: the current default `uv tool` root can differ from the installed CLI's
root. A default-root inventory alone is insufficient. Updates must address the
confirmed owner, never create a second global environment to hide that mismatch.

The procedure must inspect active-cycle exact-version commitments, preserve
existing extra requirements (including `anthropic[vertex]` and adapter additions),
qualify the exact candidate/resolution in isolation, present the native upgrade
and recovery plan for separate approval, perform only that approved native
operation, refresh its matching skill, and verify versions/imports/functional
behavior. An ordinary upgrade that drops prior `--with` requirements is not
acceptable. Record actual failures and retained state, not presumed completion.
Keep private runtime/skill preimages and compatible recovery instructions; do not
silently downgrade, replace, delete environments or replay a broad apply on failure.
Host documentation links here instead of copying this procedure.

## Acceptance and validation

| ID | Fixture / condition | Required evidence |
|---|---|---|
| G-01 | Platform/profile matrix; absent prerequisites | Only supported Mac ARM64 bootstraps; default non-Mac/headless behavior unchanged; no Python downloads or implicit prerequisite installs |
| G-02 | Missing CLI; healthy older/newer CLI; conflicting roots/owners; broken CLI or missing modules | Single missing-only native install; retained healthy runtime; actionable pre-write refusal otherwise; second apply does not request replacement/update |
| G-03 | Caller Git fixture surrounding a private-scratch native skill install | Actual-version matching skill/reference bundle and native OpenCode discovery; caller/managed project config, plugins and hooks unchanged |
| G-04 | Exact 0.9.97 isolated environment with declared direct requirements | Metadata/resolution and import checks; nonempty AST fixtures covering grammar additions; local native update and query; repeat/no-change behavior; no provider or credential access |
| G-05 | Existing managed adapter with native candidate and preserved-version fixtures | Existing functional suite plus accurate cache counters, native no-change provenance, output/receipt/rollback and security invariants; no schema/policy changes |
| G-06 | Source/runbook ownership and recovery review | One executable recipe; actual uv-root resolution and extras preserved; active pins respected; host pointer valid; private recovery and incomplete-state handling explicit |

Candidate G-03–G-05 evidence must exist before **any activation**. Mock installer
tests are necessary source evidence, not native-candidate qualification. Use only
disposable code/Git fixtures; no graph rebuild in a real repository, DVC pull/push,
credential access, provider calls or paid requests. Preserve existing graphs,
caches and cycle receipts. The disabled hash-pinned DKS 0.9.48 producer/runtime,
its locks and enablement remain untouched; global CLI qualification cannot
supersede that runtime or an active cycle's exact-version authority.

Source validation authorities: focused `tests/test_graphify_installation.py`,
`tests/test_dbsctr_project_graphify.py`, applicable
`tests/test_dependency_maintenance.py`, rendered chezmoi platform/target inventory,
platform Bash syntax, isolated native qualification above and the existing
`tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers`
publication check. The primary includes intended new files in its Git inventory
before that publication check; no replacement privacy denylist. No successful
validation or gate results are asserted by this Discovery artifact.

## Build closure and Gate Ledger

Writable implementation closure: new
`run_onchange_after_install-graphify.sh.tmpl`, `.chezmoiignore`,
`tests/test_graphify_installation.py`, `tests/test_dependency_maintenance.py` if
needed, the bounded adapter and `tests/test_dbsctr_project_graphify.py` if needed,
`docs/UPDATES.md`, root `README.md`, and distribution `CHANGELOG.md` plus Initiative
completion evidence. The current source retired canonical backlog tables; do not
recreate them or require PM tickets. Import the complete approved Discovery document closure;
Build does not own normative edits. No project lock changes, additional wrapper,
installer owner, DKS edits or live install/removal belong to this closure.

| Gate | Applicability | Gate Result |
|---|---|---|
| Domain | required | pending |
| Behavior | required | pending |
| Spec | required | pending |
| Contract | required | pending |
| Test-driven implementation | required | pending |
| Refactor | required | pending |
| Review/Integrate | required | pending |
| Release | not_applicable: upstream consumer; no independent package/release | not run |
| Deploy | not_applicable: source-only draft; live activation separately approved | not run |
| Operate | not_applicable: no live runtime/service change | not run |
| Maintain/Retire | required | pending |

No Gate Exceptions approved. Primary owns review, publication, Git delivery,
manifest validation, fresh receipt/preflight and exact launch approval. Candidate
compatibility remains an evidence obligation; exact live activation choices stay
with the Discovery-owned activation slice, not this source contract.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ordered bootstrap/reapply ownership table |
| Interaction | required: pre-write checks, native install and later approval ordering in that table |
| State | required: absent, healthy, broken, ambiguous and excluded transitions in that table |
| Data/trust | required: private scratch and retained-state boundaries in that table and adjacent Text Equivalent |
| Schema | not_applicable: existing adapter/receipt schemas are preserved |
| Dependency/deployment | required: native owner, actual runtime and separate update/activation in that table |
| Quantitative | not_applicable: counters retain their contract; no measured performance comparison |
