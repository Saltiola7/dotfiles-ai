# Upstream attribution and local adaptation

- Upstream repository: https://github.com/fastapi/typer
- Immutable commit: `a5882dedf0bc7a46cd861fdfca020f88519e0f21`
- Selected skill root: `typer/.agents/skills/typer`
- Original author: Sebastián Ramírez, Copyright (c) 2019
- License: MIT; unchanged full notice in [LICENSE.upstream](LICENSE.upstream)
- Immutable source: [selected bundle](https://github.com/fastapi/typer/tree/a5882dedf0bc7a46cd861fdfca020f88519e0f21/typer/.agents/skills/typer)

This adapted bundle remains MIT licensed. Attribution does not imply upstream
endorsement. Every original selected skill-root resource path is retained;
`LICENSE.upstream` is the unchanged repository-root `LICENSE`. The concise
entrypoint routes substantial adapted examples to supporting references. Local
reference additions, this attribution and generated `agents/openai.yaml` have no
invented upstream identity. No plugin hooks, installers or unrelated siblings
are included. UI metadata was generated with the original `skill-creator`
`generate_openai_yaml.py` helper, without changing that helper.

## Local changes

Retained the complete selected skill and exact MIT notice, moving adapted command examples on demand behind a concise Typer-specific entrypoint. Preserved CLI commands, packaging, stdout/stderr, exit status, noninteractive behavior and existing tools; made explicit-app, Annotated, Rich and Click-extension changes conditional on selected versions and actual requirements. Corrected missing-user diagnostics to stderr with nonzero exit status, added a synthetic CLI contract example, and prohibited invented typer.ClickException. Added generated UI metadata and reversible immutable provenance.

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
