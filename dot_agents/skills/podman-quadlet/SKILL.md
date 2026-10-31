---
name: podman-quadlet
description: Author, diagnose and verify Podman containers and Quadlet services, especially rootless ownership, storage, networking and systemd lifecycle. Use for actual Podman/Quadlet work.
---

# Podman and Quadlet

Bind guidance to the installed Podman/systemd versions, actual runtime host and
project policy. Keep the existing primary and authorization boundaries.

## Establish ownership before changing state

Resolve local versus remote Podman, the selected connection or VM, OS/release,
rootless versus rootful operation and the account owning containers/storage.
On macOS, the client and the Linux VM hosting systemd are different targets.
Do not switch to root or another connection to make missing objects appear.

| Boundary | Evidence needed |
|---|---|
| Service | Authored Quadlet/drop-ins, generated unit, user versus system manager and dependencies |
| Identity | Runtime account, container UID/GID and user-namespace mappings |
| State | Named volumes/bind sources, ownership, labels, consumers and retention/recovery |
| Network | Selected network/backend, published address/port and actual client path |
| Image | Project-selected registry, immutable identity/pinning policy and entrypoint |

Inspect only necessary fields: full container inspection or logs can expose
environment secrets. Missing objects under one account do not prove deletion.

## Quadlet authoring and diagnosis

Use authored Quadlet files as source, not edits to generated `.service` output.
Select the actual rootless/rootful search paths and supported keys from the
[version-appropriate Quadlet documentation](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html).
Generator support and extensions vary by release; verify cgroup/runtime
prerequisites and systemd integration on the target.

Where supported, inspect the installed generator's dry-run output and validate
the resulting service units. Keep source syntax, generated-unit validity and
actual service readiness separate. A daemon reload invokes generators and changes
manager state; start/restart and user lingering have their own operational
effect and require the task's existing authority.

Quadlet-generated services cannot be enabled through ordinary `systemctl enable`.
Express required persistent target relationships in the source `[Install]`
section supported by the selected release, then verify generated dependencies
and actual startup behavior under the intended manager.

For user services, verify the account and user-manager context. Lingering is a
chosen persistence policy, not an automatic prerequisite. Avoid obsolete generated
unit migration recipes when the project already owns Quadlet source.

## Storage and security

Review UID mappings before changing host ownership. SELinux `:Z` denotes private
relabeling and `:z` shared labeling; select according to actual consumers and
installed policy. Relabeling writes host state. Do not relabel a whole home or
system tree to repair one mount. Options that recursively change ownership, such
as `:U`, require explicit impact and recovery analysis.

Preserve least privilege and existing network/security policy. Privileged mode,
host networking or disabled labeling is not a universal fix. Preserve volumes
and bind data through upgrades/recreation; container deletion is not permission
to delete storage. Verify target-specific rootless port/network limitations.

## Validation and return

Use project-selected build/configuration checks, then authorized runtime checks
under the real account. Verify health, access, exit/restart behavior, dependencies,
persistence and recovery appropriate to the change. Local generation or a running
container does not prove application readiness or remote reachability.

Return resolved ownership/target, source and generated-unit evidence, observed
failure or proposed change, actual checks, rollback and remaining gaps. Installing
this guidance does not install Podman, start a VM or change a host/cluster.

Primary references: [Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html),
[Podman runtime](https://docs.podman.io/en/latest/markdown/podman.1.html), and the
installed Podman/systemd manuals. Resolve version differences before using a recipe.
