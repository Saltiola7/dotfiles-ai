# dotfiles-ai Distribution Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Public standalone chezmoi source for DBSCTR, OpenCode, Codex CLI, Herdr, and opt-in Hermes R&D orchestration |
| Owner | Project maintainers |
| Languages/frameworks | Go templates, TOML, JSON, Markdown, Python, Bash, and launchd plist |
| Modules | Python, Security, Cloud |
| Runtime/platform support | Apple Silicon macOS; Fedora 44 aarch64 Lima guests on VZ; CentOS Stream 10 x86_64 remote workspaces; chezmoi; OpenCode; Codex CLI; Herdr; launchd/systemd user services; Python `>=3.12` tests |
| Compatibility | Stable local TOML keys and managed state boundaries; OpenCode-default automation; sanitized defaults; qualified native platform-local installer ownership with compatibility and recovery checks |
| Trust/data | Public configuration; credentials and machine identifiers remain local |
| Delivery | Feature branch and draft pull request; managed local deployment only after affected gates pass |
| Authorities | Rendered chezmoi output, shell syntax, checksums, `pytest`, launchd validation, and configured runtime smokes |
| Product Intent | `docs/specs/dotfiles_ai_distribution/PRODUCT.md` |

RWUE-001 is elevated risk because it adds a standalone Linux platform, shell
startup, executable installers, user-service recovery, and rollback contracts.
It must preserve all existing macOS and Fedora aarch64 rendering and deployment
behavior.

The context README remains authoritative for distribution behavior and historical
cycle overrides. New cycles use this file as their Engineering Profile.

`features/native-platform-updates.md` defines approved successor update ownership.
Existing lock-gated deployments remain until qualified transition; this profile
revision does not change recorded authority of an already registered cycle.

## Python runtime review and qualification

[Python runtime qualification](features/python-runtime-qualification.md) defines
monthly owner review and urgent security intake through `docs/UPDATES.md`, which
remains the canonical installer inventory. The root floor stays `>=3.12`.
PY-08 adds a standard CPython 3.15 weekly/manual compatibility target while
retaining 3.14 PR/main authority. Exact hosted qualification evidence belongs to
the private Cycle Record; source preparation alone does not qualify a runtime.
No installed or isolated runtime pin changes.

The PY-08 cycle is elevated risk, uses Python and Security, and delivers source
and hosted CI changes only. Kernel, Review/Integrate and Maintain/Retire gates
are required. Release, Deploy and Operate are not applicable because no separately
versioned artifact or managed runtime activation is selected. Existing source,
platform and owner-specific runtime obligations remain unchanged.
