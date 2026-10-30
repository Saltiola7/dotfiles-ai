# dotfiles-ai

DeepWiki generated documentation: [https://deepwiki.com/Saltiola7/dotfiles-ai](https://deepwiki.com/Saltiola7/dotfiles-ai)

Portable macOS configuration for DBSCTR, OpenCode, Herdr, and optional Hermes
orchestration, managed as an independent chezmoi source repository.

This repository manages platform-selected agent installers, pinned Herdr releases,
and AI workbench configuration. It does not store provider credentials or
replace the DBSCTR specifications as lifecycle authority.

## Choose Your Path

| Goal | Start here |
|---|---|
| Install on a new workstation | [Safe Quickstart](#safe-quickstart) |
| Transfer files from another chezmoi source | [Existing Chezmoi Migration](#existing-chezmoi-migration) |
| Start isolated native task work | [Native Task Workspaces](#native-task-workspaces) |
| Configure Git identities and signed commits | [Git identity and signing guide](docs/git-identity-signing.md) |
| Enable autonomous R&D | [Optional Autonomous RD](#optional-autonomous-rd) |
| Create isolated Fedora workspaces | [Optional Lima Workspaces](#optional-lima-workspaces) |
| Configure a standalone CentOS user | [CentOS Remote User Foundation](#centos-remote-user-foundation) |
| Maintain this repository | [Update And Validate](#update-and-validate) and [Documentation Authority](#documentation-authority) |
| Update tools and dependencies | [Manual update runbook](docs/UPDATES.md) |

The shared `dotfiles-ai-update` skill uses that runbook for dependency checks and
explicit updates, including when invoked from another project. A check inventories
declared dependencies without installing or restarting them. Source delivery and
installation of the skill remain separate; see the runbook's owner boundaries.

## Requirements

- macOS
- [Homebrew](https://brew.sh/)
- [chezmoi](https://www.chezmoi.io/)
- [Herdr](https://herdr.dev/)
- Python 3.12+ and `uv` for repository validation
- Worktrunk for task checkout management; `lsof` for removal checks (`xz` also required on Linux)
- Optional: 1Password CLI for `op-session`
- Optional: Lima for managed Fedora workspaces
- Optional: Hermes for autonomous R&D; enabled installations manage it through
  this source

### Graphify ownership

The [Graphify contract](docs/specs/dotfiles_ai_distribution/features/graphify-ownership.md)
assigns the global CLI, dependency recipe and matching OpenCode skill to this
source. The disabled, hash-pinned DKS runtime remains separate. Consult the
[update runbook](docs/UPDATES.md) before changing a native installation; source
delivery does not approve a live upgrade or ownership migration.

## Safe Quickstart

> [!WARNING]
> Review the dry-run before applying. Back up any target already managed by
> another chezmoi source; two sources must not own the same live file.

```sh
mkdir -p ~/.config/dotfiles-ai
git clone https://github.com/Saltiola7/dotfiles-ai.git ~/.local/share/chezmoi-dotfiles-ai
cp ~/.local/share/chezmoi-dotfiles-ai/config.example.toml \
  ~/.config/dotfiles-ai/chezmoi.toml
$EDITOR ~/.config/dotfiles-ai/chezmoi.toml
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
```

The real TOML stays outside the checkout. Its `[data.dotfiles_ai]` values
override public defaults without entering Git history. Restart OpenCode after an
apply because it loads configuration only at startup.
For external-state routing and recovery from missing session history, see
[ADR 0001](docs/specs/opencode_control_plane/adr/0001-preserve-machine-state-routing.md).
Always supply this machine config when deploying from another source worktree;
changing `--source` alone does not supply its machine-local overrides.
OpenCode uses its native missing-only installer. The separate macOS bundle hook
retains Homebrew-owned prerequisites without requesting upgrades. Worktrunk must
first match the qualified macOS version; the hook pins it through native Homebrew.
Follow the [Worktrunk procedure](docs/UPDATES.md#worktrunk-on-macos) before initial
setup or an intentional upgrade.

## Configuration

- `opencode`: provider profile/region, models, local endpoint, and theme.
- `sandbox`: named Lima workspaces, mounts, Git protection, references,
  federation, aliases, and the approved Build destination.
- `herdr`: theme, Aqua LaunchAgent ownership for the Herdr server, and executable.
- `rnd`: optional Hermes profiles, schedule, review workspace, writable source,
  and non-secret GitHub identity.
- `onepassword`: optional account UUID, alias, and Keychain service.
- `tailscale`: default-off workspace enrollment and SSH policy switch; secrets,
  peer identities, and tailnet policy stay external.
- `cline_desktop` / `cline_cli`: independent default-off Cline installations.
- `cline_vertex`: optional shared Vertex Claude selection using the existing
  `opencode.vertex_*` project, region and isolated ADC settings.

When 1Password is disabled, `op-session` is not managed. Herdr and OpenCode keep
their ordinary environment-based authentication.

### Optional Cline Desktop And CLI

Enable either tool in the machine-local chezmoi TOML:

```toml
[data.dotfiles_ai.cline_desktop]
enabled = true

[data.dotfiles_ai.cline_cli]
enabled = true

[data.dotfiles_ai.cline_vertex]
enabled = true
model = "claude-sonnet-5-5@default"
hub_port = 25464
```

Desktop uses Homebrew's `cline-app` cask on macOS. New CLI installations use
`npm install --global cline@3.0.73`; npm must already be available. Installation
hooks preserve existing versions. Shared Vertex settings require CLI 3 or later;
review an explicit npm update for an older installation before using them.
Other providers and settings are preserved, with private preimages retained.

Set `opencode.vertex_project`, `vertex_location`, and `vertex_credentials` as
described in [config.example.toml](config.example.toml), then renew credentials
with `vertex-reauth` when required. Use `cline-vertex` for CLI and `cline-desktop`
for Desktop so the process receives the exact isolated ADC path. They share a
dedicated `~/.cline-vertex` profile and localhost Hub, separate from default Cline
profiles and history. Bare `cline` and Finder launches use their native profile.
`cline-vertex --check` and
`cline-desktop --check` verify local readiness without model requests. Opus is
available by selecting `claude-opus-5-5@default`, subject to project access.

Before changing the ADC path or Hub port, finish managed sessions, quit its
Desktop instance and stop only that profile's Hub:

```sh
cline hub --discovery-path "$HOME/.cline-vertex/data/locks/hub/production.json" stop
```

Reauthentication can also require restarting this Hub. Keep native profiles,
credential files and private backups; none are automatically migrated or removed.

Preview and apply only the selected Cline scripts/configuration/launchers. Setting
flags false stops future management; uninstall and application-data removal remain
explicit. See the [distribution contract](docs/specs/dotfiles_ai_distribution/README.md#optional-cline-domain)
and [maintenance runbook](docs/UPDATES.md) for recovery and update ownership.

### Choose your storage paths

Choose paths in `~/.config/dotfiles-ai/chezmoi.toml`, not public defaults. No
particular username, drive name or external disk is required. Existing settings
have distinct purposes:

| Setting | What it selects |
|---|---|
| `sourceDir` | This chezmoi source checkout; ordinary project repositories stay wherever you keep them |
| `data.dotfiles_ai.state.root` | Optional centralized runtime/session state; absent or empty retains existing home routing |
| `data.dotfiles_ai.workspaces.root` | Parent for newly created native worktrees, not primary repositories |
| `data.dotfiles_ai.workspaces.cache_root` | Parent for repository-scoped immutable DVC caches |

For example, replace these synthetic paths with existing directories you own:

```toml
sourceDir = "/Volumes/Development/repos/dotfiles-ai"

[data.dotfiles_ai.state]
root = "/Volumes/Development/state"

[data.dotfiles_ai.workspaces]
schema_version = 1
root = "/Volumes/Development/worktrees"
cache_root = "/Volumes/Development/dvc-cache"
```

Home directories or Linux mount paths work too; the source/state examples use
absolute paths. Workspace roots additionally support a leading `~/`. Keep caches
outside checkouts and worktree roots. Exact-repository workspace/cache overrides
are shown in [config.example.toml](config.example.toml).

Changing a setting does not authorize relocating repositories, moving live
session data, merging databases or reusing a replacement disk's old identity.
State-root changes need data-preserving migration; new-worktree/cache roots need
separate [storage qualification and activation](docs/specs/dotfiles_ai_distribution/features/workflow-storage-policy.md).
On macOS, an enabled signed Herdr Host also binds `herdr.state_volume_uuid` to
the selected state volume: reusing a drive name does not reuse its UUID.
Its app stays at the current user's `~/Applications/Herdr Host.app`; development
paths do not override that separate signing/registration boundary. Preview with
the same explicit machine config before applying any selected targets.

## Headless Fedora ARM64 Codex

Use [config.headless-server.example.toml](config.headless-server.example.toml)
with a separate chezmoi source and state database. Set `sourceDir` and
`persistentState` to existing owner-controlled paths, then run:

```sh
chezmoi --config ~/.config/dotfiles-ai/chezmoi.toml managed
chezmoi --config ~/.config/dotfiles-ai/chezmoi.toml diff
chezmoi --config ~/.config/dotfiles-ai/chezmoi.toml apply
```

This explicit role manages only `codex-install`, `codex-project` and the
missing-only installation hook. Dotfiles owns Bash and developer packages.
Upstream owns `~/.local/bin/codex` and `~/.codex`; reapply preserves installed
releases, authentication and sessions. Existing unknown executables or unsafe
homes fail closed. Automatic native installation is disabled; run `codex update`
explicitly, review upstream release notes, then rerun validation. Owner signs in
on the target with `codex login --device-auth`; never copy another host's tokens.
Desktop remote enrollment remains a private client setting, not public inventory.

For recovery, restore the source/configuration first, then authenticate locally
or restore an approved encrypted backup. Never remove the native home to fix an
apply failure. See the [ownership and validation contract](docs/specs/codex_control_plane/features/pi400-headless-native.md).

## Native Task Workspaces

Worktrunk owns task checkout creation, navigation and removal. With qualified
storage policy active, new task paths use the configured root and native
repository/branch namespace; older installations retain their existing layout
until separately activated. Existing primary and linked checkout paths and branches
stay stable. Start a native OpenCode or Codex session in the selected checkout. A shell
directory change does not retarget an existing conversation.

Native path templates remain the default. Worktrunk `switch --path` is an explicit
operator exception requiring destination review; managed agents do not select it
automatically. Worktrunk 0.81.0 computes a new custom destination after pre-switch,
so the existing storage hook cannot validate that destination before creation.
macOS source supports exact 0.80.0 and 0.81.0; Linux/guest routes retain 0.80.0.
Changing native version requires matching policy activation after qualification.

For example, an operator can prepare a task against the repository's protected
upstream base and launch Build there:

```sh
wt switch --create topic --base origin/main
git branch --set-upstream-to=origin/main topic
wt switch topic -x agent-worktree -- -- opencode --agent build
```

Use the actual configured base instead of assuming `origin/main`. Worktrunk does
not set tracking for differently named new branches; lifecycle registration
requires that base association. Codex uses the same launch helper with its native
arguments. The helper coordinates foreground launches only; direct launches,
in-UI session switches and background jobs remain outside its busy check.

Use `dbsctrctl` in that checkout for registration, gates and reviewed draft-PR
delivery. Initiative registration requires fresh preflight and explicit approval
of that plan: either terminal `BEGIN CYCLE_ID LAUNCH_DIGEST`, or chat approval
followed by Build's `--approval agent-confirmed` command with the exact launch
digest. The latter records reported consent, not authenticated identity. Existing cycles require
explicit, in-place adoption with retained preimages and uncertainty.

DVC checkouts start code-only. Select the repository-scoped external cache with
`worktree-dvc-setup --cache PATH`; materialize requested targets using native DVC
and reflink-only configuration. Cache/configuration conflicts require explicit
data-preserving migration. Removal requires operator approval and the blocking
managed Worktrunk preservation hook; cache garbage collection is separate.

Managed bootstrap, registration and preservation checks require the explicit
`managed-dvc` runtime with GCS support. Its dedicated dependency lock pins DVC
3.67.1, dvc-data 3.18.3 and dvc-gs 3.1.0 with resolved transitive hashes. A project
virtual environment or another `dvc` on PATH cannot satisfy this prerequisite.
`managed-dvc --check-runtime` qualifies versions/backend imports offline; it does
not verify GCS credentials or remote data. See the [runtime contract](docs/specs/dotfiles_ai_distribution/features/workflow-storage-policy.md#managed-dvc-runtime-qualification)
and [update owner](docs/UPDATES.md). Existing installations require a separately
approved coherent installer/lock/helper activation; source changes alone do not
install this runtime. Failures retain work and distinguish unavailable commands
from unsafe outputs.

The [native-workspace contract](docs/specs/dbsctr_v3_lifecycle/features/worktrunk-native-workspaces.md)
defines the source transition. Existing installations need separately qualified,
operator-approved cutover and restart; source tests do not qualify live adoption,
large-history conversion, Desktop or guest rollout.

## Optional Autonomous R&D

Identity-dependent worker registration, claiming, recovery and dispatch currently
report `native_automation_identity_unavailable`. Federated provider-evaluation
saving reports `native_capture_authority_unavailable`. The retired custom tools
cannot be replaced by caller-supplied session IDs or receipt digests.

Existing workers, reports, history and uncertain operations remain retained.
Bounded local review and explicit operator maintenance remain separate from
autonomous execution. See [`docs/RND_RUNBOOK.md`](docs/RND_RUNBOOK.md) for transition
status and historical recovery reference. Project maintainers must qualify the
native identity, complete capture and permission routes before re-enabling dispatch.

## CentOS Remote User Foundation

The default-off remote user role supports a standalone CentOS Stream 10 x86_64
home without changing the Fedora Lima profile. Host bootstrap supplies system
packages; this source owns pinned user-local `chezmoi`, tools, and configuration.
System prerequisites include `lsof` and `xz`; foundation readiness also verifies
the pinned Worktrunk runtime before running authentication probes.

```sh
git clone https://github.com/Saltiola7/dotfiles-ai.git \
  "$HOME/.local/share/chezmoi-dotfiles-ai"
revision=$(git -C "$HOME/.local/share/chezmoi-dotfiles-ai" rev-parse HEAD)
"$HOME/.local/share/chezmoi-dotfiles-ai/dot_local/bin/executable_remote-user-bootstrap" \
  bootstrap "$revision"
```

The bootstrap accepts only a full commit identity, rejects unowned or symlinked
paths, verifies the public source, installs checksum-pinned `chezmoi`, creates a
mode-`0600` non-secret config for the current home, and invokes the existing
foundation apply. The foundation records an owner-private managed-target
manifest and emits content-free status:

```sh
remote-user-foundation status
remote-user-foundation retry
remote-user-foundation rollback
remote-user-foundation refresh-auth
```

Rendering and startup never authenticate providers. OpenAI, Vertex, Codex,
1Password, and optional Atuin login remain explicit per-user operations. Atuin
server, PostgreSQL, knowledge services, R&D scheduling, and privileged container
daemons stay disabled.

After the foundation succeeds, each user runs their own interactive logins:

```sh
opencode auth login
vertex-reauth
codex login
op signin
remote-agent-readiness
```

Set only the non-secret Vertex project in the private config before running
`vertex-reauth`. The readiness command returns fixed OpenAI, Vertex, Codex, and
1Password success/failure classes plus `ready` or `auth_pending`; it discards
provider output and never prints account, credential, content, session, or path
data.
`refresh-auth` validates the recorded revision, managed targets, configuration,
and pinned runtime versions before running that probe. Damage becomes
`failed_retryable`; incomplete login becomes `auth_pending`; complete probes
become `ready`. It never starts a login.

## Optional Lima Workspaces

Managed Fedora workspaces keep OpenCode, Herdr, credentials, sessions, and
Hermes profiles isolated. Only declared mounts cross the VM boundary. Optional
Tailscale enrollment creates an external tailnet identity that disabling local
configuration does not revoke.

See [`docs/LIMA_SANDBOX.md`](docs/LIMA_SANDBOX.md) for creation, protected mounts,
credentials, federation, updates, recovery, and explicit peer retirement.

## Existing Chezmoi Migration

Do not apply two sources indefinitely. Compare ownership while the personal
source still owns the live files:

```sh
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml managed > /tmp/dotfiles-ai-managed
chezmoi managed > /tmp/personal-managed
comm -12 <(sort /tmp/dotfiles-ai-managed) <(sort /tmp/personal-managed)
```

Back up overlapping live targets, apply this source, verify OpenCode and Herdr,
then remove the transferred source-state files from the personal repository. Do
not add transferred targets to the personal repository's `.chezmoiremove`; that
would delete files now owned here. Complete only after a personal-source dry-run
no longer mentions transferred targets.

Before cutover, retire obsolete deployed DBSCTR V2 paths reversibly:

```sh
backup="$HOME/.local/state/dotfiles-ai/legacy-backup"
for path in \
  .agents/skills/discovery2 \
  .agents/skills/dbsctr2 \
  .config/opencode/commands/discovery2.md \
  .config/opencode/commands/dbsctr2.md
do
  if [ -e "$HOME/$path" ]; then
    mkdir -p "$backup/$(dirname "$path")"
    mv "$HOME/$path" "$backup/$path"
  fi
done
```

Rollback before ownership cleanup by reapplying the personal source. After
cleanup, disable this source's managed services, apply that change, rename this
checkout, restore the personal repository's ownership commit, apply the personal
source, and verify its managed list. Never leave both sources active.

## Update And Validate

```sh
git -C ~/.local/share/chezmoi-dotfiles-ai pull --ff-only
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
uv run --group test pytest
```

Restart OpenCode after managed prompt or configuration changes. Hermes updates
are separate, manual maintenance using `hermes update --backup` followed by
profile health verification.

## Documentation Authority

| Bounded context | Authority |
|---|---|
| [`dbsctr_v3_lifecycle`](docs/specs/dbsctr_v3_lifecycle/) | Lifecycle method, gates, evidence, delivery, and retirement |
| [`dotfiles_ai_distribution`](docs/specs/dotfiles_ai_distribution/) | Portable distribution, Hermes, R&D, Lima, and delivery operations |
| [`opencode_control_plane`](docs/specs/opencode_control_plane/) | Providers, agents, prompts, permissions, skills, and routing |
| [`shell_auth_startup`](docs/specs/shell_auth_startup/) | Shell, 1Password, Keychain, and Herdr startup boundaries |
| [`writing_skills`](docs/specs/writing_skills/) | Jira and Pyramid writing behavior and evidence contracts |
| [`pm_kernel`](docs/specs/pm_kernel/) | Explicit local PM reporting, Jira rollups, and optional PostgreSQL projection |
| [`dbsctr_knowledge_store`](docs/specs/dbsctr_knowledge_store/) | Rebuildable private knowledge projection, local model services, cited hybrid retrieval, and derived graph evidence |

Within each context, `README.md` and supporting specifications own durable truth.
Private Cycle Records own implementation evidence; `CHANGELOG.md` owns completed
cycle evidence. Historical V2
source is retained under [`docs/_archive/`](docs/_archive/) and is not deployed or
current guidance. Public lifecycle entry points are `/discovery`, `/dbsctr`, and
`/qa`; Method Revision 3.29 is current.

## License

[MIT](LICENSE)

## Omarchy native workbench

Copy `config.omarchy.example.toml` to `~/.config/dotfiles-ai/chezmoi.toml`
and replace `/home/you` with your home path. Use this independent config for
`chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml diff` and `apply`.
The opt-in `linux_workstation.enabled` profile installs native x86_64 Herdr,
OpenCode and Codex and deploys the shared agent configuration. It preserves
Omarchy shell configuration and disables guest VMs in the example. It does not
use the CentOS remote-user role. Authenticate providers separately on the laptop.

On Omarchy, `dotfiles-ai-omarchy-setup` creates a private user-owned state root
at `/var/lib/dotfiles-ai/<username>` and applies the profile. This avoids placing
provider credentials under a home directory that may itself be a Git worktree.
Set the matching `state.root` in the local configuration. Existing user files
should be backed up before the first apply; authentication remains interactive.
