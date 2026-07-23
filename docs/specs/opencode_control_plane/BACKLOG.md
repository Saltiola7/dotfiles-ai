# OpenCode Control Plane Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| OCP-25 | Ask before explicit improvement retirement | high | in_progress | V3.27-1 | OpenCode Bash permission for improvement-forget | DBSCTR improvement retirement command | yes | Permanent local-history deletion must remain confirmation-gated | XS | Rendered config contract and deployed permission resolution |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| OCP-24 | Preserve exact reference root and subtree rules | 2026-07-19 | `4b52a21` |
| OCP-23 | Preserve reference access after global deny | 2026-07-19 | `d0c3942` |
| OCP-22 | Render a portable local repository reference | 2026-07-19 | `ef70477` |
| OCP-21 | Make custom Build selection and routing exact | 2026-07-18 | `8870229` |
| OCP-20 | Allow Build to maintain standalone local config | 2026-07-17 | `b96dd0d` |
| OCP-19 | Expose autonomous R&D worker behavior | 2026-07-18 | `9b77969` |
| OCP-18 | Expose compact history, telemetry, and benchmark interfaces | 2026-07-19 | `0611451` |
| OCP-17 | Expose runtime attachment and advisory Herdr health | 2026-07-19 | `c96093d` |
| OCP-16 | Add Scout-only Context7 and prompt-free safe begin | 2026-07-16 | `791bc22` |
| OCP-15-1 | Pass optional history-save page identity | 2026-07-18 | `920156b` |
| OCP-15 | Add repeatable historical DBSCTR review tools | 2026-07-16 | `e61a150` |
| OCP-14 | Record structured OpenCode and advisory Herdr correlation | 2026-07-15 | `537c3a2` |
| OCP-13 | Preserve review progress across bounded report retention | 2026-07-15 | `6e072b2` |
| OCP-12 | Preserve immutable review snapshots through typed tools | 2026-07-15 | `e04aa78` |
| OCP-11 | Add provider-neutral private DBSCTR review tools and command | 2026-07-15 | `f2eb3f1` |
| OCP-10 | Retire unsupported Pro aliases and restore native Build | 2026-07-13 | Historical `dcebd6c`; imported by `ea9eaeb` |
| OCP-9 | Finalize artifacts | 2026-07-11 | `ea9eaeb` |
| OCP-8 | Deploy and validate | 2026-07-11 | `ea9eaeb` |
| OCP-7 | Clean approved machine runtime | 2026-07-11 | `ea9eaeb` |
| OCP-6 | Preserve Graphify without duplicate plugin | 2026-07-11 | `ea9eaeb` |
| OCP-5 | Remove managed legacy integrations | 2026-07-11 | `ea9eaeb` |
| OCP-4 | Curate OpenCode skills | 2026-07-11 | `ea9eaeb` |
| OCP-3 | Align routing and permissions | 2026-07-11 | `ea9eaeb` |
| OCP-2 | Add control-plane contract test | 2026-07-11 | `ea9eaeb` |
| OCP-1 | Persist approved domain and behavior | 2026-07-11 | `ea9eaeb` |
