# DKS Operations

DKS is a rebuildable local projection. Git and typed DBSCTR stores remain source
authority. Never repair source truth through PostgreSQL.

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | not_applicable: this runbook does not change the boundary view | Does recovery preserve canonical authority? | `README.md` Visual Evidence | DKS boundary change |
| Interaction | not_applicable: commands below are the accessible procedural view | Is every action ordered and reversible? | Normal Operation and Manual Recovery | Recovery flow change |
| State | not_applicable: health states are defined in the failure table | Does each state have one bounded action? | Normal Operation failure table | Doctor state change |
| Data/trust | not_applicable: no new data flow is defined here | Do logs and recovery remain content-safe? | `README.md` trust boundary | Privacy contract change |
| Schema | not_applicable: schema identity is reported, not designed here | Does recovery use the managed migration path? | Rebuild and Rollback | Schema migration change |
| Dependency/deployment | not_applicable: owned services are listed textually | Can each service be restarted or disabled independently? | Disable and Rollback | LaunchAgent change |
| Quantitative | not_applicable: this runbook makes no quantitative comparison | Are counts treated only as health evidence? | `dksctl status` output | Health metric change |

**Text Equivalent:** The runbook proceeds from health inspection to one bounded
manual retry, then managed migration/rebuild only when required; rollback or
disablement removes only owned runtime state and never edits canonical sources.

## Normal Operation

Launchd runs `dksctl reconcile --project dotfiles-ai` at the configured interval.
Each run optionally fetches only the configured remote ref, resolves one commit,
skips matching channel identities, and retries failures at the next interval.
Concurrent runs return `state: busy` without overlapping work.

Check health and freshness:

```sh
dksctl doctor --project dotfiles-ai
dksctl status --project dotfiles-ai
```

`doctor` exits nonzero for actionable drift. Output contains identities and counts,
not source text, vectors, prompts, or credentials.

| Failure | Action |
|---|---|
| `busy` | Let the active run finish; the next interval retries. Investigate only if the lock remains after its owning process exits. |
| `source_ref_unavailable` | Verify repository, fixed HTTPS remote, configured full remote ref, and network access. Never substitute a worktree revision. |
| `git_stale`, `code_stale`, `graph_stale`, `authority_stale` | Run one manual reconcile. A failed channel retains prior rows but incompatible code/graph rows stay out of current default retrieval. |
| `knowledge authority changed before activation` | Let lifecycle writes quiesce, then retry in the same bounded operator window or allow the next scheduled run. The compare-and-swap guard deliberately withholds activation. |
| `authority_unavailable` | Repair the typed DBSCTR export/privacy boundary. Unavailable-family snapshots are retained but not active. |
| `embedding_unavailable`, `code_embedding_unavailable`, `reranker_unavailable` | Restart the named model LaunchAgent, verify its immutable manifest, then reconcile. |
| `schema_unavailable`, `ranking_policy_unavailable`, `database_unavailable` | Stop reconciliation, run the managed schema/PM health path, and restore baseline ranking before rebuild. |
| `lock_unavailable` | Verify the owned lock directory and regular mode-0600 user-owned lock file; do not replace it with a symlink or special file. |

Graphify extraction cache failures appear as a failed `graphify` reconcile stage,
not as source corruption. The cache lives at
`~/.cache/dotfiles-ai-graphify/<project>/<config>/<runtime>/`, is owner-private,
and is disposable. Stop or disable reconciliation before removing an unsafe cache
namespace, then run one reconcile; the producer rebuilds it through the offline
sandbox. Never copy cache entries between projects, versions, or machines.

Logs:

```text
~/Library/Logs/dbsctr-knowledge-reconcile.log
~/Library/Logs/dbsctr-knowledge-reconcile.err.log
```

## Manual Recovery

Retry all stale channels without waiting for launchd:

```sh
dksctl reconcile --project dotfiles-ai
```

An intentionally disabled scheduler returns `state: disabled`. A one-time manual
repair while disabled must be explicit:

```sh
dksctl reconcile --project dotfiles-ai --force
```

Restart the scheduled job:

```sh
launchctl kickstart -k "gui/$(id -u)/dev.dotfiles-ai.dbsctr-knowledge-reconcile"
```

Restart a failed model service with the corresponding label:

```sh
launchctl kickstart -k "gui/$(id -u)/dev.dotfiles-ai.dbsctr-embedding"
launchctl kickstart -k "gui/$(id -u)/dev.dotfiles-ai.dbsctr-code-embedding"
launchctl kickstart -k "gui/$(id -u)/dev.dotfiles-ai.dbsctr-reranker"
```

A reconcile timeout or stage failure requires no rollback of successful source
authorities. Inspect `doctor`, repair the named dependency, and rerun; idempotent
identity checks skip completed channels.

If candidate ranking is suspect, restore the baseline before other repair:

```sh
dksctl rollback-quality --project dotfiles-ai
```

If PostgreSQL projection identity is corrupt, retain the canonical authorities,
recreate schema through the managed migration, and reconcile the configured exact
ref. Do not restore DKS projection rows as source authority.

For Graphify runtime rollback, stop reconciliation. As the migration owner, remove
only the schema 7 marker before restoring producer and `dksctl` from pre-upgrade
commit `6f52f61c73100d51a18d32ce7734ddc3d404c750` together:

```sql
SET ROLE dks_owner;
DELETE FROM dks.schema_migrations WHERE version = 7;
```

Restore `dot_local/bin/executable_dbsctr-graphify` and
`dot_local/bin/executable_dksctl` from that commit. Retain immutable runtime
`graphify-sql-0.9.48-71cb9828`, whose SHA-256 is
`71cb98287d1e526a8f8be9f60d10462de2df8c547bb1c5bfca2376e07a056be8`, and
producer SHA-256
`7e23d864064906146e20e1c99d343e9bbb22abb5b3f8c913092ed440f2533091`.
Do not drop the nullable receipt column or mix producer, importer, or runtime
versions. Reconcile the configured exact ref, then require `dksctl status` to
report migration marker 6 and Graphify `0.9.48`, and require `dksctl doctor` to be
healthy. The transaction retains the prior active graph if extraction or import
fails.

To re-upgrade, reapply current managed `dbsctr-graphify`, `dksctl`, and
`schema.sql`, run `dks-postgres-migrate`, and reconcile. Require status to report
marker 7, runtime SHA-256
`2202db22692c497e3c45fc19b746a9bc36f6409ae92f745cf19aa2e273443307`, and
producer SHA-256
`aa1bd96b0d72d4d7182843c0403f021bf21cb2da61c8bc6c9e766f179aa0b622`;
require doctor healthy before restoring the reconcile LaunchAgent. The validated
cached `0.9.50` extraction may be reused.

## Disablement

Set `dotfiles_ai.knowledge_store.reconcile_enabled = false` in machine-local
chezmoi data and apply. The managed loader unloads and removes only the reconcile
LaunchAgent. Model services and existing projections remain available unless
their separate settings are disabled.

OpenCode requires one restart after installing or removing `dks_context`. Routine
projection refreshes require no OpenCode restart. `dks_context` returns untrusted
metadata-only citations; it never returns governed private bodies.

## Benchmark And Extensions

Scheduled reconciliation never runs or activates quality benchmarks. DKS-005
silver evidence may authorize only `activate-silver-trial`, a seven-day lease
that reconciliation, doctor, and guarded query restore to `dks-rrf-v1` when
expired or unhealthy. Human v2 evidence remains required for permanent
`activate-quality`. `pg_textsearch` is not installed; DKS-006 remains blocked
until an official PostgreSQL 19 artifact exists and cannot alter production.

Run reranker calibration before a full benchmark after any model, runtime, or
scoring change. The service must retain normal memory pressure, no swap growth,
MPS allocation below 20 GiB, and total process footprint below 24 GiB at the
4096-token operational limit. Stop on any failed guard; never increase context or
batch size without new calibration evidence.
