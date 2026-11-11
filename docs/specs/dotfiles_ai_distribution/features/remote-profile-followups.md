# Remote profile follow-ups (RRW-007H)

## Domain and authority

INT-083/084 in Discovery #517 bind this critical-risk slice to the foundation
distribution. The per-user TOML owns interface preferences; managed CLI config
owns only selected keys; Worktrunk alone owns allocation; private activation owns
reviewed policy/version/filesystem identity. Source commit identifies the deployed
generation, not a change in effective allocation policy. Fork A owns setup questions,
pins, rollout and live apply. RRW-007G restore/adoption and RRW-007I editor recovery
are separate. No installers, services, databases or saved layouts change here.

## Behavior and interfaces

### Managed OpenCode preference (INT-083)

`[data.dotfiles_ai.opencode] tab_bar_mode = "off"` selects `tabs.mode` in the
managed `cli.json` modifier on Mac and remote profiles. Supported explicit values
are `auto`, `on`, `off`; the default empty string leaves the existing mode unmanaged.
The owner value is `off`; Fork A writes that value from its setup interview.

Given an explicit mode, applying replaces only the managed `tabs.mode` alongside
the existing managed keys, preserving other tab options and unrelated local JSON.
Given empty mode, an existing local tab configuration remains unchanged. Unsupported
types/values and a non-object `tabs` under explicit management refuse rendering,
leaving original destination content intact. Never reset the whole CLI config.
Native v2.2.6 source `dc2ffcf8` (`packages/tui/src/config/index.tsx`) defines the
three supported modes; CLI `schema.ts` normalizes legacy `tabs.enabled` only when
no explicit mode is supplied. This setting does not edit the legacy v1 TUI config.

### Activation identity and legacy continuity (INT-084)

Given unchanged effective policy, Worktrunk version and filesystem identity, a
source-commit-only update or rollback neither fails apply nor needs reactivation.
Existing activation bytes/inode remain unchanged. Changed naming, repository
overrides, consent/preservation/delivery policy, roots, cache rules, Worktrunk version
or mount/UUID still refuse allocation until reviewed; existing work stays reachable.

The full `policy_digest` still covers source commit and the complete document.
An optional versioned `activation_binding` contains `semantic_digest` and one
optional `legacy_policy_digest`. Semantic identity excludes only `source_commit`,
`policy_digest` and binding metadata, never effective policy fields. New activation
snapshots use schema 2: semantic digest, roots/identities and Worktrunk version.

For legacy schema-1 activation, validate the old deployed private policy and carry
its full digest only if its complete effective policy equals the new policy.
Carry that single anchor transitively through later equivalent generations; do not
grow a history list or infer identity from an activation hash alone. A missing or
invalid legacy preimage cannot authorize unknown old activation. Compare all other
snapshot fields exactly, including strict types; boolean/integer equality is not
schema validation. New documents with binding metadata require new helper support.

Render/snapshot remain read-only, bounded and deterministic before and after policy
deployment; no activation refresh, sidecar, Git ancestry scan, network or live
repair is introduced. Private prior-policy reads retain owner, mode, link, size and
duplicate-key checks. Normalized XDG configuration ownership must match the helper's
check/initialize path. Unsafe existing state fails visibly and is retained.

### Wrapper separator (INT-084)

Given an actual `--` separator, stop wrapper option parsing there and skip automatic
`--auto` injection for that invocation. Keep every subsequent argument unchanged,
including empty strings, option-like paths and literal `--auto`/`--server` values.
A `--` consumed by a known value-taking option is a value, not a separator.
Explicit endpoint choices before the separator and existing shared-service routing
remain authoritative; tokens after it cannot select a wrapper command or endpoint.
Normal invocations still receive existing automatic behavior under `HERDR_ENV`.
Cover native and legacy template branches, Bash 3.2-compatible syntax and exact argv.

## Validation, failure and maintenance

Use existing pytest rendering/subprocess fixtures, Linux/Python 3.12 typing and
Bash syntax checks. Real native/disposable CI remains distinct from synthetic tests.
Qualify legacy activation -> new helper -> multiple source-only revisions without
activation rewrites; root/version/UUID/policy drift must still fail. Remove the
disposable smoke's manual snapshot-refresh workaround, not its safety assertions.
Preserve red and failed hosted evidence; exact-head CI and independent critical
review precede delivery. No native credentials or operator values enter public tests.

Existing old helpers cannot interpret the new binding extension. Rolling back to
pre-support helper code requires explicit review rather than silent schema downgrade.
Keep old activation and policy evidence; do not delete it to manufacture success.
Final Push is a feature-branch draft PR, not main or a live deployment. No pin,
bootstrap change or new setup-owner responsibility is authorized by source delivery.

## Visual Evidence

| Concern | Decision evidence |
|---|---|
| Boundary | required: ownership transition table below |
| Interaction | required: ordering transition table below |
| State | required: activation/config state table below |
| Data/trust | required: proof transfer table below |
| Schema | not_applicable: bounded field contract above is clearer than ER notation |
| Dependency/deployment | not_applicable: no runtime topology change |
| Quantitative | not_applicable: no performance claim |

| Input / guard | Owner and direction | Result |
|---|---|---|
| Explicit supported tab mode | Per-user TOML -> managed CLI modifier | Override mode, retain unrelated JSON |
| Default empty tab mode | Local CLI JSON -> modifier | Preserve existing tabs |
| Valid equivalent old policy | Private old policy -> renderer | Carry one legacy digest anchor |
| Equivalent semantics + same version/roots | Current policy -> activation validator | Retain activation; allow normal allocation |
| Real effective policy/version/identity drift | Current facts -> activation validator | Refuse new allocation, retain work |
| Actual separator before remaining argv | Wrapper scan -> native/legacy executable | No automatic `--auto`; preserve argument tail |

**Text Equivalent:** The local user selects interface preferences, not the live
service state. The renderer may transfer only a validated equivalent policy's
legacy digest; the validator still checks native version and filesystem identity.
The wrapper never interprets tokens after a true separator. Canonical sources are
the CLI modifier, workflow-policy helper and OpenCode wrapper; owner: distribution
maintainer. Update this table when managed-key, proof-transfer or argv rules change.
