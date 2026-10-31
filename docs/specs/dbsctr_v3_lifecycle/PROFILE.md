# DBSCTR V3 Lifecycle Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Shared lifecycle skills, routing, modules, helpers, tests, and conforming runtime harness contracts |
| Owner | Dotfiles owner |
| Languages/frameworks | Language-neutral Markdown prompts; Python helpers and contract tests; TypeScript OpenCode adapters |
| Modules | Python, Shell, Mojo, Security, Data, Cloud, ML/AI, Analytics, Web/UI |
| Runtime/platform support | Delivered OpenCode harness and planned Codex peer on the managed dotfiles environment; Python `>=3.12`; Bun for OpenCode adapters |
| Compatibility | Unversioned lifecycle skills; current Method Revision `3.29` and record schema 5; schemas 3/4 remain readable without implicit migration; V1 removed; V2 source archived |
| Trust/data | Git specifications contain sanitized durable authority; transcripts, credentials, machine paths, and private runtime identity stay outside Git |
| Delivery | Feature branch and draft pull request; managed local deployment only after affected gates pass |
| Authorities | Affected `pytest`, Python compilation, Bun execution, rendered chezmoi configuration, Git fixed-commit inspection, and configured runtime smokes |

Existing active cycles remain bound to the profile path recorded in their Cycle
Record. New cycles use this file.

## Python typing policy slice

The [typing coverage feature](features/python-typing-coverage.md) is elevated risk:
shared instructions affect validation decisions. Its source slice changes existing
DBSCTR, Discovery and QA skill entrypoints and their contracts only. Project
profiles retain command, environment, scope and diagnostic authority. Tests and
notebooks are included when full coverage is selected; scope accounting, completed
analysis and diagnostic cleanliness remain independent outcomes.

Kernel, Review/Integrate and Maintain/Retire gates apply. Release, Deploy and
Operate are not applicable to this source-only draft PR: it publishes no package
and installs no instructions. Exact managed installation and consumer qualification
follow verified merged source through the existing distribution workflow. Preserve
unrelated installed specialist routing and files. Existing publication and skill
contract tests are the validation authority; no new skill or lifecycle schema.

## Bounded Forgejo local-only contract

The approved [local-only feature](features/forgejo-local-registration.md) extends
this context with typed Initiative manifest/receipt schema 2 and native Cycle
Record schema 6 for explicit Forgejo local-only registration. It preserves
existing GitHub schema 1/5 behavior and historical supported records. Controlled
read-only HTTPS Git fetches establish the selected comparison base; local
completion records exact validated source without network activity. Reviewed
manual delivery is a separate explicit Git operation. New local records confer
no push, draft, merge, release, deployment, publication or removal authority.
Remote Forgejo automation remains blocked under
[the complete feature](features/forgejo-support.md).

The support slice is critical risk, uses Python and Security modules, and retains
the existing public support-PR delivery path. Its source cycle marks Release,
Deploy and Operate not applicable with explicit source-only reasons; it neither
publishes an independent package nor installs or activates unmerged source.
Other gates remain required. Approved installation of the merged helper on the
current computer and bounded first-consumer qualification remain required in a
separate rollout plan before consumer use; they do not circularly block the
source cycle's Final Push. Credentials,
private origin/account selections and runtime evidence stay outside public Git.

## Visual Evidence

The local-only feature owns the canonical visual evidence and Text Equivalents:
Boundary is required as an ownership table; Interaction is required as an ordered
handoff table; State is required as a transition table; Data/trust is required as
a directional transfer table; Schema is required as a version/relationship table;
Dependency/deployment is required as a delivery dependency table. Quantitative is
not_applicable because this profile makes no measured comparison or threshold
claim. Canonical source and owner: the linked feature and lifecycle maintainer.
Update those tables with any represented contract change rather than duplicating
them here.
