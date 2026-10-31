---
name: dagger-pipelines
description: Design and diagnose Dagger modules and CI pipelines, focusing on actual graph execution, selected SDK/engine, caches, secrets and service boundaries. Use for concrete Dagger work.
---

# Dagger Pipeline Methods

Preserve the project's engine/CLI/SDK version, language, module/workspace manifest,
lock authority and existing CI owner. Reuse known task facts and authorization;
ask only about consequential missing choices. Return bounded findings and actual
execution evidence to the current primary and QA.

## Bind the selected execution contract

- Inspect the existing manifest, dependency pins and selected-client help before
  copying a command. Dagger API, command and manifest forms differ across versions;
  current website examples do not authorize a project migration or another SDK.
- A Container/Directory graph describes work. Use the selected SDK/CLI's relevant
  terminal evaluation and await/force its result before claiming tests or builds
  ran. Keep execution failures visible through the caller/CI exit status.
- Verify the requested check result or artifact identity/content. Graph creation,
  a submitted command or a successful connection is not sufficient execution or
  application-readiness evidence.

Consult selected-version [CLI documentation](https://docs.dagger.io/reference/cli/),
[configuration](https://docs.dagger.io/reference/config-files/) and
[SDK reference](https://docs.dagger.io/reference/sdks/) when those boundaries matter.

## Track inputs, caches and capabilities

- Identify source/lock/module/image inputs and mutable external data. Preserve
  approved pins and make freshness/cache-invalidation assumptions explicit.
- A persistent [CacheVolume](https://docs.dagger.io/reference/api/cache-volume/)
  is mutable shared state, not an immutable output or proof of hermetic execution.
  Resolve concurrent cache ownership and correctness before changing cache keys
  or volatile-input behavior for speed.
- Use typed [Secret inputs](https://docs.dagger.io/config/secrets/) and the existing
  secret authority. Secret-typed function arguments are valid; plaintext strings,
  generated shell text, echoed values and ordinary artifacts are inappropriate
  credential channels. Masking does not authorize deliberately printing a secret.
- Bind services, mounts, host directories/sockets, remote engine endpoints and
  platform assumptions explicitly. A local success does not prove equivalent CI
  source, architecture, network, secret or engine conditions.
- Starting engines/services, accessing host capabilities, fetching/executing remote
  modules, exporting, publishing and deploying require the actual task scope and
  native permissions. Loading guidance grants no additional authority.

## Verify and return

Use the existing project's build/test/artifact authorities. Report selected
versions, evaluated terminal operation, input/artifact identity, real status,
cache/secret/service implications and missing capabilities. Installation, a new
registry/login or public mutable image tag is not an automatic troubleshooting
step. Keep infrastructure and publication decisions with their existing owner.
