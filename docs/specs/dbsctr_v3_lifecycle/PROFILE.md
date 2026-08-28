# DBSCTR V3 Lifecycle Engineering Profile

| Field | Default |
|---|---|
| Deliverable | OpenCode lifecycle skills, commands, routing, modules, helpers, and tests |
| Owner | Dotfiles owner |
| Languages/frameworks | Language-neutral Markdown prompts; Python helpers and contract tests; TypeScript OpenCode adapters |
| Modules | Python, Security, Data, Cloud, ML/AI, Analytics, Web/UI |
| Runtime/platform support | OpenCode on the managed dotfiles environment; Python `>=3.12`; Bun for OpenCode adapters |
| Compatibility | Unversioned `/discovery`, `/dbsctr`, and `/qa`; Method Revision `3.28`; V1 removed; V2 source archived |
| Trust/data | Git specifications contain sanitized durable authority; transcripts, credentials, machine paths, and private runtime identity stay outside Git |
| Delivery | Feature branch and draft pull request; managed local deployment only after affected gates pass |
| Authorities | Affected `pytest`, Python compilation, Bun execution, rendered chezmoi configuration, Git fixed-commit inspection, and configured runtime smokes |

Existing active cycles remain bound to the profile path recorded in their Cycle
Record. New cycles use this file.
