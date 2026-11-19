# rdev Workspace Import

Import of the company remote-development (rdev) working set from the retired
macOS host into the Try Omarchy VM: session cluster, triaged worktrees, and
handoff. Company-anonymized by contract; see the
[rdev-workspace-import](../../initiatives/rdev-workspace-import/README.md)
initiative for scope and slices.

## Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Company-anonymized initiative records plus operational migration runbook evidence; no managed source in this repository |
| Owner | Project maintainers |
| Languages/frameworks | Markdown, JSON manifests, shell-based export/import |
| Modules | Shell; no application modules |
| Runtime/platform support | Try Omarchy VM (Arch Linux aarch64, sole workstation); macOS host is the read-only export source |
| Compatibility | Public-tree identifier neutrality (publication test); VM-private session store schema as provided by the transplant machinery |
| Trust/data | Company-private session rows and worktree content live only in VM-private locations; never in this repository |
| Validation | `dbsctrctl initiative-check`, repository publication test, row-scoped export verification, worktree status-parity checks |
| Release/deploy | No release artifact; deployment is the VM-side import recorded as deploy-gate evidence |
| Operations | Operator-owned resume after migration; no resident services |

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | not_applicable: one operational boundary (host store to VM store) fully specified in text | - | Initiative README, Contracts | Workspace owner; a second source or target appears |
| Interaction | not_applicable: the only human interaction is the handoff note and one operator authentication | - | Handoff contract (INT-004) | Workspace owner; resume flow changes |
| State | not_applicable: migration is one-shot; session/worktree states are recorded as row counts and status parity in the CHANGELOG entry | - | CHANGELOG, verification scripts | Workspace owner |
| Data/trust | not_applicable: company-private rows move between private stores only; the public repository receives anonymized text exclusively | - | INT-005, INT-006, publication test | Workspace owner; a new data class crosses stores |
| Schema | not_applicable: the export/import JSON shape belongs to the OpenCode tooling, not this specification | - | Transplant machinery | Workspace owner; tooling major version |
| Dependency/deployment | not_applicable: deployment is a single VM-side import recorded as deploy-gate evidence | - | Gate Ledger | Workspace owner |
| Quantitative | not_applicable: message counts and parity counts are recorded facts, not comparative evidence | - | CHANGELOG entry | Workspace owner |

## Current cycle

Import slice (`import-rdev-sessions`): risk elevated (company-sensitive data
movement, private-store mutation), delivery draft PR of the initiative
records, deploy evidence from the executed VM-side import.
