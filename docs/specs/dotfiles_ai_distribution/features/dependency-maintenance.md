# Qualified dependency maintenance

Status: source-ready contract; runtime qualification pending. Owner: distribution
maintainers. Profile: `../PROFILE.md`; Product Intent: `../PRODUCT.md`, journeys
5, 19 and 20. Adjacent owner: OpenCode control plane for native permissions.
Risk: critical for Worktrunk preservation and activation; elevated for maintenance
guidance. Modules: Python, Security, Cloud; apply ML/AI to changed agent guidance.

## Scope and authority

This contract supersedes the single-version Worktrunk requirement only for the
qualified macOS successor. Preserve historical 0.80.0 evidence and unchanged
Linux/guest provisioning. Existing storage separation, mount identity, branch
retention, reservation and lifecycle approval requirements still apply.

Homebrew owns the macOS Worktrunk executable. Chezmoi owns its managed integration.
A **qualified version** has exact source/interface and runtime evidence for its
platform. A **pin** prevents incidental package-manager upgrades; it does not
prove runtime health or install an arbitrary historical release. An **activation**
binds generated policy, root identities and the actual qualified native version.
These are separate facts, not interchangeable success signals.

### Worktrunk source slice

- Support exact 0.81.0 on macOS after qualification and retain exact 0.80.0
  compatibility needed by existing routes. Do not accept an open-ended version
  range or infer Linux 0.81.0 support from macOS results.
- Store the actually observed supported version in snapshots. A saved snapshot
  for another version must fail until an explicitly approved coherent activation.
  Update the independent removal version check consistently.
- Report a bounded unsupported-version category distinguishing it from malformed
  policy or unavailable storage. Include safe expected/observed version values
  only when parsed; never expose arbitrary subprocess output or local paths.
- Keep native `worktree-path` templates as default. `wt switch --path` is an
  explicit operator exception requiring destination-specific review, not managed
  automatic creation. Deny this option in managed agent shell permissions and
  state the same boundary in shared agent guidance. Operators retain native
  Worktrunk outside those agent permissions. This is not a universal security
  boundary: aliases, explicit operator overrides and disabled hooks cannot be
  represented as validated destinations.
- Do not claim the pre-switch hook validates the custom creation destination.
  In 0.81.0, path planning occurs after that hook; new target path is unavailable.
  General automated custom-path support requires fresh Discovery and a qualified
  pre-allocation interface. Do not add an allocator wrapper or post-write check
  presented as pre-write protection.
- Homebrew pinning is idempotent and only claims success after the selected
  executable and pinned installed version match the qualified macOS release.
  Missing/mismatched executables refuse visibly; do not pin an unknown version
  and call it qualified. Existing unrelated pins remain untouched.
- Managed bundle reapply does not request upgrades. Homebrew `--no-upgrade`
  alone is not an absolute dependency-update fence: installing a missing formula
  can upgrade required dependencies. Stop or preview such prerequisite changes
  explicitly; never describe the flag as preventing every transitive mutation.
- Reuse the existing macOS bundle hook and native pin command. Preserve single
  executable ownership; no second permanent Worktrunk installer. Retain exact
  archive/checksum tooling for disposable qualification and CI. CI exercises both
  supported versions where needed; unchanged Linux sources stay pinned to 0.80.0.

Candidate writable implementation closure: `dot_local/bin/executable_workflow-policy`,
`dot_local/bin/executable_agent-worktree`,
`run_onchange_before_install-opencode.sh.tmpl`, `Brewfile`,
`.github/workflows/test.yml`, `.chezmoitemplates/opencode.json.tmpl`,
`private_dot_config/opencode/AGENTS.md`,
`private_dot_config/dotfiles-ai/codex-managed/AGENTS.md`,
`tests/test_worktrunk_native_policy.py`, `tests/test_agent_worktree.py`,
`tests/test_portable_distribution.py`, `tests/test_opencode_control_plane.py`,
`tests/test_dbsctr_lifecycle.py`, `README.md`, `docs/UPDATES.md`, and distribution
README/CHANGELOG/BACKLOG completion evidence. Normative authority changes return
to Discovery; this closure does not authorize unrelated permission changes.

### Maintenance source slice

Inventory all direct dependencies declared in manifests, installers, plugins,
runtime locks, CI and enabled optional profiles, with transitive dependencies
attributed to their existing locks. Reconcile `docs/UPDATES.md` against actual
source and selected host owners. Do not inventory unrelated project runtimes or
turn this into an upgrade-all operation. Separate installed version, source pin,
available candidate and running-service version. Report unsupported/unavailable
checks and disabled optional features explicitly.

Extend `docs/UPDATES.md` as the single operator runbook and add the portable
`dot_agents/skills/dotfiles-ai-update/SKILL.md` plus native UI metadata. The skill
resolves the selected source, loads the runbook, inventories on check requests,
and routes explicit update requests through existing owners. It must work from
another repository without assuming its working directory is dotfiles-ai.
No competing copy of the runbook, new updater CLI, background polling or automatic
service restart. Use the installed original skill creator and validator.

Worktrunk procedure: inspect current binary/pin/activation; review candidate
release and exact artifact; qualify in isolation; prepare coherent source;
preview target-specific deployment and recovery; obtain approval; perform only
the selected owner's update; verify and pin; install matching activation last;
verify normal workflow. If Brew's candidate moved beyond the approved version,
stop before unpin/update. Preserve the pin on failure where possible and report
actual version; do not silently downgrade or delete retained artifacts.

Other families retain their owners: native OpenCode/Codex, source-pinned Herdr,
locked managed DVC, optional Hermes, shell utilities, plugins/skills, test locks,
CI fixtures, guest tools, models and optional services. Source/runtime disagreement
requires scoped remediation, not unconditional reapply. Host runtime version
changes may break existing virtual environments even when their packages are
locked; verify interpreter availability. Authentication and state migrations
remain explicit operations. Private effective configuration and inventories stay
local; public documentation contains only portable names and procedures.

## Acceptance and validation

| ID | Given / when | Required result |
|---|---|---|
| M-01 | Qualified version and matching activation | Native template creation passes under configured root; no ignored-data hydration |
| M-02 | Unknown/malformed/missing executable or mismatched activation version | Refuse with bounded reason before creation; preserve work/configuration |
| M-03 | Existing registered worktree with stale activation | Preserve existing navigation behavior, including branch/path and detached cases supported by native Worktrunk |
| M-04 | Missing/replaced mount, policy/config drift, occupied or sanitized collision | Existing refusal and retention contracts still hold |
| M-05 | Native removal hook/managed reservation | Dirty or unavailable preservation refuses; descriptor/lock propagation and branch retention pass disposable fixtures |
| M-06 | Agent requests custom `--path` | Managed permission denies separate and equals-value forms; standard template creation remains available under existing approvals |
| M-07 | Known installed Worktrunk during managed reapply | No requested upgrade; exact matching native pin verified; second application idempotent |
| M-08 | Unsupported installed version or newer unapproved Brew candidate | Refuse qualification/update; never silently accept or downgrade |
| M-09 | Dependency check or update skill invoked | Source ownership and requested environment determine scope; check is read-only; mutations use existing approvals/owners |
| M-10 | Partial deployment or failed smoke | Retain evidence/preimages; report incomplete activation; recover only reviewed compatible generation |

Required source authorities: affected pytest, publication/instruction checks,
rendered shell/TOML/configuration, `bash -n`, meaningful Brew invocation fixtures,
and real disposable native Worktrunk 0.80.0/0.81.0 tests. Include pre-switch target
semantics, hook stdin/foreground changes, MiniJinja rendering, selected project
identifiers, config precedence, no JSON-stdin dependency, and removal descriptor
propagation. Native managed permission resolution must corroborate rendered
rules. A mock does not establish runtime qualification. Maintain existing strict
retirement blockers; passing synthetic removal fixtures cannot enable them.

Maintenance skill: original `quick_validate.py`, portable publication checks,
isolated rendering/file-set checks and behavioral review of check/update requests.
Inventory successes are bounded to the checks actually run, not all runtime health.

Source gates: Domain through Refactor, Review/Integrate and Maintain/Retire required;
Release not applicable (no independent package); Deploy/Operate not applicable to
source-only slices. Mac activation has required Deploy/Operate and remains
Discovery-owned until exact target plan, preserved preimages, qualification,
recovery and approval are ready. No exceptions approved by this specification.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ownership and ordered transition table below |
| Interaction | required: ordered transition table below |
| State | required: acceptance rows M-01–M-10 |
| Data/trust | required: transition table; private state never becomes public authority |
| Schema | not_applicable: existing schema-1 snapshot is retained |
| Dependency/deployment | required: transition table |
| Quantitative | not_applicable: no performance or fleet-health claim |

| Order | Owner / input | Guard / outcome |
|---|---|---|
| 1 | Distribution / selected source and private inventory | Resolve actual owners, versions and target environment |
| 2 | Source primary / exact upstream candidate | Disposable native compatibility and affected source checks pass |
| 3 | Operator / target-specific deployment and recovery plan | Approve exact mutations; retain preimages |
| 4 | Existing installer owner / approved version | Update only selected tool, verify version and required pin |
| 5 | Chezmoi and activation owner / coherent generation | Apply reviewed helpers/configuration; record matching activation last |
| 6 | Primary / live smoke evidence | Report qualified state or retain incomplete state for recovery |

**Text Equivalent:** Resolve actual ownership before qualifying a candidate.
Source checks precede explicit deployment approval. The existing installer changes
only the selected tool; verified pin and coherent managed files precede activation.
Final live checks determine success. Failures retain evidence and prior recoverable
state; private inventory is never published. Scope: declared dependency maintenance,
initially macOS Worktrunk. Canonical source: this contract; owner: distribution
maintainers; update when ownership, supported routes or activation ordering changes.
