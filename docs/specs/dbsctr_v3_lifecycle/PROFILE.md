# DBSCTR V3 Lifecycle Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Shared lifecycle skills, routing, modules, helpers, tests, and conforming runtime harness contracts |
| Owner | Dotfiles owner |
| Languages/frameworks | Language-neutral Markdown prompts; Python helpers and contract tests; TypeScript OpenCode adapters |
| Modules | Python, Security, Data, Cloud, ML/AI, Analytics, Web/UI |
| Runtime/platform support | Delivered OpenCode harness and planned Codex peer on the managed dotfiles environment; Python `>=3.12`; Bun for OpenCode adapters |
| Compatibility | Unversioned lifecycle skills; current Method Revision `3.28` and record schema 4; the captured multi-harness contract proposes schema 5 while schemas 3/4 remain readable; V1 removed; V2 source archived |
| Trust/data | Git specifications contain sanitized durable authority; transcripts, credentials, machine paths, and private runtime identity stay outside Git |
| Delivery | Feature branch and draft pull request; managed local deployment only after affected gates pass |
| Authorities | Affected `pytest`, Python compilation, Bun execution, rendered chezmoi configuration, Git fixed-commit inspection, and configured runtime smokes |

Existing active cycles remain bound to the profile path recorded in their Cycle
Record. New cycles use this file.
