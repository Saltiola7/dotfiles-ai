# GPT-6 And Opus 5.5 Model Routing

## Domain And Profile

Owner: dotfiles maintainer. Home: `opencode_control_plane`; distribution consumes
the same policy in defaults, portable renders and Hermes profiles. Use the existing
control-plane and distribution Engineering Profiles and distribution Product
Intent journeys for later-launch convergence and process preservation. Modules:
ML/AI, Python, Security; source-cycle risk: routine. Inputs are public model
identifiers, provider configuration and role selection; outputs are configured
inference routes. Credentials, transcripts and runtime state remain private.

## Contract

| Managed role | Exact model | Reasoning |
|---|---|---|
| Default, native Plan, GPT Build, GPT command, OpenAI reviewer | `openai/gpt-6-astra` | Preserve existing medium setting where present |
| OpenAI Builder and Scout | `openai/gpt-6-sol` | medium |
| OpenAI Explore | `openai/gpt-6-luna` | low |
| Small-model work | `openai/gpt-6-luna` | Preserve consumer behavior |
| Claude Build and Claude command | `google-vertex-anthropic/claude-opus-5-5@default` | Preserve high setting |
| Hermes managed base/project profiles | `openai-codex/gpt-6-astra` | Preserve existing settings |

The installed OpenCode catalog lists Astra, Sol and Luna, not GPT-6 Terra or a
GPT-6 `-fast` alias. The managed Codex catalog independently lists the same three
GPT-6 slugs. Hermes accepts provider-prefixed model configuration and uses Codex
catalog discovery. Its older hardcoded fallback list is not availability proof.
Recheck capability evidence during implementation; do not silently use GPT-5.6
or change providers if a required route is unavailable.

Role selection is based on workload and catalog cost, not a quality benchmark.
Astra handles primary/review work; Sol handles bounded implementation/research;
Luna handles inexpensive exploration and helper work. Preserve provider affinity,
permissions, context preservation and delegation policy. Do not add Pro routes.
Use exact catalog limits rather than inheriting stale Sol-specific overrides.

## Behavior

- Given default machine configuration, when managed OpenCode configuration is
  rendered, then default/Plan/Build resolve to Astra and helpers to the table.
- Given explicit Claude Build or its command, when selected, then both resolve
  to Vertex Opus 5.5 without a provider change.
- Given an enabled managed Hermes base or project profile, when its existing
  configuration path runs, then it sets and verifies Astra under openai-codex.
- Given any active dotfiles-ai route, when inspected after the migration, then
  none selects GPT-5.6. Historical usage, immutable benchmarks, past changelogs,
  compatibility fixtures and historical pricing may retain their original IDs.
- Given an existing conversation, when source changes or configuration is
  rendered, then its identity, history and running process are untouched.

## Validation And Maintenance

Run affected assertions from `test_opencode_control_plane.py`,
`test_portable_distribution.py`, and `test_dbsctr_rnd.py`; add one active-route
regression covering defaults, roles, commands, provider overrides and both Hermes
setters. Compare native and explicit model routes and Darwin/Linux rendering.
Verify model/variant resolution against the installed runtime without sending
private prompts or making paid requests. Preserve original historical cost rows;
do not assign old prices to new identities. New pricing policy is separate scope.

Update affected current specification truth and review context changelogs. Keep
historical entries historical. Rollback is a source revert followed by an explicit
targeted apply; it does not restart current processes. Runtime entitlement and
quality are not proven by catalog presence; report those limits honestly.

## Visual Evidence

Boundary, interaction, state, data/trust, schema, dependency/deployment and
quantitative: not_applicable. The exact routing table is the canonical evidence;
this change adds no topology, state machine, persistence schema, trust transfer
or measured performance comparison. Owner/change trigger: maintainer/model policy.
