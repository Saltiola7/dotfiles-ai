# Codex Control Plane Changelog

## 2026-09-01 - History Adapter Sanitization Readiness

- Reopened readiness after current stable history contained interim commentary,
  web-search items, and text rejected by the generic privacy validator.
- Fixed deterministic projection: discard known interim/unsupported non-content
  items, discard unsafe text items, mark content partial with a fixed reason, and
  retain fail-closed handling for unknown shapes. No payload from discarded items
  enters pages or probe output.

## 2026-09-01 - Paginated Stable Read Readiness

- Reopened adapter readiness after the current host exposed only paginated
  threads. A body-free probe confirmed stable `thread/read(includeTurns=true)`
  returns full item views without turn/item pagination.
- Allowed frozen legacy and paginated modes through that same stable full-read
  boundary. Experimental or explicit turn/item pagination remains prohibited;
  missing, summary, or non-full item views fail closed.

## 2026-09-01 - History Adapter Applicability Plan

- Added the committed gate-applicability plan required by typed same-session
  Initiative Begin. Scope, dependencies, runtime contract, and ready slice are
  unchanged; this correction replaces the invalid Markdown plan handoff.

## 2026-09-01 - Remote User Authentication

- Forced remote CLI state into the invoking Unix user's dedicated managed
  `CODEX_HOME` and added version, managed-config, and existing-login readiness.
- The shared readiness command discards all Codex output and reports only a fixed
  success/failure class. Login remains explicit and user initiated.

## 2026-09-01 - Codex History Adapter Readiness

- Reconciled merged generic history-source delivery and promoted only
  `codex-history-adapter`; consumer parity remains captured.
- Fixed pinned app-server schema digests, exact read-only list/read requests,
  private generic page conversion, privacy rejection, and body-free probe output.
- Deferred closed review, Incident, telemetry, immutable-capture, benchmark, and
  federation reducers rather than exposing private pages or inferring mappings.
- No native storage, credentials, paths, raw tool data, reasoning, or public
  content body is added. Implementation, deployment, operation, and completion
  remain separately gated.

## 2026-08-31 - Remote User Authentication Discovery

- Added the CentOS x86_64 peer-runtime contract with dedicated user-local
  `CODEX_HOME`, checksum-pinned installation, independent login, and content-free
  readiness proof.
- Prohibited automatic login, host or peer credential copying, desktop-state
  access, and private storage inspection. No package or runtime changed.

## 2026-08-31 - History Parity Readiness Correction

- Reopened the empty history Build cycle before source changes because the ready
  artifacts did not define how Codex pages enter shared lifecycle consumers or
  whether private text may cross that boundary.
- Approved bounded sanitized user/assistant text in private local pages and one
  generic stateless `dbsctrctl` source-page validator. Credentials, reasoning, raw
  tool data, URLs, paths, duplicate native storage, and public result bodies stay
  excluded.
- Split lifecycle-owned page validation into the new
  `generic-history-source-pages` predecessor with closed request, continuation,
  page, privacy, digest, bounds, failure, and no-mutation contracts. Codex history
  returns to captured until that predecessor is delivered.
- Initiative validation, 248 affected tests, one expected skip, 21 subtests, JSON
  parsing, Git whitespace, and independent elevated-risk review passed. Gate
  Exceptions: none. Intended Final Push: feature branch and draft pull request
  into protected `main`.

## 2026-08-30 - Exact Cross-Platform Identity

- Reconciled merged distribution PR `#104` and recorded the host and all managed
  Fedora guests on the frozen Codex `0.151.0` release with isolated configuration,
  state, and separately verified boundary-local login prerequisites.
- Proved exact equality among hook session, CLI JSONL thread, app-server thread,
  and root-session identity on macOS and representative Fedora. Resume preserved
  exact identity; fork preserved exact parent ancestry with a new fork-thread
  root. The shared stable protocol-schema digest matched across platforms.
- Marked distribution and identity delivered and promoted only history parity.
  Worker routing, recovery, federation, and final parity remain dependency-gated.
- No account identity, credential, runtime identifier, guest name, path, prompt,
  transcript, or private state is retained in Git. Release and Deploy are not
  applicable; the bounded host and representative-Fedora Operate probe passed.
  Initiative validation, 231 affected tests, Python compilation, Git whitespace,
  and independent elevated-risk review passed. Gate Exceptions: none. Discovery
  commits: `d1cf745` and the commit containing this entry. Intended Final Push:
  feature branch and draft pull request into protected `main`.

## 2026-08-30 - Host Foundation

- Added portable managed Codex configuration, global instructions, six native
  roles, five identity hooks, and the standard-library `codex-control-plane`
  adapter without installing, projecting, authenticating, or operating Codex.
- Bounded and sanitized hook input, discarded `transcript_path` unread,
  classified worktrees through authoritative DBSCTR state, capped owner-only
  24-hour records under a bounded lock, and kept session and lifecycle operations
  explicitly unavailable until later probes.
- Initiative validation, 134 affected tests, Python compilation, Git whitespace,
  frozen-source review, and three independent elevated-risk reviews passed. Gate
  Exceptions: none. Release, Deploy, and Operate are not applicable. Development
  Gate Commit: `c53739ceeda963b17492cc16eef99d97e9c77670`. Intended Final
  Push: feature branch and draft pull request into protected `main`.

## 2026-08-30 - Hook Contract Correction

- Reopened and revalidated host-foundation readiness against official Codex
  `0.151.0` source after discovering that every common hook payload carries
  `transcript_path`.
- Recorded this as Discovery-owned revalidation persisted by the Build primary
  from the approved artifact-ready handoff, without changing slice ownership or
  dependencies.
- Accepted that field only as bounded transient input and required immediate
  discard without file access, canonicalization, logging, exposure, or
  persistence; every other unapproved path and all transcript content still fail
  closed.
- Fixed the source contract to stage under `codex-managed`, project custom roles
  as `$CODEX_HOME/agents/**/*.toml`, and use inline command hooks. Distribution,
  authentication, runtime probes, and deployment remain outside this cycle.
- Required evidence is Initiative validation, affected lifecycle/distribution
  tests, Python compilation, Git whitespace, official-source verification, and
  independent elevated-risk review. Gate Exceptions: none proposed. Release,
  Deploy, and Operate are not applicable. Intended Final Push: feature branch and
  draft pull request into protected `main`.

## 2026-08-30 - Host Foundation Readiness

- Promoted only `codex-host-foundation` to receipt-ready after fixing the
  dependency order, existing boundary-local login precondition, six-role native
  agent set, identity-hook schema, strict process/output bounds, transient cwd
  classification, and runtime-private transcript handling.
- Kept distribution captured and identity, history, worker, recovery, federation,
  and final parity slices dependency-blocked with explicit promotion evidence.
- Initiative validation, 154 directly affected lifecycle/distribution/Lima/R&D
  tests, Git whitespace, and fresh official-source research passed. DKS was
  unavailable under its quality-policy lock. The separate existing Herdr
  launch-health latch test remains a blocker for later worker-routing promotion,
  not host-foundation readiness. Gate Exceptions: none. For this Discovery-only
  cycle, Release, Deploy, Operate, and Maintain/Retire are not applicable.
  Intended Final Push: feature branch and draft pull request into protected
  `main`.

## 2026-08-29 - Codex CLI Integration Contract

- Established the Codex control-plane boundary, native-first adapter strategy,
  outcome-parity rules, sanitized evidence allowlist, capability probes, and
  desktop/host/guest state isolation without implementing or deploying Codex.
- The Initiative remains `discovering`; every slice is captured or blocked, all
  ticket arrays are empty, and no Initiative Build launch is authorized.
- Initiative validation, 57 focused helper/lifecycle/distribution tests, Python
  compilation, Git whitespace, official-source verification, and independent
  elevated-risk review passed. Gate Exceptions: none. Release, Deploy, and
  Operate: not applicable. Gate Commit: the commit containing this entry.
