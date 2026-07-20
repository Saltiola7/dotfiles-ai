# Backlog — DBSCTR V3 Lifecycle

Discovery readiness: complete.

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| V3.25-1 | Normalize lifecycle backlogs and audit their structure | high | in_progress | - | Lifecycle backlog contract, four current context backlogs, roadmap correction, fixed-commit audit findings, V3.17 restart verification | Committed lifecycle artifacts, Git history, current audit JSON contract, DAI-004 follow-up | no | Executable backlogs currently contain completed Active rows, duplicate IDs, stale decisions, and contradictory completion evidence that the audit does not detect | M | Red/green fixed-commit fixtures for every canonical rule, legacy artifact normalization, additive JSON compatibility, V3.17 live verification, affected pytest, diff check, deployment identity, and live report-only audit |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| V3.24-1 | Add private critical-path spans and helper-validated, benchmark-gated read concurrency | 2026-07-19 | `526515b`, `06312c4`, `876b171`, `ef78f0d`, `609ca49` |
| V3.22-1 | Add immutable activation-bound 30-day benchmark effects and deterministic replay | 2026-07-19 | `b4c5993` |
| V3.21-1 | Add privacy-safe structured telemetry with explicit capability availability and attribution | 2026-07-19 | `ae537d2`, `26589ce` |
| V3.20-1 | Add atomic multi-page captures and bounded summary/drill-down replay | 2026-07-19 | `f3f84b2`, `8ce2317`, `cdc91fc`, `2a4d27c` |
| V3.16-3 | Save source-bound continuation cohorts despite unrelated history writes | 2026-07-18 | `edf481a`, `920156b`, `d833df3` |
| V3.16-2 | Refresh mixed live and archive-only history cohorts during save | 2026-07-18 | `bc2bb08` |
| V3.12-5 | Allow page-stable completion during unrelated OpenCode writes | 2026-07-18 | `9830b2f` |
| V3.23-1 | Add capability-first autonomous improvement coordination and draft-PR delivery | 2026-07-18 | `9b77969`, `5f12796`, `7b863d8`, `04627bf`, `6f9a112` |
| V3.19-1 | Add transactional private SQLite review ledger | 2026-07-16 | `5cd1fd5`, `8468feb` |
| V3.18-1 | Add exact runtime correlation and resumed-runtime attachment | 2026-07-16 | `4729796`, `d506ab7` |
| V3.17-1 | Make live history self-safe while preserving external mutation detection | 2026-07-16 | `caa1fd7`, `5b66415`, `c669a24`, `eb3c9fc`, `03a1958` |
| V3-1–V3-15 | Implement and deploy DBSCTR V3 lifecycle | 2026-07-11 | Historical `3151772`; imported by `ea9eaeb` |
| V3-16 | Automate Gate Commits and Final Push | 2026-07-11 | Historical `f7b11ca`; imported by `ea9eaeb` |
| V3.1-1–V3.1-5 | Add deterministic V3.1 cycles and OpenCode integration | 2026-07-12 | Historical `c9827e0`; imported by `ea9eaeb` |
| V3.2-1–V3.2-5 | Add planned, ordered, monotonic cycle transitions | 2026-07-12 | Historical `da65d0b`, `66df166`, `00c2950`; imported by `ea9eaeb` |
| V3.3-1–V3.3-4 | Isolate concurrent worktree cycle state and delivery | 2026-07-12 | Historical `d444950`, `7d80d21`; imported by `ea9eaeb` |
| V3.4-1–V3.4-3 | Automate isolated cycle setup and safe cleanup | 2026-07-12 | Historical `da4ddf8`, `2b4191a`; imported by `ea9eaeb` |
| V3.5-1–V3.5-4 | Add typed OpenCode and Herdr execution adapters | 2026-07-12 | Historical `d9a7363`, `9916235`; imported by `ea9eaeb` |
| V3.6-1–V3.6-3 | Add fixed-commit lifecycle reconciliation audit | 2026-07-12 | Historical `696971c`, `178bf26`; imported by `ea9eaeb` |
| V3.6.1-1 | Correct integrated roadmap and stale-base delivery | 2026-07-12 | Historical `02bcf34`, `1b75001`; imported by `ea9eaeb` |
| V3.6.2-1 | Enforce begin authorization and correct Method Revision | 2026-07-12 | Historical `95ef8ba`; imported by `ea9eaeb` |
| ROADMAP-1 | Persist approved V3.7–V3.10 roadmap and boundaries | 2026-07-12 | Historical `08cd102`; imported by `ea9eaeb` |
| V3.7-1–V3.7-4 | Add bounded fixed-commit inspection and typed adapter | 2026-07-12 | Historical `4af8365`; imported by `ea9eaeb` |
| V3.8-1–V3.8-4 | Add secret-safe Evidence Envelopes and Python reference | 2026-07-12 | Historical `9fd353d`; imported by `ea9eaeb` |
| V3.9-1–V3.9-3 | Add report-only semantic reconciliation protocol | 2026-07-12 | Historical `82dd3da`; imported by `ea9eaeb` |
| V3.10-1–V3.10-4 | Add conditional Product Intent and Web/UI guidance | 2026-07-12 | Historical `d0bc5bd`; imported by `ea9eaeb` |
| V3.11-1–V3.11-4 | Add private lifecycle review and delivery hygiene | 2026-07-15 | `f2eb3f1` |
| V3.12-1–V3.12-4 | Make private review snapshots and state trustworthy | 2026-07-15 | `e04aa78` |
| V3.13-1 | Stabilize private review retention and queue semantics | 2026-07-15 | `6e072b2` |
| V3.14-1 | Add structured OpenCode and advisory Herdr correlation | 2026-07-15 | `537c3a2` |
| V3.15-1 | Reconcile linearly integrated Final Push targets | 2026-07-15 | `bdf7fe8` |
| V3.16-1 | Add repeatable historical review and backtesting | 2026-07-16 | `25fb2b1`, `e61a150` |

## Notes

Graphify and Herdr runtime hygiene remain separate bounded-context work.
