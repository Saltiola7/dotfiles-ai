# Hermes R&D Loop Runbook

## Operating Model

Launchd starts the Herdr server and Hermes gateway at login. Hermes schedules two
jobs:

| Job | Default | Purpose |
|---|---|---|
| `dotfiles-ai R&D worker spawner` | Daily at 09:00 | Create one fresh native-Build OpenCode tab and global-history R&D run |
| `dotfiles-ai R&D worker watchdog` | Every five minutes | Run a zero-token precheck and wake Hermes only when durable worker state changes |

Missed recurring times collapse into one catch-up run after wake. Every scheduled
run creates a new worker even when older workers are waiting in Discovery.

Use `herdr` to attach to the visible workspace. `hermes` starts an ordinary
interactive chat; it is not required for automatic operation.

## Configure

Set these machine-local values in `~/.config/dotfiles-ai/chezmoi.toml`:

```toml
[data.dotfiles_ai.hermes]
enabled = true
review_workdir = "/Users/you/.local/share/chezmoi-dotfiles-ai"
review_schedule = "0 9 * * *"
watchdog_schedule = "every 5m"
review_delivery = "local"
workspace_label = "DBSCTR R&D"
github_account = "your-github-account"
github_repository = "your-github-account/dotfiles-ai"
```

The GitHub account is non-secret. Authenticate Hermes and GitHub separately:

```sh
hermes auth add openai-codex
gh auth login --hostname github.com
```

Apply and restart OpenCode so it loads the new command and typed tools:

```sh
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
```

## Daily Use

Open the workspace:

```sh
herdr
```

Each scheduled worker appears in its own tab. A blocked Discovery worker is an
operator inbox item. Read its questions, answer in that tab, and type an explicit
instruction such as `proceed with the discovered scope` only when satisfied.
Hermes notices the state change within five minutes and continues supervision.

After required gates pass, the worker pushes its isolated branch and opens a
draft pull request. It compacts its OpenCode session and leaves the tab open.
Manage the PR and tab manually. Hermes observes merged or closed outcomes but
never merges, marks ready, reopens, releases, or deploys.

## Health

```sh
herdr status server
herdr integration status
hermes doctor
hermes gateway status
hermes cron status
hermes cron list
hermes cron runs "dotfiles-ai R&D worker spawner" --limit 20
hermes cron runs "dotfiles-ai R&D worker watchdog" --limit 20
dbsctrctl improvement-status | jq
```

Healthy operation has one managed Herdr workspace, two active Hermes jobs, a
running gateway heartbeat, current OpenCode and Hermes integrations, and no
unexpected duplicate session IDs.

## Controls

Trigger one worker immediately:

```sh
hermes cron run "dotfiles-ai R&D worker spawner"
```

Pause or resume new workers without stopping supervision of existing workers:

```sh
hermes cron pause "dotfiles-ai R&D worker spawner"
hermes cron resume "dotfiles-ai R&D worker spawner"
```

Retry an unrecoverable worker after correcting its underlying problem:

```sh
dbsctrctl improvement-recover --worker-id WORKER_ID --action retry
```

Abandon a worker and release its declared path ownership:

```sh
dbsctrctl improvement-recover --worker-id WORKER_ID --action abandon
```

Claims never expire automatically. Abandon only after confirming the associated
OpenCode session, DBSCTR worktree, and draft PR no longer need recovery.

## Recovery

The watchdog matches only exact OpenCode session IDs. A missing pane is recreated
with `opencode -s SESSION_ID --agent build`. Three failed recoveries leave the
worker durably blocked. Ambiguous duplicate panes, missing sessions, unsafe
worktrees, ownership conflicts, and unrecognized permissions fail closed.

Inspect before manual recovery:

```sh
herdr agent list
dbsctrctl improvement-status --worker-id WORKER_ID | jq
hermes logs errors
hermes cron runs "dotfiles-ai R&D worker watchdog" --limit 20
```

Do not release a claim merely because a pane is absent. DBSCTR Cycle Records,
private improvement state, and Git worktrees are authoritative; pane labels and
screen contents are not.

## Security

Global OpenCode history supplies sanitized evidence only. Workers may modify
`chezmoi-dotfiles-ai`, not the projects that inspired a pattern. Public commits
and PRs must omit private repository names, paths, excerpts, account data, and
traceable provenance.

The draft-PR helper obtains the configured account token from the GitHub CLI
credential store in memory. Tokens are never accepted as arguments or persisted
in config, lifecycle evidence, logs, or PR bodies.

## Disable And Roll Back

Pause spawning first. Set `data.dotfiles_ai.hermes.enabled=false`, preview, and
apply. The apply removes both managed Hermes jobs while preserving Hermes OAuth,
sessions, memories, logs, private ledger, OpenCode sessions, and existing PRs.

```sh
hermes cron pause "dotfiles-ai R&D worker spawner"
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply --dry-run --verbose
chezmoi -c ~/.config/dotfiles-ai/chezmoi.toml apply
```

Do not delete `~/.hermes`, `~/.local/state/dbsctr`, Herdr workspaces, or DBSCTR
worktrees as part of normal rollback.
