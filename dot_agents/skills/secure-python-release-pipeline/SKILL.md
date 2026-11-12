---
name: secure-python-release-pipeline
license: Apache-2.0
description: Design or review a selected Python package release pipeline on GitHub Actions, including sdist and wheel verification, native wheel matrices and PyPI Trusted Publishing. Use for actual packaging/release work, not generic Python edits.
---
# Secure Python package release pipeline

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

**Status: Experimental.** The upstream consolidated workflow is a draft grounded
in shipping projects and PyPA documentation. Verify recipes against the selected
versions and review permissions/publisher identity before relying on them.

Read [project boundaries](GUARDRAILS.md). Preserve the project's backend,
package manager, version scheme, release trigger, platforms and acceptance
criteria. This technique returns release design and evidence to the current
primary, QA and Release owners; it does not publish or create another lifecycle.

## Establish the artifact contract

Identify the package, source commit, version authority, expected sdist contents,
wheel families, supported Python/OS/architecture targets and release destination.
Distinguish a review from an authorized CI change, local build or publication.
Inspect existing workflows and publisher configuration without exposing secrets.

A pure-Python package normally needs a platform-independent wheel. Native
extensions need a justified platform/ABI matrix and repair policy. cibuildwheel
is an option for a selected native build pipeline; preserve an existing adequate
builder rather than replacing it automatically.

## Build from the distributable source

Build the sdist first and build wheels from that exact sdist, so missing headers,
package data or generated sources fail before publication. With supported uv/build
versions, their default build performs sdist then wheel-from-sdist; do not pass
both independent-output flags and assume the same coverage. A split pipeline can
pass the sdist as a run-scoped artifact into wheel jobs. Check the selected
frontend's archive-input support; otherwise unpack into a disposable directory.

Keep build dependencies and tool versions under the project's selected authority.
A runtime lockfile does not automatically constrain isolated PEP 517 dependencies.
Retain artifact names, hashes, version and originating run/commit for the handoff.

## Verify the artifacts actually shipped

- Inspect sdist/wheel contents, metadata, licenses, entrypoints and version
  consistency. `twine check` checks distribution metadata/rendering, not imports,
  native ABI correctness, runtime behavior or reproducibility.
- Install the built wheel in a clean supported target outside the source tree and
  exercise the package's meaningful import/CLI/smoke contract. Native matrix jobs
  must test compatible built wheels on their target; a single Linux verification
  job cannot import all platform wheels. Preserve the existing test authority.
- For claimed abi3 wheels, use a compatible symbol auditor such as abi3audit;
  verify tags and platform repair separately. Test every support claim affected
  by the change, or report missing coverage explicitly.
- Feed only the verified run's exact distributions to publication. A green build,
  metadata check or provenance signature alone does not prove functional behavior.

## Isolate publication authority

For a project using PyPI Trusted Publishing, configure the exact owner,
repository, workflow filename and optional environment on PyPI. Verify these
against the intended GitHub job; an environment field alone does not configure
required reviewers or ref restrictions. Retain existing approved protections.

The publishing job should consume verified run-scoped artifacts and perform only
upload/signing, with no checkout, build or source execution. Scope `id-token:
write` to that job and grant other permissions only when needed. PyPA's supported
publish action can generate PEP 740 attestations for Trusted Publisher uploads;
check the pinned action's actual behavior. GitHub-native attestations use a
separate API and permissions; add them only when that distribution channel is
selected. A publishing identity establishes origin claims, not code safety or
bit-for-bit reproducibility.

## Apply relevant hardening

Review minimal job permissions, immutable action revisions, credential persistence,
artifact selection, cache trust boundaries, build-dependency resolution and release
serialization. Maintain pins through the existing updater. Cooldowns, scheduled
checks, VCS versioning, security scanners and cache removal are project choices;
do not introduce or replace them merely because a template contains them.
Do not cancel an in-progress publication without a recovery decision: partial
uploads and published versions are externally visible and may be immutable.

Read [templates](reference/templates.md) for selected workflow examples and
[hardening rationale](reference/hardening.md) for permissions, attestations,
cache/dependency boundaries and validation limits. Templates require current pins,
project-specific smoke commands and the selected tool versions; they are not
ready-to-run installation instructions.

## Return evidence

Report the selected commit/version, sdist and wheel identities, build-from-sdist
proof, artifact installation/smoke results, compatibility coverage, permission and
publisher review, and unresolved gaps. Separate prepared configuration from an
observed upload. Existing QA/Release owners decide applicable gates and completion.

Primary authorities: [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/),
[PyPA publish action](https://github.com/pypa/gh-action-pypi-publish),
[cibuildwheel](https://cibuildwheel.pypa.io/en/stable/),
[build CLI](https://build.pypa.io/en/stable/reference/cli.html),
[GitHub token permissions](https://docs.github.com/actions/security-guides/automatic-token-authentication).
