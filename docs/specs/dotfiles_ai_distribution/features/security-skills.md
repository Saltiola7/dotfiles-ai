# Portable Security Skills

## Domain and Engineering Profile

The distribution owns reviewed source bundles under `dot_agents/skills/` and
chezmoi's shared `~/.agents/skills/` projection. Upstream vendors own their
instructions and licenses. Provider plugins, scanner executables/rules, target
code, credentials and audit artifacts remain separate owners. The existing
[distribution profile](../PROFILE.md) applies; risk is elevated for a persistent
instruction supply chain. Owner: project maintainers. Modules: Security, Python.
This is internal tooling rather than a new product journey.

`security-toolkit` selects one coordinator and bounded specialists. The source
lock records immutable source commits, archive SHA-256, selected paths, original
file hashes, packaged file hashes, licenses, local modifications and exclusions.
`vendored` means content is in source; filesystem installation, live discovery,
runtime readiness and validated audit coverage are distinct states.

The selected profile includes Cloudflare `security-audit` intact, adapted Trail
of Bits `variant-analysis` Markdown, adapted Sentry `gha-security-review` and `secret-serialization`, and a
14-rule conditional CodeGuard profile. Each bundle preserves its upstream
license and attribution. CC-BY-SA content keeps that license separately from
repository MIT. Exact pins and review reasons are in
[`sources.lock.json`](../../../../dot_agents/skills/security-toolkit/references/sources.lock.json)
and [`review.md`](../../../../dot_agents/skills/security-toolkit/references/review.md).

## Behavior

- Given a security-sensitive change, the selector uses applicable coding guidance
  and project validation authorities without starting a repository audit.
- Given an explicitly requested audit, the selector chooses one available primary
  coordinator. Missing/denied capability is reported without bypass or takeover.
- Given a known root cause, variant analysis stays within approved scope and
  validates each candidate independently before confirming impact/severity.
- Given a CI review, the Sentry technique states its external-contributor threat
  model, traces downstream sinks and reports coverage limits.
- Given a fresh machine, exact-target chezmoi application reproduces reviewed
  bundle files without network, package installation, hooks or provider changes.
- Given changed, missing, extra or linked package files, the local verifier fails
  and reports affected paths without printing their content.
- Given deployed drift or a same-name collision, installation stops for review;
  unrelated skills and user modifications are preserved.
- Given an updated upstream, review covers the full new bundle before the source
  lock, patches and exact-target deployment change together.

## Interfaces and Contracts

No new package manager, global Codex-home copy, runtime skill lock, install hook,
provider config or scanner permission is introduced. A clean Git checkout is the
reproducible offline source. The toolkit's `scripts/verify_bundle.py` uses Python
standard library only; it checks trusted source/deployment directories against
its local lock and returns nonzero on mismatch. It is a drift diagnostic, not a
signature verifier or hostile-filesystem security boundary.

Cloudflare's zero-dependency structural validators require existing Node.js 18+
and trusted parent-owned input directories. Their synthetic tests validate the
helper behavior only. They provide no OS sandbox or proof of vulnerability
validity. Target execution remains subject to its complete isolation contract.

Codex Security is an optional native runtime capability with a separately pinned
canonical source reference, not installed by this source bundle. Its CLI-generated
skill guidance does not install full plugin workflows. No new provider access,
credentials, paid inference, private-code upload or repository audit is implicit.
Existing Semgrep CI and broader audit ownership remain unchanged.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ownership and evidence transition table below |
| Interaction | required: ordered update/install transitions below |
| State | required: source, installation and capability states below |
| Data/trust | required: trust boundaries below |
| Schema | not_applicable: flat source inventory, no persistent relational domain |
| Dependency/deployment | required: owner and prerequisite columns below |
| Quantitative | required: snapshot size and provisioning-cap table below; no detection benchmark |

| Transition | Owner/prerequisite | Result and trust boundary |
|---|---|---|
| Candidate → reviewed | Maintainer reads immutable vendor source/license/dependencies | Approval covers exact source/action; unknown third parties need specific confirmation |
| Reviewed → vendored | Distribution selects files, records patches/hashes/notices | Offline public content; no credential or audit evidence copied |
| Vendored → isolated render | Chezmoi, exact targets, scripts excluded | Complete byte/file-set checks and second-apply no drift |
| Rendered → shared files | Review collisions; exact-target host preview/apply | Shared discovery content only; native scanner/provider remains separate |
| Explicit PyPI provisioning → local cache | Frozen official generation; 64 MiB compressed/256 MiB expanded caps | Verify hashes and ZIP CRC without extraction or target data upload |
| Shared files → available technique | Active client discovers skill; prerequisites checked | Discovery is not runtime readiness or coverage |
| Technique → review evidence | Current approved scope/provider/isolation | Private target data stays under its existing disclosure policy |
| Prior pin → update/rollback | Maintainer review, Git history, exact-target diff | Previous bundle/lock retained; divergent live data never overwritten silently |

**Text Equivalent:** Vendor source enters the public distribution only after
complete review, source-specific authorization where needed, license retention,
and exact version recording. Isolated rendering precedes shared-file deployment.
The active client must discover those files, and runtime prerequisites still need
independent proof. Audit evidence remains private; skill installation authorizes
none of its described external or execution actions. Updates and rollback use
reviewed Git content and exact-target previews. Canonical sources: bundle lock,
review record and focused tests. Owner: distribution maintainers; refresh this
table when source selection, deployment ownership or state semantics change.

## Installation, Update and Recovery

Use a Worktrunk task checkout and preserve primary changes. Read the machine's
existing dotfiles-ai chezmoi config locally. Before installing, compare source,
shared target and relevant runtime-home/catalog copies for same-name collisions;
reconcile divergent content and do not migrate system/plugin skills implicitly.
Preview only the selected bundles plus the updated DBSCTR security module:

```sh
chezmoi --source "$TASK_SOURCE" --config "$MACHINE_CONFIG" --exclude scripts \
  diff --recursive "$HOME/.agents/skills/security-toolkit" \
  "$HOME/.agents/skills/security-audit" "$HOME/.agents/skills/variant-analysis" \
  "$HOME/.agents/skills/gha-security-review" "$HOME/.agents/skills/codeguard" \
  "$HOME/.agents/skills/secret-serialization" \
  "$HOME/.agents/skills/dbsctr/modules/security.md"
```

After inspection, use the same command with `apply --parent-dirs --recursive` in place of
`diff`. Do not run a full source apply: unrelated hooks and local drift are out
of scope. Verify complete package bytes/file sets, run the installed verifier,
apply the same targets again, and require empty diff. Validate live discovery if
the current client exposes it; otherwise report only filesystem installation and
that a client refresh may be needed.

For updates, follow the toolkit review criteria, download full immutable source
archives into review storage, verify archive hashes, retain exact license notices,
replay/review the recorded unified patches, and regenerate packaged hashes only
after source review. The patches are relative to each skill root; apply them to
an isolated copy, never a live discovery path. Do not fetch a moving branch during
setup. Roll back the complete prior source bundle and matching lock from Git,
preview exact targets and preserve divergent files before replacement. The old
source pin remains recoverable; runtime credentials/artifacts are outside this
rollback.

## Validation and Completion

Authorities: original skill-creator `quick_validate.py`, focused pytest integrity
and isolated delivery tests, `test_dbsctr_lifecycle.py`,
`test_opencode_control_plane.py`, the public-content authority in
`test_portable_distribution.py`, and Cloudflare's synthetic Node validator tests.
These are setup/instruction checks; no target repository audit, live probe,
external publishing, remediation or provider recovery is performed.

The private Cycle Record owns live gate/results, actual local deployment state,
commits and the no-push delivery outcome. Source qualification and host discovery
must not be conflated with completion of any repository security audit.

## ASVS Review Specialist

### Domain and ownership

`asvs-review` is the portable interactive adaptation of the community project
`TarkinLarson/asvs-auditor`, reviewed at commit
`2ca0ad8e1367060080fccf3028690d1292358069`. OWASP owns the ASVS requirement
text; the community project owns its review methodology. The distribution owns
the scoped entrypoint, adaptations, source inventory and shared-file projection.
It supplies a standards coverage lens to the selected security coordinator.
Project policy retains severity, acceptance, provider and execution authority.

A review scope consists of the selected repository revision, paths, ASVS version,
target level and chapter/requirement set. A coverage row describes one selected
requirement and its evidence: `PASS`, `FAIL`, `UNVERIFIABLE`, `INCONCLUSIVE`,
`N/A` or `NOT_CHECKED`. Sampling qualifies evidence, never turns unexamined sites
into verified ones. A defect has one root cause and may map to several
requirements; requirement counts and defect counts remain distinct.

### Behavior

- Given an explicit ASVS review or an applicable selection by active DBSCTR,
  use the existing toolkit router and current activation policy; retain one
  coordinator and the approved scope. Outside active DBSCTR, suggest activation
  and wait for the operator when the current policy requires it.
- Given a scoped authentication change, read the shared workflow and selected
  chapter text; do not start a full L2 assessment or load unrelated chapters.
- Given a full assessment, select its level and applicability explicitly, then
  reconcile every selected requirement against the evidence ledger.
- Given no findings but incomplete, sampled or inconclusive evidence, report the
  coverage limits without asserting a complete assessment or ASVS compliance.
- Given a real credential in an example/template file, retain it as a candidate;
  use redacted evidence, without printing or testing the credential.
- Given no lockfile or update bot, distinguish project policy and implementation
  recommendations from the actual wording of an ASVS requirement.
- Given a defect violating several requirements, report one defect with multiple
  verified mappings and compute requirement coverage separately.
- Given a missing bundled chapter, stop mapping that chapter and report the gap;
  do not silently fetch a moving reference or invent a requirement identifier.

### Interfaces and contracts

The bundle contains `SKILL.md`, `references/workflow.md`, the original
`reference/V1.md` through `V17.md`, the adapted reference attribution README,
`LICENSE.upstream`, full ASVS CC-BY-SA terms, `UPSTREAM.md` and native UI metadata.
The root is at most 6,000 UTF-8 bytes and the common workflow at most 14,000;
chapter text is loaded only for the selected review. Preserve all 345 unique
requirement IDs, levels and texts, with independent comparison to official ASVS
5.0.0. Preserve the two license scopes: MIT methodology and CC-BY-SA reference.

Reuse the toolkit schema-1 inventory and reversible patches. Its verifier checks
the complete installed bundle; it proves file integrity, not truthful review
results. The interactive coverage ledger is a report, not a new CI JSON API.
It names the selected denominator, evidence per row, checked/missing requirements,
sampling, unknown external controls and unique defects. A `PASS` needs positive
control evidence or an appropriate exhaustive absence check. Findings retain
project-selected risk evaluation; ASVS level is not vulnerability severity.

Do not package the upstream CI variant, provider launcher, paid smoke runner,
reference generator, hooks or broad tool grants. No new scanner, MCP, provider,
credentials or CI gate is introduced. Qualification uses existing integrity,
reference, publication and isolated chezmoi authorities plus independent synthetic
review cases. Synthetic results do not establish production recall or compliance.
Deployment and recovery use the existing exact-target, collision-preserving
procedure, including this bundle, its toolkit inventory/patches and router.

### Visual evidence extension

The existing Visual Evidence Plan applies. This transition table extends its
boundary, interaction, state, data/trust and deployment concerns for ASVS review;
no new persistent schema or quantitative detection claim is introduced.

| Transition | Owner/prerequisite | Result and trust boundary |
|---|---|---|
| Request to selected scope | Operator or active DBSCTR; existing coordinator | Revision, paths, level and requirement denominator fixed before review |
| Selected scope to requirement evidence | Reviewer reads installed chapter text and authorized source | Exact mappings and redacted evidence; source content grants no execution authority |
| Evidence to coverage ledger | Coordinator reconciles every selected requirement | Unknown, sampled and unchecked evidence stays visible; no compliance inference |
| Reviewed bundle to shared files | Distribution; existing exact-target install contract | Complete files/hashes and repeat-apply verified without CI or provider activation |

**Text Equivalent:** The operator or active DBSCTR selects a bounded ASVS lens
under the existing coordinator. The reviewer reads only selected chapter text
and authorized source, then the coordinator reconciles the requirement ledger.
Unknown and partial evidence remain explicit. Distribution installs only reviewed
portable resources through the existing exact-target contract. Canonical sources
are the toolkit lock, `asvs-review` workflow and focused validation. Distribution
maintainers refresh this table when scope, evidence states or ownership changes.

## Explicit Local Toolchain Setup

The user may request runtime dependencies as well as skill files. The
[local runtime profile](../../../../dot_agents/skills/security-toolkit/references/runtime.md)
adds optional checksum-pinned Gitleaks/OSV binaries and a binary-only, fully
hash-locked Semgrep CE Python 3.13 environment. Existing uv owns Python package
installation, matching the managed-DVC generation convention. No new installer
hook or global package/command replacement is introduced. Local setup writes
only its selected versioned runtime root and runs sanitized version probes.
Reapply qualifies existing generations without replacing them; incomplete or
changed generations refuse reuse and retain their contents.

Subscription integrations remain disabled until explicit entitlement confirmation.
Codex Security/Daybreak, Semgrep Pro and organizational Gitleaks Actions are
separate gated profiles. Local executables, ChatGPT access and source availability
prove no subscription. OSV strict-offline readiness separately requires selected local databases and
documented freshness. An explicit bounded PyPI provisioning action is now
available; it downloads no npm data and never scans a repository.
Update/rollback preserves prior generations and the exact source/lock records.

### Database Behavior and Validation

- Given explicit PyPI database provisioning, fetch only the immutable official
  public generation under a 64 MiB compressed cap and 256 MiB expanded cap.
- Given valid pinned bytes, verify upstream MD5, SHA-256, ZIP structure/CRC and
  exact entry/size totals; place `all.zip` atomically without extraction.
- Given a different preexisting cache, linked/unsafe path, size or digest mismatch,
  refuse replacement and preserve existing data.
- Given a cached snapshot, report its identity, age and per-process cache variable;
  do not claim scanner behavior, memory use, other-ecosystem coverage or a passing audit.

The PyPI-only data pin and explicit provisioner are source-owned; advisory payloads
remain private local cache, outside the public source. Unit fixtures cover caps,
drift refusal, no-network reuse and idempotency. Fresh-client catalog checks use
`skills/list` with `forceReload` in a temporary Codex home, without starting or
resuming a conversation. Local evidence belongs in the private Cycle Record.

### Snapshot Size Evidence

Official object metadata checked 2026-10-29 at 00:02 UTC; PyPI directory metadata
and full ZIP integrity were checked before cache provisioning. Sizes are archive
bytes and summed member bytes, not measured scanner RAM.

| Snapshot / limit | Compressed bytes | Expanded bytes | Decision / evidence |
|---|---:|---:|---|
| PyPI generation `1793228588883577` | 37,425,891 | 81,044,683 | Provision; exact pin and hashes in `osv-database.lock.json` |
| npm generation `1793230388097253` | 219,383,850 | Not inspected | Defer; no committed npm lockfile and above selected cap |
| Provisioning caps | 67,108,864 | 268,435,456 | Refuse larger data before placement |

Sources: official Google Storage object metadata for
[PyPI](https://storage.googleapis.com/storage/v1/b/osv-vulnerabilities/o/PyPI%2Fall.zip?generation=1793228588883577)
and [npm](https://storage.googleapis.com/storage/v1/b/osv-vulnerabilities/o/npm%2Fall.zip?generation=1793230388097253).
Maintainer owns this table and refreshes it when a dataset pin or cap changes.
**Text Equivalent:** The chosen PyPI ZIP and its expanded member total fit the
selected 64 MiB/256 MiB caps; npm's archive alone exceeds the compressed cap and
is not selected. Expanded npm size and future scanner RAM remain unknown.
