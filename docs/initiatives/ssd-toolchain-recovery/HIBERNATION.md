# Hibernation — bounded fork qualification, activation blocked

Latest decision INT-039 selects bounded OpenCode-only fork qualification after
host delivery and source reconciliation. This supersedes the undecided fork
scope and blanket pause in INT-017/020; guest and Python deferrals still apply.
Qualification found a native eligibility-interlock gap. The slice remains
Discovery-owned: no Build readiness, launch approval, or activation is implied.
See [pinned candidate findings](findings/hibernation-fork-qualification.md).

Home: shell_auth_startup. Existing PROFILE.md remains authoritative. Owner: primary
maintainer. Review trigger: completion report for all non-deferred workstreams,
or earlier explicit operator request. No expiry date is invented.

## Retained requirements for resumption

- OpenCode only; at least fifteen minutes idle and unfocused.
- Keep focused, working and blocked sessions alive.
- Restore exact native conversation, cwd and launch options; no most-recent guess.
- Preserve registry ordering and detect real process exit; qualify crash/interruption
  cases before deployment.
- Draft text and exact scroll-position loss remain accepted limitations.
- Prefer existing integration and official Herdr support. Qualify a bounded fork
  of the pinned existing plugin rather than introduce another process supervisor.

Dependencies for later activation: signed Herdr Host recovery, final native-launch
and update behavior, and isolated eligibility/exact-session tests. Recheck the
candidate release and original known gaps at resumption; historical review is not
qualification of a changed version.

## Selected qualification boundary

Reuse the `shell_auth_startup` profile and existing exact-session recovery
contracts. Risk is elevated; candidate target is the local macOS managed OpenCode
shared-server route. Standalone, remote servers, other agents and guests are not
admitted by this qualification. Unsupported or incompletely observed launches
must remain running rather than lose options. A narrower route is not permission
to rewrite existing launches into that route.

Retain upstream MIT attribution. Candidate changes belong to this repository's
managed distribution; no new hosted fork or installer owner is selected. Plugin
registration/linking enables execution and therefore belongs to deployment, not
source preparation. Reuse native launch routing, authentication and pacing.
Never stop the shared OpenCode service to sleep one client.

### Behavioral acceptance

1. Given an OpenCode client continuously idle/done and unfocused for fifteen
   minutes, sleep is eligible only with fresh native identity, terminal/process
   identity, complete reproducible launch context and authoritative eligibility.
   Unknown data, observation gaps and identity changes reset eligibility.
2. Given focus, work or a blocked state arising before termination, abort sleep.
   A final polling read followed by an unguarded signal does not prove this rule.
   Manual actions do not bypass the focused/working/blocked exclusions.
3. Before termination, durably retain exact recovery intent. Confirm the captured
   client actually exited and the same terminal returned to an available shell;
   metadata disappearance, a changed session, PID reuse and API errors are not
   positive exit evidence. Never signal a fallback foreground process.
4. Preserve both process launch cwd/options and the authoritative current session
   directory. A session move can change the latter without changing process cwd.
   Resolve that distinction before reconstructing a launch; never guess from the
   shell cwd or most recently used session. Do not replay prompt-bearing or
   otherwise non-reproducible arguments automatically.
5. On focus, retain wake intent until the same terminal has attached the exact
   saved native conversation with its saved effective launch context. Another
   OpenCode session, an empty home screen or `agent_not_ready` is not success.
   Startup uncertainty is reconciled before retrying; never launch duplicates.
6. Interrupted sleep/wake, corrupt state, storage failure, vanished/moved panes,
   server replacement and conflicting recovery owners preserve recoverable
   records. Do not prune the only recovery reference or overwrite newer work.
   Serialize with the existing restoration owner before any live trial.
7. Recovery records are private local state under managed external routing, with
   restrictive access. Credentials, raw command lines and conversation content
   must not enter public artifacts or diagnostic logs. Secret-bearing launch
   context requires a qualified secret reference or makes the launch ineligible.

## Qualification and gates

Source findings are not live sleep/wake evidence. Start with deterministic fake
Herdr/process/storage checks for every acceptance rule, including interruptions
on both sides of each external action, concurrent hooks, stale locks and partial
API failures. Use the existing repository publication authority and affected
recovery tests; upstream's green suite is only a baseline.

After interface readiness and exact-plan approval, qualify a disposable native
canary with an existing saved conversation, then verify exact identity, effective
directory/options, visible conversation, focus behavior and preservation of
unrelated panes. Do not manufacture a production interruption for evidence.
Activation requires successful canary and rollback qualification. Rollback stops
new sleeps, preserves the journal and recovers outstanding sleepers before
retiring the plugin. Preserve historical failed evidence throughout.

| Gate group | Applicability | Current result |
|---|---|---|
| Development Kernel and Review/Integrate | required: behavior and recovery changes | Not started; native interlock unresolved |
| Release | not_applicable: no independent public package release selected | Not assessed by a cycle |
| Deploy | required: managed plugin activation changes live clients | Blocked |
| Operate | required: exact canary recovery and failure/rollback evidence | Pending |
| Maintain/Retire | required: pinned upstream review, journal compatibility and safe disable | Pending |

No gate exception is requested. An artifact-ready applicability plan and fresh
receipt/preflight follow interface resolution, not this qualification report.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: selected qualification boundary explicitly names owners and exclusions |
| Interaction | not_applicable: acceptance rules specify persist-before-stop and verify-before-complete ordering |
| State | required: transition table below |
| Data/trust | not_applicable: private-state and credential boundaries explicit in acceptance rule 7 |
| Schema | not_applicable: registry design awaits native interface resolution |
| Dependency/deployment | not_applicable: prose and gate table name activation prerequisites |
| Quantitative | not_applicable: fifteen minutes is a requirement, not a measurement |

| Current state | Trigger | Next state |
|---|---|---|
| Deferred | Explicit request to resume | Discovery; requalify candidate and implementation scope |
| Discovery | Recovery or sleep/wake evidence missing | Activation blocked; preserve live sessions |
| Discovery | Native eligibility interlock unavailable | Readiness blocked; retain findings and resolve scope |
| Discovery | Scope, dependencies and qualification resolved | Fresh Build readiness and registration preflight |

**Text Equivalent:** qualification resumed; implementation requires fresh
readiness and registration, activation requires exact recovery evidence.
Canonical source: this decision.
Owner: primary maintainer; update trigger: operator resumption or changed requirements.
