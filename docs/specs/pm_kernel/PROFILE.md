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

## Optional Obsidian Adapter

[OBSIDIAN.md](OBSIDIAN.md) defines a separately opted-in personal macOS adapter;
its behavior does not change the PM ticket schema, explicit invocation boundary,
Jira approval contract, or optional PostgreSQL service.

| Field | Adapter commitment |
|---|---|
| Deliverable and owner | Managed note-projection automation; the personal operator owns activation, operation, recovery, and retirement |
| Runtime | Python 3.12+ and Prefect 3.7.7, resolved from the selected lab's exact uv metadata and lock with its existing exporter dependencies |
| Platform and services | macOS user session; one host watcher and one isolated localhost Prefect server; Obsidian CLI refresh requires the existing app to be available |
| Compatibility | Personal Markdown/YAML remains authoritative under the existing lab exporter schema; no conversion into Local Tickets or lifecycle evidence |
| Trust/data | Private local configuration, captures, checkpoints, generations, and diagnostics; no note content, credentials, or raw CLI output enters Prefect metadata |
| Operations | Opt-in installation and scoped removal, serial capture/publication, pending refresh recovery, bounded retention, and rollback without deleting source notes |
| Validation | Adapter synthetic tests, affected PM/distribution regression checks, and host edit/recovery/SQL/Bases parity evidence |

The adapter's [Visual Evidence](OBSIDIAN.md#visual-evidence) and
[Contract](OBSIDIAN.md#contract) are canonical for its topology, ordering, privacy,
and recovery obligations. Disabled or unconfigured adapter use creates no watcher
or personal Prefect service.
