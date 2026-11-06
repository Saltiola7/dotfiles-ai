# Codex Projection Runtime State

## Scope and ownership

RRW-007A-R1 repairs upgrades of an existing projected CODEX_HOME after Codex has
written native UI state. Distribution owns `codex-project`, the managed source,
projection manifest and transaction journal. Codex owns the explicitly allowlisted
top-level `tui` and `notice` tables, including first-launch
`tui.screen_reader_detection_done`. These tables must not occur in managed source;
all other configuration remains fingerprint-protected. This is an elevated-risk
compatibility repair, not a general configuration importer or live-host migration.

The operator's live configuration, authentication, sessions and history are never
read or changed during source development. Fork A owns the later pin update,
bootstrap fetch/convergence and authorized RHEL rollout. Keep the bootstrap bytes
unchanged and report their actual checksum with the merged source SHA.

## Behavior and contracts

- Given a legacy projection and only added native UI/notice state, when upgrading
  with unchanged managed settings, preserve that native state and migrate ownership
  metadata without requiring the broader explicit reconciliation option.
- Given version-2 ownership metadata, changes confined to native state may be
  preserved while new managed settings are projected. Compare the current managed
  fingerprint to the previous one before admitting an upgrade, not to a future
  desired value that could conceal an edit to an already owned key.
- Given changed hooks, models, sandbox/approval controls, unknown top-level keys,
  missing owned keys, unsafe files or malformed/oversized configuration, refuse
  before publication. Never infer that an arbitrary local key is Codex-written.
- Legacy manifests contain no semantic baseline. If the full recorded digest no
  longer matches, automatic migration requires the non-native values to equal the
  reviewed incoming source. Different/ambiguous legacy managed values still block;
  do not guess a historical baseline. Exact digest matches retain ordinary upgrade
  behavior. Existing explicit hooks-only reconciliation stays separately opt-in.
- Native tables must be TOML tables with bounded JSON-compatible values. Preserve
  their values; preserve complete config bytes when managed values do not change.
  A managed update may rewrite formatting but must retain native values. No new
  TOML dependency, interpreter, provider call or credential access is introduced.
- Retain a private mode-0600 config/manifest preimage when accepting byte drift.
  Existing directory locks, bounded source admission, no-follow checks, journaled
  publication and fail-closed ambiguous recovery remain authoritative. Validate
  all owned targets before backup/staging. Interrupted version-1 and version-2
  transactions remain recoverable; native writes during recovery never authorize
  overwrite of an unexpected digest.
  Recheck expected target/staging digests immediately before each replacement and
  all completed target digests before manifest commit. These checks detect
  observed interleavings; the advisory lock does not control Codex itself and
  portable filesystem replacement is not a compare-and-swap against an unrelated
  writer. Guaranteed snapshot publication requires native config writers to be
  quiescent. This source repair never stops a live user process automatically.

## Versioned interface

CLI and public setup keys do not change. New projection manifests use
`{schema_version: 2, files: {relative_path: sha256}, config_owned_sha256: sha256}`.
The additional digest fingerprints canonical non-native TOML values, separately
from the full published config digest in `files`. Version-2 journals add the same
digest alongside the existing entries/manifest fields. Version 1 retains its
existing exact shape and recovery meaning. Unknown, mixed or malformed metadata
fails closed. Metadata remains private runtime state, never shared Git evidence.
An old projector that only understands version 1 cannot read the new manifest.
Downgrade to such a binary requires a separately reviewed metadata migration;
never delete the manifest or reset the live config to make a downgrade pass.

Validation covers first-launch legacy upgrades with and without hooks-only
source, mutable native values across reapply, subsequent managed changes, mixed
native/owned edits, unknown keys, malformed/unsafe inputs, all-target validation,
preimage retention, concurrency and interrupted transactions. Existing Codex
projection, distribution and remote bootstrap tests remain affected consumers.
Hosted UBI is disposable upgrade proof, not acceptance of the owner's RHEL host.

## Visual Evidence

| Concern | Decision / review question |
|---|---|
| Boundary | required: ownership table below; who can change each config portion? |
| Interaction | required: transition table below; when is drift admitted? |
| State | required: transition table; can ambiguity silently become success? |
| Data/trust | required: ownership table; does private native state enter Git? |
| Schema | required: versioned interface above; are legacy records preserved? |
| Dependency/deployment | not_applicable: no deployment topology or runtime dependency changes |
| Quantitative | not_applicable: no performance or numerical comparison claim |

| Artifact | Owner | Admission |
|---|---|---|
| Managed config excluding native tables | Distribution | Prior semantic fingerprint or verified legacy baseline |
| `tui` / `notice` tables | Native Codex/user | Bounded values, preserved in private CODEX_HOME |
| Other projected files | Distribution | Existing exact file digests |
| Manifest/journal/preimages | Projector | Private, versioned, locked and transactionally published |
| Live RHEL rollout | Fork A/operator | Separate deployment authority; no development-time access |

| State / observation | Action | Outcome |
|---|---|---|
| Legacy full digest matches | Ordinary verified upgrade | Version-2 ownership baseline |
| Legacy digest differs, non-native values match source | Preserve native values and preimage | Version-2 ownership baseline |
| Version 2, prior managed fingerprint matches | Merge new managed source with native state | Updated version-2 transaction |
| Owned edit or ambiguous legacy baseline | Refuse without publication | Original state retained |
| Interrupted transaction, expected old/new bytes | Existing journal recovery | Complete only the recorded transaction |
| Unexpected bytes during recovery | Refuse | Preserve evidence and require operator investigation |

**Text Equivalent:** Distribution protects every non-native setting and other
projected file. Native Codex may change only the allowlisted UI/notice tables
without explicit reconciliation. Legacy migration needs a verifiable managed
baseline; version 2 stores a separate fingerprint for later upgrades. All admitted
changes use the existing private transaction/preimage machinery. Ambiguity blocks,
and no live owner configuration or private runtime state enters source evidence.
Owner: distribution maintainer. Update these tables when ownership, metadata or
recovery boundaries change.
