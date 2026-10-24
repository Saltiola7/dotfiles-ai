# Continuous Validation Engineering Profile

| Field | Default |
|---|---|
| Deliverable | Portable standalone Python runner and versioned repository-adapter protocol for opt-in advisory validation during development |
| Accountable owner | Dotfiles owner; repository maintainers own check definitions and validation authorities |
| Languages/frameworks | Python `>=3.12`, Python Dagger SDK for Linux checks, native subprocess backend for required macOS checks, JSON requests/results/events |
| Applicable modules | Python and Security; Cloud is conditional on a later remote-compute slice |
| Runtime/platform support | Initial local Apple Silicon macOS controller, Linux Dagger execution on the explicitly selected platform, and native macOS validation; additional platforms require qualification |
| Compatibility | Versioned closed runner/adapter protocol; explicit snapshot/check/lane identities; preserve repository-owned test, affected-selection, coverage, and vulnerability authorities |
| Configuration | Default-off feature flag plus private per-worktree enrollment; distribution owns concrete settings, managed installation, and service configuration |
| Trust/data | Check definitions execute repository code only after enrollment. Source snapshots, logs, credentials, absolute paths, runtime/session identities, and observation storage remain private. Published documents and summaries are generic and sanitized |
| Agent boundary | Optional exact-session feedback through the owning control-plane adapter; check output is untrusted diagnostic data; native permissions and approvals remain authoritative |
| Gate boundary | Observations are advisory. No automatic Gate Ledger mutation, required-check acceptance, merge, delivery, or production authority |
| Release | Initial source slice creates no independently published package or image; later releasable artifacts require the Release gate |
| Deployment | Feature branch and draft pull request; separate targeted opt-in activation only after registered implementation, pinned-component checks, and real backend/session qualification |
| Operations | One host-wide admission budget, responsive foreground work, cancellation, recovery, bounded private retention, telemetry availability, disable and rollback evidence |
| Maintenance/retirement | Exact supported-version pins and capability reprobes, dependency/EOL intake through existing owners, safe disable/uninstall, and explicit private evidence retention/removal policy |
| Quality/security authorities | Repository-selected affected pytest, Python compilation, publication/instruction checks, declared coverage and vulnerability authorities, plus real Dagger/native/feedback runtime smokes for activation |
| Product Intent | Internal developer infrastructure; no separate product-facing document required for the initial slice |

The current slice is elevated risk because it runs repository-defined checks and
may submit diagnostic input to an existing agent session. The runner owns neither
DBSCTR lifecycle semantics nor native session transport nor managed installation.
Those integrations remain with their existing contexts.

Version pins must identify the Python runtime, runner, adapter, Dagger CLI, engine,
SDK, selected images/tools, and session transport capabilities. A documented CLI
surface is not end-to-end activation evidence. Missing or incompatible components
report unavailable; no automatic installation, version upgrade, or beta-feature
assumption is permitted.

## Visual Evidence

The [context specification](README.md#visual-evidence) owns canonical visuals and
Text Equivalents. Boundary, Interaction, State, Data/trust, Schema, and
Dependency/deployment are required and represented there through an ownership
flowchart and contract tables. Quantitative is not_applicable because this profile
makes no measured performance claim. The context owner updates those representations
when profile boundaries, identity, feedback, platform, or activation contracts change.
