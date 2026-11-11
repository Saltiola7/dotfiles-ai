# Remote Global Mise Toolchain

## Scope and ownership

RRW-007C implements INT-041/057/058/059 under the merged coordinator receipt.
Dotfiles-ai owns the remote global mise config and matching Linux-x64 lockfile.
The host owner keeps system Python for OS/host scripts. Project repositories own
their tool selections and uv locks; the optional personal overlay owns neither
global mise configuration nor shared Python. No GUI application is introduced.

When `prefect_mcp` is enabled, the global config declares exact Python 3.13.18.
The reviewed mise-generated lock pins its python-build-standalone 20261026 asset
URL, SHA-256 and GitHub-attestation provenance. mise's built-in Python backend
installs it; no source build fallback or independent Python downloader is added.
RRW-F04 makes the managed lock byte-identical to native mise serialization:
the exact `@generated` header, blank lines, and one terminating newline are part
of the compatibility contract, not merely the parsed pins. Native lock rewriting
must leave managed bytes unchanged. Preserve Python/version, artifact URL,
checksum, backend, specifier and provenance values; this is not a pin upgrade.
For a previously native-rewritten lock with only this known formatting drift,
the matching desired bytes allow ordinary chezmoi apply without resetting the
live file or passing `--force`. Unrelated local edits remain protected.
With the flag disabled the global tool table is empty, and no interpreter is
installed or removed. Disabling never deletes existing environments or Python.

## Behavior and contracts

- Given a remote user, manage `.config/mise/config.toml` and `mise.lock`; exclude
  both targets on non-remote profiles. Existing host/guest settings stay unchanged.
- Given a changed global config, apply runs native `mise install --locked` before
  the existing Prefect installer. A bounded cached check also runs on reapply so
  retry can repair missing installs. mise retains installed/download ownership;
  there is no second installer state machine or unpinned `latest` selection.
  The verified upstream archive carries group-writable file modes that native
  mise preserves. Before interpreter qualification, remove group/other write
  bits from owned real files/directories in this exact pinned install only.
  Preflight ownership, types and single-link regular files before mutation;
  reject unsafe ancestors and bound traversal. Do not follow/chmod symlinks,
  change file bytes, or weaken the adapter's existing path/permission checks.
- Given matching cached tools, reapply does not upgrade them. Missing locked
  assets fail loud, preserving their checksum/provenance requirements. Do not
  disable attestation or checksum checks to get a green deployment.
- Given enabled Prefect, expose mise's user-owned shims to shell, install and
  integrity paths. The selected interpreter must be the declared mise install
  with the exact pinned version. Keep the adapter's frozen lock, interpreter
  identity checks and `--no-python-downloads`. uv owns environments, not Python
  acquisition. `UV_PYTHON_DOWNLOADS=never` is the remote default; never set a
  global `UV_PYTHON` pin that overrides a repository's own Python selection.
- Given a project selection, interactive `mise activate bash` and shims retain
  normal per-project precedence. Foundation installation/integrity and adapter
  installation use the thin `remote-mise` exec adapter: all native config scopes
  explicitly select the one reviewed global file, ambient mise/interpreter
  overrides are cleared, and calls run from HOME. HOME/project configuration,
  global fragments and system configuration cannot add bootstrap tools or hooks.
  The early rc loader is bounded separately: skip HOME/project rc traversal;
  reject extra global `miserc.toml`/`miserc.local.toml` files before native parsing.
  Unsupported global rc customization is retained and reported, never deleted.
  This adapter adds no installer state, downloader or project-trust mutation.
- RRW-F05 explicitly sets `idiomatic_version_file_enable_tools = ["python"]`
  under global `[settings]`. A repository's `.python-version` overrides the
  optional global 3.13.18 baseline for ordinary mise/shim discovery, including
  a requested Python 3.14. The repository/user installs that interpreter through
  mise, not uv; this setting alone does not preinstall every repository version
  or automatically trust repository hooks. Foundation's isolated context still
  ignores HOME/project version files and retains the exact global adapter pin.
- Failure, unsafe config/lock paths and a missing or wrong interpreter remain
  visible. No provider login, model request, live host change, virtualenv deletion,
  broad cache cleanup, credential copying or application restart is authorized.

## Interfaces and validation

`dotfiles_ai.remote_user_environment.prefect_python_version` is a source-owned
pin, not a setup option. Existing configuration validation rejects pin overrides.
The old Fork-A-provisions-Python prerequisite is superseded: Fork A only confirms
that enabled Prefect applies on the next separately authorized setup run.

Remote Prefect also receives a source-owned `.python-version` input. Its digest is
part of the existing immutable adapter generation identity. Adding/changing the
pin selects a new generation, without deleting any older generation/environment.
Installation and reuse validate the actual adapter interpreter's exact patch and
mise install path; a generic 3.13 qualification is not sufficient for a remote
pinned generation. Non-remote adapters without this input keep existing behavior.
uv discovery uses only system/PATH interpreters for a pinned generation, never a
previous uv-managed cache or an ambient project interpreter selection.

Use the existing pinned mise/gh/conditional-uv bootstrap, then the remote mise
hook, then the existing Prefect install hook. Global mise assets and Bash drop-in
are shared-foundation targets, disjoint from personal overlay snippets/config.
No public flag name changes and no extra host provisioning are needed.

Offline tests cover conditional render/target selection, lock/config identity,
failure propagation, unsafe paths, shell/adapter PATH, disabled no-effects,
ordering and no-download policy. Disposable UBI proves actual pinned installation,
cached reapply, and the existing frozen Prefect installation/check-runtime path
without credentials or API calls. UBI is not live RHEL or owner acceptance.
UBI also runs the pinned native lock serializer after enabled Prefect installation,
asserts the exact lock digest remains unchanged, then performs another ordinary
foundation apply and asserts that digest again. Offline tests reproduce the
old chezmoi conflict and two non-forced convergences in a disposable home.
UBI further installs Python 3.14 through mise for a disposable repository with
`.python-version`, verifies its user-shell selection, and proves the foundation
still selects Python 3.13.18 with an unchanged global lock despite project/HOME
idiomatic pins. Repository test installs do not expand the production global pin.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: ownership flow below; is every tool/config owned once? |
| Interaction | required: ownership flow; does Python exist before adapter install? |
| State | required: transition table below; does disabling delete user data? |
| Data/trust | required: ownership flow; do credentials enter the toolchain? |
| Schema | not_applicable: existing flag/config shapes plus native mise config/lock |
| Dependency/deployment | required: ownership flow; which layer owns interpreter downloads? |
| Quantitative | not_applicable: no performance claim |

| Order | Owner / action | Boundary |
|---|---|---|
| 1 | Host bootstrap supplies system Python | OS/host scripts only |
| 2 | Chezmoi declares global mise config/lock | Non-secret, user-owned remote files |
| 3 | Pinned mise installs locked Python when enabled | Verified upstream Python artifact |
| 4 | Existing uv installer creates frozen Prefect environment | No interpreter downloads or provider calls |
| 5 | Project mise/uv selects project tools/environments | No implicit project trust or global override |

| Input/state | Result |
|---|---|
| Prefect disabled | Empty global tool set; preserve existing user installs |
| Enabled, missing Python | Native locked install, then adapter qualification |
| Enabled, cached Python | Reuse exact install; no upgrade |
| Install/check failure | Fail apply; preserve evidence and existing state |

**Text Equivalent:** Host Python serves host scripts. Chezmoi declares user-global
mise config; mise acquires the pinned interpreter before uv builds the adapter's
frozen environment. Project tools retain their own mise/uv owners. Disabled flags
do not delete data; failures do not trigger another downloader, login or restart.
Owner: distribution maintainer. Update this view when toolchain ownership or
ordering changes.
