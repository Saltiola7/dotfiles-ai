# OpenCode R&D Loop Runbook

## Operating Model

Launchd runs two opt-in jobs in the macOS Aqua session:

| Job | Default | Purpose |
|---|---|---|
| `dev.dotfiles-ai.dbsctr-spawner` | Daily at 09:00 | Start one fresh native-Build OpenCode `/dbsctr-improve` worker |
| `dev.dotfiles-ai.dbsctr-watchdog` | Every five minutes | Reconcile durable workers, exact sessions, and pull-request outcomes |

The daily launchd tick creates a worker only when the private adaptive cadence is
due. Older workers awaiting Discovery do not block an otherwise eligible run.
Herdr keeps each worker in a visible single-pane tab. OpenCode performs review,
Discovery, implementation, validation, and draft-PR delivery; launchd and the
runner provide only scheduling and deterministic recovery.

## Configure

Shared defaults disable scheduling. Enable only the desired machine in
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

Run `herdr` and open the `DBSCTR R&D` workspace. A Discovery worker is an
operator inbox item: answer in its tab and explicitly say `proceed` only when
satisfied. The worker then completes its isolated DBSCTR cycle and opens a draft
pull request. It never merges, marks ready, releases, or deploys.

## Health And Controls

```sh
herdr status server
herdr integration status
launchctl print gui/$(id -u)/dev.dotfiles-ai.dbsctr-spawner
launchctl print gui/$(id -u)/dev.dotfiles-ai.dbsctr-watchdog
dbsctrctl improvement-status | jq
dbsctr-rnd spawn
dbsctr-rnd watchdog
```

Disable both scheduled jobs without removing the manual runner:

```toml
[data.dotfiles_ai.rnd]
enabled = false
```

Apply the source after changing the flag. Existing OpenCode tabs, claims,
worktrees, and draft pull requests remain untouched.

Retry or abandon an exhausted worker explicitly:

```sh
dbsctrctl improvement-recover --worker-id WORKER_ID --action retry
dbsctrctl improvement-recover --worker-id WORKER_ID --action abandon
```

## Recovery And Security

The watchdog matches exact native session IDs. A missing process is restarted
as `opencode --mini REVIEW_WORKDIR -s SESSION_ID --agent build --no-replay` in a fresh single-pane tab. Exactly one
recorded pane with that foreground argv may be adopted when Herdr omits native
metadata. Ambiguity blocks; three failed recoveries require explicit retry or
abandonment. Live idle, blocked, and Discovery sessions are never prompted or
answered by automation.

Global OpenCode history supplies sanitized evidence only. Workers may modify
this source, not projects that inspired a pattern. GitHub credentials remain in
the `gh` store and enter only the child process environment used for PR status.
The DBSCTR ledger, not launchd or Herdr labels, remains coordination authority.
