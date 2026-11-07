# Remote OpenCode Boot Service (RRW-F01)

## Ownership and contract

This completes the remaining INT-066 repair in `rrw-007d-remote-profile-repairs`.
F03/F04/F05 are already merged. Fork A owns host user declaration, INT-068
lingering, VM start and approved rollout; dotfiles-ai owns the remote user unit
and its idempotent enablement. Personal overlays own neither service nor wrapper.
The user still owns authentication, native service configuration, sessions and
database. No credential, service registration or database is projected/reset.

The remote-only `opencode-shared.service` is enabled under `default.target` and
runs the existing managed wrapper in foreground native shared-service mode:
`opencode serve --service --hostname 127.0.0.1 --port 0`. The wrapper validates
the native binary and keeps normal remote XDG routing. Native OpenCode owns its
private discovery registration/password, database and API. Loopback is explicit;
no public listener, forwarded port, second daemon, watchdog or private API is added.

Systemd owns the foreground process with `Restart=on-failure`, a three-second
delay and a five-start/60-second limit. Repeated startup failures stop visibly;
do not hide them by resetting limits or replacing native state automatically.
The unit uses private umask 0077 and has a 30-second shutdown timeout.

## Behavior

- Given declared-user lingering and a running user manager, foundation apply
  reloads units and enables the service without restarting an active unit.
  The hook selects `/run/user/UID` and that user's bus explicitly, so observer-
  driven setup does not require login-provided runtime/bus environment variables.
- Given a healthy native shared process predating this unit, preserve it rather
  than taking ownership mid-session. The enabled unit starts on a later boot,
  when that old process is absent. No automatic service restart is performed.
- Native `service status` can return success with `stopped`; exit status alone
  is not health. Require a valid loopback endpoint, private owned registration,
  and authenticated explicit API/PID match. Never log the password or API body.
- Given no healthy native shared service, request native systemd start (a no-op
  for an already active unit) and wait at most 30 one-second retries, each call capped at
  five seconds. An already active unit gets the same bounded readiness check
  without a restart. Failure remains loud;
  no manual `opencode service start` fallback or unrelated process stop occurs.
- Given boot without login, lingering supplies the user manager, whose default
  target starts the enabled foreground service. The wrapper can attach using its
  existing authenticated loopback/PID/version checks without manual startup.
- Given a failed managed process, systemd restarts it within the configured
  limit. Given source reapply with a healthy process, PID/session remain intact.
- Given a newer native binary while an older service is healthy, preserve the
  session. Existing wrapper version checks still refuse incompatible attachment;
  the owner schedules a coordinated restart, rather than apply interrupting it.
- Non-remote profiles do not manage the unit or hook. Disabling a profile does
  not silently terminate existing processes or erase native state.

## Qualification and operation

Offline tests verify the unit, flags, restart policy, enablement, no-restart
branches, startup failures and disabled-profile effects. Ordinary UBI smoke uses
the existing systemctl fixture and is not boot proof. Required native qualification
uses a separate disposable UBI container with systemd PID 1, dbus/logind and a
real lingering fixture user, with no login sessions. It must prove user-manager
boot startup, native status, authenticated/version-compatible wrapper attachment,
unchanged PID after reapply and restart after killing only its owned MainPID.

The isolated hosted CI fixture may require privileged container/cgroup support.
Unavailable support blocks this required capability; a stubbed pass cannot replace
it. It receives only public source, has no provider credentials and sends no model
request. Container restart is disposable proof, not acceptance of the actual RHEL
VM, SELinux or host lingering rollout. Actual results remain in the cycle ledger.

Fork A previews/pins the merged source and obtains approval for targeted metadata
up and VM start, then verifies service status and wrapper attachment as the owner.
Inspect `systemctl --user status opencode-shared.service` and native
`opencode service status`; keep native registration/password/database private.
For recurring failure, investigate the user unit and native version/configuration;
do not delete service files or reset the database. Retirement requires owner
coordination with active sessions before disabling/stopping the unit. Retain
sessions, history and credentials; this source change performs no live retirement.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: flow/state table; who starts which process? |
| Interaction | required: flow/state table; can apply restart a healthy session? |
| State | required: flow/state table; how do boot and failure differ? |
| Data/trust | required: flow/state table; who owns private native state? |
| Schema | not_applicable: no new user configuration or persistent schema |
| Dependency/deployment | required: flow/state table; does startup require login? |
| Quantitative | not_applicable: no benchmark claim |

| Input/action | Owner | Outcome |
|---|---|---|
| Declared user + host lingering | Fork A host bootstrap | User manager available at boot, without login |
| User default target | systemd | Enabled unit runs native foreground shared service |
| Native startup | OpenCode | Private registration, authenticated loopback API, existing database |
| Wrapper attach | Managed wrapper | Require same version/PID and authenticated loopback endpoint |
| Healthy unit or pre-existing native service + reapply | Foundation hook | Enable/reload only; do not restart healthy process |
| Managed process failure | systemd | Bounded restart; persistent failures remain visible |

**Text Equivalent:** Fork A supplies lingering; systemd starts the enabled user
service without a login. Native OpenCode owns discovery and private state; the
existing wrapper authenticates/version-checks attachment. Apply enables/reloads
without restarting healthy work. Systemd restarts failed owned processes within
its limit. Canonical sources: unit, enablement hook and native boot fixture.
Owner: distribution maintainer. Update when process ownership/startup changes.
