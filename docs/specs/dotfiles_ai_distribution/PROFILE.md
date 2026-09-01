# dotfiles-ai Distribution Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Public standalone chezmoi source for DBSCTR, OpenCode, Codex CLI, Herdr, and opt-in Hermes R&D orchestration |
| Owner | Project maintainers |
| Languages/frameworks | Go templates, TOML, JSON, Markdown, Python, Bash, and launchd plist |
| Modules | Python, Security, Cloud |
| Runtime/platform support | Apple Silicon macOS; Fedora 44 aarch64 Lima guests on VZ; CentOS Stream 10 x86_64 remote workspaces; chezmoi; OpenCode; Codex CLI; Herdr; launchd/systemd user services; Python `>=3.12` tests |
| Compatibility | Stable local TOML keys and managed target paths; OpenCode-default automation; sanitized defaults; pinned native release contracts |
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
