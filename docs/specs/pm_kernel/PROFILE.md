# PM Kernel Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Explicitly invoked local PM/Jira reporting workflow, CLI, and optional PostgreSQL projection |
| Owner | dotfiles-ai maintainer |
| Languages/frameworks | Python, Markdown, SQL, Bash, and Go templates |
| Runtime/platform support | Python 3.12+, Git, OpenCode; optional rootless Podman and PostgreSQL 19 on macOS and configured Fedora Lima workspaces |
| Compatibility | Existing PM rows migrate without loss; lifecycle consumers remain ticket-blind; Jira remains optional and explicitly invoked |
| Trust/data | Local PM files may contain private project context; Jira payloads and generated reports are private |
| Delivery | Feature branch and draft pull request; local deployment only after affected gates pass |
| Authorities | `pytest`, Git fixed-commit inspection, chezmoi dry-run/apply, and configured runtime smokes |

The context README remains authoritative for ticket behavior and historical cycle
overrides. New cycles use this file as their Engineering Profile.
