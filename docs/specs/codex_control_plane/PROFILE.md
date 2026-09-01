# Codex Control Plane Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Managed Codex CLI instructions, skills, agents, models, sandbox, approvals, hooks, sessions, and thin shared-contract adapters |
| Owner | Dotfiles owner |
| Languages/frameworks | TOML and Go templates; Markdown instructions and skills; Python `>=3.12` adapters and tests; supported Codex CLI and app-server stdio interfaces |
| Modules | Python, Security, Cloud, ML/AI, Data, Analytics |
| Runtime/platform support | Managed Codex CLI peer on Apple Silicon macOS, Fedora 44 aarch64 Lima guests, and CentOS Stream 10 x86_64 remote workspaces; frozen deployed target `0.151.0` until a reviewed update |
| Compatibility | Preserve OpenCode behavior and explicit invocation; capability-probe version-dependent Codex interfaces; never depend on private storage schemas |
| Trust/data | Public configuration and bounded sanitized evidence; credentials, transcripts, machine paths, CODEX_HOME, sessions, and private runtime identity remain outside Git |
| Delivery | Feature branch and draft pull request; managed deployment only after affected gates and runtime probes pass |
| Operations | Exact version, identity, worker, history, federation, recovery, rollback, and coexistence evidence |
| Authorities | Official Codex documentation and release metadata, rendered configuration, `pytest`, Python compilation, shared DBSCTR conformance, and fresh host/guest runtime smokes |

New cycles use this profile. Existing OpenCode cycles and profiles remain
unchanged.
