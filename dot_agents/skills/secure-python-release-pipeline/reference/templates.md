# Selected workflow examples

Local adaptation of pinned Experimental upstream guidance; see bundle UPSTREAM.md.

**Experimental examples, not ready-to-run workflows.** Preserve the existing
release trigger, backend, manager, protected environment and accepted platforms.
Replace action-revision placeholders with reviewed immutable commits and confirm
current syntax for those versions. The uv example applies only when uv is selected.
Do not copy a release workflow into a project merely because this file is loaded.

Upstream grounding: [zipwire/retread](https://github.com/tiran/agent-skills/blob/0c51c24122b33afed31fd8d50534e089534f77a7/skills/reference-repos.md)
for pure Python and [pycxxfilt](https://github.com/tiran/pycxxfilt)
for native wheels. These links are source context, not execution dependencies.

## Pure Python: build, inspect, install, then publish

This example's `release_smoke` module must already be an agreed project-owned
smoke entrypoint shipped in the wheel; substitute the actual package/CLI contract.
Its successful execution must exercise useful behavior. Running from a temporary
directory with isolated Python prevents an import from the checkout from masking
a broken wheel. The example assumes exactly one pure-Python wheel and a Unix runner.

```yaml
name: Package release example
on:
  push:
    tags: ["v*"]
permissions: {}
concurrency:
  group: package-release-${{ github.ref }}
  cancel-in-progress: false
jobs:
  build-verify:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<reviewed-commit-sha>
        with:
          persist-credentials: false
          fetch-depth: 0  # only needed if the selected version authority uses Git
      - uses: astral-sh/setup-uv@<reviewed-commit-sha>
        with:
          enable-cache: false  # selected example's cache policy
      - run: uv build
      - run: uvx twine check dist/*
      - name: Install and exercise the wheel outside the checkout
        shell: bash
        run: |
          set -euo pipefail
          shopt -s nullglob
          wheels=(dist/*.whl)
          test "${#wheels[@]}" -eq 1
          uv venv "$RUNNER_TEMP/release-venv"
          uv pip install --python "$RUNNER_TEMP/release-venv/bin/python" "${wheels[0]}"
          cd "$RUNNER_TEMP"
          "$RUNNER_TEMP/release-venv/bin/python" -I -m release_smoke
      - uses: actions/upload-artifact@<reviewed-commit-sha>
        with:
          name: verified-distributions
          path: dist/
  publish:
    needs: build-verify
    runs-on: ubuntu-latest
    environment: pypi  # must match the existing approved PyPI publisher
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@<reviewed-commit-sha>
        with:
          name: verified-distributions
          path: dist/
      - uses: pypa/gh-action-pypi-publish@<reviewed-commit-sha>
```

The publish job has no checkout or build. Project dependency constraints still
apply to the fresh artifact environment; add the existing install authority's
supported constraints/lock mechanism when required. Metadata checks are not the
installation/smoke check. A tag-trigger example does not require migrating a
project using another approved trigger or static version authority.

## Native wheels: distribute the sdist to matrix jobs

Build the sdist in one job and upload it as a current-run artifact. On each
selected supported OS/architecture, download that exact sdist and pass its path
to a compatible cibuildwheel version. The selected build command must fail if
zero or multiple sdist candidates are found; do not rely on an unchecked `ls`.
This fragment illustrates the handoff, not a complete workflow:

```yaml
steps:
  - uses: actions/download-artifact@<reviewed-commit-sha>
    with:
      name: sdist
      path: source-distribution
  - id: sdist
    shell: bash
    run: |
      set -euo pipefail
      shopt -s nullglob
      sdists=(source-distribution/*.tar.gz)
      test "${#sdists[@]}" -eq 1
      printf 'path=%s\n' "${sdists[0]}" >> "$GITHUB_OUTPUT"
  - uses: pypa/cibuildwheel@<reviewed-commit-sha>
    with:
      package-dir: ${{ steps.sdist.outputs.path }}
```

Configure cibuildwheel's selected test command and dependencies to install and
exercise the built wheel outside the source tree. Confirm its platform repair,
Python/ABI coverage and test-skip reasons. Preserve excluded/unsupported targets
as explicit gaps; an import on one host does not test foreign platform wheels.

After matrix jobs, a verification job can download the exact expected wheel
artifacts, inspect metadata/tags and audit claimed abi3 symbols. If it calls uv,
include a pinned setup-uv step in that job too; job-local tool setup is not
inherited from the build job. Inspect the sdist as well as every expected wheel.
Publish only distributions from the same verified run, never arbitrary previous
runs or a broad cache. GitHub-native release assets/attestations are an optional
separate authorized channel with their own scopes.

## Optional updater and audit integration

Reuse the existing Dependabot/Renovate setup, grouping, schedules and selected
cooldown policy. Verify package-ecosystem support against the updater version.
Do not add a new scheduled workflow, pre-commit hook or dependency automatically.

When a project selects zizmor, use its configured failure/report policy. SARIF
upload success can coexist with findings, so inspect the actual code-scanning
ruleset or use a supported local failure mode. Add actionlint only when selected
for syntax/expression checking. Neither tool establishes artifact correctness.
