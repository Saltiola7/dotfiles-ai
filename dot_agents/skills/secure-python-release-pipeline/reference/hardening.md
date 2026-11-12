# Release trust and hardening decisions

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

Apply to the selected release path; preserve existing project controls and scope.
The examples below do not add scanners, schedules, credentials or publication.

## Separate build, verification and upload authority

A source/build job executes repository and dependency code. A verification job
checks the exact resulting distributions. A publish job should only download
those verified artifacts from the current run and upload/sign them. Isolate the
OIDC permission from checkout, build hooks and arbitrary source execution.

| Job role | Typical permissions, qualified to actual steps |
| --- | --- |
| Checkout/build/test | `contents: read`; no PyPI/OIDC authority |
| Download and inspect current-run artifacts | Only permissions the selected artifact action/API requires |
| PyPI Trusted Publisher | `id-token: write`; other scopes only if a step needs them |
| Optional GitHub native attestation/release | Its own job and required `attestations: write` / `contents: write` scopes |
| Optional SARIF upload | Required code-scanning scopes, separate from publication |

Explicit per-job permissions are easier to review. If a workflow uses a deny-all
`permissions: {}` default, inspect every job rather than assuming later jobs
inherit checkout access. `persist-credentials: false` avoids retaining checkout
credentials for later steps that do not need them; inspect the pinned checkout
action's actual storage behavior rather than relying on one historical path.

Configure a Trusted Publisher for the exact repository, workflow filename and
optional environment. GitHub environment protection and PyPI identity matching
are separate configuration checks. OIDC removes a stored long-lived publishing
token; a compromised authorized workflow can still publish malicious artifacts.
No credential value belongs in diagnostic output.

## What attestations establish

Supported PyPA publish-action versions generate PEP 740 attestations for Trusted
Publisher uploads. Check the pinned version and selected settings. The same
OIDC identity can sign them without granting GitHub's separate native-attestation
permission. Consumers verify the artifact digest and expected signer identity
using compatible PyPI attestation tooling. GitHub's native provenance and
`gh attestation verify` are a different distribution/verification path.

An attestation binds the uploaded bytes to an identity and statement. It does
not independently prove that an isolated publish job built those bytes from the
claimed source, that the source is safe, or that the build is reproducible.
Preserve the build-to-artifact/run identity chain and test its actual claims.

## Artifact completeness and runtime correctness

Building wheels from the sdist catches missing source/package files. Verify the
selected frontend's semantics: default uv/build operation normally builds a wheel
from its generated sdist; independently requesting both outputs is different.
Archive arguments require frontend-version support; an explicit unpack is a
compatible alternative. PEP 517 isolation separates the build environment from
the caller but does not by itself freeze dependency versions or artifact bytes.

`twine check` validates metadata/rendering. Add package-content checks and clean
artifact installation/smoke evidence. Native wheels require target-compatible
execution, repair/tag inspection and the ABI claims the project actually makes.
Tests importing from the checkout can miss an empty or incomplete wheel.

## Pinning and dependency resolution

Pin action revisions to immutable reviewed commits when project policy selects
that control; retain a readable version comment and an existing update owner.
An immutable revision prevents tag movement but does not make the selected code
trustworthy. Review transitive downloads and privileged scripts as well.

Keep the selected application, test, build and CI dependency authorities explicit.
A committed runtime lockfile is not automatically consumed inside isolated
PEP 517 builds. Verify the build frontend's supported build-constraints/locking
mechanism and actual resolved versions. A constraints file limits resolution;
hash enforcement and deterministic output are additional claims to verify.

Use the existing updater and cadence. Group related CodeQL subactions when that
fits the project's update policy. Resolution/update cooldowns can delay adoption
of new releases but do not certify them; preserve urgent security-update handling
and exceptions. Fixed three- or seven-day waits are examples, not universal gates.

## Caches and artifact handoff

Caches and artifacts serve different purposes. Run-scoped artifacts carry the
selected distribution outputs; a broad cache lookup is not a release-artifact
identity check. Inspect who can write and restore each cache scope, keys,
restore-prefixes and trust boundary. Fork PRs do not universally have write access
to the base branch's cache; avoid that blanket assumption.

For a selected release policy, disabling build caches is a simple way to avoid
trusting cached compiler/build inputs. An existing cache strategy can remain when
its provenance and isolation meet the accepted contract. Per-run save keys with
broad restore prefixes still consume earlier entries and do not remove poisoning
risk. Retention follows recovery/audit needs; an arbitrary one-day window is not
a security requirement.

## Serialization and optional checks

Prevent concurrent publication of the same version through the selected release
owner and appropriate concurrency controls. Do not cancel an upload already in
progress by default; first inspect partial uploads and immutable version state.
A new tag or retry is not permission to move or reuse a published version.

Use existing configured checks. zizmor can inspect workflow security and actionlint
can check syntax/expressions, but both have coverage limits. SARIF-producing jobs
may exit successfully while reporting findings; inspect the configured ruleset or
explicit failure policy. CodeQL and Scorecard are optional complementary methods,
not new requirements of this skill. Report actual invocation, findings and gaps.

Primary sources:
[GitHub permissions](https://docs.github.com/actions/security-guides/automatic-token-authentication),
[GitHub cache restrictions](https://docs.github.com/actions/using-workflows/caching-dependencies-to-speed-up-workflows#restrictions-for-accessing-a-cache),
[PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/),
[PyPI digital attestations](https://docs.pypi.org/attestations/),
[build CLI](https://build.pypa.io/en/stable/reference/cli.html),
[zizmor](https://docs.zizmor.sh/).
