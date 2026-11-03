# OpenCode Control Plane Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Managed OpenCode providers, agents, commands, permissions, plugins, skills, tools, and routing |
| Owner | Dotfiles owner |
| Languages/frameworks | JSON/JSONC and Go-template configuration; Markdown prompts; TypeScript adapters and plugins; Python contract tests |
| Modules | ML/AI, Security |
| Runtime/platform support | OpenCode on managed macOS and Fedora 44 Lima guests; intended RHEL 10 x86_64 remote-workspace successor (release qualification pending); Bun; Python `>=3.12` tests |
| Compatibility | Preserve native Plan-to-Build and provider-affine Build workflows; capability-probe experimental or version-dependent interfaces |
| Trust/data | Local configuration and public provider metadata; credentials, transcripts, and private runtime identity remain outside Git |
| Delivery | Feature branch and draft pull request; managed OpenCode apply only after affected gates pass |
| Authorities | OpenCode CLI capabilities, Bun execution, rendered/resolved configuration, `pytest`, and fresh runtime smokes |

The context README remains authoritative for domain behavior and historical cycle
overrides. New cycles use this file as their Engineering Profile.

`rhel-remote-workspace` / `rrw-002-rhel-user-runtime` (planned `RRW-002`)
approves the standalone RHEL successor in Discovery only. It does not establish
implementation or deployment evidence or reclassify historical RWUE checks.
OpenCode remains user-local with independent per-user authentication; both users
are supported targets, but colleague readiness requires independent exercise.
Readiness and gate results remain pending primary verification and coordinator
authority; UBI10 userland smoke cannot qualify the actual RHEL host.
