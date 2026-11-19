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

## Current cycle

Import slice (`import-rdev-sessions`): risk elevated (company-sensitive data
movement, private-store mutation), delivery draft PR of the initiative
records, deploy evidence from the executed VM-side import.
