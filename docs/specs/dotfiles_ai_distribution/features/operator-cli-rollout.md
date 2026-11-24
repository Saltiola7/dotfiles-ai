# Managed Linux rollout for the lifecycle CLI corrections

INT-110. Owner: distribution maintainer. [Engineering Profile](../PROFILE.md);
[existing Product Intent](../PRODUCT.md). The operator uses Omarchy desktops and
RHEL-family servers. Qualify the [six source contracts](../../dbsctr_v3_lifecycle/features/operator-cli-fixes.md)
on these two native target classes. macOS is not a development or qualified
deployment target for this work. Since the owner decision of 2026-11-24 the
Mac keeps applying this source: it receives the reviewed files through the
owner's direct apply only, without CI or installed qualification
([decisions](../../../initiatives/macos-workstation-retirement/README.md)).
A hosted Linux test result is source evidence only.

| Stage | Admission | Evidence / stop condition |
|---|---|---|
| Source | Each serial source PR has passed applicable gates and full current-head CI and its merge is verified | Identify the exact merged helper and any changed managed instructions as one reviewed file set. Preserve earlier evidence. |
| Omarchy desktop | Operator selects the managed installation and approves the scoped preview | Verify current target identity, installed preimage, compatible fallback reader, tools, exact rendered bytes and modes. Apply only reviewed targets; verify installed hashes and repeat preview for idempotence. |
| RHEL-family server | Operator privately nominates the server, approved user and managed target configuration | Repeat preview, approval, exact-file apply and readback on that native server. No inferred fleet-wide permission or qualification. |
| Operate | Installed command selected by the user's PATH on each target | Run disposable public-CLI journeys and the actual managed hook's read-only decision. Record positive, refusal and unavailable outcomes per host; a skip or development-host pass cannot satisfy the other target. |

For each target exercise tracked staging with an untouched ignored neighbor,
safe amendment refusal, early dirty/wrong-upstream refusal, and the published
PR guidance. Use synthetic PR observations for the guidance check; deployment
does not require updating a live PR. Exercise unrelated versus ambiguous orphan
ownership and a file held open by a process with its cwd elsewhere. Include a
known complete observation and a warned/incomplete one. If scoped clearance
is unsupported on a particular configuration, record that limit and verify it
blocks safely; do not report an exercised positive clearance there. Never use
a retained operator checkout or backup system as the test subject.

Stop on missing prerequisites, preview drift, incompatible readers, fail-open
behavior or partial apply. Preserve the observed state and original private
preimages; reconcile exact files before retry. Switch back only to separately
approved compatible managed bytes, keeping records and evidence readable. No
system upgrade, global apply, new service or restart is part of this change.
Record the selected host/version/architecture and receipts privately. The
project's RHEL 10 x86_64 profile is a candidate for a nominated server; a stub,
container, or another derivative does not certify an untested host.

Use the established distribution
[rollout gate plan](../../../initiatives/dbsctr-workflow-convergence/COMPLETION-ROLLOUT.plan.json):
Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor,
Review/Integrate, Deploy, Operate and Maintain/Retire required. Release is
not applicable because no separate package is published. All gate results are
pending, no exceptions. The earlier completion initiative's consumer recovery
is not part of this rollout.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary / interaction / state | Required: stage table distinguishes authorization, source delivery, installed bytes and operation for each target. |
| Data/trust | Required: native readbacks and disposable operation establish runtime evidence; machine identities and preimages remain private. |
| Schema | Not applicable: reuse existing managed activation evidence. |
| Dependency/deployment | Required: source precedes both native activations and each has independent evidence. |
| Quantitative | Not applicable: no quantitative comparison. |

**Text Equivalent:** The operator approves a target-specific preview after
verified source merges. The distribution owner applies and verifies the reviewed
files on Omarchy and the nominated RHEL-family server. Each target then proves
the installed command's behavior independently. Unavailable or partial evidence
is retained with its scope. Update the table and equivalent together if target
selection, approval or evidence obligations change.
