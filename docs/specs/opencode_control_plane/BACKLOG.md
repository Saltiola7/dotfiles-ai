# OpenCode Control Plane Backlog

## Active

| id | title | priority | status | depends_on | owns | reads | parallel_safe | reason | effort | validation |
|---|---|---|---|---|---|---|---|---|---|---|
| OCP-27 | Add versioned exact provider identity for five-cycle reports | P1 | pending | DAI-011 | Nested telemetry schema; DBSCTR runtime/tool adapters; control-plane specs/tests | integrated DAI-011 telemetry and federation contracts at `c24f7e5` | no | Exact identity must update helper, VM exporter, and typed validators together without changing federation schema v2 | M | Cross-version identity, privacy, attribution, host/VM continuation, and provider-affinity fixtures |
| OCP-28 | Optimize provider-native agents and exact DBSCTR entry commands | P1 | pending | OCP-27 | OpenCode model config, provider primaries, provider commands, routing contracts/tests | current OpenAI and Anthropic guidance; integrated telemetry identity | no | Model, prompt, command, and lifecycle-core changes need one integrated provider-isolation review | M | Rendered config, focused tests, GPT live probes, provider-affinity denial, and Opus follow-up when unavailable |

## Completed

| id | outcome | completed | commit |
|---|---|---|---|
| OCP-26 | Add VM-only always-auto control plane and bounded federation adapters | 2026-07-25 | `ae72606` |
| OCP-25 | Ask before every shell form of explicit improvement retirement | 2026-07-23 | `ec9cbc4`, `732ae79` |
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
