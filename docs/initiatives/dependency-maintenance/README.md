# Dependency maintenance

Status: source preparation; no live activation qualified. Coordinator: distribution
maintainers. Authority: `MANIFEST.json` and the linked source contract. Method:
DBSCTR V3 revision 3.29.

## Outcome and ownership

Restore native template-based Worktrunk creation on macOS with 0.81.0, preserve
existing Linux/guest 0.80.0 routes, and make dependency maintenance discoverable.
Homebrew remains the macOS executable owner. The approved direction preserves
normal Worktrunk usage; custom `--path` is an explicit operator exception, not
the default allocation strategy or an automatically qualified agent route.

All source belongs to this repository. `dotfiles_ai_distribution` owns version
qualification, installation policy, dependency inventory, runbook and shared skill.
`opencode_control_plane` owns the adjacent rendered permission contract; its
bounded custom-path rule and tests travel in the Worktrunk source slice. No new
allocator, scheduler, updater daemon or fleet rollout is selected.

## Delivery

1. `worktrunk-source`: compatibility, failure diagnostics, Homebrew pin handling,
   non-upgrading reapply, native-route guidance, affected tests and CI.
2. `maintenance-source`: declared-dependency inventory and reusable update skill
   backed by `docs/UPDATES.md`. Existing native owners execute updates.
3. `mac-activation`: separately prepared exact target plan after source validation;
   preserve preimages, activate the coherent generation and verify installed state.

Source slices may be prepared independently but one primary serializes shared
files and validates their union. Neither source delivery nor a readiness receipt
authorizes live installation, reactivation, a service restart or removal.

The repair bootstrap may use an isolated checksum-verified official 0.80.0 binary
to create native checkouts through unchanged hooks. It does not replace the
Homebrew binary, alter activation or authorize later use as the installed default.
Retain bootstrap evidence privately. Discovery authority stays committed locally;
Build imports its complete changed-document closure from a clean approved-base
checkout after fresh receipt, preflight and exact launch approval.

## Evidence and remaining work

The original failure was reproduced: installed Worktrunk reports 0.81.0, while
the source/deployed validator and saved activation require 0.80.0. Homebrew had no
pinned packages. Native bootstrap with the official 0.80.0 archive passed the
existing pre-switch policy. These observations are not 0.81.0 qualification.

Managed DVC's offline backend/version check passed. Other version-only probes
responded; they establish executable availability, not service health or complete
dependency compatibility. Remaining inventory must distinguish source pins,
selected installed owners, running services, disabled features and unavailable
checks. No claim that all dependencies work is established here.

Source contract: [dependency maintenance](../../specs/dotfiles_ai_distribution/features/dependency-maintenance.md).
Live records and host-specific details remain private. Historical Initiative and
cycle evidence remains unchanged.

## Visual Evidence

Boundary, interaction, state, data/trust and deployment: required; use the ordered
transition table in the source contract. Schema: not applicable, no new runtime
schema. Quantitative: not applicable, no performance claim. Owner: distribution
maintainers; refresh when scope, ownership or activation ordering changes.
