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
| `projection_busy` | Retry the read later. Query activation and one optional policy repair share a two-second deadline; this temporary result contains no citations. Do not bypass policy locks or search another project. |
| `source_ref_unavailable` | Verify repository, fixed HTTPS remote, configured full remote ref, and network access. Never substitute a worktree revision. |
| `git_stale`, `code_stale`, `graph_stale`, `authority_stale` | Run one manual reconcile. A failed channel retains prior rows but incompatible code/graph rows stay out of current default retrieval. |
| `authority_unavailable` | Repair the typed DBSCTR export/privacy boundary. Unavailable-family snapshots are retained but not active. |
| `embedding_unavailable`, `code_embedding_unavailable`, `reranker_unavailable` | Restart the named model LaunchAgent, verify its immutable manifest, then reconcile. |
| `schema_unavailable`, `ranking_policy_unavailable`, `database_unavailable` | Stop reconciliation, run the managed schema/PM health path, and restore baseline ranking before rebuild. |
| `lock_unavailable` | Verify the owned lock directory and regular mode-0600 user-owned lock file; do not replace it with a symlink or special file. |

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
