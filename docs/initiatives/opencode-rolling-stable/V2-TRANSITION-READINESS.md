# Latest V2 transition — Discovery working record

Status: control-plane source merged; distribution source contract prepared for
launch preflight. Live deployment qualification remains pending.
Authority: INT-033 and V2-MIGRATION.md. Risk: critical. Existing approved context
homes, Engineering Profiles and distribution Product Intent remain authoritative.

## Current operator scope

Complete the one-time transition to the latest official stable OpenCode V2 and
get the operator working with it. Resolve the latest release when staging, then
bind that migration attempt to its verified artifact identity. A newly published
version requires fresh qualification before replacing the staged candidate.

Hourly OpenCode/Codex updates, automatic idle service upgrades, independent fleet
rolling updates and scheduler work are deferred under INT-032. They are not
dependencies of this transition and do not revise the existing recurring-update
contract in this work. Codex update redesign and Codex Desktop remain out of scope.

The operator approved synthetic edge-case rehearsal followed by a disposable
boundary-local copy of retained real history after capacity checks. Originals
remain immutable, private content remains local, and only aggregate verification
results are surfaced. Operator-assisted TUI/Desktop checks are available after
isolated staging. Maintenance activation follows successful qualification.

## Source and candidate evidence

### Source completion and next delivery

PR 194 merged at `8124f163840c58e163df0cca0da9d2adfd00af5a`. Its exact 2.0.22
checks covered 14 managed roles, provider routing, native permission boundaries,
Ponytail 4.10.3 loading and synthetic MCP Code Mode allow/deny/ask cancellation.
121 affected tests and final focused checks passed; hosted Python 3.12/3.13/3.14
and CentOS smoke checks passed before merge. Actual provider connectivity, UI
acceptance and fleet deployment remain separate. The old running session's
continuation binding was recovered and released with explicit quiescence consent.

The Codex native-workspace source dependency was already implemented in PR 193;
a fresh run on merged source passed 99 Codex control-plane/distribution/retirement
tests, including native 0.155.1 sandbox reads, task writes and denied sibling writes.
This closes the source dependency without inventing another implementation cycle.

The distribution source delta is specified in
`docs/specs/dotfiles_ai_distribution/features/opencode-v2-distribution-source.md`.
It covers verified staging, truthful V2 generation locks, held recurring updates,
safe launch and interrupted maintenance. Desktop/service/data admission and live
fleet retirement remain in the downstream cutover slice. The current primary's
VM command permission denies even inventory; this is unavailable evidence, not
an empty fleet or permission to bypass the boundary.

The earlier evidence below remains the chronological rehearsal record.

PR 193 merged at `2f83545f0dd7a8ed65600042eaf6b656116b7aa7`, delivering the
native-workspace source replacement. It did not deploy or adopt live worktrees.
The merged updater still uses V1 discovery/validation and cannot serve as a V2
activation authority unchanged. A coherent one-time transition must keep that
path from installing or launching an incompatible generation afterward; doing
so does not require a new periodic updating system.

Latest V2 CLI metadata observed on 2026-10-03: **2.0.22**, publisher-recorded source
`05018b8862a8fc198ec9810aafd397c96bb7d86e`. The official CLI npm manifest points
to exact platform package `@opencode/cli-darwin-arm64@2.0.22`.

Research staged that package without executing npm installation hooks. Archive
bytes matched its registry-published SHA-512 integrity value; only the expected
regular package metadata and executable were accepted. Derived archive SHA-256:
`16f5f5851e0fcf86dc38c98042bc50e5f167319a9973897c9487f17b2e810117`.
Derived executable SHA-256:
`af29b0b1b0291dbf2471c66c89d2e055b6afa9c41a950e052fa609c3295e2a75`.
These SHA-256 values bind the verified bytes; they are not represented as
publisher-supplied SHA-256 sidecars or independently verified registry signatures.
The distribution contract must explicitly settle this V2 artifact trust route.

| Qualification | Actual result | Limit |
|---|---|---|
| Checksum-bound CLI surface | passed on 2.0.22 | macOS aarch64 only |
| Isolated configuration loading | native debug output obtained | synthetic providers; integrations excluded |
| Managed Markdown roles | all 11 returned with exact IDs and explicit location | existence/location, not execution or provider authentication |
| Native Plan/Build write boundary | Plan write unavailable with a persisted tool error; Build wrote the exact synthetic content | loopback provider; integrations excluded; not the full permission matrix |
| Native synthetic conversion | same session, all 4 original message IDs retained, 9 messages after continuation | one small session; not edge-case or real-history coverage |
| Original synthetic archive | unchanged after conversion | no production archive read or migrated |
| Overlapping V1/prior-V2 synthetic session | failed preservation: 4 of 9 prior-V2 message IDs absent after conversion; prior-V2 source file unchanged | native 2.0.22 overlap import must not be admitted without a qualified disposition |
| TUI picker and resume | operator saw both synthetic sessions and opened their messages; Build appeared and was selectable; Shift+Tab switched agents | synthetic history only; appearance check incomplete |
| Desktop, guests, real history | not run | required before claimed rollout |

The role check also retrieved native Plan and Build with exact location identity.
An isolated TUI launcher is prepared against synthetic history for the operator's
picker, role-selection and resume observations; its preflight passed, but no UI
result is inferred from that check. It supplies isolated configuration/data roots,
no production credentials and stops its isolated service when the TUI exits.

The operator initially saw the selected Plan role, then confirmed Build in the
agent selector. Plain Tab did not switch roles. The exact upstream 2.0.22 keymap
uses Shift+Tab for cycling and Ctrl+X followed by A for agent selection; Tab is
the prompt autocomplete key. The operator subsequently confirmed Shift+Tab works.
The isolated fixture omitted the managed TUI theme; Catppuccin was subsequently
added using the existing theme setting, whose upstream dark palette is Mocha.
V2 stores this preference in cli.json as a structured theme object; legacy
tui.json migration does not replace an already present cli.json. Inspection of
the fixture found the correct theme name but no explicit color mode. The fixture
now requests Catppuccin with mode dark. Mocha visual confirmation remains pending.
The production transition must preserve the preference in the V2 CLI configuration,
not assume repeatedly rendering the legacy TUI file updates the native setting.

## Real-history admission findings

A body-free read-only inventory found zero sessions and zero messages in the
current host's prior-V2 database, hence no overlapping session IDs at that
observation. The demonstrated overlap defect therefore does not currently affect
that host database. This is not quiescence or fleet evidence: recheck the exact
inputs before cutover, and block any newly observed overlap until a qualified
preservation path exists.

Real-history capacity rehearsal could not start: the retained archive named in
the existing recovery status no longer resolves at its recorded location. A
targeted state-directory filename search found only old temporary sidecars.
This does not prove the archive was destroyed or exclude relocation elsewhere.
Resolve its authoritative location or establish a newly verified consistent
backup before real-history rehearsal. Do not treat the historical status document
as proof of a currently available backup. No live conversion or archive cleanup
was attempted.

The operator then explicitly authorized a fresh consistent backup. The online
SQLite snapshot completed; its first integrity-check attempt did not complete
within the initial bound. Verification resumed on the same retained copy rather
than recopying it. The fresh snapshot passed quick_check and a full SHA-256 pass,
was made read-only, and contains 5,702 sessions, 620,727 messages and 2,820,419 parts
in 97,566,822,400 bytes. Its identity and private location are recorded in local
recovery metadata. It is an online snapshot, not proof of writer quiescence.

Body-free resource measurement found a largest per-session part payload of
2,188,044,944 bytes; a separate largest-part query did not finish in the shared
measurement bound. No raw content was surfaced. A foreground native conversion
runner passed its synthetic smoke with provider use denied, authenticated loopback
status access, an APFS clone, owned-process cleanup and time/memory/space limits.

The real-history runner uses a separate APFS clone of that verified snapshot.
An initial attempt stopped after a status-request timeout. A resumed attempt
reached the initial five-minute HTTP-readiness bound with low measured RSS, before
the status API became available. These are retained failed attempts, not proof of
conversion failure or success. The next attempt allows database bootstrap within
the whole-run thirty-minute bound while keeping the twenty-GiB RSS ceiling and
fifty-GiB free-space reserve. No live database conversion is authorized by these
partial results; reconciliation and recovery checks still follow native completion.

### Completed real-history rehearsal and reconciliation

The thirty-minute attempt reached 5,516 of 5,702 sessions before its deadline;
native checkpoint resumption completed in a further 61.6 seconds. Sampled peak
RSS in the long attempt was approximately 8.1 GB. The time and resource stops and
their earlier records remain retained. The source backup's metadata was unchanged;
the native process was stopped after each attempt. No live history was converted.

Read-only reconciliation on the completed clone found:

- All 5,702 original session identities retained; zero changed directories,
  project associations or parent associations.
- 620,727 original messages and 620,425 native converted messages. Raw count
  equality is not a preservation criterion because native conversion folds and
  synthesizes records.
- 3,529 original summary-message identities folded into compaction records;
  summary text independently matched exactly.
- 102 incomplete compaction request records and 100 incomplete compaction summary
  records omitted by native conversion; originals remain in the retained backup.
- One malformed original assistant record omitted, correlated locally with the
  native invalid-message warning and missing required agent metadata. No remaining
  unclassified missing message identities; zero invalid-part/orphan-part warning
  occurrences were observed in the retained logs.
- Semantic checks covered 613,466 surviving messages, including user text, inline
  file bytes, assistant text/reasoning, model/agent identity, 811,565 tool identities,
  inputs/statuses, completed output, attachment references and failed/interrupted
  tool state. Zero mismatches in these checked fields. The 252 split synthetic-text
  cases also matched. Auxiliary metadata and agent mentions were not independently
  compared, so this is not a claim of universal byte-for-byte parity.
- Native behavior replaced 376 external attachment references with unavailable
  placeholders. Metadata-only inspection found 298 referenced local paths absent,
  59 nonregular references and 19 references to regular files still present. No external bytes
  were read and no URLs fetched. Retaining the database alone does not archive
  those referenced files' bytes. This disposition requires operator review before admission.
- 1,695 already-compacted tool results use the expected native placeholder; 99
  pending/running tools become explicit interrupted errors, never successes.

The operator explicitly accepted the documented incomplete-compaction,
malformed-record and external-attachment dispositions with retained recovery.
The 19 available regular-file references resolved to five distinct current files;
126,150 bytes were archived separately, made read-only and verified by digest.
Private path mappings remain local. Their historical byte identity is unverified;
no historical message was rewritten to substitute current file contents.

Do not mark deployment ready solely from these successful checks. Native
startup/configuration compatibility, retained integrations,
Desktop/guest qualification and the bounded live cutover still require completion.

## Native interface findings

An unqualified API request can resolve the service's own directory instead of the
caller's checkout. Use explicit `location[directory]` and verify the response's
location. Do not infer absent roles from a query against the wrong location.

The first role request can arrive before role initialization: the observed first
request failed, then succeeded after a bounded retry. Qualification must wait for
the complete expected role set and fail at a deadline rather than accepting an
empty list. Existence is not native permission enforcement.

Bulk `debug agents` output was observed truncated mid-JSON at approximately
256 KiB for the managed configuration. An initial 128 KiB fixture bound also
correctly refused that large output. Individual `agent.get` API requests with
explicit location produced complete responses under a 1 MiB fixture ceiling.
The isolated service was stopped after each attempt, including failed attempts.
Do not port the V1 `debug agent build` validator or parse incomplete bulk JSON.

## Remaining work and ownership

- OpenCode control plane: qualify native execution/denial, exact managed config,
  retained integrations, session/location behavior and operator UI observations.
- Distribution/recovery: specify the one-time trusted staging and coherent
  binary/configuration/service/data generation; prevent stale V1 update/start
  paths from undermining cutover. Preserve external-state-root refusal.
- Rehearsal: compaction, attachments, malformed rows, interruption, recovery,
  post-conversion work and realistic capacity/time. Reconcile warnings and identity
  or content changes locally; unexplained loss blocks admission.
- Cutover: inventory and qualify each claimed target, use a bounded maintenance
  window, confirm writers/jobs are quiescent, preserve recovery generations, adopt
  eligible cycles explicitly in place, and verify exact conversation resumption.

Reuse pytest, Bun, chezmoi rendering, shell checks and native probes.
The v2-control-plane source slice now has a bounded contract and applicability
plan; specification readiness is not verified launch feasibility. No live restart,
configuration apply, production data conversion or cycle adoption occurred.

## Visual Evidence

This informative record uses the canonical boundary, interaction, state, data/trust
and deployment flow in V2-MIGRATION.md and the native-workspace specifications.
Schema visuals are not applicable: no new persistent schema is proposed here.
Quantitative comparison is not applicable: small-fixture counts do not establish
large-history capacity or timing. Update the normative transition tables when
the remaining recovery and admission contracts are finalized.
