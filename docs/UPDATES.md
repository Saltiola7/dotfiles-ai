# Manual dependency updates

Use this when an upstream release becomes available. **There is no universal
upgrade-all command or background autoupdate enabled by this runbook.** “All
dependencies” means the manifests, installers and supported optional features in
this repository—not every program already installed on a host.

This is operator reference, not activation approval. The active workflow backlog
is source-only: merge it first, then approve an exact host plan before activation.
No fleet rollout, VM operation, service restart or ownership migration is implied.
The [native-platform update contract](specs/dotfiles_ai_distribution/features/native-platform-updates.md)
distinguishes prepared source from deployed qualification; do not infer host state
from a branch's templates.

The shared `dotfiles-ai-update` skill is the conversational entry point for
dependency checks and explicit updates. It resolves this selected source even
when invoked from another project. It reads this runbook rather than maintaining
a second inventory. Source preparation does not install the skill automatically.

## Check after a package-manager upgrade

A check is read-only. Use the owner table and bounded version/health probes below;
do not run the update sequence's pull, backup, apply, installer or restart commands.
Compare actual selected executables with their platform-specific source owner,
then report each family as checked, incompatible, unavailable or disabled. Version
output establishes availability only; distinguish it from running-service health,
authentication, stored-state compatibility and activation. Native diagnostic
commands may start a service: verify their interface before using them as a check.

“All dependencies” covers the declared families below, including plugins, optional
services and CI inputs. Resolve effective profile conditions before probing them.
In particular, disabled knowledge-store ownership also disables its managed
quality/reconcile routes even if subordinate flags remain true. Configuration
exclusion does not prove an old installed process has stopped. Do not start a
disabled feature to complete an inventory or claim fleet health from one host.

For each family record privately: source revision/declaration, selected environment,
installer owner, source constraint, installed/running version, check/result, and
remaining action. Review transitive dependencies through their existing locks;
wheel hashes or direct pins alone are not full dependency locks. Published reports
contain portable conclusions, not resolved configuration or host inventories.

If a Worktrunk upgrade blocks the repair checkout, preserve installed state and
seek explicit approval for an isolated official previously qualified binary.
Verify its archive against the recorded checksum and use it only for native
checkout creation with unchanged hooks. Keep the normal executable, configuration,
activation and existing work in place. This is a bounded bootstrap, not a fake
version response, hook bypass or automatic downgrade; fresh source qualification
and separately approved activation still follow.

## Quick checklist

1. Check release notes; select **one tool on one environment**.
2. Find its owner below. Back up affected state and record installed/running versions.
3. Review any required pin change and tests; preview the exact deployment.
4. After approval, use that owner's update route; do not restart unrelated services.
5. Verify the new binary **and** running service; stop on failure, preserving backups.

For an already qualified native installation: OpenCode uses its interactive
`/update`; Codex uses `codex update` in its managed environment. Herdr and
Worktrunk need the reviewed pin/qualification procedure below, not a generic
“latest” command. These instructions do not authorize executing an update now.

## Detailed sequence

1. **Choose one environment and one update family.** Read its release notes and
   the owner table below. Check the selected machine-local chezmoi TOML against
   [the example](../config.example.toml): local overrides can retain old pins,
   change state roots or enable services. Inspect privately; never publish values.
2. **Preserve before changing.** Inspect the source checkout's branch and dirty
   state; stop on unreviewed local changes. Record the current revision, selected
   executable paths/versions and running-service versions separately. Back up the
   affected configuration and state privately; obtain service-consistent database
   backups before a migration. Confirm the configured state volume is available.
3. **Review source first.** For an already clean checkout on the intended tracking
   branch, the [README](../README.md#update-and-validate) uses:

   ```sh
   git -C ~/.local/share/chezmoi-dotfiles-ai pull --ff-only
   chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
   ```

   Substitute the actual selected source/config paths. A fast-forward is not a
   review: inspect the incoming changes and rendered scripts before activation.
   Dry-run output can contain private configuration; keep it local. A pin change
   still needs a reviewed source change and qualification, not an ad-hoc host edit.
4. **Apply only the approved change.** After backlog merge and exact host-plan
   approval, use the selected owner's route below. For chezmoi changes, preview
   the exact target selection again and activate only the reviewed target/script
   set. Do not copy the README's unqualified full `apply` as a harmless refresh:
   scripts can download binaries, provision guests, migrate databases or reload
   services. Do not guess target paths or run raw template scripts.
5. **Verify, record, stop.** Use the checks below. Leave other environments alone;
   record deferred families/platforms rather than trying to force version equality.

## Which owner updates what?

| Family | Existing owner and safe maintenance boundary |
|---|---|
| Optional Cline Desktop / CLI | Independent default-off `cline_desktop.enabled` and `cline_cli.enabled` switches select missing-only installation. Desktop uses the official Homebrew `cline-app` cask on macOS; new CLI installations use npm `cline@3.0.73` on macOS/Linux. Existing installations keep their owner/version. Desktop updates use its native updater or explicitly selected Homebrew cask upgrade; CLI updates use explicit npm installation after reviewing the candidate. Do not replace the deprecated Homebrew CLI formula with npm implicitly. Shared Vertex configuration requires CLI 3+, uses `cline_vertex.enabled` and inherits `opencode.vertex_*`; `cline-vertex` / `cline-desktop` supply the exact ADC path renewed by `vertex-reauth` in a dedicated `~/.cline-vertex` profile and loopback Hub. Finish managed sessions and stop only that profile Hub before changing ADC paths/ports; reauthentication may require restarting it. Default Cline profiles/history remain separate. Check local readiness with each launcher's `--check`, not a paid model request. Native settings preimages under `~/.config/dotfiles-ai/backups/cline/` can contain secrets: retain privately, restore only with Cline stopped, and never publish them. Setting a switch false does not uninstall or delete native data. |
| Native OpenCode | [Bootstrap](../dot_local/bin/executable_opencode-install.tmpl) is missing-only on supported macOS ARM64 and Linux ARM64/AMD64 source routes; reapply is not an upgrade and must not downgrade a healthy newer binary. The [contract](specs/dotfiles_ai_distribution/features/native-platform-updates.md) selects native notify/manual `/update`, no automatic installation or implicit shared-service restart. Use only after that environment's native ownership is qualified/activated. Do not invoke legacy `opencode-update-all` on selected native routes. Legacy Linux pins in TOML are not native update authority. |
| Native Codex | macOS ARM64 [bootstrap](../dot_local/bin/executable_codex-install.tmpl) owns the separate native install directory and preserves `CODEX_HOME`. On the qualified native route, use explicit `codex update` through the managed environment exporting `CODEX_INSTALL_DIR`; no legacy `codex-update-all`. The explicit [headless Linux ARM64 profile](../config.headless-server.example.toml) has its own native missing-only route; ordinary Linux routing remains distinct in [the apply hook](../run_after_update-codex.sh.tmpl). The contract requires native daemon automatic installation disabled independently of notifications; its settings interface was qualified for 0.160.1 and needs requalification on later releases. |
| Herdr | Chezmoi owns the version/protocol/asset URL/SHA-256 tuple in [defaults](../.chezmoidata.toml), with selected local TOML overrides. Review/update the coherent tuple for each supported architecture, installers and matching skill; this is not a `herdr update` command. The [macOS installer](../run_onchange_before_install-herdr.sh.tmpl) checks the asset, version and server protocol, then uses supported live handoff without killing/restarting panes. It refuses incompatible clients, missing handoff support or more than 64 panes. The [Linux installer](../run_onchange_after_install-00-remote-herdr.sh.tmpl) refuses an executable upgrade while its server is active; defer to a separately approved maintenance plan, not an automatic stop. See the operational hold below. |
| Worktrunk | Homebrew owns the Mac executable. The source validator supports exact **0.80.0 and 0.81.0 on macOS**, and only **0.80.0 on Linux**; activation binds the actual version. The macOS bundle hook requires and pins 0.81.0 before non-upgrading reapply. [Linux workstation](../run_onchange_after_install-workstation-tools.sh.tmpl) and [guest/remote](../run_onchange_after_install-guest-development-tools.sh.tmpl) remain on checksum-pinned 0.80.0. [CI](../.github/workflows/test.yml) exercises both Mac versions. Follow [Worktrunk on macOS](#worktrunk-on-macos); source support does not activate a host. |
| Homebrew and host prerequisites | Brewfile contains only the Anomaly tap, `mise` and `worktrunk`; it is not a complete host inventory. Chezmoi, Git, Python, uv, Bun, Lima and other preinstalled host prerequisites retain their actual native installation owner unless a source installer explicitly owns them. Review each owner's supported update procedure separately; no blanket Brew/OS upgrade or second competing installer. |
| Python / uv / Bun / CI | [pyproject.toml](../pyproject.toml) requires Python >=3.12 and a pytest test group; [uv.lock](../uv.lock) owns its resolved transitive test dependencies. Review constraints and regenerate/review the lock together when changing that family; updating uv itself is separate from updating this lock. [CI](../.github/workflows/test.yml) owns Python 3.12–3.14, Node 26.12.1, Node-24-based setup actions, Bun 1.4.4 and the separate `opencode-ai@1.19.4` test fixture. Those are not live OpenCode pins or permission for a global Bun upgrade. Review the [CentOS workflow](../.github/workflows/centos-remote-user.yml) independently. |
| Optional Hermes | Disabled by default. [Installer](../run_onchange_before_install-hermes.sh.tmpl) pins Hermes 0.19.0 wheel/SHA and Python 3.13.16 and rejects unsupported existing versions. README documents manual `hermes update --backup` followed by profile health verification, but a newer version can conflict with that installer guard. Reconcile/requalify the source pin before approved maintenance; do not promise any latest release works on reapply. Preserve the backup and authenticate only interactively in that environment. |
| Lima, guest OS and remote user | [Lima template](../private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl) selects Fedora 44, minimum Lima 2.1.4, and separately pinned guest Herdr 0.9.1/chezmoi 2.69.4 assets; changing host TOML does not update those literals. [Guest/remote installer](../run_onchange_after_install-guest-development-tools.sh.tmpl) owns pinned Compose, Worktrunk, 1Password CLI and gcloud assets. Guest OS packages use the guest package owner; host Lima uses its installed owner. Guest recreation, OS updates and remote activation are separate reviewed work, not host dependency refresh. Never boot, recreate or update every guest/remote automatically. |
| Optional local Dagger shadow | Distribution's [explicit local-engine bootstrap](../private_dot_config/dotfiles-ai/continuous_validation/local_engine.py) owns a private checksum-pinned Dagger 0.21.10 CLI, the isolated locked Python SDK environment, and one dedicated 2-CPU/4-GiB Lima worker. `continuous-validation engine plan` is read-only; only `engine setup --enable-shadow` installs or starts this optional worker. Its Fedora image, Dagger engine, and Python/uv image are digest-pinned; rootful Podman is confined to this worker, with no host mounts or SSH-agent forwarding and a private Unix socket. Existing agent guests keep their rootless policy. Ordinary checks never provision the host CLI/SDK or start a VM; repository-owned uv commands may sync their frozen workload environments. Reuse requires the owned stamp and unchanged configuration; version drift requires reviewed requalification. This source route is not evidence of a deployed or qualified engine. |
| Optional PR-Agent review | The [review contract](specs/continuous_validation/PR-AGENT.md) selects PR-Agent 0.49.0 at an immutable image digest, including its Python and LiteLLM dependencies. Shared continuous-validation installation owns the private worker integration; upstream image tags alone never select an upgrade. Source changes, image provenance, dependency risk and affected regression/runtime qualification must be reviewed together. Review and feedback remain default-off. Interactive Vertex renewal stays with the existing isolated `vertex-reauth` owner. Installation and synthetic qualification never make a live provider call; real review needs separately explicit private model/disclosure settings and activation. |
| Podman, Compose, PostgreSQL and Atuin server | Supported containers are rootless **inside selected managed guests**, not a host-runtime rollout ([configuration](../config.example.toml)). Podman comes from guest provisioning; Compose is asset-pinned. PostgreSQL image/backup location are selected local inputs. [Postgres configuration](../run_onchange_after_configure-pm-postgres.sh.tmpl) can invoke legacy tooling, update Lima, migrate data and reload a backup job: it is not a safe generic refresh, especially on a native route. Review enabled Atuin/Postgres service configuration, image compatibility, backups and exact restart/migration plan separately. |
| Embeddings, reranker and models | Optional [embedding installer](../run_onchange_after_install-dbsctr-embedding.sh.tmpl) owns exact llama.cpp/model revisions, sizes and hashes. [Quality installer](../run_onchange_after_install-dbsctr-quality-services.sh.tmpl) and [space manifests](../private_dot_config/dotfiles-ai/knowledge/) own additional runtime/model identities. A new model is not just “latest”: preserve dimensions, space compatibility, artifact verification and required benchmark activation. Keep retrieval activation separate from candidate installation. No paid model requests are needed for this runbook. |
| Auth CLIs | Guest/remote `op` and gcloud are version/checksum-pinned by the guest installer; host `op`, gcloud, `gh` and optional Tailscale retain their actual installation owner unless explicitly provisioned. Updating a binary is not credential migration or reauthentication consent. Preserve isolated ADC, Keychain and per-environment boundaries; never print tokens or copy credentials between hosts/guests. |
| Shell tools and skills | [Atuin](../run_onchange_after_install-atuin.sh.tmpl), [Starship](../run_onchange_after_install-starship.sh.tmpl) and [bash-preexec](../run_onchange_after_install-bash-preexec.sh.tmpl) retain their selected source-owned pins. Repository [skills](../dot_agents/skills/) update with reviewed source; [Herdr skill](../run_onchange_after_install-herdr-skill.sh.tmpl) is generated by its matching binary. Other preinstalled skills are not automatically owned here. |
| Global Graphify | This source's [native uv bootstrap and skill hook](../run_onchange_after_install-graphify.sh.tmpl) owns the single executable version/dependency recipe on macOS ARM64. Existing healthy installations are retained, not upgraded or migrated on reapply. The [project adapter](../dot_local/bin/executable_dbsctr-project-graphify) consumes this CLI with each cycle's exact version selection. Follow [Graphify](#graphify) before an explicit update; personal dotfiles must not retain a competing package/installer declaration. |
| Optional DKS Graphify | The [quality installer](../run_onchange_after_install-dbsctr-quality-services.sh.tmpl) stages the separate hash-pinned SQL runtime 0.9.48 used by [dbsctr-graphify](../dot_local/bin/executable_dbsctr-graphify). Package, Python, runtime and producer identities are jointly bound. Preserve it and its disabled state; updating the global CLI neither updates nor qualifies this consumer. |
| OpenCode plugins and SDKs | [Managed configuration](../.chezmoitemplates/opencode.json.tmpl) selects `@dietrichgebert/ponytail@4.10.3` and unversioned `@ai-sdk/openai-compatible` provider adapters. Repository [DKS tool](../private_dot_config/opencode/tools/dks.ts) and [maintenance observer](../private_dot_config/dotfiles-ai/opencode-maintenance-observer/tui.ts) consume distinct OpenCode plugin APIs. Review their native runtime compatibility and actual resolver ownership; source identifiers alone are not a transitive lock. Preserve vendor-owned caches/locks excluded by [.chezmoiignore](../.chezmoiignore). Loading/installing a plugin is not a read-only probe. |
| MCP and Node tooling | [Managed configuration](../.chezmoitemplates/opencode.json.tmpl) declares remote Context7, macOS `1password-mcp`, and disabled browser tools `chrome-devtools-mcp@1.12.0` / `@playwright/mcp@0.0.83`. Node/npm/npx and the 1Password MCP executable retain their installed owners. `npx` may download packages; do not invoke it merely to inventory a disabled server. Authentication and enabling a server are separate actions. |
| Optional JFrog CLI and skills | The default-off [missing-only installer](../run_onchange_after_install-jfrog-cli.sh.tmpl) owns official 2.129.0 assets only when no selected CLI exists. Preserve existing compatible native owners; do not silently upgrade an older CLI. Review upstream release, all supported hashes, isolated qualification and failure/idempotence tests before updating. Seven complete [skills](../dot_agents/skills/jfrog/UPSTREAM.md) share immutable provenance and reversible adaptations in the specialist inventory; review the full resource/helper tree and local ownership patches together. Skill updates do not install a plugin, Agent Guard or MCP, log in, change native client settings or bypass project scans. Retain private deployment preimages and existing authentication for rollback. |
| Optional self-hosted Prefect MCP | [Dedicated project and lock](../private_dot_config/dotfiles-ai/runtime/prefect-mcp/pyproject.toml) bind official source commit, runtime closure and hash-pinned isolated build constraints. The [launcher](../dot_local/bin/executable_prefect-mcp) is the explicit installer/qualifier; use an existing Python 3.13, never a project environment or interpreter download. Review upstream factory/settings/tool changes and advisory results before regenerating the lock; run offline qualification and native stdio/catalog tests again. Native clients own registration, private settings own API/authentication selection, and the existing Prefect owner retains backend service/profile changes. Disabling opt-in does not uninstall a generation or remove a previously registered Codex entry: remove only the exact reviewed entry with the native writer and explicitly reconcile its projector. Retain generations and private preimages for rollback. |
| Inference providers and local models | [Defaults](../.chezmoidata.toml), [managed configuration](../.chezmoitemplates/opencode.json.tmpl) and [agent definitions](../private_dot_config/opencode/agents/) select hosted model IDs and optional LM Studio models. IDs such as an `@default` model are service selections, not immutable artifact checksums. Report configured identities without issuing paid requests; separately qualify availability, capabilities and any changed model behavior. LM Studio owns its installation and model downloads. |
| Optional PostgreSQL/pgvector build | [Containerfile](../dot_local/share/pm-kernel/Containerfile.pgvector) pins the PostgreSQL 19beta3 base digest, development-package version and pgvector 0.8.6 source tuple. [Image builder](../dot_local/bin/executable_pm-postgres-image-build) owns building; configured runtime image selection is separate. Build tools still resolve from the package repository. Image rebuild, data migration, backup and service activation each require their own reviewed scope. |
| Optional Atuin server | [Quadlet](../private_dot_config/containers/systemd/atuin.container) pins Atuin 18.17.1 by image digest and stores SQLite state. This is distinct from the platform's Atuin client owner; changing a client does not update or qualify the server. Preserve server data and review compatibility before container replacement. |
| Reranker Python closure | [Requirements input](specs/dbsctr_knowledge_store/DKS-003.reranker-requirements.in), [macOS ARM64 hash lock](specs/dbsctr_knowledge_store/DKS-003.reranker-macos-arm64-py312.lock) and [runtime/model manifest](../private_dot_config/dotfiles-ai/knowledge/reranker-space.json.tmpl) jointly own Python 3.12.11, torch 2.9.1, transformers 5.5.0, tokenizers 0.22.2 and safetensors 0.7.0. Preserve artifact/model revisions and activation benchmark boundaries; a different global Python or package set is not equivalent. |
| Jira and native platform utilities | Jira `acli`, Git/gh, lsof, xz, native mount tools and Apple Swift/SDK are prerequisites with their existing platform owners. [Jira adapter](../dot_local/bin/executable_pm-jira.tmpl) and [Host build hook](../run_onchange_before_build-herdr-host.sh.tmpl) define consumers. Updating the CLI/compiler does not grant authentication, publication, signing, app registration or process-control authority. |

### Platform and lock distinctions

- The October 2026 Node security releases are 22.23.4, 24.22.1 and 26.12.1.
  Check both installed and running runtimes: replacing a binary does not update
  existing MCP processes. Application-bundled Node and OpenCode's compiled Bun
  runtime require their own installer owners; a host Node/Bun update does not
  patch them. CI action runtimes come from the runner, independently of the
  Node version selected for test commands. Bun 1.4.4 includes separate security
  fixes; retain installer ownership if a package-manager release lags.

- Host Atuin/Starship may be Homebrew-owned while guest/remote installers pin
  Atuin 18.17.1 and Starship 1.26.0. Their source installers exclude macOS; do not
  diagnose newer host clients as guest pin violations.
- Hermes pins its wheel and Python interpreter, but does not supply a repository
  transitive dependency lock. Record its resolved environment separately before
  any explicit upgrade; do not promise reproducibility from the wheel hash alone.
- [Remote bootstrap](../dot_local/bin/executable_remote-user-bootstrap) separately
  pins chezmoi 2.69.4 on Linux AMD64. Lima's guest literals and ordinary Codex guest
  bootstrap are independent of the current host's native installation.
- CI action tags and runner/container tags may move. The
  [CentOS job](../.github/workflows/centos-remote-user.yml) uses `ubuntu-latest` and
  `stream10`; OS package managers own their package versions. Review CI changes
  as CI input changes, not evidence that the live host was updated.
- Explicitly select the supported validation interpreter. An unconstrained
  `uv run` may choose a newer installed Python than the tested CI matrix even
  while `python3` resolves another interpreter. Package lock identity does not
  pin the interpreter or keep a Homebrew-backed virtual environment alive after
  its base interpreter is removed.

## Graphify

`graphifyy` is the Python package; `graphify` is its CLI. The
[hook](../run_onchange_after_install-graphify.sh.tmpl) is the sole executable recipe:
review its `VERSION` and `ADDITIONS` together, rather than maintaining a second
install command here. The new bootstrap selects an already-installed system Python
3.12–3.14 through uv; it never downloads Python. Existing native runtimes retain
their actual interpreter and package version. Default Linux, headless and Intel
Mac profiles do not acquire a new installation route.

### Check without changing the environment

1. Inspect `command -v graphify` and resolve that entry point's symlink. In its
   real native uv environment, identify sibling `bin/python` and
   `uv-receipt.toml`; verify receipt ownership and the recorded `graphify` entry
   point. Read only bounded version and requirement metadata, privately.
2. Compare that environment's parent tool root with `uv tool dir` and its recorded
   entry-point directory with `uv tool dir --bin`. A changed XDG root can make
   plain `uv tool list` miss an existing CLI. Inventory the confirmed owner with
   explicit `UV_TOOL_DIR`; never interpret an empty default inventory as consent
   to install a second environment. Broken links, orphan receipts or competing
   owners stop maintenance; no `--force` or silent migration.
3. Check the actual runtime's `graphify --version`, package/interpreter identity,
   required imports and `uv pip check --python <actual-runtime-python>`. Check the
   OpenCode skill's `.graphify_version`, `SKILL.md` and complete packaged references
   separately. These checks establish neither provider authentication nor project
   graph freshness. Do not use `uv tool run`/`uvx` merely to locate an interpreter;
   they can install another environment.

### Qualify, update and verify

1. Review the exact candidate and hook recipe before any host change. Preserve
   adapter additions (`boto3`, HCL, language-pack and SQL grammars) and existing
   extras such as `anthropic[vertex]`. Follow upstream's parser ABI and grammar
   constraints; newest grammar versions are not automatically compatible.
   Direct pins and uv receipts are not a full transitive hash lock. Retain the
   complete resolved package inventory and actual Python identity privately.
2. Account for active cycles and batches selecting the old exact Graphify version.
   Their adapter snapshots do **not** snapshot the external CLI environment.
   Finish those consumers or prepare a separately qualified preserved runtime
   before switching their selected executable. Never rewrite their recorded
   version or interpret an unknown consumer inventory as safe to upgrade.
3. In disposable fixtures, with independent HOME/tool/bin/cache directories and
   no credentials or external provider access, qualify imports, Python/SQL/HCL/R
   parsing, native AST/update/query, complete skill installation and native
   OpenCode discovery. Run the managed adapter's tests against that exact runtime,
   including genuine warm/cold/partial cache counters and no-change provenance.
   Version output or mocked fixtures alone do not qualify the candidate. The
   optional `GRAPHIFY_NATIVE_TEST_EXECUTABLE` (installer suite) and
   `DBSCTR_GRAPHIFY_NATIVE_TEST_EXECUTABLE` (adapter suite) inputs select an
   already-prepared test runtime; neither is a production override or installer.
4. Preserve runtime, interpreter, receipt/extra requirements and skill preimages
   privately. Verify recovery can restore the compatible generation at its
   original identity; a copied/moved virtual environment is not automatically
   relocatable. Preview the exact native update, source/hook deployment, skill
   refresh, checks and recovery, then obtain separate approval for that host plan.
5. Only after approval, use native `uv tool install --upgrade` with the exact
   approved requirement and qualified existing Python, `--no-python-downloads`,
   and the complete reviewed `--with` requirements. Address the **confirmed**
   `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR`, not a new default root. Merge the hook's
   requirements with retained required extras; omission can silently drop them.
   This is one selected tool, not `uv tool upgrade --all`, a Python upgrade or
   authorization to replace an unknown owner.
6. Preview/select only the reviewed Graphify hook through native chezmoi with the
   selected source and machine config. `apply --dry-run --verbose --source-path`
   accepts its exact source script path. Confirm the plan actually runs it: an
   unchanged `run_onchange` hook is not re-triggered by a package upgrade alone.
   The reviewed recipe/source change normally supplies that trigger; otherwise
   stop and plan an exact native rerun, not a blanket state-history reset. Never
   execute a raw template or run `graphify install` from a working repository.
7. The hook checks the actual runtime, invokes native skill installation inside
   private scratch, validates its complete packaged bundle, and publishes only
   the matching user skill. Changed prior skills are retained privately under
   OpenCode's `graphify-backups`, outside skill discovery. Repeat checks must show
   matching CLI/package/skill versions, required imports and unchanged unrelated
   project/config/plugin/hook state. Do not rebuild a real project's graph merely
   to complete a binary update.

On failure retain the observed installation, preimages and failed evidence. Stop
dependent updates; restore only a reviewed compatible runtime/skill generation,
not an assumed automatic downgrade. Keep real graphs, caches, cycle receipts and
the separate DKS 0.9.48 runtime untouched. No deletion, fleet rollout, paid request
or live activation follows from source delivery or this runbook.

## Worktrunk on macOS

Use Homebrew's native pin so ordinary `brew update && brew upgrade` skips
Worktrunk. A pin protects the installed version; it is neither a lockfile nor a
promise that an arbitrary older release can later be installed by Homebrew.

1. Inspect the selected `wt --version`, Homebrew executable owner,
   `brew list --versions worktrunk`, `brew list --pinned --versions`, and private
   workflow activation. Keep effective roots and host details private.
2. Select an exact upstream release. Review hooks, templates, destination
   variables, project selectors, config precedence and foreground removal. Verify
   official archive checksums and run disposable native compatibility tests before
   changing the live binary. Test both retained 0.80.0 and candidate 0.81.0 routes.
3. Prepare the matching source helper, removal check, CI checksums, guidance and
   configuration. The current 0.81.0 successor preserves template creation; custom
   `switch --path` remains an explicit operator exception outside automatic agent
   allocation. Do not describe its destination as validated by pre-switch.
4. Preview the exact host generation and preserve binary/configuration preimages.
   Confirm the proposed Brew candidate still matches the qualified release using
   `brew info --json=v2 worktrunk`. If it advanced, stop and requalify; do not
   unpin and silently install whatever is latest. Include any prerequisite changes
   and rollback route in the separately approved host plan.
5. After approval, use native `brew unpin worktrunk`, the selected `brew upgrade
   worktrunk` (or reviewed first installation), and `brew pin worktrunk` only as
   needed for the exact version. Preserve preimages before Brew cleanup can remove
   a previous keg. Verify actual selected binary and pinned version afterwards.
   Stop on failure; retain/report actual state rather than claiming rollback.
6. Apply the reviewed helpers and generated policy/configuration coherently, then
   install the freshly validated activation snapshot **last**. `workflow-policy
   snapshot` only prints a proposal; it does not activate it. Old-version snapshots
   deliberately remain invalid after upgrading.
7. Check installed byte identities, `workflow-policy check`, and disposable native
   creation/navigation and hook refusal. Preserve existing branches, worktrees and
   data. A successful version command alone is not a successful deployment.

The managed bundle hook refuses missing, shadowed or unsupported Worktrunk and a
conflicting pin before invoking the bundle. It verifies the pin and uses
`brew bundle --no-upgrade`. That flag suppresses requested upgrades, but installing
a missing formula may still change required dependencies; review missing
prerequisites before applying. `HOMEBREW_NO_AUTO_UPDATE=1` alone only suppresses
formula metadata refresh, not package upgrades. Unrelated package pins are kept.

Recovery when new Worktrunk blocks repair checkout creation: explicitly approve
an isolated, official checksum-verified previously qualified binary for that
bootstrap only. Select it consistently for native Worktrunk and its unchanged
hooks; never fake version output or bypass hooks. Keep the Homebrew installation
and saved activation unchanged while preparing the repair. Later activation
requires its own compatible generation and approval.

## Managed DVC owner and update boundary

The distribution owns the distinct `managed-dvc` executable and its isolated
runtime, not existing bare `dvc` installations or project virtual environments.
The [source input](../private_dot_config/dotfiles-ai/runtime/dvc/requirements.in)
pins DVC 3.67.1, dvc-gs 3.1.0 and the preservation-qualified dvc-data 3.18.3.
The adjacent `requirements.txt` is the resolved transitive hash authority. Review
both together; DVC's direct pin alone is not a reproducible environment.

Regenerate only this lock using existing uv, then review the diff and run the
affected native-runtime/installer/preservation tests:

```sh
uv pip compile private_dot_config/dotfiles-ai/runtime/dvc/requirements.in \
  --python-version 3.12 --universal --generate-hashes --no-annotate --no-header \
  --default-index https://pypi.org/simple \
  --output-file private_dot_config/dotfiles-ai/runtime/dvc/requirements.txt
```

The [installer](../run_onchange_after_install-managed-dvc.sh.tmpl) uses installed
Python 3.12–3.14 and uv; it does not update them or download another interpreter.
It installs hash-checked packages into a generation selected by the lock SHA-256,
qualifies GCS import and exact versions, then marks that generation complete.
Completed generations are verified on reapply. An incomplete or unsafe generation
refuses and requires explicit recovery; the installer does not remove or reuse it.
Package installation uses independent copies; this does not change DVC's
reflink-only cache policy. No old generation or shared cache is collected.

Preview and separately approve the exact lock, managed entry point, installer,
bootstrap and lifecycle-helper target set before activation. Keep their preimages
and deploy them coherently; do not install only a new caller that requires a
missing runtime. Verify `managed-dvc --check-runtime`, installed file identity,
and bounded helper execution. On failure retain work and restore only a reviewed
compatible helper/lock generation; an unavailable backend is not proof of dirty
outputs, failed authentication or missing remote data. GCS connectivity needs its
own authorized check. Guest/remote environments remain unactivated until their
own qualification; the source installer is not fleet consent.
Automatic installation is currently qualified only for macOS. Other platforms
exclude the installer, and explicit unsupported execution refuses before writes.
Managed DVC consumers on those platforms require a separately qualified runtime;
an unavailable runtime retains work without reverting to project/global PATH.

For offline native regression coverage, select an already prepared disposable
managed test home with `MANAGED_DVC_TEST_HOME`; fixtures create their own temporary
configuration and data and read only that home's qualified runtime. The default
test environment does not install DVC implicitly. This selection is test-only and
is never a production runtime override.

## Verification and recovery

Herdr source defaults now select 0.9.5/protocol 22. The macOS ARM64 isolated
named-server probe and both selected asset checksums qualify only those source
inputs—not live handoff, Linux execution, guest updates or deployment. The separate
guest literals remain 0.9.1. Upstream 0.9.5 stops installing Codex turn hooks and
uses screen detection for Codex status; review existing integration configuration
and any `herdr integration install codex` change inside the exact approved host
plan, never run it automatically as pin maintenance. See the
[release notes](https://github.com/herdrdev/herdr/releases/tag/v0.9.5).
The operation hold, old-sender pane bound and all installer refusal guards remain.

- In the reviewed source checkout, [the existing validation command](../README.md#update-and-validate)
  is `uv run --group test pytest`. It may resolve/install test dependencies;
  run only in the approved validation environment. Passing source tests does not
  prove host activation or a release's live compatibility.
- Compare selected installed paths/versions against the approved owner/pins and
  running-service versions separately. For Herdr, existing non-mutating checks
  include `herdr --version` and `herdr status server --json`; privately compare
  pane inventory and process continuity before/after any approved handoff.
  Never treat binary replacement as proof that a running service changed.
- The [Herdr operation authority](specs/shell_auth_startup/OPERATION.md) retains
  an operator hold on restart, live capture/restore and recovery-manifest mutation.
  A large-server cold restart is a separately controlled procedure, not a fallback
  in this update sequence. Probe-only `Herdr Host.app` staging does not activate
  ownership or grant privacy permissions. Do not kill/restart a server to bypass
  handoff refusal, alter TCC, or create fallback state on a missing volume.
- Keep private preimages, backups and failure evidence. On failure stop dependent
  updates and diagnose actual binary/service/data versions. Revert only the
  reviewed configuration/binary unit when compatible; preserve paired wrapper/helper
  versions and recovery schema evidence. **Never blindly restore an old OpenCode
  database or PostgreSQL volume after newer software may have written it.** Use
  the service's separately reviewed restore/migration procedure.
- Record locally: source revision, environment, owners, before/after versions,
  checksums where pinned, approved changes, checks/failures and deferrals. Do not
  include credentials, session content or private host inventory in public Git.

## Deliberately unresolved

No new updater, release poller or universal notification service is specified here.
Adding one, qualifying newer Worktrunk/Herdr/Hermes releases, reconciling remaining
legacy/native callers, and activating any source-only platform require future
Discovery with an exact scope and host plan. Existing native OpenCode notification
policy is not a promise to notify for every dependency. Local ownership and live
qualification must be checked by the operator; this document cannot establish them.
