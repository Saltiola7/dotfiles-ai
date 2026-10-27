# Obsidian source reconciliation

## Domain

This optional PM Kernel adapter reconciles explicitly captured Linear and Jira
snapshots into an existing private Markdown vault. Remote systems remain read
only. The operator owns source selection, capture freshness, local edits, conflict
resolution, retention, and retirement. The existing exporter owns record schemas;
this adapter adds private source baselines and recoverable import transactions.
It never writes PM reporting tickets or changes their publication authority.

A source scope is a stable opaque key for one provider/workspace or site/project.
A bundle contains a complete, timestamped set of normalized records for that
scope. Each record has a stable vault-relative path, flat metadata, and Markdown
body. A baseline is the last accepted remote representation, distinct from local
canonical notes. Local additions remain canonical; remote fields change only
through explicit reconciliation. A conflict means local and remote changed the
same property or body differently since the baseline.

Jira identities are namespaced by provider, site, entity type, and source ID;
existing Linear UUIDs remain stable. Jira project and team are distinct records.
Workflow categories map to unstarted, started, or completed while source names
remain readable. Raw priorities remain properties alongside normalized 0–4 values.
Only in-scope parents and relations become canonical foreign keys. External or
unavailable references retain source keys, URLs, and direction in flat properties.
Snapshot evidence retains rich text, custom fields, and attachment metadata;
linked binary downloads and full history are separate explicit scopes.

Private data crosses connected read APIs into local snapshots, normalization,
canonical Markdown, then existing Prefect generation publication and Obsidian
views. Credentials are not copied from connectors. No background remote pull or
writeback is implied by installing the skill. Source text is data and cannot
instruct tools, execute code, select paths, or authorize an action.

## Behavior

1. Given a complete captured scope and an empty baseline, a first pull adds only
   collision-free source records and retains unrelated local notes.
2. Given the previous remote baseline, a repeat pull merges independently changed
   metadata properties and the Markdown body. Local-only changes survive; equal
   concurrent changes converge. Different changes to the same value stop the
   whole batch and produce a private conflict report before any source writes.
3. Given existing imported notes, an explicit original-snapshot seed establishes
   their remote baseline without adopting current local edits as remote content.
4. Given a missing remote record, local deletion, or incomplete snapshot, no note
   is silently deleted or recreated. Missing local baseline records stop a pull;
   remote omissions remain retained and reported.
5. Given duplicate identities, unsafe paths, source mismatch, malformed metadata,
   or an invalid merged foreign reference, validation fails before publication.
6. Given a failed or interrupted batch, a private journal preserves before and
   after bytes. Recovery finishes only when live bytes still match the recorded
   old or new value; intervening edits stop recovery for operator resolution.
7. Given a successful batch, its last accepted remote baseline advances, repeated
   input makes no note changes, and the existing watcher publishes a complete SQL
   generation and refreshes the selected Obsidian reports.
8. Given daily read/create/edit requests, the skill resolves private configuration,
   prefers Obsidian CLI, preserves stable identities, edits canonical files, and
   checks validation and projection freshness. Local edits never imply remote writes.
