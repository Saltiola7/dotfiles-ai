# OpenCode R&D Loop Runbook

## Operating Model

Hermes runs isolated opt-in profiles on the host and enabled Lima workspaces:

| Component | Default | Purpose |
|---|---|---|
| Daily agent job | 09:00 | Refine bounded evidence and canonical backlogs, then start eligible OpenCode Discovery work |
| Script-only maintenance | Profile schedule | Reconcile durable workers and clean eligible completed worktrees without model tokens |

The daily Hermes tick creates a worker only when the private lens cadence is
due. One pass applies five fixed lens families to one shared immutable capture.
Three daily no-yield passes back off to weekly and four weekly no-yield passes
back off to monthly; a distinct claim or UTC quarter rollover restores daily.
Older workers awaiting Discovery do not block an otherwise eligible run, but a
capture day has exactly one owning worker until its result is recorded.
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
Discovery worker is an operator inbox item: answer in its session and explicitly
say `proceed` only when satisfied. The worker then completes its isolated DBSCTR
cycle and opens a draft pull request. It never merges, marks ready, releases, or
deploys.

P0/P1 claims enter Discovery automatically. P2/P3 claims stop in `claimed`; run
`/dbsctr-backlog` for the report-only queue. Promote one deliberately with
`/dbsctr-integrate`, or directly with the exact confirmation:

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
