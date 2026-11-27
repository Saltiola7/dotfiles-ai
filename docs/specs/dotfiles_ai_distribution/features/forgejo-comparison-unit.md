# Run Forgejo local-only preflight and registration in a Linux user service

**Superseded design.** Do not implement the same-user unit described below.
See the [separate-controller Discovery](forgejo-controller-isolation.md).
This page retains the original scope and validation history.

**Discovery decision.** The distribution maintainer owns a reusable unit, a
dedicated launcher and an enrollment runbook in `dotfiles-ai`. A developer
should be able to return to a prepared checkout after a reboot and obtain a
native launch digest without logging in to Git again. The target direction
for DBSCTR and dotfiles-ai is Linux only: on Mac hardware the user runs a
Linux VM and enrolls there. Inventorying and retiring earlier native macOS
paths is follow-up work; this feature adds only Linux targets.

Use the [Distribution Engineering Profile](../PROFILE.md) and existing
[Product Intent](../PRODUCT.md). The [local-only lifecycle contract](../../dbsctr_v3_lifecycle/features/forgejo-local-registration.md#linux-systemd-service-credential)
already owns repository identity, the credential envelope, the comparison
fetch and digest-bound approval. This feature supplies the missing execution
environment. It does not change `dbsctrctl`, enroll Initiative Auto, or grant
Forgejo write access.

## Operator interface

- **Install once.** A default-off `dotfiles_ai.forgejo_comparison.enabled`
  machine setting selects the launcher and `dbsctr-forgejo-begin@.service`
  only on Linux profiles with DBSCTR. One instance identifies one enrollment.
  Neither a normal apply nor boot starts a comparison.
  A repeat apply preserves existing enrollments. No changes are required in
  a personal dotfiles repository or on the Forgejo server.
- **Enroll one repository.** An enrollment name is an opaque local identifier
  for one encrypted file, never a URL, command or caller-supplied path. The
  runbook uses native `systemd-creds` user-scoped encryption with credential
  name `dbsctr-forgejo`; the manager loads it with `LoadCredentialEncrypted=`.
  The operator supplies the existing schema-1 envelope by private input. Keep
  the token out of command arguments, shell history, environment variables,
  journal, chat and Git; keep even the ciphertext outside managed source.
  Verify the actual Forgejo account/token has read-only access to the single
  intended repo. The envelope's `role` and a successful fetch do not prove that.
- **Invoke from the task checkout.** `dbsctr-forgejo-begin ENROLLMENT -- BEGIN_ARGS…`
  runs only the installed `dbsctrctl begin` in a short-lived user service.
  `BEGIN_ARGS` are the native local-only Forgejo Initiative arguments with
  `--forge-credential-source systemd`. Require an explicit `--preflight` or
  an exact `--expected-launch-digest` and native approval. Preserve the
  selected checkout, plan, manifest, session binding, result and exit status.
  Reject ambiguous modes, other providers/credential sources, arbitrary
  executables, unit overrides and path-like enrollment names. The service
  takes no code or environment configuration from the task repository.

## Behavior and trust

| Given | When | Then |
|---|---|---|
| A prepared checkout and matching enrollment | The operator requests preflight | The service runs the native comparison fetch. The caller receives the native plan and digest privately; no cycle is registered. The fetch can update local Git objects and the comparison ref. |
| The operator approves that exact digest | Registration is invoked separately | Run inside a fresh credentialed service in the same checkout. DBSCTR re-fetches and rechecks the plan before recording approval. Preserve real operator input or the existing explicit chat-approval mode; the launcher never supplies consent. |
| The credential is absent, expired, revoked or bound to a different selection; the base or plan changed | Either step cannot establish its prerequisites | Return failure. No SSH, interactive Git, cached digest, broader account, or automatic retry. Correct the enrollment or rerun fresh preflight as appropriate. |
| An invocation is interrupted or overlaps another for the same enrollment | A result is unavailable or the request is busy | Separate requests and outputs; refuse overlap if separation cannot be guaranteed. Never replay registration on the caller's behalf. Check native record state before retry. |

| From → to | What crosses the boundary |
|---|---|
| Forgejo owner → controller operator | An expiring read-only credential for the enrolled origin, repository and account. Forgejo controls issuance and revocation. |
| Operator → systemd user manager → fixed DBSCTR process | A user/host-local encrypted enrollment at rest; a read-only credential file in the service for that invocation. The launcher does not decrypt it. |
| DBSCTR → isolated Git fetch → canonical Forgejo HTTPS endpoint | The existing get-only helper authenticates only the selected comparison. Normal shell, OpenCode and Build workers receive neither the token nor its locator. |
| DBSCTR → requesting operator | The private native result, for this invocation only. Shared journals and public evidence receive no plan, credential, private endpoint or account. |

**Text equivalent:** Only Forgejo grants access. Systemd makes the enrolled
credential available for one service activation; DBSCTR decides which read is
allowed and whether registration has approval. The service exits between
preflight and registration. A successful preflight authenticates a read and
produces a digest; it is not approval to act on that digest.

## Validation and first rollout

An exploratory check on one Linux user manager passed an inert credential to
the installed reader: it accepted the matching repository and refused a
different one. This established the runtime path and permissions only. It did
not exercise encrypted enrollment, worker isolation or a Forgejo fetch.

1. **Source and disposable Linux proof.** Test opted-in, disabled and
   inapplicable chezmoi renders. Run the rendered service under an actual
   user manager with an inert encrypted enrollment and a controlled HTTPS
   Git fixture. Exercise both steps, digest drift, a second enrollment,
   refusal, rotation and cleanup. A parser test or mocked credential directory
   alone cannot demonstrate that systemd delivers the file DBSCTR accepts.
   Reuse `tests/test_dbsctr_forgejo_systemd.py`,
   `tests/test_dbsctr_forgejo_transport.py` and the existing registration
   fixtures. The tracked-tree privacy authority is
   `tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers`.
2. **Prove worker separation before using a real token.** With inert data on
   the selected Linux setup, check the actual Build/OpenCode worker boundary:
   filesystem and process view, environment, inherited descriptors, access to
   the user manager and ability to change the trusted launcher/unit or decrypt
   the enrollment. Running as a user service or clearing an environment
  variable alone does not isolate two processes with the same Unix authority.
  If separation cannot be demonstrated, stop before enrollment and reopen the
  host-isolation decision. Check user-scoped encryption on that host with an
  inert envelope; a plaintext fixture does not qualify at-rest encryption.
3. **First consumer after merge.** Preview and apply the exact managed files
   on the nominated controller; verify installed bytes, modes and a clean repeat
   preview. After the operator enrolls the credential, use the already-blocked
   checkout as the first real, read-only Forgejo preflight. Recheck its state
   and inputs first. Success is a native launch digest with no new cycle.
   Registration is exercised in the fixture; registering the consumer requires
   a separate decision on its fresh digest. A fixture pass is not a host pass.
4. **Renew and retire.** Publish a tested rotation procedure: privately
   replace the enrollment, verify a fresh preflight, retire the old token in
   Forgejo (revoke immediately if compromised). A rebuild or different VM
   needs its own enrollment. To withdraw access, stop new invocations, let an
   in-flight request settle, revoke the token, then remove the enrollment and
   the selected managed targets. Preserve native cycle records and task work.

## Build handoff and gate ledger

**Risk: critical** because a faulty service could expose a private repository
credential to a worker. Modules: Security and Python (native helper/fixture
contracts), with distribution template and systemd validation. One Build
writer owns the coupled launcher, unit, opt-in render rules, tests and
operator runbook. Review of credential isolation can run independently against
the candidate. The first consumer waits on merged source and installation.

The [source applicability plan](../FORGEJO-COMPARISON-UNIT.plan.json) names
the committed profile and all eleven gates. Delivery is a draft PR: six
kernel gates, Review/Integrate and Maintain/Retire required; Release, Deploy
and Operate do not apply to that source delivery. The post-merge rollout
requires Deploy (selected files and readback) and Operate (isolation and
consumer preflight); neither can be credited from CI. No package release.
Required gate results are pending, inapplicable gates not run, no exceptions.
No native installation, live qualification or launch feasibility is asserted
by this specification.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary / data and trust | Required: directional table above. Who owns the token, the fetch and the approval? |
| Interaction / state | Required: Given/When/Then table above. Where does preflight end, and what permits registration or a retry? |
| Dependency / deployment | Required: ordered rollout above. Which proof permits the first real comparison? |
| Schema | Not applicable: the existing envelope, plan, digest and Cycle Record have no schema change. |
| Quantitative | Not applicable: acceptance depends on observed behavior, not a measured threshold. |

**Rollout text equivalent:** The distribution maintainer verifies inert
operation and worker separation. After merge the operator installs the
reviewed targets, enrolls privately and tries the existing checkout. A missing
prerequisite stops that step; registration does not follow automatically.
Update these tables and equivalents together when an owner, invocation,
credential boundary or rollout dependency changes.

Native reference: [systemd service credentials](https://systemd.io/CREDENTIALS/).
