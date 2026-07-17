# Backlog — DBSCTR V3 Lifecycle

Discovery readiness: complete.

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| V3.17-1 | Make live history self-safe | critical | done | — | Caller exclusion, snapshot identity, validated archive reuse | V3.16 history contract, OpenCode tool context | yes, only with OCP-16 | Typed caller self-mutation is excluded without weakening unrelated mutation detection | M | 124 tests, live deployment, independent privacy review, active-tool continuation/save fixtures |
| V3.18-1 | Correct correlation and attach resumed runtimes | critical | done | V3.17-1 | Correlation precedence, quality, runtime attachment, Cycle Record compatibility | Runtime IDs, worktrees, session families | no | Source fallback duplicates cycles and telemetry | M | 128 tests, typed context fixtures, live quality scan, deployment, independent review |
| V3.19-1 | Add private SQLite improvement ledger | high | ready | V3.17-1,V3.18-1 | Ledger schema, migrations, JSON compatibility, backup, restore | Private review history | no | Durable trends and experiments need transactional relational state | L | Migration, permissions, atomicity, integrity, backup, and restore tests |
| V3.20-1 | Add multi-page captures and compact history transport | high | ready | V3.19-1 | Logical manifests, aggregate projection, bounded drill-down, replay | Ledger and history filters | no | Cohorts exceed 100 and current output truncates | M | 201-session replay, response-size, ordering, deletion, and latency tests |
| V3.21-1 | Add structured telemetry and attribution | high | ready | V3.18-1,V3.19-1 | Capability detection, stable error classes, model families, attribution status | OpenCode schema and correlation quality | no | Approval, retry, delegation, and failure causes are unavailable | L | Optional-schema, unavailable-semantics, privacy, and attribution tests |
| V3.22-1 | Add longitudinal benchmarks and implementation effects | high | ready | V3.20-1,V3.21-1 | Benchmark runs, before/after windows, recurrence, effect tracking | Cycles, deployments, review runs | no | Implemented changes are not evaluated over time | M | Baseline, replay, confounder, neutral, invalid, and regression tests |
| V3.23-1 | Make daily review autonomous and creatively adaptive | high | ready | V3.20-1,V3.22-1,OCP-16 | Default loop, steering, lens rotation, dedupe, proposal handoff | Ledger, Scout, Context7, backlogs | no | Daily use needs low-steering continuous improvement | M | New-session, no-session, no-finding, steering, creative-lens, and restart scenarios |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| V3.18-1 | Add exact runtime correlation and resumed-runtime attachment | 2026-07-16 | `4729796`, `d506ab7` |
| V3-1–V3-15 | Implement and deploy DBSCTR V3 lifecycle | 2026-07-11 | `3151772` |
| V3-16 | Automate Gate Commits and Final Push | 2026-07-11 | `f7b11ca` |
| V3.1-1–V3.1-5 | Add deterministic V3.1 cycles and OpenCode integration | 2026-07-12 | `c9827e0` |
| V3.2-1–V3.2-5 | Add planned, ordered, monotonic cycle transitions | 2026-07-12 | `da65d0b`, `66df166`, `00c2950` |
| V3.3-1–V3.3-4 | Isolate concurrent worktree cycle state and delivery | 2026-07-12 | `d444950`, `7d80d21` |
| V3.4-1–V3.4-3 | Automate isolated cycle setup and safe cleanup | 2026-07-12 | `da4ddf8`, `2b4191a` |
| V3.5-1–V3.5-4 | Add typed OpenCode and Herdr execution adapters | 2026-07-12 | `d9a7363`, `9916235` |
| V3.6-1–V3.6-3 | Add fixed-commit lifecycle reconciliation audit | 2026-07-12 | `696971c`, `178bf26` |
| V3.6.1-1 | Correct integrated roadmap and stale-base delivery | 2026-07-12 | `02bcf34`, `1b75001` |
| V3.6.2-1 | Enforce begin authorization and correct Method Revision | 2026-07-12 | `95ef8ba` |
| ROADMAP-1 | Persist approved V3.7–V3.10 roadmap and boundaries | 2026-07-12 | `08cd102` |
| V3.7-1–V3.7-4 | Add bounded fixed-commit inspection and typed adapter | 2026-07-12 | `4af8365` |
| V3.8-1–V3.8-4 | Add secret-safe Evidence Envelopes and Python reference | 2026-07-12 | `9fd353d` |
| V3.9-1–V3.9-3 | Add report-only semantic reconciliation protocol | 2026-07-12 | `82dd3da` |
| V3.10-1–V3.10-4 | Add conditional Product Intent and Web/UI guidance | 2026-07-12 | `d0bc5bd` |
| V3.11-1–V3.11-4 | Add private lifecycle review and delivery hygiene | 2026-07-15 | `f2eb3f1` |
| V3.12-1–V3.12-4 | Make private review snapshots and state trustworthy | 2026-07-15 | `e04aa78` |
| V3.13-1 | Stabilize private review retention and queue semantics | 2026-07-15 | `6e072b2` |
| V3.14-1 | Add structured OpenCode and advisory Herdr correlation | 2026-07-15 | `537c3a2` |
| V3.15-1 | Reconcile linearly integrated Final Push targets | 2026-07-15 | `bdf7fe8` |
| V3.16-1 | Add repeatable historical review and backtesting | 2026-07-16 | `25fb2b1`, `e61a150` |

Graphify and Herdr runtime hygiene remain separate bounded-context work.
