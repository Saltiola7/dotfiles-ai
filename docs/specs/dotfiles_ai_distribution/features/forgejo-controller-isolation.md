# Isolate Forgejo comparison credentials per enrolled teammate

This Discovery supersedes the same-user deployment in the
[comparison-unit proposal](forgejo-comparison-unit.md). On the first Linux
host, a same-UID process outside an inert unit could read its credential file
even with `PrivateMounts=yes`. A separate UID is required. A fresh preflight
in the nominated consumer checkout confirmed the current blocker:
`Forgejo systemd credential unavailable`. No digest or cycle was created.

## Ownership and behavior

- One ordinary login and one dedicated non-login controller account per
  enrolled teammate per Linux host, not one account per repository. Reuse
  the same service template. Each enrolled repository gets an independently
  scoped read-only Forgejo credential. No shared controller or token across
  teammates. On Mac hardware enroll inside the Linux VM.
- The host administrator owns controller accounts, trusted binaries, service
  units, the caller-to-controller mapping, and repository enrollment. Ordinary
  chezmoi apply does not create accounts, install privileged files or activate
  services. Use native systemd encrypted credentials with an operator runbook;
  no token, ciphertext, or private enrollment mapping in Git. A worker must
  not have host admin rights, including the ability to act as the controller.
- Keep `dbsctrctl begin`, plan checks, approval, and Cycle Record writes in
  the teammate's checkout and UID. Do **not** run `begin` as the credential
  owner inside a worker-writable checkout. That would cross the boundary
  through Git configuration, hooks, or other code execution.
- Recommend a fixed-purpose local comparison service. Bind each enrollment
  to its caller UID, controller UID, canonical HTTPS origin, repository, read
  account and protected ref. Admit only a bounded request authenticated by
  the local kernel; accept no caller-supplied executable, path, environment,
  Git configuration, remote or ref. The controller fetches in its own
  isolated Git store and returns only the fresh comparison result and Git
  objects required by the caller. A worker under the teammate's UID may
  request the same enrolled read, but never receives the token. This is not a
  design for hiding repo contents from a worker already authorized to use it.
- The client validates the result, imports verified objects and uses the
  existing expected-old-value guard on the tracking ref. Native preflight
  emits its digest only after the existing checks pass. Approved registration
  rechecks against a fresh comparison and remains separately authorized.
  Missing enrollment, wrong UID, mismatched target, unavailable service or
  failed validation refuse without fallback to SSH or interactive login.

## Git handoff

Use one Unix-domain socket per enrollment. The trusted service checks the
kernel peer UID before serving the fixed comparison request; the client verifies
the root-owned socket and non-writable ancestry, the system manager's
listener UID (not the controller UID), and the response's enrollment digest.
Use system-manager socket activation (`Accept=no`); the service must receive
exactly one listener at the enrolled address. There is no caller-supplied
ref or repository path and no shared writable directory. For each request the
controller fetches the enrolled ref and exports one self-contained native Git
bundle for exactly that ref. The result binds the enrolled repository, exact
ref, object format and freshly observed commit. Use a length-bounded stream,
cap the first rollout at 128 MiB of bundle data and 60 seconds end to end,
and fail closed on malformed, oversized or incomplete results. No incremental
bundle or compatibility fallback in this slice.

Version 1 sends `DBSCTR FORGEJO 1` followed by a newline and closes the
request side. A successful reply is one UTF-8 JSON line (at most 1024 bytes
including newline) with exactly `version`, `enrollment`, `object_format`,
`commit` and `size`, followed by exactly `size` bundle bytes and EOF. The
enrollment is the lowercase SHA-256 hex of compact ASCII JSON array
`[caller UID, canonical origin, repository, account, full comparison ref]`.
Use `/run/dbsctr-forgejo/<digest>.sock`. Refusal closes without a success
header. Credentials load at service start; rotation requires recycling
the corresponding service, not merely replacing ciphertext.

The teammate's CLI imports to a temporary ref with Git object checking enabled,
verifies the staged commit against the result, and then compare-and-swaps the
tracking ref. Neither a readable bundle header nor `git bundle verify` alone
validates the pack. A failure must leave the tracking ref unchanged; private
staging is cleaned up.

Select the new route explicitly with `--forge-credential-source systemd-broker`.
Derive the endpoint from the caller UID and canonical Forgejo origin,
repository, account and comparison ref via a canonical tuple digest in an
administrator-owned runtime directory. No user-supplied endpoint, enrollment
alias, or configurable endpoint override. The administrator's enrollment uses
that same tuple; token rotation for an identical scope does not change it.
The launch digest and local Cycle Record already carry the forge selection
and comparison binding; store the explicit new source in those fields
without changing their shape. Existing direct `systemd` and `osxkeychain`
records remain unchanged. An older helper that does not recognize the new
source must refuse it. Do not add the broker source to the direct Git
credential helper or to Initiative Auto.

**Out of scope:** Forgejo write access, Initiative Auto activation, macOS
retirement, fleet rollout, or migrating existing direct credential records.
The existing credential envelope remains owned by the
[lifecycle contract](../../dbsctr_v3_lifecycle/features/forgejo-local-registration.md#linux-systemd-service-credential).

## Build readiness and validation

The Git handoff passed a disposable Linux namespace probe with two distinct
teammate/controller UID pairs. Each teammate imported its own bundle; the
controller rejected the other UID. Neither teammate could read the dummy
credential, neither controller could traverse its teammate's checkout, and
Git rejected a stale expected-old ref update. An independent offline Git
probe imported a new tip and parent into an empty store and rejected a
truncated bundle without staging a ref.

The opt-in `tests/forgejo_broker_systemd/run-rootless.sh` fixture also passed
with `sha1` and `sha256` on Linux aarch64, systemd 262 and Git 2.56.1. A real
system manager activated the broker socket, decrypted a host-bound dummy
credential, fetched over fixture HTTPS and imported the expected comparison
ref. The fixture rejected an unrelated UID both at the socket and in the
broker independently. This tests the broker transport, not native launch
approval, live enrollment, or full host rollout.

| Order | Required evidence |
|---|---|
| 1. Inert Linux fixture | Two teammate/controller pairs. Own enrollment works; other teammate and ordinary worker cannot read credential files, decrypt enrollment, inspect controller secrets or modify service code. Test revoked or expired credential, wrong target, incomplete transfer, and ref races. Use a controlled HTTPS Git fixture. |
| 2. Source cycle | One Build writer owns the coupled transport, units, fixtures and admin runbook. Independent security review checks the boundary. Use the [Distribution Engineering Profile](../PROFILE.md) and [source gate plan](../FORGEJO-COMPARISON-UNIT.plan.json): six kernel gates, Review/Integrate and Maintain/Retire required. Release, Deploy and Operate are not applicable to source-only draft delivery. All gate results pending; no exceptions. |
| 3. First live consumer | After merge and an approved exact installation, verify controller isolation with inert material, then enroll one read-only token privately. Rerun native preflight in the preserved consumer checkout. Deploy/Operate evidence is separate. A digest is success for preflight, not authorization to register. |

Risk remains critical. Relevant modules: Security, Python and Cloud/Platform.
No account creation, unit activation, credential enrollment or registration
is authorized by this Discovery.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary / data and trust | Required: directional ownership table below. |
| Interaction / state | Required: ownership table and ordered validation above distinguish refusal, preflight and approved registration. |
| Dependency / deployment | Required: ordered validation above distinguishes source, host and consumer evidence. |
| Schema | Required: the Git handoff defines result bindings, and the existing forge selection records an explicit new source without rewriting earlier records. |
| Quantitative | Not applicable: no quantitative claim or threshold. |

| From → to | Permitted transfer |
|---|---|
| Forgejo operator → controller | One repo-scoped read-only token, enrolled privately through systemd. |
| Teammate CLI → controller | One authorized comparison request on the enrolled ref, never task code or approval. |
| Controller → teammate CLI | Validated comparison data, never credentials. |
| Operator → teammate CLI | Exact-digest approval for registration, separate from comparison. |

**Text equivalent:** Forgejo grants read permission. A separate Linux UID
holds that permission. The teammate can get comparison data for an authorized
enrollment, but registration and task files stay on the teammate side.
The distribution maintainer updates these tables when the handoff or identity
rules change.
