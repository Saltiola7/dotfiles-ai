# Binding execution boundary

Review scripts before use. Preserve the selected workspace/configuration owner,
private preimages and all unrelated state. Installing guidance executes no merge
and starts no hook. The helper writes only `repositories` and can drop unknown
top-level fields: reconcile such fields before use rather than silently losing
them. Concrete task consent persists; do not impose repeated confirmation.

# `.jfrog/local/package-resolution.json` — Workspace Binding File

This records non-secret workspace decisions for an explicitly selected binding.
A separately installed SessionStart hook may consume them; standalone skills do
not install that hook or make a marker proof of active routing.

The file is the **decisions** record, not a credential store. Tokens live
in `jf config` and in package-manager-native files written by `jf setup` itself.

## Location

```
<workspace-root>/.jfrog/local/package-resolution.json
```

`<workspace-root>` is the directory the user opened in the IDE — **not**
`$HOME`. Workspace-scoped on purpose: different projects can override
different Artifactory repos.

## Schema

```json
{
  "repositories": {
    "npm": "<repository-key>",
    "pypi": "<repository-key>",
    "maven": "<repository-key>",
    "gradle": "<repository-key>",
    "go": "<repository-key>",
    "docker": "<repository-key>",
    "helm": "<repository-key>",
    "nuget": "<repository-key>"
  }
}
```

| Field | Required | Description |
|---|---|---|
| `repositories` | yes | Map keyed by **package type** — same keys as `servers.<serverId>.repositories` in the global resolver cache. Omit package types you do not override. |

### Package-manager name → package type (when merging after `jf setup`)

Aligned with Agent Package Resolution (`PACKAGE_TYPES` / eager families).
`gradle` is its **own** Artifactory package type — never fold it under `maven`.

| `jf setup` package manager | `repositories` key |
|---|---|
| `npm`, `pnpm` | `npm` |
| `yarn` | `npm` (CLI may still accept `jf setup yarn`; APR zero-touch does **not** auto-setup yarn — only bind on explicit user request) |
| `pip`, `pipenv`, `uv`, `twine` | `pypi` |
| `poetry` | `pypi` (CLI may accept it; APR zero-touch does **not** auto-setup poetry — bind only on explicit user request) |
| `maven` | `maven` |
| `gradle` | `gradle` |
| `go` | `go` |
| `docker`, `podman` | `docker` |
| `helm` | `helm` |
| `nuget`, `dotnet` | `nuget` |

## Operations

### 1. Load

Before setup, **read** the file (if it exists). For each package manager in the
to-bind set, map it to a package type and compare
`repositories.<type>` against what the resolver chose in Step 2:

| Case | Action |
|---|---|
| Missing type in `repositories` | Validate selected repo and authorized config change; merge only after actual setup success. |
| Same repo key | Verify actual unchanged native configuration/selected hook before skipping; the marker alone is not readiness proof. |
| Different repo key | Review native owner/preimages and perform the concretely authorized change; ask only for missing material selection or authority. |
| Value fails `^[A-Za-z0-9._-]+$` | Not the current binding. Do not diff it or pass it through. Stop and ask for a replacement key. Other types in the file stay usable. |

APR's `normalizeWorkspaceConfig` drops the same unsafe keys when the hook
reads this file. This skill applies that charset on Load because it also reads
the file when the hook is absent. Run `scripts/check-repo-key.sh` before `jf setup`.

### 2. Write / merge

After each successful `jf setup`, run the skill script (do **not** hand-edit
JSON):

```bash
bash <skill_path>/scripts/merge-workspace-binding.sh \
  --package-manager <package-manager> \
  --repo "$REPO" \
  [--workspace-root <workspace-root>]
```

`$REPO` is the key `check-repo-key.sh` printed in this same shell. Do not
substitute the raw binding-file value, and do not paste that value into the
checker command. Load it with `jq -r` into `$raw`, then pass `--repo "$raw"`.

The script:

1. Maps `--package-manager` → package type using the table above (unknown PM → exit 1).
2. Validates `--repo` (`^[A-Za-z0-9._-]+$`).
3. Reads the current file (ENOENT → empty `repositories`).
4. Sets `repositories[<pkgType>] = <repoKey>`, preserve other package types, **last write wins** for the same type.
5. Writes `{ "repositories": { ... } }` only (drops other top-level keys), 2-space indent, atomic replace via `mktemp` + `mv`.
6. Serializes concurrent merges with a workspace **directory** lock (`package-resolution.lock.d`; symlink-safe; reclaim when owner PID is dead on this host or the owner hostname differs; owner-less lock dirs are **not** reclaimed — `mkdir` is the mutex; reclaimers take an exclusive side-gate so a late reclaim cannot delete a newly acquired lock).
7. On corrupt/invalid existing JSON → exit 1 and **leaves the file untouched**.
8. Requires `jq`; if missing → exit 1.

### 3. Never write

- Credentials (`accessToken`, passwords, …).
- Package-manager-native config paths — those are owned by `jf setup`.

## Integration contract

| Consumer | What it reads |
|---|---|
| Session-start hook | `repositories` — first workspace root with this file (multi-root) |
| This skill | Round-trip load → diff → confirm → `check-repo-key.sh` → `jf setup` → `merge-workspace-binding.sh` |
| `opencode-jfrog-plugin` | **Not updated** — out of scope until it reads this file |

Changing the `repositories` key semantics is a breaking change; coordinate
with the hook before altering them.
