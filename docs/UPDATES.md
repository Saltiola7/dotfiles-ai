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
| Native OpenCode | [Bootstrap](../dot_local/bin/executable_opencode-install.tmpl) is missing-only on supported macOS ARM64 and Linux ARM64/AMD64 source routes; reapply is not an upgrade and must not downgrade a healthy newer binary. The [contract](specs/dotfiles_ai_distribution/features/native-platform-updates.md) selects native notify/manual `/update`, no automatic installation or implicit shared-service restart. Use only after that environment's native ownership is qualified/activated. Do not invoke legacy `opencode-update-all` on selected native routes. Legacy Linux pins in TOML are not native update authority. |
| Native Codex | macOS ARM64 [bootstrap](../dot_local/bin/executable_codex-install.tmpl) owns the separate native install directory and preserves `CODEX_HOME`. On the qualified native route, use explicit `codex update` through the managed environment exporting `CODEX_INSTALL_DIR`; no legacy `codex-update-all`. Linux source routing remains distinct in [the apply hook](../run_after_update-codex.sh.tmpl)—do not infer native parity. The contract requires native daemon automatic installation disabled independently of notifications; its settings interface was qualified for 0.160.1 and needs requalification on later releases. |
| Herdr | Chezmoi owns the version/protocol/asset URL/SHA-256 tuple in [defaults](../.chezmoidata.toml), with selected local TOML overrides. Review/update the coherent tuple for each supported architecture, installers and matching skill; this is not a `herdr update` command. The [macOS installer](../run_onchange_before_install-herdr.sh.tmpl) checks the asset, version and server protocol, then uses supported live handoff without killing/restarting panes. It refuses incompatible clients, missing handoff support or more than 64 panes. The [Linux installer](../run_onchange_after_install-00-remote-herdr.sh.tmpl) refuses an executable upgrade while its server is active; defer to a separately approved maintenance plan, not an automatic stop. See the operational hold below. |
| Worktrunk | [Brewfile](../Brewfile) declares it on macOS, but [workflow policy](../dot_local/bin/executable_workflow-policy) requires **exactly `wt v0.80.0`**. [Linux workstation](../run_onchange_after_install-workstation-tools.sh.tmpl), [guest/remote](../run_onchange_after_install-guest-development-tools.sh.tmpl) and [CI](../.github/workflows/test.yml) installers also pin 0.80.0 with architecture-specific checksums. Do **not** blanket `brew upgrade worktrunk`. A newer release needs source/interface/checksum/guard requalification before any host update; do not merely relax the guard. |
| Homebrew and host prerequisites | Brewfile contains only the Anomaly tap, `mise` and `worktrunk`; it is not a complete host inventory. Chezmoi, Git, Python, uv, Bun, Lima and other preinstalled host prerequisites retain their actual native installation owner unless a source installer explicitly owns them. Review each owner's supported update procedure separately; no blanket Brew/OS upgrade or second competing installer. |
| Python / uv / Bun / CI | [pyproject.toml](../pyproject.toml) requires Python >=3.12 and a pytest test group; [uv.lock](../uv.lock) owns its resolved transitive test dependencies. Review constraints and regenerate/review the lock together when changing that family; updating uv itself is separate from updating this lock. [CI](../.github/workflows/test.yml) owns Python 3.12–3.14, setup actions, Bun 1.3.14 and the separate `opencode-ai@1.18.35` test fixture. Those are not live OpenCode pins or permission for a global Bun upgrade. Review the [CentOS workflow](../.github/workflows/centos-remote-user.yml) independently. |
| Optional Hermes | Disabled by default. [Installer](../run_onchange_before_install-hermes.sh.tmpl) pins Hermes 0.19.0 wheel/SHA and Python 3.13.16 and rejects unsupported existing versions. README documents manual `hermes update --backup` followed by profile health verification, but a newer version can conflict with that installer guard. Reconcile/requalify the source pin before approved maintenance; do not promise any latest release works on reapply. Preserve the backup and authenticate only interactively in that environment. |
| Lima, guest OS and remote user | [Lima template](../private_dot_config/dotfiles-ai/lima/workspace.yaml.tmpl) selects Fedora 44, minimum Lima 2.1.4, and separately pinned guest Herdr 0.9.1/chezmoi 2.69.4 assets; changing host TOML does not update those literals. [Guest/remote installer](../run_onchange_after_install-guest-development-tools.sh.tmpl) owns pinned Compose, Worktrunk, 1Password CLI and gcloud assets. Guest OS packages use the guest package owner; host Lima uses its installed owner. Guest recreation, OS updates and remote activation are separate reviewed work, not host dependency refresh. Never boot, recreate or update every guest/remote automatically. |
| Podman, Compose, PostgreSQL and Atuin server | Supported containers are rootless **inside selected managed guests**, not a host-runtime rollout ([configuration](../config.example.toml)). Podman comes from guest provisioning; Compose is asset-pinned. PostgreSQL image/backup location are selected local inputs. [Postgres configuration](../run_onchange_after_configure-pm-postgres.sh.tmpl) can invoke legacy tooling, update Lima, migrate data and reload a backup job: it is not a safe generic refresh, especially on a native route. Review enabled Atuin/Postgres service configuration, image compatibility, backups and exact restart/migration plan separately. |
| Embeddings, reranker and models | Optional [embedding installer](../run_onchange_after_install-dbsctr-embedding.sh.tmpl) owns exact llama.cpp/model revisions, sizes and hashes. [Quality installer](../run_onchange_after_install-dbsctr-quality-services.sh.tmpl) and [space manifests](../private_dot_config/dotfiles-ai/knowledge/) own additional runtime/model identities. A new model is not just “latest”: preserve dimensions, space compatibility, artifact verification and required benchmark activation. Keep retrieval activation separate from candidate installation. No paid model requests are needed for this runbook. |
| Auth CLIs | Guest/remote `op` and gcloud are version/checksum-pinned by the guest installer; host `op`, gcloud, `gh` and optional Tailscale retain their actual installation owner unless explicitly provisioned. Updating a binary is not credential migration or reauthentication consent. Preserve isolated ADC, Keychain and per-environment boundaries; never print tokens or copy credentials between hosts/guests. |
| Shell tools, skills and Graphify | [Atuin](../run_onchange_after_install-atuin.sh.tmpl), [Starship](../run_onchange_after_install-starship.sh.tmpl) and [bash-preexec](../run_onchange_after_install-bash-preexec.sh.tmpl) have source-owned release/commit and checksum pins for their selected routes. Repository [skills](../dot_agents/skills/) update with reviewed source; [Herdr skill](../run_onchange_after_install-herdr-skill.sh.tmpl) is generated by the matching pinned binary. The optional quality installer stages a specific Graphify SQL runtime (0.9.48), used by [the adapter](../dot_local/bin/executable_dbsctr-graphify); qualify that runtime/adapter together, not an unrelated global Graphify package. Other preinstalled skills are not automatically owned here. |

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
