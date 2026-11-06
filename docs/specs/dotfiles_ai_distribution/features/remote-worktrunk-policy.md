# Remote Worktrunk Policy (RRW-F03)

## Boundary and behavior

This distribution repair unblocks Fork A's INT-061 branch reconstruction without
owning migration, GitHub pushes, Herdr pane changes or live activation. It is
critical-risk storage-guard work; existing checkouts and source history stay put.
The existing [storage-policy contract](workflow-storage-policy.md) remains the
schema and safety authority except for the explicit remote-home qualification
extension below. The operator owns activation; chezmoi owns only the policy and
native Worktrunk configuration. No activation command that writes files is added.

- Given a remote profile, render private mode-0600
  `~/.config/dotfiles-ai/workflow-policy.json` from the existing
  `data.dotfiles_ai.workspaces` table using the same clean-source generation as
  Worktrunk's configuration. Do not manage or write its activation file.
- Given setup's root `HOME/.local/state/worktrees` (normally `/home/USER/...`),
  retain `ROOT/{{ repo }}-{{ repo_path | hash }}/{{ branch | sanitize }}`.
  Explicit foundation apply provisions the configured root through its existing
  setup owner; previews and snapshot never create storage or allocate checkouts.
- Given the exact Linux home-backed root, snapshot classifies it as `owned_home`
  and reads native `findmnt --json --output UUID,TARGET --target ROOT`.
  Bind an available filesystem UUID and absolute mountpoint. For this exact
  owned-home default only, a native null UUID is permitted (e.g. UBI overlay);
  retain/bind its mountpoint and make no replacement-disk guarantee without UUID.
  Missing/broken findmnt, malformed output or an unavailable root still refuse.
  Other configured roots retain mandatory UUID identity. Existing defaults and
  macOS qualification keep their current behavior.
- Given no reviewed activation or changed policy/version/root identity, refuse
  new allocation before native membership changes. `--yes` is not activation.
  Existing registered work remains reachable under the existing exception.
- Given an owner-reviewed snapshot installed as a private single-link regular
  activation file, native `wt switch REMOTE_BRANCH --no-cd --yes` may allocate in
  the configured namespace. Never bypass `workflow-storage`, copy worktrees,
  upload files, or delete retained work. Reapply never replaces activation.

## Owner activation handoff

After Fork A's separately approved foundation apply, the owner explicitly ensures
the configured worktree root and existing default cache directory exist. For the
setup defaults only (no DVC hydration or policy fallback):

```bash
install -d -m 0700 "$HOME/.local/state/worktrees" "$HOME/.cache/dotfiles-ai/dvc"
proposal=$(mktemp "$HOME/.config/dotfiles-ai/workflow-policy.proposal.XXXXXX")
workflow-policy snapshot >"$proposal" && cat "$proposal"
```

Stop if snapshot fails. Review the complete proposal against the rendered policy:
policy digest, root/cache paths, root kind, native Worktrunk version, and the
findmnt identity. Keep this private; it contains local paths and identifiers.
Only after that exact proposal is accepted, the owner runs:

```bash
install -m 0600 "$proposal" "$HOME/.config/dotfiles-ai/workflow-policy.activation.json"
# Run from the intended canonical primary checkout:
workflow-policy check
wt switch REMOTE_BRANCH --no-cd --yes
```

The second block is a separate manual authorization step, not automatic setup.
Refuse suspicious paths/symlinks and investigate existing incompatible activation
rather than overwriting it blindly. A later changed policy/version/mount needs a
new snapshot review. Fork B never writes the owner's activation; Fork A documents
this step for the owner and preserves the excluded panes until acceptance.

## Validation and limits

Offline tests cover remote target inclusion, activation exclusion, native Linux
identity with/without a home UUID, changed identity rejection and strict external
UUID requirements. UBI uses native findmnt and Worktrunk: fresh foundation apply,
remote-tracking branch from a disposable bare remote, refusal without activation,
fixture-owner review/activation, successful switch in the existing namespace,
and unchanged activation across reapply. Fixture owner actions are not live-host
authority. No full RHEL VM, IAP, mount replacement or Herdr acceptance is claimed.
Bootstrap bytes remain unchanged; handoff reports the verified merged SHA/checksum.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: transition table; who owns activation? |
| Interaction | required: transition table; can apply alone enable allocation? |
| State | required: transition table; does unactivated allocation refuse? |
| Data/trust | required: transition table; what stays private and owner-reviewed? |
| Schema | not_applicable: existing policy/snapshot schema retained |
| Dependency/deployment | not_applicable: native findmnt and Worktrunk, no new service |
| Quantitative | not_applicable: no numerical claim |

| State/action | Owner | Result |
|---|---|---|
| Foundation apply | Distribution/setup | Policy + native config; activation remains absent/unchanged |
| Switch without matching activation | Worktrunk guard | Refuse new allocation; retain existing work |
| Snapshot | Read-only validator | Private proposal with native root identity |
| Review then install proposal 0600 | Human owner | Explicit activation, no assistant write |
| Native switch with matching activation | Worktrunk | Create code-only checkout in existing namespace |
| Changed policy/version/identity | Worktrunk guard | Refuse pending renewed owner review |

**Text Equivalent:** Apply supplies coherent policy/config but no activation.
Snapshot reads native identity into a private proposal. Only the owner may review
and install it; native Worktrunk then allocates through the unchanged guard.
Missing or stale activation blocks new work without removing retained work.
Canonical sources: workflow-policy, chezmoi templates and smoke. Owner:
distribution maintainer. Update when ownership, identity or activation changes.
