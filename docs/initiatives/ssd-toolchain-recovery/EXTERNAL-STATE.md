# External-state recovery and remaining integrations

Home: dotfiles_ai_distribution; coordinate dotfiles shell configuration and
shell_auth_startup. Profile: docs/specs/dotfiles_ai_distribution/PROFILE.md.
Product Intent: docs/specs/dotfiles_ai_distribution/PRODUCT.md.
Risk: elevated. Scope: all session-related tools/services using relocated state,
including authentication, histories, Git/Worktrunk, DVC and local VM-backed services.

## Baseline and boundaries

Prior private recovery evidence records exact conversation/pane recovery, a corrected
personal guest mount, service-account and desktop MCP authentication checks, and
some interpreter/dependency checks. These are bounded observations, not full health.
Refresh affected evidence after deployment without replaying completed recovery.
State root and replacement-volume identity are machine-local values, never public
constants. Preserve original recovery inventories, archives and uncertain operations.

## Acceptance

| Given | When | Required outcome |
|---|---|---|
| Valid external volume | Tool/service starts | Intended state and credential boundary selected; functional probe succeeds |
| Missing/wrong volume | Startup/probe runs | Fail clearly before writes; no empty fallback profile |
| Intentionally removed PPC DVC data | Inventory runs | Classified as intentional, not clone damage; no automatic hydration |
| Missing Git worktree registration/path | Native inventory runs | Distinguish absent checkout, broken gitdir and retained work; preserve evidence |
| Optional auth unavailable | Shell starts | Remains usable; integration reports unavailable without secret output |
| Existing conversations and histories | Runtime is repaired/restarted | Exact identities and correct local databases remain accessible |

## Evidence matrix and ownership

Inventory each known state-dependent tool as verified, failed, unavailable,
intentional omission or not yet checked. Record command, time, source version,
selected state location and bounded result privately. Public findings contain
sanitized categories only. A version check alone never proves state access.

- Git/Worktrunk: native worktree inventory, gitdir/backlink checks, non-destructive
  Git reads. Do not prune historical temporary registrations or repair ambiguous
  ownership automatically. Investigate the known SDS worktree inventory failure.
- DVC: configuration/cache identity, metadata and requested-target availability;
  no full pull, shared-cache GC or copy fallback. DVC upload remains separately
  approved if metadata/output identities actually change.
- Atuin/local PostgreSQL: service health and bounded connectivity inside the owning
  guest; do not print history bodies or query protected knowledge contents.
- 1Password: independently verify managed CLI broker, desktop MCP and any existing
  environment-file consumers. List names/status only; no credential export.
- Remaining credential-backed developer tools: discover configured use from source,
  select a read-only capability check and keep provider/account details local.
- Herdr: external volume and signed-host ownership belong to HERDR-RECOVERY.md;
  guest services belong to GUESTS.md; executable migration to NATIVE-UPDATES.md.

Source anchors: dot_common_profile.tmpl, op-session/secret helpers, sandbox-vm,
worktree-dvc-setup and context operations docs. Validate touched source with existing
affected rendering, auth, native workspace and DVC tests; live checks use native
tools without alternate transports when permission is denied.

Kernel/review/deploy/operate/maintain gates required for repairs; release N/A.
Inventory alone may finish read-only, but any behavior repair requires its owning
context's committed plan and qualification. Remaining gap: exhaustive consumer
matrix and exact repair ownership. No blanket credential/functionality claim.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: evidence/ownership matrix above |
| Interaction | not_applicable: repairs follow inventory and boundary-local qualification |
| State | required: acceptance table |
| Data/trust | not_applicable: existing state remains local; transport exclusions explicit |
| Schema | not_applicable: existing metadata formats reused |
| Dependency/deployment | required: WORKSTREAMS.md activation table |
| Quantitative | not_applicable: no invented coverage percentage |

**Text Equivalent:** each state consumer needs functional boundary-local evidence;
missing state cannot trigger fallback writes or wholesale restore. Intentional
omissions are retained and ambiguous Git/DVC ownership is reported. Canonical source:
this contract. Owner: distribution maintainer; update on consumer/boundary changes.
