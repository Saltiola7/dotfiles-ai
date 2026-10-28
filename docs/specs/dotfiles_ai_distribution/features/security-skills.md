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
| Quantitative | not_applicable: selection is source review, not a detection benchmark |

| Transition | Owner/prerequisite | Result and trust boundary |
|---|---|---|
| Candidate → reviewed | Maintainer reads immutable vendor source/license/dependencies | Approval covers exact source/action; unknown third parties need specific confirmation |
| Reviewed → vendored | Distribution selects files, records patches/hashes/notices | Offline public content; no credential or audit evidence copied |
| Vendored → isolated render | Chezmoi, exact targets, scripts excluded | Complete byte/file-set checks and second-apply no drift |
| Rendered → shared files | Review collisions; exact-target host preview/apply | Shared discovery content only; native scanner/provider remains separate |
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
prove no subscription. OSV strict-offline readiness separately requires selected
local databases and documented freshness; setup downloads none and scans nothing.
Update/rollback preserves prior generations and the exact source/lock records.
