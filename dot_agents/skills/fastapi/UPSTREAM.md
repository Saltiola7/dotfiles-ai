# Upstream attribution and local adaptation

- Upstream repository: https://github.com/fastapi/fastapi
- Immutable commit: `45cb2252c737906f37544f5ba6bee0295fb81468`
- Selected skill root: `fastapi/.agents/skills/fastapi`
- Original author: Sebastián Ramírez, Copyright (c) 2018
- License: MIT; unchanged full notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [selected bundle](https://github.com/fastapi/fastapi/tree/45cb2252c737906f37544f5ba6bee0295fb81468/fastapi/.agents/skills/fastapi)

This adapted bundle remains MIT licensed. Attribution does not imply upstream
endorsement. Every original selected skill-root resource path is retained;
`LICENSE.upstream` is the unchanged repository-root `LICENSE`. The concise
entrypoint routes substantial adapted examples to supporting references. Local
reference additions, this attribution and generated `agents/openai.yaml` have no
invented upstream identity. No plugin hooks, installers or unrelated siblings
are included. UI metadata was generated with the original `skill-creator`
`generate_openai_yaml.py` helper, without changing that helper.

## Local changes

Retained every selected resource and exact MIT notice, moving adapted entrypoint examples on demand and adding focused lifecycle guidance. Corrected the synchronous database query shown inside an asynchronous handler, distinguished app/request/iterator resource ownership and actual response filtering, marked fake authentication and incomplete snippets as illustrative, and scoped new frontend/SSE/telemetry/serialization APIs to installed-version support. Preserved selected dependency owners, servers, checkers, ORM, HTTP and async tooling, valid class dependencies, router composition and RootModel contracts instead of requiring migrations. Added generated UI metadata and reversible immutable provenance. Converted the unrelated internal response model to an explicit mapping before public-model validation after a focused offline probe exposed a ResponseValidationError with the installed FastAPI/Pydantic versions.

The exact original repository paths, Git blob identities, SHA-256, modes, complete
packaged inventory and reversible per-file adaptations are recorded in
`dbsctr/references/python-expansion-sources/frameworks/sources.lock.json`.
Reversing those patches with zero fuzz recovers each original resource exactly;
forward application restores the adapted set. New local files remain identified
only as local additions. All packaged resources are regular non-executable files.
Ordinary loading uses reviewed installed bytes, not moving upstream instructions.
Examples illustrate the described boundary; they do not prove real integration,
security, concurrency, packaging or deployment behavior. Match version-sensitive
APIs to the consuming project's installed release and selected support policy.
