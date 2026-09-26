# Selected desktop active-deployment requalification

Status: implementation candidate; actual native qualification and production
deployment remain separate required gates. Profile: `../PROFILE.md`; critical
risk; Python and Security modules. Owner: dotfiles operator.

## Domain and approved boundary

The coordinator authorizes temporarily routing the **same selected conversation**
to an external-storage disposable fixture. Production selection, writer,
generation, receipts, journals and business files are off limits. This is an
installation lane, not a second continuation protocol or a quiescence assertion.
The existing shared core still owns fixture enrollment, approvals and admission.

The fixed management entry is `~/.local/state/dbsctr/codex/qualification`, an
operator-created link to an owner-private external directory. Its `selected.json`
and `native/` journal are separate from production. No runtime command or
environment variable selects a descriptor. Only the exact pinned fixture pair
resolves this lane. Other producer/core copies refuse production admission while
the lane is unclosed. Native callbacks for other conversations remain unaffected.

This bounded first implementation supports native-executable drift only. The old
production native pin **must differ** from the candidate's actual verified hash.
Thus already-loaded old production hooks continue to refuse even before native
reload. Same-pin pair upgrades require another design; do not waive this guard.
This remains cooperative-session enforcement, not confinement of arbitrary
same-user shell commands or an OS sandbox.

## Behavior and contract

1. Given a clean approved candidate and a registered active disposable cycle in
   a different Git repository, staging copies the candidate pair and captures
   exact production descriptor and hook bytes. It initializes only the fixture
   journal. It neither edits hooks nor grants trust, quiescence or a writer.
2. Given exactly one selected pre-hook and post-hook with the qualified matchers,
   installation changes only those two command values, preserving all other hook
   JSON values, conversation identity and tool coverage. Missing, duplicated or
   unfamiliar mappings refuse. No broad exemption is added.
3. Given descriptor/pin/hook drift or no completed installation receipt, fixture
   admission refuses before receipt issuance. The producer and shared-core
   consumer both choose the fixed lane; neither falls back to production.
4. Given a native control check, enrollment, attach or admitted shell call, the
   existing native identity and approval protocol applies unchanged, using only
   fixture records. Actual native trust and exact-state terminal approvals are
   separate actions. Unit tests and metadata probes cannot qualify this runtime.
5. Given interrupted, raced or failed hook exchange, retain the intent, both
   file inodes and all fixture evidence. No automatic overwrite, journal reset,
   guessed completion or writer recovery is permitted.
6. Given restoration, compare the exact installed hook bytes before exchanging
   back the exact original bytes. Preserve concurrent edits rather than merge or
   replace them automatically. Close the lane only after restoration is verified.
   A closed fixture itself never turns qualification hooks into an exemption.
7. Given restored hooks, production remains on its original descriptor and stale
   pin until separately qualified refresh. Restoration alone does not fix the
   lockout. Verify production routing before the final original-coordinator
   native control check. No FNBH relocation or SEO work belongs to this cycle.

## Interface

`codex-requalify stage --directory ABSOLUTE_NEW_EXTERNAL_DIRECTORY
--fixture REGISTERED_EXTERNAL_FIXTURE --cycle FIXTURE_CYCLE
--native-sha256 REVIEWED_NATIVE_SHA256` prepares, never qualifies. A stale fixed
lane is retained and refuses replacement. Use the source executable with a known
Python interpreter until source delivery; no broad managed configuration apply.

`codex-requalify install`, `restore`, and `recover` use only the fixed lane.
The owner-private route record binds production descriptor SHA-256, canonical
fixture descriptor digest, and before/after hook SHA-256. Receipts bind the
hook path, exchange path and exact before/after digests. Candidate descriptors
retain the existing schema; the original journal schema is not migrated.

Installation uses the existing pre matcher
`^(Bash|apply_patch|Edit|Write|mcp__.*)$` and post matcher `^Bash$` without widening
or removing coverage. Unrecognized definitions refuse. Runtime admission also
checks the current native hash, pinned pair, exact conversation/home, distinct
Git repository, production descriptor hash, and installed hook hash.

## Failure and recovery

Hook changes use a serialized management lock and atomic file **exchange**, not
destructive replacement. A durable `ACTION.intent.json` names the exchange file
in the hook directory before any swap. `ACTION.complete.json` is written only
after both exact byte images match. macOS `renameatx_np` and Linux `renameat2`
exchange are supported; unavailable exchange refuses, with no unsafe fallback.

An edit racing the exchange can be displaced to the receipt-listed exchange
path but is never destroyed. If either image differs, do not run another install
or force a restore. Both images remain for manual reconciliation. A callback
cannot use an incomplete installation. No claim is made that advisory locking
prevents unrelated programs from editing configuration.

After interruption, inspect the intent and both retained files. `recover` can
finish an uncompleted exchange only when they are exactly the expected before
and after images, in either order. Any third image refuses and requires the
operator to reconcile that edit explicitly; never blindly copy a backup over
live hooks. If native activity may still exist, obtain exact-state quiescence
and use the existing fixture recovery protocol separately. Hook recovery never
changes the writer or marks an uncertain operation completed.

After successful `restore`, verify original hook bytes and production descriptor
bytes, preserve all fixture receipts and exchange files, and reload the **same**
conversation if the native runtime requires it. No automatic restart or deletion.
The operator owns retention and future retirement; failed evidence has no expiry.

## Validation and native handoff

Selected authorities: affected pytest route/transaction, native adapter and
shared-core conformance; Python compilation; direct security review; exact-head
hosted checks before merge; actual native callbacks before promotion. New runtime
qualification must exercise denial/rewrite, pre/post admission/completion, long
call polling, replay, interruption/recovery and unsupported tool refusal against
the fixture. Preserve the existing accepted collaboration-mode limitation without
claiming a Plan-mode enforcement pass. No native action is synthesized by OpenCode.

The first native action after reviewed installation is to review/trust the two
changed commands and, if needed, reload the same conversation. Then that original
coordinator runs **`codex-continuation control check` through native Bash**. It
must report the disposable fixture's unenrolled state, not FNBH ownership. Next,
native `control prepare enroll` produces the exact terminal approval instruction;
the human executes that instruction outside the agent, and native apply consumes
it. Do not invent an approval command or run it from this repair session.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary, data/trust, dependency/deployment | required: route table below |
| Interaction, state | required: transition table below |
| Schema | not_applicable: existing descriptor/journal schema, flat receipt fields above |
| Quantitative | not_applicable: no comparative claim |

| Source | Direction and consumer | Authority |
|---|---|---|
| Original conversation callbacks | Fixed fixture producer → pinned fixture core → disposable cycle | Native identity plus exact fixture approvals |
| Other conversation callbacks | Existing hook behavior, no fixture routing | No new authority |
| Production descriptor and journals | Read-only preservation checks | No writer/generation mutation |
| Candidate tests and metadata | Review evidence only | Never native qualification |

**Text Equivalent:** Only the original selected conversation enters the fixed
fixture pair. Production state is preserved. Other conversations gain no fixture
authority. Synthetic and metadata results cannot promote a candidate.

| State | Permitted transition | Admission |
|---|---|---|
| Staged | Exact-preimage install | No fixture writer; production pin-blocked |
| Exchange incomplete | Exact-image recover or manual drift reconciliation | No fixture admission |
| Installed, native trust pending | Actual trust/reload and native fixture checks | Never infer trust or enrollment |
| Native qualified | Exact-preimage restore, retain evidence | Production still blocked on original pin |
| Restored | Separately qualified production refresh | Fixture hooks refuse; final native check still required |

**Text Equivalent:** Staging and installation are not qualification. Incomplete
exchange fails closed. Native trust and approvals remain separate. Restoration
closes only the fixture route; promotion and final production verification follow.
Source: coordinator-approved repair boundaries and implementation in this cycle.
Owner: dotfiles operator; refresh when routing, transaction or approval changes.
