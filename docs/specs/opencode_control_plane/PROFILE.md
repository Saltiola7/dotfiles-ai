# OpenCode Control Plane Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Managed OpenCode providers, agents, commands, permissions, plugins, skills, tools, and routing |
| Owner | Dotfiles owner |
| Languages/frameworks | JSON/JSONC and Go-template configuration; Markdown prompts; TypeScript adapters and plugins; Python contract tests |
| Modules | ML/AI, Security |
| Runtime/platform support | OpenCode on managed macOS and Fedora 44 Lima guests; Bun; Python `>=3.12` tests |
| Compatibility | Preserve native Plan-to-Build and provider-affine Build workflows; capability-probe experimental or version-dependent interfaces |
| Trust/data | Local configuration and public provider metadata; credentials, transcripts, and private runtime identity remain outside Git |
| Delivery | Feature branch and draft pull request; managed OpenCode apply only after affected gates pass |
| Authorities | OpenCode CLI capabilities, Bun execution, rendered/resolved configuration, `pytest`, and fresh runtime smokes |

The context README remains authoritative for domain behavior and historical cycle
overrides. New cycles use this file as their Engineering Profile.
