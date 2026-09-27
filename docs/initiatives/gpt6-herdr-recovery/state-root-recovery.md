# Standalone Recovery State-Root Routing

## Readiness Reopened

Host preflight found that the persistent supervisor sets the configured central
state root without setting XDG_DATA_HOME. The standalone restore helper currently
falls back to the legacy internal OpenCode store. The live central store contains
the expected conversations; the legacy store does not. No process was stopped.

Home: shell_auth_startup; existing Engineering Profile; elevated risk; Python,
Security and Cloud modules. Source ownership is one database-path fallback in the
recovery helper, its focused regression and context completion evidence. The
previous native identity and workload qualification remains historical evidence,
not proof of this independent environment-routing boundary.

## Contract And Behavior

Given DOTFILES_AI_STATE_ROOT is configured and XDG_DATA_HOME is absent, recovery
resolves `xdg/data/opencode/opencode.db` beneath that configured root. It never
selects the legacy internal database as a fallback. Given explicit XDG_DATA_HOME,
the existing override behavior is retained. Missing configured data fails closed,
retaining pending intent. No database, credential or session is moved or copied
by this correction. The no-central-root behavior remains unchanged.

Regression evidence uses a central fixture containing the expected session and
a populated legacy database containing no matching session, with XDG_DATA_HOME
removed. `--check` must succeed against the central store without mutating
recovery intent; explicit-XDG and missing-database cases remain covered.

Use the committed RUNTIME-MAINTENANCE applicability plan. Source-only correction
must pass scoped checks and merge through a normal PR before rollout readiness
is renewed. Do not change the supervisor environment as a one-off workaround for
the shared helper. Existing live processes, inventories and data remain intact.

## Visual Evidence

State/data-trust: required decision table; question: which database is authoritative?
Owner/source: shell-auth maintainer, Contract above; refresh when precedence changes.

| Inputs | Database selection |
|---|---|
| Configured root and explicit XDG data home | Existing explicit XDG path |
| Configured root without explicit XDG | Central root's xdg/data subtree |
| Selected database missing | Failure with pending intent retained; no legacy fallback |
| No configured root | Existing inactive recovery behavior |

**Text Equivalent:** Explicit data-home selection retains precedence. Otherwise,
a configured central root determines recovery storage. Missing selected storage
fails rather than switching to internal history; no configured root retains the
existing inactive behavior.

Boundary/interaction/schema/dependency-deployment/quantitative: not_applicable;
no other boundary, state schema, ordering, runtime topology or measured performance
claim changes in this localized source correction.
