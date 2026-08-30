# Codex Control Plane Changelog

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
