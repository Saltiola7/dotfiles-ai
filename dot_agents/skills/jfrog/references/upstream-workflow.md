# Local scope for the retained workflow

The complete upstream workflow below is retained for task-specific reference. The active [skill](../SKILL.md) and [local execution boundaries](local-ownership.md) govern every procedure. Environment probes, telemetry/model disclosure, upgrade offers, installation, login and runtime permission recipes below are conditional upstream facilities, never automatic prerequisites. Do not execute a helper or change an installer, credential or client configuration merely to follow this reference. Skill-root-relative backtick paths still refer to the enclosing skill root.

# JFrog Skill

Extended JFrog Platform concepts, CLI/API mechanics and workflow examples. The
compact entrypoint owns current selection and execution boundaries.

## At a glance (always-read core)

Network-facing `jf` this session. Exempt until `<SID>`: `jf --version`,
`jf config show`.

**Tier A — always-read floor** (before first *non-exempt* `jf`):

- **Environment:** use existing version-qualified tools. Upstream environment,
  telemetry/cache and upgrade helpers are conditional facilities governed by
  [local ownership](local-ownership.md), not mandatory session probes.
- **Server:** resolve default once → `--server-id <SID>` **after** subcommand
  (`jf api --server-id …`, never `jf --server-id … api`). One request → one
  server (unless user names servers, e.g. `compare <a> and <b>`)
- **Error (401/403/404/timeout):** never hop servers. List a repo with AQL
  (local or `<remote>-cache`). 401 → report authentication failure; only after separately authorized
  same-server recovery, consider at most one retry. 403/404/timeout → never re-fire
  the same path+query (package-block 403 → `jfrog-package-curation`). Empty
  `offset`/`page` → stop. Pager ≤20 pages. Same path 403 → stop (one hop)
- **No prep mutations:** missing repo/artifact/build → stop + report; no
  create/copy/move/upload to fill the gap (workaround ask ≠ permission)
- **Never guess** tools / `jf api` paths → tool list / `--help` / `references/`.
  404 → stop (no guessed retry). `jf api` needs product prefix
  (`/artifactory`, `/xray`, …). Never `GET /api/v1/artifacts` to list a repo
- **Hard-rule signals:** [Cautious execution](#cautious-execution),
  [Server selection rules](#server-selection-rules-mandatory),
  [Gotchas](#gotchas--hard-rules-never-skip) Tier A bullets below — not tips
- **Gotcha floor (Tier A):** never interactive (`jf config add`, `jf login`,
  template wizards, …); if a call fails **with** `--server-id`, do **not**
  retry without it; 401 → authorized same-server recovery only; 403/404/timeout → stop, never
  hop or loop; `--quiet` is not global — check `--help` before adding it

**Tier B — path-gated MUST** (before `jf api` / AQL / advanced CLI I/O /
MCP-result-via-shell anti-patterns): full
[`references/cli-gotchas.md`](../references/cli-gotchas.md),
[`references/jf-api.md`](../references/jf-api.md),
[`references/preserving-command-output.md`](../references/preserving-command-output.md),
[`references/cli-command-discovery.md`](../references/cli-command-discovery.md).
Setup / `jf setup` / ordinary CLI do **not** require Tier B.

**Tier C — on-demand:** [`references/INDEX.md`](../references/INDEX.md) domain
refs; login / CLI install when needed.

Contents (prefer full SKILL.md; At a glance = Tier A floor if you only see the
top):

| Section | Topic |
|---------|-------|
| [Tool selection strategy](#tool-selection-strategy) | MCP vs CLI vs `jf api` |
| [Prerequisites](#prerequisites), [Environment check](#environment-check) | before first non-exempt `jf` |
| [Cautious execution](#cautious-execution), [Server selection rules](#server-selection-rules-mandatory) | **Tier A hard rules** |
| [Gotchas — hard rules](#gotchas--hard-rules-never-skip) | Tier A reminders; full `cli-gotchas.md` = **Tier B** |
| [Path-gated base references](#path-gated-base-references-must-before-jf-api--advanced-cli) | **Tier B MUST** before `jf api` / advanced CLI |
| [When to read reference files](#when-to-read-reference-files) → [`references/INDEX.md`](../references/INDEX.md) | Tier C domain refs |
| [Command discovery](#command-discovery) / [jf api](#invoking-platform-apis-with-jf-api) | Tier B when those paths apply |
| [Structured inputs](#structured-inputs) / [Batch](#batch-and-parallel-execution) / [Preserving output](#preserving-command-output) | templates / parallel / temp files |

> **Floor for partial reads:** Tier A (this section) before first non-exempt
> `jf`. Prefer the full SKILL.md when you can. Load **Tier B** only when the
> next action needs `jf api` / AQL / advanced CLI I/O (checklist). Domain
> detail → Tier C [`references/INDEX.md`](../references/INDEX.md).

Interact with the JFrog Platform through three tool tiers — see
[Tool selection strategy](#tool-selection-strategy). In code examples,
`<skill_path>` is this skill's directory, resolved automatically by the agent.
If unresolved, locate this SKILL.md file and use its parent directory.

> **MCP ownership:** existing native client/configuration owners handle general
> MCP management. The JFrog Agent Guard workflow applies only when a JFrog-governed
> catalog or Agent Guard task is explicitly selected. Installing this collection
> neither enables governance nor installs the Agent Guard npm package.

## Tool selection strategy

Choose the existing capability appropriate to the task. A missing feature can
justify another already authorized same-target capability; an access denial does
not justify trying a more privileged transport:

1. **JFrog MCP tools** (when already connected and appropriate): `CallMcpTool` against the JFrog MCP
   server. Discover available tools from the server's tool list; never
   guess tool names.
2. **`jf` CLI subcommands** (fallback): dedicated commands such as
   `jf rt upload`, `jf rt dl`, `jf build-publish`.
3. **`jf api`** (last resort): REST/GraphQL endpoints with no dedicated
   subcommand. Validate the path first — see rule 6 in
   [Cautious execution](#cautious-execution).

MCP and CLI may use different token scopes and target identities. Verify both
before combining evidence; never change transport or credentials merely to bypass
a 401/403 or other denial. Report failure and preserve the selected target.

## Prerequisites

The following tools must be available on `PATH`:

| Tool | Purpose |
|------|---------|
| `jq` | JSON parsing of CLI and API output |

All JFrog HTTP traffic from Tiers 2 and 3 goes through the `jf` CLI itself
(`jf api`, see [Invoking platform APIs with `jf api`](#invoking-platform-apis-with-jf-api) below) —
no standalone `curl` is required for any JFrog interaction.

**Runtime permission:** use the actual native permission model. Do not infer a
blanket network/filesystem escalation from an upstream harness example. Missing
access remains a capability gap; respect denials and existing configuration owners.

## Environment check

Use the compact entrypoint's capability/version contract and existing installer
owner. Missing or incompatible CLI does not trigger an installation, login or
upgrade. Planning and existing appropriate MCP tools can remain usable without CLI.

The complete upstream `check-environment.mjs`/`.sh` and
`cli-newer-version-offer.mjs`/`.sh` resources remain present. They can contact
release endpoints, write cache/state and emit model-bearing telemetry headers.
Read [local ownership](local-ownership.md) and the actual scripts before selecting
them for an explicitly relevant diagnostic. Do not invent a model identity, export
telemetry, execute a version offer or clear state merely because this reference
was loaded. Ordinary operations need no upstream-generated user agent.

Use private temporary directories for task output, selected with unpredictable
names and appropriate permissions; reuse captured output for parsing. Avoid
predictable shared `/tmp` filenames and credential-bearing stdout/logging.

## Cautious execution

**HARD RULES — never skip.** Speculative / preparatory / guessed ops are
forbidden. Before any JFrog CLI command, MCP tool call, or API call:

1. Confirm the operation is needed to fulfill the user's request.
   If the request is ambiguous or could refer to multiple systems (e.g.
   "builds" could mean Artifactory build-info or CI/CD pipeline runs),
   **ask the user for clarification** instead of guessing. Never fetch data
   from the wrong system — a wrong answer is worse than asking a question.
2. Resolve the target server using the **Server selection rules** below —
   there must be no ambiguity about which server is used
3. For mutating operations (create, update, delete, upload), confirm with the
   user unless the intent is clearly implied. This applies to all tiers
   (MCP tools, CLI commands, and `jf api` with POST/PUT/DELETE).
4. Prefer read operations first to understand current state before making changes
5. **Never invent preparatory mutations.** If the requested operation fails
   because a precondition is not met (artifact missing from the specified repo,
   repository does not exist, package not at the expected location, build not
   found), **stop and report the gap to the user**. Do not perform copy, move,
   upload, create-repo, or any other mutating operation to satisfy the
   precondition. "Put it there so the download succeeds", "make it work", or
   "do whatever you need" is still a workaround — not permission to invent
   the missing artifact. Only perform that mutation when it **is** the
   user's requested work (publish this file, create this repo, move this
   artifact), not a helper to make a different operation succeed. These
   "helper" mutations
   can have cascading effects the user has not considered — virtual repository
   resolution changes, storage quota consumption, replication triggers, Xray
   re-indexing, or permission propagation.
6. **Never guess tool names or API paths.** For MCP tools, confirm the tool
   exists in the server's tool list. For `jf api` paths, validate against
   `<skill_path>/references/` (or
   [JFrog OpenAPI specifications](https://docs.jfrog.com/integrations/docs/openapi-specifications)
   if you have web access). On a 404, stop and report — never retry with a guessed
   alternative path.
7. **Never retry a failed call in a loop.** AQL on `<repo>-cache` (virtuals
   are not `-cache`). 401 → then **one** retry. Pager **20-page cap** —
   `cli-gotchas.md`. Do not invent `GET /api/v1/artifacts`.

## Server selection rules (mandatory)

**HARD RULES — never skip or soften.** Wrong-server answers and silent
server-switching are worse than stopping to ask.

**Single-server invariant.** After `<SID>` is resolved, every subsequent
network-facing `jf` call MUST pass `--server-id <SID>` (default resolved below);
bootstrap `jf --version` / `jf config show` stay exempt until then. For one user
request, all network `jf` calls use **exactly one** server-id — unless the user
names servers to compare (e.g. `compare <a> and <b>`), where each call passes
its own target's `--server-id`.

**JFrog MCP and CLI use independent auth.** MCP tools authenticate through
the MCP server session (not `jf config`); CLI commands authenticate through
`jf config`. If you switch the CLI target server via `jf config use`, the
MCP connection still points to its original server. Do not mix MCP and CLI
calls targeting different servers in the same session. If the user asks to
switch servers, warn that MCP tools will continue to target the original
server until the MCP connection is re-established.

**MUST NOT** retry on a second configured server after 401/403/404, empty, or
partial results; **MUST NOT** infer multi-server intent from "my"/"our" or
from seeing extra entries in `jf config show`. **Override:** only when the user
**explicitly** names another id ("on `<id>`, …", "use `<id>`", "compare `<a>`
and `<b>`") — inferred intent is not an override.

### Resolve the default once per session

Before your first `jf` call, resolve the default server-id and **remember it**
as `<SID>` for the rest of the session, without changing the global default:

```bash
jf config show 2>/dev/null \
  | awk '/^Server ID:/{id=$NF} /^Default:[[:space:]]*true/{print id; exit}'
# stdout: the default server-id; if empty, stop and ask which to use
```

Pass `--server-id <SID>` to every subsequent network-facing `jf` call. The flag goes
**after** the subcommand name, not after `jf` itself:

- ✅ `jf api --server-id <SID> /artifactory/api/system/version`
- ✅ `jf rt ping --server-id <SID>`
- ❌ `jf --server-id <SID> api /…` — fails with `flag provided but not defined`

When launching a subagent, pass `<SID>` in its prompt — subagents do not
re-resolve. Examples elsewhere in this skill and in `references/*.md` omit
`--server-id` for readability; the explicit target rule remains global. To add a new server, read
`references/jfrog-login-flow.md`.

### On any error, stop — never switch

If a `jf` call returns 403, 404, network error, timeout, or any other
non-401 failure, **stop with no further `jf` calls** and respond. 401 →
report the authentication gap. After separately authorized same-server recovery,
at most one retry is justified; if that fails, stop:

> `<server-id>` returned `<code>` for `<endpoint>`: `<short reason>`. Other
> configured server(s): `<list>` — I won't query them without your explicit
> instruction. How would you like to proceed?

## Path-gated base references (MUST before `jf api` / advanced CLI)

These four files **are Tier B of the base skill** — content that used to live
in this SKILL.md. They are **not** optional INDEX domain lookups, and they are
**not** required before every CLI / setup path.

**MUST read every one in full before** `jf api`, AQL via `jf api`, advanced
CLI I/O (temp-file / stdout-stderr patterns), or acting on MCP results via
shell/`jq`. Ordinary `jf` (e.g. `jf setup`, `jf rt …` with known flags) needs
**Tier A only** ([At a glance](#at-a-glance-always-read-core)).

The short [Gotchas](#gotchas--hard-rules-never-skip) Tier A bullets are the
session floor — **they do not replace** full
[`references/cli-gotchas.md`](../references/cli-gotchas.md) when you enter Tier B.

| Tier B — MUST read in full (path-gated) | Covers |
|-----------------------------------------|--------|
| [`references/cli-gotchas.md`](../references/cli-gotchas.md) | gotchas, caveats, known issues, do/don't, I/O & auth traps |
| [`references/jf-api.md`](../references/jf-api.md) | product-prefix table, flags, examples, GraphQL payload |
| [`references/preserving-command-output.md`](../references/preserving-command-output.md) | private `mktemp -d` dir, no re-fetch for `jq` |
| [`references/cli-command-discovery.md`](../references/cli-command-discovery.md) | namespaces, top-level cmds, Pipelines sunset |

Skipping any of these **on a Tier B path** = incomplete base-skill load /
hard-rule violation. Skipping them on a Tier A-only path (setup / simple CLI)
is **not** a violation.

## When to read reference files

Read the compact [entrypoint](../SKILL.md) once for common guards. This extended
workflow is lazy reference material, not a mandatory full-context bootstrap. **Path-gated base references**
above are **Tier B** (mandatory on those paths, not every session). Everything
else under [`references/INDEX.md`](../references/INDEX.md) is **Tier C** domain
detail — load ≤2–3 most specific files for the task; skip unused domains.

`references/INDEX.md` lists every `references/*.md` file (Tier B + Tier C).
Update INDEX when adding, renaming or removing local reference files. The
distribution validates resource closure and provenance in its own test suite.
## Command discovery

Run `--help` to verify options — do not rely on memorized commands.

1. `jf --help` → 2. `jf <namespace> --help` → 3. `jf <command> --help`

**Tier B — MUST read in full before relying on discovery beyond `--help`:**
[`references/cli-command-discovery.md`](../references/cli-command-discovery.md)
(namespaces, top-level lifecycle/security commands, Pipelines sunset).

## Invoking platform APIs with `jf api`

Tier 3 for Platform REST/GraphQL, auto-authenticated. **Do not use
`jf rt curl` / `jf xr curl`.** Always include the **product prefix**
(`/artifactory`, `/xray`, `/access`, …) — omit → 404.

**Tier B — MUST read in full before `jf api`:**
[`references/jf-api.md`](../references/jf-api.md)
(prefixes, flags, examples, OneModel GraphQL payload). Body on stdout / status
on stderr — see [Gotchas](#gotchas--hard-rules-never-skip) + full
`cli-gotchas.md` (Tier B).
## Structured inputs

Interactive wizards (`jf rt rpt` / `ptt` / `rplt`) are unusable for agents.
Fetch an existing config via REST and edit:

```bash
jf api /artifactory/api/repositories/<repo-key>
```

More REST/template patterns → `references/artifactory-api-gaps.md` or
`references/platform-admin-api-gaps.md` via [`references/INDEX.md`](../references/INDEX.md).

## Gotchas — hard rules (never skip)

**Not tips.** Tier A bullets below are the always-read floor. Full
[`references/cli-gotchas.md`](../references/cli-gotchas.md) is **Tier B** —
**MUST** before `jf api` / AQL / advanced CLI I/O / MCP-via-shell; **not**
required before every CLI or `jf setup`. Short bullets do **not** replace the
full file on Tier B paths.

**Tier A floor (every non-exempt `jf` session):**

- **`--quiet`** is not global — check `--help` before adding it
- **`--server-id`:** if a call fails with it, do not retry without it (silent
  default-server switch). See [Server selection rules](#server-selection-rules-mandatory)
- **Non-interactive only** — avoid `jf config add`, `jf login`, `*template`
  wizards; use `references/jfrog-login-flow.md` / REST
- **Auth errors:** 401 → report; retry once only after authorized same-server recovery.
  403 → stop (package-block → `jfrog-package-curation`). 404 → path, stop

**Tier B reminders (load full `cli-gotchas.md` + sibling Tier B refs before
these paths):**

- **MCP:** read structured tool results directly — do not pipe through shell/`jq`
- **`jf api` I/O:** body → stdout, status → stderr; pipe stdout to `jq`;
  **never `2>&1 | jq`**. No `-L` / `-o` — redirect: `jf api … > "${JF_TMP:?}/<label>.json"`
- **Product prefix** required on every `jf api` path (see Tier B `jf-api.md`)
- **Never re-fetch to retry `jq`** — save output first
  ([Preserving command output](#preserving-command-output) + Tier B
  `preserving-command-output.md`)
## Batch and parallel execution

Independent ops → lightest parallelism: (1) loops/`&` in one Shell, (2) parallel
Shell calls, (3) subagents for large fan-out. Details →
`references/general-parallel-execution.md`.

## Preserving command output

Save network responses inside a private `mktemp -d` dir (created once, echoed,
reused); re-read for `jq` — never re-run the same network call to fix parsing.

**Tier B — MUST read in full before advanced I/O / re-parse patterns:**
[`references/preserving-command-output.md`](../references/preserving-command-output.md)
(`JF_TMP` dir + echo, no re-fetch / no cross-context reuse).

## Before you run `jf` — quick checklist

[At a glance](#at-a-glance-always-read-core) **Tier A** floor; add **Tier B**
only when the next action needs `jf api` / advanced CLI:

- [ ] Existing version-qualified capability, installer/config owner and task authority
      established; no automatic telemetry/environment/update helpers.
- [ ] network `jf`: `--server-id <SID>` after subcommand (not `jf --version` /
      `jf config show` pre-SID)
- [ ] one server; error → stop, don't switch (multi only if user names /
      `compare`); no prep create/copy/move/upload to fill a gap
- [ ] never guess tools/paths → list / `--help` / `references/`; 404 → stop;
      `jf api` product prefix; same path 403/404 → stop (no pager); never
      `GET /api/v1/artifacts`
- [ ] **Tier A** hard rules: Cautious execution + Server selection + Gotchas
      floor (interactive / `--server-id` retry / stop-on-error / `--quiet`)
- [ ] **Tier B** (`jf api` / AQL / advanced CLI I/O): full `cli-gotchas.md`,
      `jf-api.md`, `preserving-command-output.md`, `cli-command-discovery.md`
