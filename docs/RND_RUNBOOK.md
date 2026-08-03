# OpenCode R&D Loop Runbook

## Operating Model

Hermes runs isolated opt-in profiles on the host and enabled Lima workspaces:

| Component | Default | Purpose |
|---|---|---|
| Lens fill agent job | Every 5 minutes | Fill every eligible independent lens slot and start exact OpenCode workers |
| Script-only maintenance | Profile schedule | Reconcile durable workers and clean eligible completed worktrees without model tokens |

Each Hermes tick reserves and registers every due lens, then those workers run in
parallel. Five ordinary lenses exclude autonomous R&D session families; only
`review_session_governance` reviews those sessions and proposes source-controlled
lens changes. A yield immediately reopens that lens. Three daily no-yield passes
back off that lens to weekly and four weekly no-yield passes back it off to
monthly; another lens remains independent.
OpenCode performs review, Discovery, implementation, validation, and draft-PR
delivery. Herdr is optional presentation and attachment; it is not required for
scheduling, recovery, or lifecycle proof. Hermes provides orchestration only.

## Configure

Shared defaults disable Hermes orchestration. Enable only the desired machine in
`~/.config/dotfiles-ai/chezmoi.toml`:

```toml
[data.dotfiles_ai.rnd]
enabled = true
review_workdir = "/Users/you/.local/share/chezmoi-dotfiles-ai"
review_hour = 9
review_minute = 0
watchdog_interval_seconds = 300
workspace_label = "DBSCTR R&D"
github_account = "your-github-account"
github_repository = "your-github-account/dotfiles-ai"
```

Authenticate `gh`, preview, apply, then restart OpenCode because agent config is
loaded only at startup:

```sh
gh auth login --hostname github.com
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
```

## Daily Use

Resume the exact OpenCode session directly or attach it to a Herdr pane. A
Critical or materially uncertain Discovery remains an operator inbox item.
Evidence-ready noncritical workers may complete their isolated DBSCTR cycle and
open a draft pull request autonomously. They never merge, mark ready, release, or
deploy.

P0 and materially uncertain claims stop for the operator. An ordinary manual
P2/P3 claim remains queued, while a continuous worker may advance P1-P3 only
with explicit autonomous readiness. Use `/dbsctr-backlog` for the remaining
report-only queue or promote one deliberately with `/dbsctr-integrate`:

```sh
dbsctrctl improvement-promote --worker-id WORKER_ID --confirm WORKER_ID
```

To preview and combine completed feature branches without weakening `main`, use
`/dbsctr-integrate`. It creates `rnd/batch/BATCH_ID`, records exact source SHAs,
and uses no-fast-forward merges. Hermes may create, preview, and integrate the
batch; only the operator may publish its draft pull request:

```sh
dbsctrctl batch-create --batch-id BATCH_ID --github-account ACCOUNT --github-repository OWNER/REPO
dbsctrctl batch-integrate --batch-id BATCH_ID --source dbsctr/CONTEXT/CYCLE --preview
dbsctrctl batch-integrate --batch-id BATCH_ID --source dbsctr/CONTEXT/CYCLE
dbsctrctl batch-publish --batch-id BATCH_ID --confirm BATCH_ID
```

## Health And Controls

```sh
herdr status server
herdr integration status
dbsctrctl improvement-status | jq
dbsctr-rnd spawn
dbsctr-rnd watchdog
dbsctr-rnd lens-plan --worker-id WORKER_ID
hermes -p system cron list
```

Disable Hermes orchestration without removing durable DBSCTR state:

```toml
[data.dotfiles_ai.rnd]
enabled = false
```

Apply the source after changing the flag. Existing OpenCode tabs, claims,
worktrees, and draft pull requests remain untouched.

Herdr pane history uses a 10 MB scrollback bound. Daily Hermes maintenance keeps
private UTC-day snapshots under `~/.local/state/dotfiles-ai/herdr-history` and
prunes snapshots older than 30 days. Run `herdr-history-maintain` for an explicit
archive/prune pass; missing source history is a no-op and unsafe ownership or
symlinks fail closed.

Retry or abandon an exhausted worker explicitly:

```sh
dbsctrctl improvement-recover --worker-id WORKER_ID --action retry
dbsctrctl improvement-recover --worker-id WORKER_ID --action abandon
```

## Recovery And Security

Hermes reconciliation matches exact native session IDs. A stopped delegated task
may resume only its recorded `opencode -s SESSION_ID`; an existing or ambiguous
session blocks duplicate launch. Three failed recoveries require explicit retry
or abandonment. Live idle, blocked, and Discovery sessions are never prompted or
answered by automation.

Global OpenCode history supplies sanitized evidence only. Workers may modify
this source, not projects that inspired a pattern. GitHub credentials remain in
the `gh` store and enter only the child process environment used for PR status.
The DBSCTR ledger, not Hermes Kanban or Herdr labels, remains coordination authority.
